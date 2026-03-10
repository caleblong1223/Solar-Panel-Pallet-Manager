using System.Net;
using System.Text;
using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using Xunit;

namespace PalletManager.ParityTests.Flows;

public sealed class NonCoreFlowsParityTests
{
    [Fact]
    public async Task Customers_SaveWithoutDisplayName_ShowsParityValidationMessage()
    {
        var vm = new CustomersViewModel(new FakeApiClient(), new FixedAuthService(), new InMemoryCacheRepository());
        vm.DisplayName = "   ";

        await vm.SaveAsync();

        Assert.Equal("Display name is required.", vm.StatusMessage);
    }

    [Fact]
    public async Task Import_SearchWithBlankSerial_ShowsParityValidationMessage()
    {
        var vm = new ImportSimulatorViewModel(
            new FakeApiClient(),
            new FixedAuthService(),
            new FixedSettingsService(),
            new StaticHttpClientFactory(new HttpResponseMessage(HttpStatusCode.OK)));

        vm.SearchSerial = "   ";
        await vm.SearchAsync();

        Assert.Equal("Enter a serial to search.", vm.StatusMessage);
    }

    [Fact]
    public async Task Exports_SearchWithInvalidPalletNumber_ShowsParityValidationMessage()
    {
        var vm = new ExportsLibraryViewModel(
            new FakeApiClient(),
            new FixedAuthService(),
            new FixedSettingsService(),
            new RecordingLauncher());
        vm.PalletNumber = "ABC";

        await vm.SearchAsync();

        Assert.Equal("Pallet number must be a positive number.", vm.StatusMessage);
    }

