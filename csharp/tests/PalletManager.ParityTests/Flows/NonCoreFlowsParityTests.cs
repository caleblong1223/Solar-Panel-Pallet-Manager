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
    public async Task Import_UploadWithMixedResults_ShowsPartialFailureSummary()
    {
        var okPath = Path.Combine(Path.GetTempPath(), $"ok-{Guid.NewGuid():N}.csv");
        var failPath = Path.Combine(Path.GetTempPath(), $"fail-{Guid.NewGuid():N}.csv");
        await File.WriteAllTextAsync(okPath, "SerialNo,Pm\nSN-OK,410");
        await File.WriteAllTextAsync(failPath, "SerialNo,Pm\nSN-FAIL,409");
        try
        {
            var vm = new ImportSimulatorViewModel(
                new FakeApiClient(),
                new FixedAuthService(),
                new FixedSettingsService(),
                new RoutingHttpClientFactory(request =>
                {
                    var body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult() ?? string.Empty;
                    if (body.Contains(Path.GetFileName(okPath), StringComparison.OrdinalIgnoreCase))
                    {
                        return new HttpResponseMessage(HttpStatusCode.OK)
                        {
                            Content = new StringContent("""{"id":41,"status":"completed","rows_total":1,"rows_imported":1,"rows_rejected":0}""", Encoding.UTF8, "application/json"),
                        };
                    }

                    return new HttpResponseMessage(HttpStatusCode.InternalServerError)
                    {
                        Content = new StringContent("failed", Encoding.UTF8, "text/plain"),
                    };
                }));
            vm.UploadPathsInput = $"{okPath}\n{failPath}";

            await vm.UploadAsync();

            Assert.Equal(2, vm.UploadResults.Count);
            Assert.Single(vm.UploadResults, r => r.BatchId.HasValue);
            Assert.Single(vm.UploadResults, r => !string.IsNullOrWhiteSpace(r.Error));
            Assert.Equal("Imported 1 file(s), failed 1.", vm.StatusMessage);
        }
        finally
        {
            if (File.Exists(okPath)) File.Delete(okPath);
            if (File.Exists(failPath)) File.Delete(failPath);
        }
    }

    [Fact]
    public async Task Import_SearchNoResults_ShowsParityNoDataMessage()
    {
        var vm = new ImportSimulatorViewModel(
            new FakeApiClient(),
            new FixedAuthService(),
            new FixedSettingsService(),
            new StaticHttpClientFactory(new HttpResponseMessage(HttpStatusCode.OK)));
        vm.SearchSerial = "SN-404";

        await vm.SearchAsync();

        Assert.True(vm.HasSearched);
        Assert.Empty(vm.SearchResults);
        Assert.Equal("No Sun Simulator data found for this serial.", vm.StatusMessage);
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
    public async Task Exports_OpenPdfAndXlsx_UsesSystemLauncherEndpoints()
    {
        var launcher = new RecordingLauncher();
        var vm = new ExportsLibraryViewModel(
            new CapturingExportsApiClient(),
            new FixedAuthService(),
            new FixedSettingsService(),
            launcher);

        await vm.OpenExportAsync(9001, "pdf");
        await vm.OpenExportAsync(9001, "xlsx");

        Assert.Equal(2, launcher.Targets.Count);
        Assert.Equal("http://api.test/api/v1/exports/9001/download?format=pdf", launcher.Targets[0]);
        Assert.Equal("http://api.test/api/v1/exports/9001/download?format=xlsx", launcher.Targets[1]);
    }

    [Fact]
    public async Task Exports_SearchNoResults_ShowsEmptyStateMessage()
    {
        var vm = new ExportsLibraryViewModel(
            new CapturingExportsApiClient(),
            new FixedAuthService(),
            new FixedSettingsService(),
            new RecordingLauncher());

        await vm.SearchAsync();

        Assert.Empty(vm.Results);
        Assert.Equal("No exports found for the given filters.", vm.StatusMessage);
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

    [Fact]
    public async Task Customers_OfflineFallback_RespectsSearchAndInactiveToggle()
    {
        var api = new FakeApiClient { ThrowOnCustomersList = true };
        var cache = new InMemoryCacheRepository();
        await cache.UpsertCustomersAsync(new[]
        {
            new Customer { Id = 1, DisplayName = "Alpha Solar", IsActive = true },
            new Customer { Id = 2, DisplayName = "Beta Archived", IsActive = false },
        });
        var vm = new CustomersViewModel(api, new FixedAuthService(), cache);

        vm.Search = "Alpha";
        vm.ShowInactive = false;
        await vm.RefreshAsync();
        Assert.Single(vm.Customers);
        Assert.Equal("Using cached customers (offline).", vm.StatusMessage);

        vm.Search = "Beta";
        vm.ShowInactive = true;
        await vm.RefreshAsync();
        Assert.Single(vm.Customers);
        Assert.Equal("Beta Archived", vm.Customers[0].DisplayName);
    }

    [Fact]
    public async Task SettingsAndSyncIssues_ManualTriggerAndRetryDiscard_MaintainParityFlow()
    {
        var syncEngine = new RecordingSyncEngine();
        var settings = new SettingsViewModel(new FixedSettingsService(), new ThrowingConnectivityService(), syncEngine);
        syncEngine.Publish(new SyncState { Syncing = true, PendingCount = 4, NeedsReviewCount = 2, FailedCount = 1 });
        Assert.Contains("Pending: 4", settings.SyncSummary);
        Assert.Contains("Review: 2", settings.SyncSummary);
        await settings.TriggerSyncNowAsync();
        Assert.Equal(1, syncEngine.TriggerNowCalls);

        var outbox = new InMemoryOutboxRepository();
        var opId = Guid.NewGuid();
        await outbox.EnqueueAsync(new OutboxOperation
        {
            OpId = opId,
            OpType = OperationType.PalletItemAdd,
            PayloadJson = """{"pallet_id":42,"serial":"SN-RETRY"}""",
            State = OutboxState.NeedsReview,
            AttemptCount = 2,
            LastError = "conflict",
            LastErrorCode = "SIM_DATA_REQUIRED",
            CreatedAtUtc = DateTime.UtcNow,
            UpdatedAtUtc = DateTime.UtcNow,
        });

        var syncIssues = new SyncIssuesViewModel(outbox, syncEngine);
        await syncIssues.RefreshAsync();
        Assert.Single(syncIssues.NeedsReview);

        await syncIssues.RetryOperationAsync(opId);
        Assert.Equal(2, syncEngine.TriggerNowCalls);
        Assert.Empty(syncIssues.NeedsReview);
        var remaining = Assert.Single(await outbox.ListAsync());
        Assert.Equal(OutboxState.Pending, remaining.State);
        Assert.Null(remaining.LastError);

        await syncIssues.RefreshAsync();
        Assert.Empty(syncIssues.PendingErrors);
        await syncIssues.DiscardOperationAsync(opId);
        Assert.Empty(await outbox.ListAsync());
    }

    private sealed class FakeApiClient : IApiClient
    {
        public bool ThrowOnCustomersList { get; set; }

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/customers?", StringComparison.OrdinalIgnoreCase))
            {
                if (ThrowOnCustomersList)
                {
                    throw new InvalidOperationException("offline");
                }
            }

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

    private sealed class FixedAuthService : IApiTokenProvider
    {
        public Task<string?> GetBearerTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
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
        public List<string> Targets { get; } = new();

        public Task OpenAsync(string target, CancellationToken ct = default)
        {
            Targets.Add(target);
            return Task.CompletedTask;
        }
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
        private readonly List<Customer> _customers = new();

        public Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default)
        {
            _customers.Clear();
            _customers.AddRange(customers);
            return Task.CompletedTask;
        }

        public Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default)
        {
            IEnumerable<Customer> rows = _customers;
            if (!includeInactive)
            {
                rows = rows.Where(c => c.IsActive);
            }

            if (!string.IsNullOrWhiteSpace(search))
            {
                rows = rows.Where(c => c.DisplayName.Contains(search, StringComparison.OrdinalIgnoreCase));
            }

            return Task.FromResult((IReadOnlyList<Customer>)rows.ToList());
        }
        public Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<Pallet>)Array.Empty<Pallet>());
        public Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<ExportRecord>)Array.Empty<ExportRecord>());
    }

    private sealed class InMemoryOutboxRepository : IOutboxRepository
    {
        private readonly List<OutboxOperation> _operations = new();

        public Task<IReadOnlyList<OutboxOperation>> ListAsync(CancellationToken ct = default) =>
            Task.FromResult((IReadOnlyList<OutboxOperation>)_operations.ToList());

        public Task EnqueueAsync(OutboxOperation operation, CancellationToken ct = default)
        {
            _operations.Add(operation);
            return Task.CompletedTask;
        }

        public Task UpdateAsync(OutboxOperation operation, CancellationToken ct = default)
        {
            var index = _operations.FindIndex(o => o.OpId == operation.OpId);
            if (index >= 0)
            {
                _operations[index] = operation;
            }

            return Task.CompletedTask;
        }

        public Task RemoveAsync(Guid opId, CancellationToken ct = default)
        {
            _operations.RemoveAll(o => o.OpId == opId);
            return Task.CompletedTask;
        }

        public Task MarkNeedsReviewAsync(Guid opId, string reason, string? errorCode, CancellationToken ct = default)
        {
            var op = _operations.FirstOrDefault(o => o.OpId == opId);
            if (op is not null)
            {
                op.State = OutboxState.NeedsReview;
                op.LastError = reason;
                op.LastErrorCode = errorCode;
            }

            return Task.CompletedTask;
        }
    }

    private sealed class RecordingSyncEngine : ISyncEngine
    {
        private readonly SimpleSubject<SyncState> _subject = new();
        public int TriggerNowCalls { get; private set; }
        public IObservable<SyncState> State => _subject;

        public Task TriggerNowAsync(CancellationToken ct = default)
        {
            TriggerNowCalls += 1;
            return Task.CompletedTask;
        }

        public void Publish(SyncState state) => _subject.Publish(state);
    }

    private sealed class SimpleSubject<T> : IObservable<T>
    {
        private readonly List<IObserver<T>> _observers = new();

        public IDisposable Subscribe(IObserver<T> observer)
        {
            _observers.Add(observer);
            return new Subscription(_observers, observer);
        }

        public void Publish(T value)
        {
            foreach (var observer in _observers.ToArray())
            {
                observer.OnNext(value);
            }
        }

        private sealed class Subscription : IDisposable
        {
            private readonly List<IObserver<T>> _observers;
            private readonly IObserver<T> _observer;

            public Subscription(List<IObserver<T>> observers, IObserver<T> observer)
            {
                _observers = observers;
                _observer = observer;
            }

            public void Dispose()
            {
                _observers.Remove(_observer);
            }
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
