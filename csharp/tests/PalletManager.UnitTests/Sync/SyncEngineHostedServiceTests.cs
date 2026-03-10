using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using PalletManager.Domain.Errors;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Infrastructure.Sync;
using Xunit;

namespace PalletManager.UnitTests.Sync;

public sealed class SyncEngineHostedServiceTests
{
    [Fact]
    public async Task TriggerNowAsync_ReplaysPalletItemAdd_WithAllowMissingSimDataTrue()
    {
        var outbox = new InMemoryOutboxRepository();
        var api = new RecordingApiClient();
        var auth = new FixedAuthService();
        var mappings = new InMemoryIdMappingRepository();

        var operation = new OutboxOperation
        {
            OpId = Guid.NewGuid(),
            OpType = OperationType.PalletItemAdd,
            PayloadJson = """{"pallet_id":101,"serial":"SN-FALLBACK-9001","allow_missing_sim_data":true}""",
            State = OutboxState.Pending,
            AttemptCount = 0,
            CreatedAtUtc = DateTime.UtcNow,
            UpdatedAtUtc = DateTime.UtcNow,
        };
        await outbox.EnqueueAsync(operation);

        var engine = new SyncEngineHostedService(outbox, api, auth, mappings);
        await engine.TriggerNowAsync();

        Assert.Single(api.PostCalls);
        var post = api.PostCalls[0];
        Assert.Equal("/pallets/101/items", post.Path);
        Assert.Equal("SN-FALLBACK-9001", post.Body.GetProperty("serial").GetString());
        Assert.True(post.Body.GetProperty("allow_missing_sim_data").GetBoolean());
        Assert.Empty(await outbox.ListAsync());
    }

    [Theory]
    [InlineData(409, "SIM_DATA_REQUIRED")]
    [InlineData(422, "PALLET_STATE_CONFLICT")]
    public async Task TriggerNowAsync_WhenReplayHasConflict_MarksNeedsReview(int statusCode, string errorCode)
    {
        var outbox = new InMemoryOutboxRepository();
        var api = new RecordingApiClient
        {
            PostError = new ApiError("conflict", statusCode, "POST", "/pallets/101/items", errorCode),
        };
        var auth = new FixedAuthService();
        var mappings = new InMemoryIdMappingRepository();

        var operation = new OutboxOperation
        {
            OpId = Guid.NewGuid(),
            OpType = OperationType.PalletItemAdd,
            PayloadJson = """{"pallet_id":101,"serial":"SN-CONFLICT-1","allow_missing_sim_data":true}""",
            State = OutboxState.Pending,
            AttemptCount = 1,
            CreatedAtUtc = DateTime.UtcNow,
            UpdatedAtUtc = DateTime.UtcNow,
        };
        await outbox.EnqueueAsync(operation);

        var engine = new SyncEngineHostedService(outbox, api, auth, mappings);
        await engine.TriggerNowAsync();

        var remaining = await outbox.ListAsync();
        var op = Assert.Single(remaining);
        Assert.Equal(OutboxState.NeedsReview, op.State);
        Assert.Equal("conflict", op.LastError);
        Assert.Equal(errorCode, op.LastErrorCode);
        Assert.Null(op.NextRetryAtUtc);
    }

    [Fact]
    public async Task SyncIssuesViewModel_RetryAndDiscard_FollowExpectedLifecycle()
    {
        var outbox = new InMemoryOutboxRepository();
        var sync = new RecordingSyncEngine();
        var vm = new SyncIssuesViewModel(outbox, sync);
        var opId = Guid.NewGuid();

        await outbox.EnqueueAsync(new OutboxOperation
        {
            OpId = opId,
            OpType = OperationType.PalletItemAdd,
            PayloadJson = """{"pallet_id":5,"serial":"SN-NEEDS-REVIEW"}""",
            State = OutboxState.NeedsReview,
            AttemptCount = 3,
            LastError = "conflict",
            LastErrorCode = "SIM_DATA_REQUIRED",
            CreatedAtUtc = DateTime.UtcNow,
            UpdatedAtUtc = DateTime.UtcNow,
        });

        await vm.RefreshAsync();
        Assert.Single(vm.NeedsReview);

        await vm.RetryOperationAsync(opId);
        Assert.Equal(1, sync.TriggerNowCalls);

        var afterRetry = Assert.Single(await outbox.ListAsync());
        Assert.Equal(OutboxState.Pending, afterRetry.State);
        Assert.Null(afterRetry.LastError);
        Assert.Null(afterRetry.LastErrorCode);
        Assert.Null(afterRetry.NextRetryAtUtc);

        await vm.DiscardOperationAsync(opId);
        Assert.Empty(await outbox.ListAsync());
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

    private sealed class RecordingApiClient : IApiClient
    {
        public List<PostCall> PostCalls { get; } = new();
        public Exception? PostError { get; set; }

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task<T> PostAsync<T>(
            string path,
            object? body = null,
            string? token = null,
            IDictionary<string, string>? headers = null,
            CancellationToken ct = default)
        {
            if (PostError is not null)
            {
                throw PostError;
            }

            var json = JsonSerializer.Serialize(body ?? new { });
            using var document = JsonDocument.Parse(json);
            PostCalls.Add(new PostCall(path, document.RootElement.Clone()));

            var result = typeof(T) == typeof(object)
                ? (T)(object)new object()
                : JsonSerializer.Deserialize<T>("{}")!;
            return Task.FromResult(result);
        }

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default) =>
            throw new NotSupportedException(path);
    }

    private sealed record PostCall(string Path, JsonElement Body);

    private sealed class FixedAuthService : IAuthService
    {
        public Task<string?> GetTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
        public Task SetTokenAsync(string? token, CancellationToken ct = default) => Task.CompletedTask;
        public Task ClearSessionAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class InMemoryIdMappingRepository : IIdMappingRepository
    {
        private readonly Dictionary<(string Entity, int Local), int> _mappings = new();

        public Task<int?> ResolveRemoteIdAsync(string entityType, int localId, CancellationToken ct = default)
        {
            var found = _mappings.TryGetValue((entityType, localId), out var remote);
            return Task.FromResult(found ? (int?)remote : null);
        }

        public Task SaveMappingAsync(string entityType, int localId, int remoteId, CancellationToken ct = default)
        {
            _mappings[(entityType, localId)] = remoteId;
            return Task.CompletedTask;
        }
    }

    private sealed class RecordingSyncEngine : ISyncEngine
    {
        public int TriggerNowCalls { get; private set; }
        public IObservable<SyncState> State { get; } = new EmptyObservable<SyncState>();

        public Task TriggerNowAsync(CancellationToken ct = default)
        {
            TriggerNowCalls += 1;
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
