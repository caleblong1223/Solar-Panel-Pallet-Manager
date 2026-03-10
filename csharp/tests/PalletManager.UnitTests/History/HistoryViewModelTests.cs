using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using Xunit;

namespace PalletManager.UnitTests.History;

public sealed class HistoryViewModelTests
{
    [Fact]
    public async Task MergeSelectedPalletsAsync_WithFewerThanTwoSelected_SetsWarningMessage()
    {
        var launcher = new RecordingSystemLauncher();
        var vm = CreateViewModel(launcher, new FakeApiClient(), new InMemoryCacheRepository());
        vm.VisiblePallets.Add(new HistoryPalletRow(1, 101, "200WT", 1, DateTime.Now, "completed", isSelected: true));

        await vm.MergeSelectedPalletsAsync();

        Assert.Equal("Select at least 2 pallets to merge.", vm.StatusMessage);
        Assert.Empty(launcher.Targets);
    }

    [Fact]
    public async Task MergeSelectedPalletsAsync_WithInsufficientExports_SetsWarningMessage()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient();
        api.ExportMap[10] = new[] { 7001 };
        api.ExportMap[11] = Array.Empty<int>();

        var vm = CreateViewModel(launcher, api, new InMemoryCacheRepository());
        vm.VisiblePallets.Add(new HistoryPalletRow(10, 101, "200WT", 1, DateTime.Now, "completed", isSelected: true));
        vm.VisiblePallets.Add(new HistoryPalletRow(11, 102, "200WT", 1, DateTime.Now, "completed", isSelected: true));

        await vm.MergeSelectedPalletsAsync();