    [Fact]
    public async Task Settings_TestPrimaryProbeFailure_DoesNotPersistTemporaryEndpoint()
    {
        var settings = new FixedSettingsService();
        var connectivity = new ThrowingConnectivityService();
        var vm = new SettingsViewModel(settings, connectivity, new StubSyncEngine());
        vm.PrimaryApiBaseUrl = "http://temporary.test";

        await vm.TestPrimaryAsync();

        Assert.Equal("http://api.test/api/v1", settings.Current.PrimaryApiBaseUrl);
        Assert.Contains("failed", vm.StatusMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Customers_CreateSearchArchive_JourneyMaintainsParityState()
    {
        var api = new StatefulCustomersApiClient();
        var vm = new CustomersViewModel(api, new FixedAuthService(), new InMemoryCacheRepository());

        vm.DisplayName = "North Ridge";
        vm.Email = "north@example.com";
        await vm.SaveAsync();
        Assert.NotEmpty(vm.Customers);
        Assert.Contains(vm.Customers, c => c.DisplayName == "North Ridge");

        vm.Search = "North";
        await vm.RefreshAsync();
        var created = Assert.Single(vm.Customers);
        Assert.Equal("North Ridge", created.DisplayName);

        await vm.ArchiveAsync(created.Id);
        Assert.Contains("Loaded 0 customer(s) from API.", vm.StatusMessage);

        await vm.RefreshAsync();
        Assert.Empty(vm.Customers);
        vm.ShowInactive = true;
        await vm.RefreshAsync();
        Assert.Single(vm.Customers);
    }

    [Fact]
    public async Task Import_UploadWhenAllCandidatesFail_ShowsFailedSummary()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"sim-fail-{Guid.NewGuid():N}.csv");
        await File.WriteAllTextAsync(tempFile, "SerialNo,Pm\nSN-1,410");
        try
        {
            var vm = new ImportSimulatorViewModel(
                new FakeApiClient(),
                new FixedAuthService(),
                new FixedSettingsService(),
                new StaticHttpClientFactory(new HttpResponseMessage(HttpStatusCode.InternalServerError)
                {
                    Content = new StringContent("fail", Encoding.UTF8, "text/plain"),
                }));
            vm.UploadPathsInput = tempFile;

            await vm.UploadAsync();

            var row = Assert.Single(vm.UploadResults);
            Assert.Equal("failed", row.Status);
            Assert.Contains("Imported 0 file(s), failed 1.", vm.StatusMessage);
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
    public async Task Exports_SearchWithInvalidDate_OmitsDateFiltersFromQuery()
    {
        var api = new CapturingExportsApiClient();
        var vm = new ExportsLibraryViewModel(
            api,
            new FixedAuthService(),
            new FixedSettingsService(),
            new RecordingLauncher());

        vm.PalletNumber = "5";
        vm.CreatedFrom = "not-a-date";
        vm.CreatedTo = "2026-03-10";
        await vm.SearchAsync();

        Assert.Contains("pallet_id=5", api.LastGetPath);
        Assert.DoesNotContain("created_from=", api.LastGetPath, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("created_to=2026-03-10T23%3A59%3A59", api.LastGetPath);
    }

    [Fact]
    public async Task Settings_SaveThenPrimaryTestFailure_PreservesSavedConfiguration()
    {
        var settings = new FixedSettingsService();
        var connectivity = new ThrowingConnectivityService();
        var vm = new SettingsViewModel(settings, connectivity, new StubSyncEngine());

        vm.PrimaryApiBaseUrl = "http://saved-primary.test";
        vm.FallbackApiBaseUrl = "http://saved-fallback.test";
        await vm.SaveAsync();
        Assert.Equal("http://saved-primary.test/api/v1", settings.Current.PrimaryApiBaseUrl);

        vm.PrimaryApiBaseUrl = "http://temporary.test";
        await vm.TestPrimaryAsync();

        Assert.Equal("http://saved-primary.test/api/v1", settings.Current.PrimaryApiBaseUrl);
    }

    private sealed class FakeApiClient : IApiClient
    {
        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            const string json = """{"customers":[],"exports":[],"results":[]}""";
            var result = JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            return Task.FromResult(result!);
        }

        public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            Task.FromResult(typeof(T) == typeof(object) ? (T)(object)new object() : JsonSerializer.Deserialize<T>("{}")!);

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default) =>
            Task.FromResult(typeof(T) == typeof(object) ? (T)(object)new object() : JsonSerializer.Deserialize<T>("{}")!);

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            Task.CompletedTask;
    }

    private sealed class StatefulCustomersApiClient : IApiClient
    {
        private readonly List<Customer> _rows = new();
        private int _nextId = 1;

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (!path.StartsWith("/customers?", StringComparison.OrdinalIgnoreCase))
            {
                throw new NotSupportedException(path);
            }

            var includeInactive = !path.Contains("is_active=true", StringComparison.OrdinalIgnoreCase);
            var search = ReadQueryValue(path, "search");
            IEnumerable<Customer> rows = _rows;
            if (!includeInactive)
            {
                rows = rows.Where(r => r.IsActive);
            }

            if (!string.IsNullOrWhiteSpace(search))
            {
                rows = rows.Where(r => r.DisplayName.Contains(search, StringComparison.OrdinalIgnoreCase));
            }

            var payload = new
            {
                customers = rows.Select(r => new
                {
                    id = r.Id,
                    display_name = r.DisplayName,
                    contact_name = r.ContactName,
                    business_name = r.BusinessName,
                    email = r.Email,
                    phone = r.Phone,
                    address = r.Address,
                    city = r.City,
                    state = r.State,
                    zip_code = r.ZipCode,
                    is_active = r.IsActive,
                    created_at = r.CreatedAtUtc ?? DateTime.UtcNow,
                }).ToArray(),
            };
            var json = JsonSerializer.Serialize(payload);
            var result = JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            return Task.FromResult(result!);
        }

        public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        {
            if (!string.Equals(path, "/customers", StringComparison.OrdinalIgnoreCase))
            {
                throw new NotSupportedException(path);
            }

            var payload = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(JsonSerializer.Serialize(body))!;
            var displayName = payload.TryGetValue("display_name", out var n) ? n.GetString() ?? string.Empty : string.Empty;
            _rows.Add(new Customer
            {
                Id = _nextId++,
                DisplayName = displayName,
                Email = payload.TryGetValue("email", out var e) && e.ValueKind == JsonValueKind.String ? e.GetString() : null,
                IsActive = payload.TryGetValue("is_active", out var a) && a.ValueKind == JsonValueKind.True,
                CreatedAtUtc = DateTime.UtcNow,
            });
            return Task.FromResult(typeof(T) == typeof(object) ? (T)(object)new object() : JsonSerializer.Deserialize<T>("{}")!);
        }

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        {
            if (!path.StartsWith("/customers/", StringComparison.OrdinalIgnoreCase))
            {
                throw new NotSupportedException(path);
            }

            var id = int.Parse(path.Split('/').Last());
            var row = _rows.First(r => r.Id == id);
            row.IsActive = false;
            return Task.CompletedTask;
        }

        private static string ReadQueryValue(string path, string key)
        {
            var query = path.Split('?', 2).Length == 2 ? path.Split('?', 2)[1] : string.Empty;
            var entries = query.Split('&', StringSplitOptions.RemoveEmptyEntries);
            foreach (var entry in entries)
            {
                var parts = entry.Split('=', 2);
                if (parts.Length == 2 && string.Equals(parts[0], key, StringComparison.OrdinalIgnoreCase))
                {
                    return Uri.UnescapeDataString(parts[1]);
                }
            }

            return string.Empty;
        }
    }

