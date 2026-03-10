using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using Xunit;

namespace PalletManager.ParityTests.Flows;

public sealed class CoreFlowsParityTests
{
    public static IEnumerable<object[]> BuilderTemplateSizeMatrix()
    {
        var templates = new[] { "200WT", "220WT", "220M6", "330WT", "450WT", "450BT" };
        var sizes = new[] { 25, 26, 30, 35 };
        foreach (var template in templates)
        {
            foreach (var size in sizes)
            {
                yield return new object[] { template, size };
            }
        }
    }

    [Theory]
    [MemberData(nameof(BuilderTemplateSizeMatrix))]
    public async Task Builder_TemplateAndSizeMatrix_UsesSelectedValuesInCreatePayload(string templateType, int palletSize)
    {
        var outbox = new InMemoryOutboxRepository();
        var api = new BuilderApiClient();
        api.SimSerials.Add("SN-MATRIX-1");
        var vm = new BuilderViewModel(
            new InMemoryDraftRepository(),
            outbox,
            new FixedClock(new DateTime(2026, 3, 10, 12, 0, 0, DateTimeKind.Utc)),
            api,
            new FixedAuthService());

        vm.SelectedTemplateType = templateType;
        vm.SelectedPalletSize = palletSize;

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MATRIX-1";
        await vm.AddSerialAsync();
        await vm.CompleteDraftAsync();

        var create = outbox.Operations.First(o => o.OpType == OperationType.PalletCreate);
        using var payload = JsonDocument.Parse(create.PayloadJson);
        Assert.Equal(templateType, payload.RootElement.GetProperty("template_type").GetString());
        Assert.Equal(palletSize, payload.RootElement.GetProperty("max_panels").GetInt32());
    }

    [Fact]
    public async Task Builder_MissingSimDecisionJourney_PreservesQueueSemantics()
    {
        var outbox = new InMemoryOutboxRepository();
        var vm = new BuilderViewModel(
            new InMemoryDraftRepository(),
            outbox,
            new FixedClock(new DateTime(2026, 3, 10, 12, 0, 0, DateTimeKind.Utc)),
            new BuilderApiClient(),
            new FixedAuthService());

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MISSING-100";
        await vm.AddSerialAsync();
        Assert.True(vm.IsMissingSimPromptOpen);
        Assert.Empty(vm.Items);

        await vm.ResolveMissingSimDecisionAsync(useFallback: false);
        Assert.False(vm.IsMissingSimPromptOpen);
        Assert.Empty(vm.Items);

        vm.SerialInput = "SN-MISSING-100";
        await vm.AddSerialAsync();
        await vm.ResolveMissingSimDecisionAsync(useFallback: true);
        Assert.Single(vm.Items);
        Assert.Equal(1, vm.FallbackSerialCount);

        await vm.CompleteDraftAsync();
        Assert.False(vm.HasActivePallet);

        var ops = outbox.Operations.ToList();
        Assert.Equal(3, ops.Count);
        Assert.Equal(OperationType.PalletCreate, ops[0].OpType);
        Assert.Equal(OperationType.PalletItemAdd, ops[1].OpType);
        Assert.Equal(OperationType.PalletComplete, ops[2].OpType);
        using var payload = JsonDocument.Parse(ops[1].PayloadJson);
        Assert.True(payload.RootElement.GetProperty("allow_missing_sim_data").GetBoolean());
    }

