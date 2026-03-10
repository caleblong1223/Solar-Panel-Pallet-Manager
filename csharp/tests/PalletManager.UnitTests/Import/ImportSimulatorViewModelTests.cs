using System.Net;
using System.Text;
using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using Xunit;

namespace PalletManager.UnitTests.Import;

public sealed class ImportSimulatorViewModelTests
{
    [Fact]
    public async Task UploadAsync_WhenNoValidFiles_SetsWarningMessage()
    {
        var vm = CreateViewModel(new FakeApiClient(), new RoutingHttpClientFactory(_ => new HttpResponseMessage(HttpStatusCode.OK)));
        vm.UploadPathsInput = "/tmp/does-not-exist.csv";

        await vm.UploadAsync();

        Assert.Equal("Choose at least one simulator file first.", vm.StatusMessage);
        Assert.Empty(vm.UploadResults);
    }

    [Fact]
    public async Task UploadAsync_UsesFallbackCandidateAfterPrimaryFailure()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"sim-{Guid.NewGuid():N}.csv");
        await File.WriteAllTextAsync(tempFile, "SerialNo,Pm\nSN-1,410");
        try
        {
            var factory = new RoutingHttpClientFactory(request =>
            {
                if (request.RequestUri?.Host == "bad.test")
                {
                    return new HttpResponseMessage(HttpStatusCode.InternalServerError)
                    {
                        Content = new StringContent("failed"),
                    };
                }

                var json = """{"id":7,"status":"completed","rows_total":1,"rows_imported":1,"rows_rejected":0}""";
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json"),
                };
            });

            var vm = CreateViewModel(new FakeApiClient(), factory);
            vm.UploadPathsInput = tempFile;

            await vm.UploadAsync();

            var row = Assert.Single(vm.UploadResults);
            Assert.Equal(7, row.BatchId);
            Assert.Equal("completed", row.Status);
            Assert.Equal("Imported 1 file(s), failed 0.", vm.StatusMessage);
        }
        finally
        {
            if (File.Exists(tempFile))
            {
                File.Delete(tempFile);
            }
        }
    }

    [Fact]
    public async Task SearchAsync_OnlyIncludesSimPanelResults()
    {
        var api = new FakeApiClient
        {
            SearchResponseJson = """
            {
              "results": [
                { "source": "pallet_item", "serial": "SN-X" },
                { "source": "sim_panel", "serial": "SN-SIM-1", "sim_test_timestamp": "2026-03-10T09:00:00Z", "sim_watts": 410.5 }
              ]
            }
            """,
        };

        var vm = CreateViewModel(api, new RoutingHttpClientFactory(_ => new HttpResponseMessage(HttpStatusCode.OK)));
        vm.SearchSerial = "SN";

        await vm.SearchAsync();

        var row = Assert.Single(vm.SearchResults);
        Assert.Equal("SN-SIM-1", row.Serial);
        Assert.Contains("Pm: 410.50", row.ElectricalSummary);
    }

    private static ImportSimulatorViewModel CreateViewModel(IApiClient apiClient, IHttpClientFactory httpClientFactory)
    {
        return new ImportSimulatorViewModel(
            apiClient,
            new FixedAuthService(),
            new FixedSettingsService(),
            httpClientFactory);
    }

    private sealed class FixedAuthService : IAuthService
    {
        public Task<string?> GetTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
        public Task SetTokenAsync(string? token, CancellationToken ct = default) => Task.CompletedTask;
        public Task ClearSessionAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class FixedSettingsService : IRuntimeSettingsService
    {
        public Task<RuntimeSettings> GetAsync(CancellationToken ct = default) => Task.FromResult(new RuntimeSettings
        {
            PrimaryApiBaseUrl = "http://bad.test/api/v1",
            FallbackApiBaseUrl = "http://good.test/api/v1",
            LockToLocalBackend = false,
        });

        public Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default) =>
            Task.FromResult(settings);

        public IObservable<RuntimeSettings> Changes { get; } = new EmptyObservable<RuntimeSettings>();
    }

    private sealed class FakeApiClient : IApiClient
    {
        public string SearchResponseJson { get; set; } = """{"results":[]}""";

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/barcodes/search?", StringComparison.OrdinalIgnoreCase))
            {
                var result = JsonSerializer.Deserialize<T>(SearchResponseJson, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                return Task.FromResult(result!);
            }

            throw new NotSupportedException(path);
        }

        public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);
    }

    private sealed class RoutingHttpClientFactory : IHttpClientFactory
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _route;

        public RoutingHttpClientFactory(Func<HttpRequestMessage, HttpResponseMessage> route)
        {
            _route = route;
        }

        public HttpClient CreateClient(string name) => new(new RoutingHandler(_route));
    }

    private sealed class RoutingHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _route;

        public RoutingHandler(Func<HttpRequestMessage, HttpResponseMessage> route)
        {
            _route = route;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromResult(_route(request));
        }
    }

    private sealed class EmptyObservable<T> : IObservable<T>
    {
        public IDisposable Subscribe(IObserver<T> observer) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
