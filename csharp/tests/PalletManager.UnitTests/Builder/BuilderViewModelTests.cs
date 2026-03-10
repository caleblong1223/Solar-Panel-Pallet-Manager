using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using Xunit;

namespace PalletManager.UnitTests.Builder;

public sealed class BuilderViewModelTests
{
    [Fact]
    public async Task AddSerialAsync_WhenSimMissing_OpensPrompt_AndSkipsEnqueueUntilDecision()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient();
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MISSING-1";

        await vm.AddSerialAsync();

        Assert.True(vm.IsMissingSimPromptOpen);
        Assert.Equal("SN-MISSING-1", vm.MissingSimSerial);
        Assert.Empty(vm.Items);
        Assert.Single(outboxRepo.Operations, o => o.OpType == OperationType.PalletCreate);
        Assert.DoesNotContain(outboxRepo.Operations, o => o.OpType == OperationType.PalletItemAdd);
    }

    [Fact]
    public async Task ResolveMissingSimDecisionAsync_WhenApproved_EnqueuesAllowMissingAndTracksFallback()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient();
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MISSING-2";
        await vm.AddSerialAsync();
        await vm.ResolveMissingSimDecisionAsync(useFallback: true);

        Assert.False(vm.IsMissingSimPromptOpen);
        Assert.Single(vm.Items);
        Assert.Equal(1, vm.FallbackSerialCount);

        var addOp = outboxRepo.Operations.Single(o => o.OpType == OperationType.PalletItemAdd);
        using var payload = JsonDocument.Parse(addOp.PayloadJson);
        Assert.Equal("SN-MISSING-2", payload.RootElement.GetProperty("serial").GetString());
        Assert.True(payload.RootElement.GetProperty("allow_missing_sim_data").GetBoolean());
    }

    [Fact]
    public async Task AddSerialAsync_WhenSimLookupUnavailable_StillAddsWithAllowMissingFalse()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient { ThrowOnSearch = true };
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-OFFLINE-1";

        await vm.AddSerialAsync();

        Assert.False(vm.IsMissingSimPromptOpen);
        Assert.Single(vm.Items);
        Assert.Equal(0, vm.FallbackSerialCount);

        var addOp = outboxRepo.Operations.Single(o => o.OpType == OperationType.PalletItemAdd);
        using var payload = JsonDocument.Parse(addOp.PayloadJson);
        Assert.False(payload.RootElement.GetProperty("allow_missing_sim_data").GetBoolean());
    }

    [Fact]
    public async Task RemoveSerialAsync_RemovesFallbackTrackingForThatSerial()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient();
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MISSING-REMOVE";
        await vm.AddSerialAsync();
        await vm.ResolveMissingSimDecisionAsync(useFallback: true);
        var addedId = vm.Items.Single().Id;

        Assert.Equal(1, vm.FallbackSerialCount);

        await vm.RemoveSerialAsync(addedId);

        Assert.Equal(0, vm.FallbackSerialCount);
    }

    [Fact]
    public async Task CompleteDraftAsync_ClearsFallbackTrackingAndQueuesComplete()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient();
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-MISSING-COMPLETE";
        await vm.AddSerialAsync();
        await vm.ResolveMissingSimDecisionAsync(useFallback: true);

        Assert.Equal(1, vm.FallbackSerialCount);

        await vm.CompleteDraftAsync();

        Assert.Equal(0, vm.FallbackSerialCount);
        Assert.False(vm.HasActivePallet);
        Assert.Contains(outboxRepo.Operations, o => o.OpType == OperationType.PalletComplete);
    }

    [Fact]
    public async Task SelectedPalletSize_WhenActiveAndLowerThanItemCount_IsRejectedWithParityMessage()
    {
        var draftRepo = new InMemoryDraftRepository();
        var outboxRepo = new InMemoryOutboxRepository();
        var api = new FakeApiClient();
        api.SimSerials.Add("SN-SIZE-1");
        api.SimSerials.Add("SN-SIZE-2");
        var vm = CreateViewModel(draftRepo, outboxRepo, api);

        await vm.StartNewPalletAsync();
        vm.SerialInput = "SN-SIZE-1";
        await vm.AddSerialAsync();
        vm.SerialInput = "SN-SIZE-2";
        await vm.AddSerialAsync();

        vm.SelectedPalletSize = 1;

        Assert.Equal(25, vm.SelectedPalletSize);
        Assert.Equal("Pallet size cannot be lower than current panel count (2)", vm.StatusMessage);
    }

    private static BuilderViewModel CreateViewModel(
        InMemoryDraftRepository draftRepo,
        InMemoryOutboxRepository outboxRepo,
        FakeApiClient apiClient)
    {
        return new BuilderViewModel(
            draftRepo,
            outboxRepo,
            new FixedClock(new DateTime(2026, 3, 10, 12, 0, 0, DateTimeKind.Utc)),
            apiClient,
            new FakeAuthService());
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

        public Task<IReadOnlyList<OutboxOperation>> ListAsync(CancellationToken ct = default) =>
            Task.FromResult((IReadOnlyList<OutboxOperation>)Operations.ToList());

        public Task EnqueueAsync(OutboxOperation operation, CancellationToken ct = default)
        {
            Operations.Add(operation);
            return Task.CompletedTask;
        }

        public Task UpdateAsync(OutboxOperation operation, CancellationToken ct = default)
        {
            var index = Operations.FindIndex(o => o.OpId == operation.OpId);
            if (index >= 0)
            {
                Operations[index] = operation;
            }
            return Task.CompletedTask;
        }

        public Task RemoveAsync(Guid opId, CancellationToken ct = default)
        {
            Operations.RemoveAll(o => o.OpId == opId);
            return Task.CompletedTask;
        }

        public Task MarkNeedsReviewAsync(Guid opId, string reason, string? errorCode, CancellationToken ct = default)
        {
            var op = Operations.FirstOrDefault(o => o.OpId == opId);
            if (op is not null)
            {
                op.State = OutboxState.NeedsReview;
                op.LastError = reason;
                op.LastErrorCode = errorCode;
            }
            return Task.CompletedTask;
        }
    }

    private sealed class FakeAuthService : IApiTokenProvider
    {
        public Task<string?> GetBearerTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
    }

    private sealed class FixedClock : IClock
    {
        public FixedClock(DateTime utcNow) => UtcNow = utcNow;
        public DateTime UtcNow { get; }
    }

    private sealed class FakeApiClient : IApiClient
    {
        public bool ThrowOnSearch { get; set; }
        public HashSet<string> SimSerials { get; } = new(StringComparer.OrdinalIgnoreCase);

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (!path.StartsWith("/barcodes/search", StringComparison.OrdinalIgnoreCase))
            {
                throw new NotSupportedException(path);
            }

            if (ThrowOnSearch)
            {
                throw new InvalidOperationException("Search unavailable.");
            }

            var queryString = path.Split('?', 2).Length == 2 ? path.Split('?', 2)[1] : string.Empty;
            var parameters = queryString.Split('&', StringSplitOptions.RemoveEmptyEntries)
                .Select(p => p.Split('=', 2))
                .ToDictionary(p => Uri.UnescapeDataString(p[0]), p => p.Length > 1 ? Uri.UnescapeDataString(p[1]) : string.Empty);
            var serial = parameters.TryGetValue("q", out var q) ? q : string.Empty;

            var hasSim = SimSerials.Contains(serial);
            var json = hasSim
                ? $$"""{"results":[{"source":"sim_panel","serial":"{{serial}}"}]}"""
                : """{"results":[]}""";

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
}