    [Fact]
    public async Task Builder_SimDataPresentJourney_AddRemoveComplete_PreservesSlotParity()
    {
        var outbox = new InMemoryOutboxRepository();
        var api = new BuilderApiClient();
        api.SimSerials.Add("SN-OK-1");
        api.SimSerials.Add("SN-OK-2");
        var vm = new BuilderViewModel(
            new InMemoryDraftRepository(),
            outbox,
            new FixedClock(new DateTime(2026, 3, 10, 12, 0, 0, DateTimeKind.Utc)),
            api,
            new FixedAuthService());

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-OK-1";
        await vm.AddSerialAsync();
        vm.SerialInput = "SN-OK-2";
        await vm.AddSerialAsync();
        Assert.Equal(2, vm.Items.Count);
        Assert.False(vm.IsMissingSimPromptOpen);

        var removeId = vm.Items[0].Id;
        await vm.RemoveSerialAsync(removeId);
        Assert.Single(vm.Items);
        Assert.Equal(1, vm.Items[0].SlotIndex);
        Assert.Equal("SN-OK-2", vm.Items[0].Serial);

        await vm.CompleteDraftAsync();
        Assert.Contains(outbox.Operations, o => o.OpType == OperationType.PalletItemRemove);
        Assert.Contains(outbox.Operations, o => o.OpType == OperationType.PalletComplete);
    }

    [Fact]
    public async Task History_RefreshFilterMergeAndOpenExport_MatchesExpectedFlow()
    {
        var launcher = new RecordingLauncher();
        var api = new HistoryApiClient();
        var vm = new HistoryViewModel(
            api,
            new FixedAuthService(),
            new InMemoryCacheRepository(),
            new FixedSettingsService(),
            launcher,
            new NoopSpreadsheetService(),
            new NoopHttpClientFactory());

        await vm.RefreshAsync();
        Assert.Equal(2, vm.VisiblePallets.Count);

        vm.Query = "HIST-900";
        vm.Exact = false;
        vm.ApplyFilters();
        Assert.Equal(2, vm.VisiblePallets.Count);

        vm.VisiblePallets[0].IsSelected = true;
        vm.VisiblePallets[1].IsSelected = true;
        await vm.MergeSelectedPalletsAsync();
        Assert.Contains("merge-pdf", launcher.Targets.Last());

        await vm.OpenExportAsync(5001, "xlsx");
        Assert.Contains("/exports/5001/download?format=xlsx", launcher.Targets.Last());
    }

    [Fact]
    public async Task History_FilterComboAndSort_MatchesExpectedRows()
    {
        var launcher = new RecordingLauncher();
        var api = new HistoryApiClient
        {
            CompletedPalletsJson = """
            {
              "total": 3,
              "pallets": [
                {
                  "id": 910,
                  "pallet_number": 910,
                  "status": "completed",
                  "template_type": "HIST-910",
                  "max_panels": 25,
                  "customer_id": null,
                  "created_at": "2026-03-10T08:00:00Z",
                  "completed_at": "2026-03-10T08:30:00Z",
                  "deleted_at": null,
                  "item_count": 3,
                  "items": [{ "id": 1, "serial": "SN-AAA-910", "slot_index": 1, "added_at": "2026-03-10T08:02:00Z" }]
                },
                {
                  "id": 911,
                  "pallet_number": 911,
                  "status": "completed",
                  "template_type": "HIST-911",
                  "max_panels": 25,
                  "customer_id": null,
                  "created_at": "2026-03-10T09:00:00Z",
                  "completed_at": "2026-03-10T09:30:00Z",
                  "deleted_at": null,
                  "item_count": 1,
                  "items": [{ "id": 2, "serial": "SN-BBB-911", "slot_index": 1, "added_at": "2026-03-10T09:02:00Z" }]
                },
                {
                  "id": 850,
                  "pallet_number": 850,
                  "status": "completed",
                  "template_type": "HIST-850",
                  "max_panels": 25,
                  "customer_id": null,
                  "created_at": "2026-02-10T09:00:00Z",
                  "completed_at": "2026-02-10T09:30:00Z",
                  "deleted_at": null,
                  "item_count": 7,
                  "items": [{ "id": 3, "serial": "SN-CCC-850", "slot_index": 1, "added_at": "2026-02-10T09:02:00Z" }]
                }
              ]
            }
            """
        };

        var vm = new HistoryViewModel(
            api,
            new FixedAuthService(),
            new InMemoryCacheRepository(),
            new FixedSettingsService(),
            launcher,
            new NoopSpreadsheetService(),
            new NoopHttpClientFactory());

        await vm.RefreshAsync();
        vm.DatePreset = "all";
        vm.Query = "911";
        vm.Exact = true;
        vm.SortMode = "number_desc";
        vm.ApplyFilters();
        var exact = Assert.Single(vm.VisiblePallets);
        Assert.Equal(911, exact.PalletNumber);

        vm.Query = string.Empty;
        vm.Exact = false;
        vm.SortMode = "items_desc";
        vm.ApplyFilters();
        Assert.Equal(3, vm.VisiblePallets.Count);
        Assert.Equal(850, vm.VisiblePallets[0].PalletNumber);
    }

