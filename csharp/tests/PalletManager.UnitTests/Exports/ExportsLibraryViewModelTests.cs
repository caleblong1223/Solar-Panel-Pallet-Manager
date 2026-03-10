using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using Xunit;

namespace PalletManager.UnitTests.Exports;

public sealed class ExportsLibraryViewModelTests
{
    [Fact]
    public async Task SearchAsync_InvalidPalletNumber_SetsValidationMessage()
    {
        var vm = CreateViewModel(new FakeApiClient(), new RecordingLauncher());
        vm.PalletNumber = "abc";

        await vm.SearchAsync();

        Assert.Equal("Pallet number must be a positive number.", vm.StatusMessage);
        Assert.Empty(vm.Results);
    }

    [Fact]
    public async Task SearchAsync_MapsResultsAndSetsStatus()
    {
        var api = new FakeApiClient();
        var vm = CreateViewModel(api, new RecordingLauncher());
        vm.PalletNumber = "12";
        vm.TemplateType = "200WT";
        vm.CreatedFrom = "2026-03-01";
        vm.CreatedTo = "2026-03-10";

        await vm.SearchAsync();

        Assert.Single(vm.Results);
        Assert.Contains("pallet_id=12", api.LastGetPath);
        Assert.Contains("template_type=200WT", api.LastGetPath);
        Assert.Contains("created_from=2026-03-01T00%3A00%3A00", api.LastGetPath);
        Assert.Contains("created_to=2026-03-10T23%3A59%3A59", api.LastGetPath);
        Assert.Equal("Found 1 export(s).", vm.StatusMessage);
    }

    [Fact]
    public async Task OpenExportAsync_UsesConfiguredBaseUrl()
    {
        var launcher = new RecordingLauncher();
        var vm = CreateViewModel(new FakeApiClient(), launcher);

        await vm.OpenExportAsync(55, "pdf");

        var target = Assert.Single(launcher.Targets);
        Assert.Equal("http://api.test/api/v1/exports/55/download?format=pdf", target);
    }

    private static ExportsLibraryViewModel CreateViewModel(FakeApiClient apiClient, RecordingLauncher launcher)
    {
        return new ExportsLibraryViewModel(
            apiClient,
            new FixedAuthService(),
            new FixedSettingsService(),
            launcher);
    }

    private sealed class FakeApiClient : IApiClient
    {
        public string LastGetPath { get; private set; } = string.Empty;

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            LastGetPath = path;
            if (path.StartsWith("/exports?", StringComparison.OrdinalIgnoreCase))
            {
                const string json = """
                {
                  "total": 1,
                  "exports": [
                    {
                      "id": 99,
                      "pallet_id": 12,
                      "template_type": "200WT",
                      "file_name": "export-99.pdf",
                      "size_bytes": 2048,
                      "created_at": "2026-03-10T10:00:00Z"
                    }
                  ]
                }
                """;
                var result = JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
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

    private sealed class FixedAuthService : IAuthService
    {
        public Task<string?> GetTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
        public Task SetTokenAsync(string? token, CancellationToken ct = default) => Task.CompletedTask;
        public Task ClearSessionAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class FixedSettingsService : IRuntimeSettingsService
    {
        private readonly RuntimeSettings _settings = new()
        {
            PrimaryApiBaseUrl = "http://api.test/api/v1",
            FallbackApiBaseUrl = null,
            LockToLocalBackend = false,
        };

        public Task<RuntimeSettings> GetAsync(CancellationToken ct = default) => Task.FromResult(_settings);
        public Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default) => Task.FromResult(settings);
        public IObservable<RuntimeSettings> Changes { get; } = new EmptyObservable<RuntimeSettings>();
    }

    private sealed class RecordingLauncher : ISystemLauncher
    {
        public List<string> Targets { get; } = new();

        public Task OpenAsync(string target, CancellationToken ct = default)
        {
            Targets.Add(target);
            return Task.CompletedTask;
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
