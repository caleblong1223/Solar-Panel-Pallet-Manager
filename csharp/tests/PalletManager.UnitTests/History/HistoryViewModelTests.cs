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

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/pallets?status=completed", StringComparison.OrdinalIgnoreCase))
            {
                const string json = """
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

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

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

    private sealed class FixedAuthService : IAuthService
    {
        public Task<string?> GetTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
        public Task SetTokenAsync(string? token, CancellationToken ct = default) => Task.CompletedTask;
        public Task ClearSessionAsync(CancellationToken ct = default) => Task.CompletedTask;
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