    private sealed class CapturingExportsApiClient : IApiClient
    {
        public string LastGetPath { get; private set; } = string.Empty;

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            LastGetPath = path;
            const string json = """{"total":0,"exports":[]}""";
            var result = JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            return Task.FromResult(result!);
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
        public RuntimeSettings Current { get; private set; } = new()
        {
            PrimaryApiBaseUrl = "http://api.test/api/v1",
            FallbackApiBaseUrl = "http://fallback.test/api/v1",
            LockToLocalBackend = false,
        };

        public Task<RuntimeSettings> GetAsync(CancellationToken ct = default) => Task.FromResult(Current);
        public Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default)
        {
            Current = settings;
            return Task.FromResult(settings);
        }

        public IObservable<RuntimeSettings> Changes { get; } = new EmptyObservable<RuntimeSettings>();
    }

    private sealed class ThrowingConnectivityService : IConnectivityService
    {
        public Task<ConnectivitySnapshot> ProbeAsync(CancellationToken ct = default) =>
            throw new InvalidOperationException("Probe failed.");

        public IObservable<ConnectivitySnapshot> StatusChanges { get; } = new EmptyObservable<ConnectivitySnapshot>();
    }

    private sealed class StubSyncEngine : ISyncEngine
    {
        public IObservable<SyncState> State { get; } = new EmptyObservable<SyncState>();
        public Task TriggerNowAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class RecordingLauncher : ISystemLauncher
    {
        public Task OpenAsync(string target, CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class StaticHttpClientFactory : IHttpClientFactory
    {
        private readonly HttpResponseMessage _response;

        public StaticHttpClientFactory(HttpResponseMessage response)
        {
            _response = response;
        }

        public HttpClient CreateClient(string name) => new(new StaticHandler(_response));
    }

    private sealed class StaticHandler : HttpMessageHandler
    {
        private readonly HttpResponseMessage _response;

        public StaticHandler(HttpResponseMessage response)
        {
            _response = response;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var clone = new HttpResponseMessage(_response.StatusCode)
            {
                Content = _response.Content is null ? null : new StringContent(_response.Content.ReadAsStringAsync().GetAwaiter().GetResult(), Encoding.UTF8, "application/json"),
            };
            return Task.FromResult(clone);
        }
    }

    private sealed class InMemoryCacheRepository : ILocalCacheRepository
    {
        public Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<Customer>)Array.Empty<Customer>());
        public Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<Pallet>)Array.Empty<Pallet>());
        public Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<ExportRecord>)Array.Empty<ExportRecord>());
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