        Assert.Equal("Need at least 2 pallets with exports to merge.", vm.StatusMessage);
        Assert.Empty(launcher.Targets);
    }

    [Fact]
    public async Task MergeSelectedPalletsAsync_UsesDistinctExportIds_AndOpensMergeEndpoint()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient();
        api.ExportMap[21] = new[] { 9001 };
        api.ExportMap[22] = new[] { 9002 };
        api.ExportMap[23] = new[] { 9002 };

        var vm = CreateViewModel(launcher, api, new InMemoryCacheRepository());
        vm.VisiblePallets.Add(new HistoryPalletRow(21, 201, "220WT", 1, DateTime.Now, "completed", isSelected: true));
        vm.VisiblePallets.Add(new HistoryPalletRow(22, 202, "220WT", 1, DateTime.Now, "completed", isSelected: true));
        vm.VisiblePallets.Add(new HistoryPalletRow(23, 203, "220WT", 1, DateTime.Now, "completed", isSelected: true));

        await vm.MergeSelectedPalletsAsync();

        var target = Assert.Single(launcher.Targets);
        Assert.Equal("http://api.test/api/v1/exports/merge-pdf?export_id=9001&export_id=9002", target);
        Assert.Equal("Opened merged PDF for 2 exports.", vm.StatusMessage);
    }

    [Fact]
    public async Task ApplyFilters_ExactModeRequiresExactSerial_NonExactAllowsContains()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient();
        var cache = new InMemoryCacheRepository();
        var vm = CreateViewModel(launcher, api, cache);

        await vm.RefreshAsync();
        Assert.NotEmpty(vm.VisiblePallets);

        vm.Query = "900";
        vm.Exact = true;
        vm.ApplyFilters();
        Assert.Empty(vm.VisiblePallets);

        vm.Exact = false;
        vm.ApplyFilters();
        Assert.NotEmpty(vm.VisiblePallets);
    }

    [Fact]
    public async Task ApplyFilters_DatePresetSortAndExactCombination_MatchesExpectedRows()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient();
        api.CustomCompletedPalletsJson = """
        {
          "total": 4,
          "pallets": [
            {
              "id": 601,
              "pallet_number": 120,
              "status": "completed",
              "template_type": "450WT",
              "max_panels": 35,
              "customer_id": null,
              "created_at": "2026-03-10T09:00:00Z",
              "completed_at": "2026-03-10T09:30:00Z",
              "deleted_at": null,
              "item_count": 4,
              "items": [{ "id": 1, "serial": "SN-EXACT-1", "slot_index": 1, "added_at": "2026-03-10T09:05:00Z" }]
            },
            {
              "id": 602,
              "pallet_number": 122,
              "status": "completed",
              "template_type": "220WT",
              "max_panels": 25,
              "customer_id": null,
              "created_at": "2026-03-10T10:00:00Z",
              "completed_at": "2026-03-10T10:30:00Z",
              "deleted_at": null,
              "item_count": 2,
              "items": [{ "id": 2, "serial": "SN-CONTAINS-2", "slot_index": 1, "added_at": "2026-03-10T10:05:00Z" }]
            },
            {
              "id": 603,
              "pallet_number": 119,
              "status": "completed",
              "template_type": "200WT",
              "max_panels": 25,
              "customer_id": null,
              "created_at": "2026-03-09T11:00:00Z",
              "completed_at": "2026-03-09T11:30:00Z",
              "deleted_at": null,
              "item_count": 8,
              "items": [{ "id": 3, "serial": "SN-EXACT-3", "slot_index": 1, "added_at": "2026-03-09T11:05:00Z" }]
            },
            {
              "id": 604,
              "pallet_number": 150,
              "status": "completed",
              "template_type": "330WT",
              "max_panels": 30,
              "customer_id": null,
              "created_at": "2026-02-15T12:00:00Z",
              "completed_at": "2026-02-15T12:30:00Z",
              "deleted_at": null,
              "item_count": 10,
              "items": [{ "id": 4, "serial": "SN-EXACT-4", "slot_index": 1, "added_at": "2026-02-15T12:05:00Z" }]
            }
          ]
        }
        """;
        var vm = CreateViewModel(launcher, api, new InMemoryCacheRepository());

        await vm.RefreshAsync();
        vm.DatePreset = "today";
        vm.Query = "122";
        vm.Exact = true;
        vm.SortMode = "number_desc";
        vm.ApplyFilters();

        var row = Assert.Single(vm.VisiblePallets);
        Assert.Equal(602, row.Id);
        Assert.Equal(122, row.PalletNumber);

        vm.DatePreset = "all";
        vm.Query = string.Empty;
        vm.Exact = false;
        vm.SortMode = "items_desc";
        vm.ApplyFilters();

        Assert.Equal(4, vm.VisiblePallets.Count);
        Assert.Equal(604, vm.VisiblePallets[0].Id);
        Assert.Equal(603, vm.VisiblePallets[1].Id);
    }

    [Fact]
    public async Task DeleteSelectedPalletAsync_WhenApiDeleteFails_SetsFailureMessage()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient { ThrowOnDelete = true };
        var vm = CreateViewModel(launcher, api, new InMemoryCacheRepository());

        await vm.RefreshAsync();
        vm.SelectedPallet = vm.VisiblePallets.First();

        await vm.DeleteSelectedPalletAsync();

        Assert.Equal("Failed to delete pallet", vm.StatusMessage);
        Assert.NotNull(vm.SelectedPallet);
    }

    [Fact]
    public async Task MergeSelectedPalletsAsync_WhenExportLookupFails_SetsFailureMessage()
    {
        var launcher = new RecordingSystemLauncher();
        var api = new FakeApiClient { ThrowOnExportLookup = true };
        var vm = CreateViewModel(launcher, api, new InMemoryCacheRepository());
        vm.VisiblePallets.Add(new HistoryPalletRow(71, 301, "220WT", 1, DateTime.Now, "completed", isSelected: true));
        vm.VisiblePallets.Add(new HistoryPalletRow(72, 302, "220WT", 1, DateTime.Now, "completed", isSelected: true));

        await vm.MergeSelectedPalletsAsync();

        Assert.Equal("Failed to merge selected pallets", vm.StatusMessage);
        Assert.Empty(launcher.Targets);
    }

    private static HistoryViewModel CreateViewModel(
        RecordingSystemLauncher launcher,
        FakeApiClient apiClient,
        InMemoryCacheRepository cacheRepository)
    {
        return new HistoryViewModel(
            apiClient,
            new FixedAuthService(),
            cacheRepository,
            new FixedSettingsService(),
            launcher,
            new NoopSpreadsheetService(),
            new NoopHttpClientFactory());
    }

    private sealed class FakeApiClient : IApiClient
    {
        public Dictionary<int, int[]> ExportMap { get; } = new();
        public string? CustomCompletedPalletsJson { get; set; }
        public bool ThrowOnDelete { get; set; }
        public bool ThrowOnExportLookup { get; set; }

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/pallets?status=completed", StringComparison.OrdinalIgnoreCase))
            {
                var json = CustomCompletedPalletsJson ?? """
                {
                  "total": 1,
                  "pallets": [
                    {
                      "id": 501,
                      "pallet_number": 501,
                      "status": "completed",
                      "template_type": "200WT",
                      "max_panels": 25,
                      "customer_id": null,
                      "created_at": "2026-03-10T10:00:00Z",
                      "completed_at": "2026-03-10T10:10:00Z",
                      "deleted_at": null,
                      "item_count": 1,
                      "items": [
                        { "id": 1, "serial": "SN-9001", "slot_index": 1, "added_at": "2026-03-10T10:02:00Z" }
                      ]
                    }
                  ]
                }
                """;
                return Task.FromResult(JsonSerializer.Deserialize<T>(json, JsonOptions())!);
            }

            if (path.StartsWith("/exports?pallet_id=", StringComparison.OrdinalIgnoreCase))
            {
                if (ThrowOnExportLookup)
                {
                    throw new InvalidOperationException("Failed to merge selected pallets");
                }

                var palletId = ParseIntQuery(path, "pallet_id");
                var exportIds = ExportMap.TryGetValue(palletId, out var mapped) ? mapped : Array.Empty<int>();
                var exportsJson = string.Join(",", exportIds.Select(id => $$"""
                  { "id": {{id}}, "pallet_id": {{palletId}}, "template_type": "200WT", "packout_date": "2026-03-10", "object_key": "k", "file_name": "f-{{id}}.pdf", "mime_type": "application/pdf", "size_bytes": 10, "checksum_sha256": "x", "created_at": "2026-03-10T10:20:00Z" }
                """));
                var json = $$"""{"exports":[{{exportsJson}}]}""";
                return Task.FromResult(JsonSerializer.Deserialize<T>(json, JsonOptions())!);
            }

            throw new NotSupportedException(path);
        }

        public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        {
            if (ThrowOnDelete && path.StartsWith("/pallets/", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("Failed to delete pallet");
            }

            return Task.CompletedTask;
        }

        private static int ParseIntQuery(string path, string key)
        {
            var query = path.Split('?', 2).Length == 2 ? path.Split('?', 2)[1] : string.Empty;
            var values = query.Split('&', StringSplitOptions.RemoveEmptyEntries);
            foreach (var value in values)
            {
                var parts = value.Split('=', 2);
                if (parts.Length == 2 && string.Equals(parts[0], key, StringComparison.OrdinalIgnoreCase) && int.TryParse(parts[1], out var parsed))
                {
                    return parsed;
                }
            }

            return 0;
        }

        private static JsonSerializerOptions JsonOptions() => new() { PropertyNameCaseInsensitive = true };
    }

    private sealed class InMemoryCacheRepository : ILocalCacheRepository
    {
        public Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default) => Task.CompletedTask;

        public Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default) =>
            Task.FromResult((IReadOnlyList<Customer>)Array.Empty<Customer>());

        public Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default) => Task.CompletedTask;

        public Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default) =>
            Task.FromResult((IReadOnlyList<Pallet>)Array.Empty<Pallet>());

        public Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default) => Task.CompletedTask;

        public Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default) =>
            Task.FromResult((IReadOnlyList<ExportRecord>)Array.Empty<ExportRecord>());
    }

    private sealed class FixedSettingsService : IRuntimeSettingsService
    {
        private readonly RuntimeSettings _settings = new()
        {
            PrimaryApiBaseUrl = "http://api.test/api/v1",
            FallbackApiBaseUrl = "http://api-fallback.test/api/v1",
            LockToLocalBackend = false,
        };

        public Task<RuntimeSettings> GetAsync(CancellationToken ct = default) => Task.FromResult(_settings);

        public Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default) =>
            Task.FromResult(settings);

        public IObservable<RuntimeSettings> Changes { get; } = new EmptyObservable<RuntimeSettings>();
    }

    private sealed class RecordingSystemLauncher : ISystemLauncher
    {
        public List<string> Targets { get; } = new();

        public Task OpenAsync(string target, CancellationToken ct = default)
        {
            Targets.Add(target);
            return Task.CompletedTask;
        }
    }

    private sealed class NoopSpreadsheetService : ISpreadsheetService
    {
        public Task<WorkbookEditModel> LoadAsync(byte[] xlsxBytes, CancellationToken ct = default) =>
            Task.FromResult(new WorkbookEditModel());

        public Task<byte[]> SaveAsync(WorkbookEditModel workbook, CancellationToken ct = default) =>
            Task.FromResult(Array.Empty<byte>());
    }

    private sealed class NoopHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new();
    }

    private sealed class FixedAuthService : IApiTokenProvider
    {
        public Task<string?> GetBearerTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
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