    [Fact]
    public async Task History_DeleteAndMergeFailures_SetOperatorSafeMessages()
    {
        var launcher = new RecordingLauncher();
        var api = new HistoryApiClient
        {
            ThrowOnDelete = true,
            ThrowOnExportLookup = true,
        };
        var vm = new HistoryViewModel(
            api,
            new FixedAuthService(),
            new InMemoryCacheRepository(),
            new FixedSettingsService(),
            launcher,
            new NoopSpreadsheetService(),
            new NoopHttpClientFactory());

        await vm.RefreshAsync();
        vm.SelectedPallet = vm.VisiblePallets.First();
        await vm.DeleteSelectedPalletAsync();
        Assert.Equal("Failed to delete pallet", vm.StatusMessage);

        vm.VisiblePallets[0].IsSelected = true;
        vm.VisiblePallets[1].IsSelected = true;
        await vm.MergeSelectedPalletsAsync();
        Assert.Equal("Failed to merge selected pallets", vm.StatusMessage);
        Assert.DoesNotContain(launcher.Targets, t => t.Contains("merge-pdf", StringComparison.OrdinalIgnoreCase));
    }

    private sealed class InMemoryDraftRepository : IBuilderDraftRepository
    {
        private BuilderDraft? _draft;
        public Task<BuilderDraft?> GetAsync(CancellationToken ct = default) => Task.FromResult(_draft);
        public Task SaveAsync(BuilderDraft draft, CancellationToken ct = default)
        {
            _draft = draft;
            return Task.CompletedTask;
        }
        public Task ClearAsync(CancellationToken ct = default)
        {
            _draft = null;
            return Task.CompletedTask;
        }
    }

    private sealed class InMemoryOutboxRepository : IOutboxRepository
    {
        public List<OutboxOperation> Operations { get; } = new();
        public Task<IReadOnlyList<OutboxOperation>> ListAsync(CancellationToken ct = default) => Task.FromResult((IReadOnlyList<OutboxOperation>)Operations.ToList());
        public Task EnqueueAsync(OutboxOperation operation, CancellationToken ct = default)
        {
            Operations.Add(operation);
            return Task.CompletedTask;
        }
        public Task UpdateAsync(OutboxOperation operation, CancellationToken ct = default) => Task.CompletedTask;
        public Task RemoveAsync(Guid opId, CancellationToken ct = default)
        {
            Operations.RemoveAll(o => o.OpId == opId);
            return Task.CompletedTask;
        }
        public Task MarkNeedsReviewAsync(Guid opId, string reason, string? errorCode, CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class BuilderApiClient : IApiClient
    {
        public HashSet<string> SimSerials { get; } = new(StringComparer.OrdinalIgnoreCase);

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/barcodes/search?", StringComparison.OrdinalIgnoreCase))
            {
                var serial = ReadQuery(path, "q");
                var json = SimSerials.Contains(serial)
                    ? $$"""{"results":[{"source":"sim_panel","serial":"{{serial}}"}]}"""
                    : """{"results":[]}""";
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

    private sealed class HistoryApiClient : IApiClient
    {
        public string? CompletedPalletsJson { get; set; }
        public bool ThrowOnDelete { get; set; }
        public bool ThrowOnExportLookup { get; set; }

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/pallets?status=completed", StringComparison.OrdinalIgnoreCase))
            {
                var json = CompletedPalletsJson ?? """
                {
                  "total": 2,
                  "pallets": [
                    {
                      "id": 901,
                      "pallet_number": 901,
                      "status": "completed",
                      "template_type": "HIST-900",
                      "max_panels": 25,
                      "customer_id": null,
                      "created_at": "2026-03-10T10:00:00Z",
                      "completed_at": "2026-03-10T10:10:00Z",
                      "deleted_at": null,
                      "item_count": 1,
                      "items": [{ "id": 1, "serial": "SN-HIST-1", "slot_index": 1, "added_at": "2026-03-10T10:02:00Z" }]
                    },
                    {
                      "id": 902,
                      "pallet_number": 902,
                      "status": "completed",
                      "template_type": "HIST-900",
                      "max_panels": 25,
                      "customer_id": null,
                      "created_at": "2026-03-10T11:00:00Z",
                      "completed_at": "2026-03-10T11:10:00Z",
                      "deleted_at": null,
                      "item_count": 1,
                      "items": [{ "id": 2, "serial": "SN-HIST-2", "slot_index": 1, "added_at": "2026-03-10T11:02:00Z" }]
                    }
                  ]
                }
                """;
                return Task.FromResult(JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!);
            }

            if (path.StartsWith("/exports?pallet_id=901", StringComparison.OrdinalIgnoreCase))
            {
                if (ThrowOnExportLookup)
                {
                    throw new InvalidOperationException("Failed to merge selected pallets");
                }

                const string json = """{"exports":[{"id":5001,"pallet_id":901,"template_type":"HIST-900","packout_date":"2026-03-10","object_key":"k","file_name":"h1.pdf","mime_type":"application/pdf","size_bytes":10,"checksum_sha256":"x","created_at":"2026-03-10T10:20:00Z"}]}""";
                return Task.FromResult(JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!);
            }

            if (path.StartsWith("/exports?pallet_id=902", StringComparison.OrdinalIgnoreCase))
            {
                if (ThrowOnExportLookup)
                {
                    throw new InvalidOperationException("Failed to merge selected pallets");
                }

                const string json = """{"exports":[{"id":5002,"pallet_id":902,"template_type":"HIST-900","packout_date":"2026-03-10","object_key":"k","file_name":"h2.pdf","mime_type":"application/pdf","size_bytes":10,"checksum_sha256":"x","created_at":"2026-03-10T11:20:00Z"}]}""";
                return Task.FromResult(JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!);
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

    private sealed class RecordingLauncher : ISystemLauncher
    {
        public List<string> Targets { get; } = new();
        public Task OpenAsync(string target, CancellationToken ct = default)
        {
            Targets.Add(target);
            return Task.CompletedTask;
        }
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

    private sealed class NoopSpreadsheetService : ISpreadsheetService
    {
        public Task<WorkbookEditModel> LoadAsync(byte[] xlsxBytes, CancellationToken ct = default) => Task.FromResult(new WorkbookEditModel());
        public Task<byte[]> SaveAsync(WorkbookEditModel workbook, CancellationToken ct = default) => Task.FromResult(Array.Empty<byte>());
    }

    private sealed class NoopHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new();
    }

    private sealed class FixedAuthService : IApiTokenProvider
    {
        public Task<string?> GetBearerTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
    }

    private sealed class FixedClock : IClock
    {
        public FixedClock(DateTime utcNow) => UtcNow = utcNow;
        public DateTime UtcNow { get; }
    }

    private static string ReadQuery(string path, string key)
    {
        var query = path.Split('?', 2).Length == 2 ? path.Split('?', 2)[1] : string.Empty;
        foreach (var segment in query.Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = segment.Split('=', 2);
            if (parts.Length == 2 && string.Equals(parts[0], key, StringComparison.OrdinalIgnoreCase))
            {
                return Uri.UnescapeDataString(parts[1]);
            }
        }

        return string.Empty;
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
