using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using PalletManager.Domain.Errors;
using PalletManager.Infrastructure.Persistence;
using PalletManager.Infrastructure.Persistence.Repositories;
using PalletManager.Infrastructure.Sync;
using Xunit;

namespace PalletManager.IntegrationTests.Sync;

public sealed class OutboxSyncLifecycleIntegrationTests
{
    [Fact]
    public async Task ReplaySuccess_RemovesOperationFromSqliteOutbox()
    {
        await using var context = await IntegrationContext.CreateAsync();
        var op = BuildItemAddOperation("""{"pallet_id":2001,"serial":"SN-INT-SUCCESS","allow_missing_sim_data":true}""");
        await context.Outbox.EnqueueAsync(op);

        await context.Engine.TriggerNowAsync();

        var remaining = await context.Outbox.ListAsync();
        Assert.Empty(remaining);
        Assert.Single(context.ApiClient.PostCalls);
        Assert.Equal("/pallets/2001/items", context.ApiClient.PostCalls[0].Path);
    }

    [Fact]
    public async Task ReplayConflict_MovesOperationToNeedsReviewInSqlite()
    {
        await using var context = await IntegrationContext.CreateAsync();
        context.ApiClient.PostError = new ApiError("conflict", 409, "POST", "/pallets/2002/items", "SIM_DATA_REQUIRED");
        var op = BuildItemAddOperation("""{"pallet_id":2002,"serial":"SN-INT-CONFLICT","allow_missing_sim_data":true}""");
        await context.Outbox.EnqueueAsync(op);

        await context.Engine.TriggerNowAsync();

        var remaining = await context.Outbox.ListAsync();
        var persisted = Assert.Single(remaining);
        Assert.Equal(OutboxState.NeedsReview, persisted.State);
        Assert.Equal("conflict", persisted.LastError);
        Assert.Equal("SIM_DATA_REQUIRED", persisted.LastErrorCode);
        Assert.Null(persisted.NextRetryAtUtc);
    }

    [Fact]
    public async Task RetryViaSyncIssuesViewModel_ReplaysAndClearsNeedsReviewOperation()
    {
        await using var context = await IntegrationContext.CreateAsync();
        var op = BuildItemAddOperation("""{"pallet_id":2003,"serial":"SN-INT-RETRY","allow_missing_sim_data":true}""");
        await context.Outbox.EnqueueAsync(op);
        await context.Outbox.MarkNeedsReviewAsync(op.OpId, "sim missing", "SIM_DATA_REQUIRED");

        var vm = new SyncIssuesViewModel(context.Outbox, context.Engine);
        await vm.RefreshAsync();
        Assert.Single(vm.NeedsReview);

        await vm.RetryOperationAsync(op.OpId);

        var remaining = await context.Outbox.ListAsync();
        Assert.Empty(remaining);
        Assert.Single(context.ApiClient.PostCalls);
        using var postedBody = JsonDocument.Parse(context.ApiClient.PostCalls[0].BodyJson);
        Assert.True(postedBody.RootElement.GetProperty("allow_missing_sim_data").GetBoolean());
    }

    private static OutboxOperation BuildItemAddOperation(string payloadJson)
    {
        return new OutboxOperation
        {
            OpId = Guid.NewGuid(),
            OpType = OperationType.PalletItemAdd,
            PayloadJson = payloadJson,
            State = OutboxState.Pending,
            AttemptCount = 0,
            LastError = null,
            LastErrorCode = null,
            NextRetryAtUtc = null,
            CreatedAtUtc = DateTime.UtcNow,
            UpdatedAtUtc = DateTime.UtcNow,
        };
    }

    private sealed class IntegrationContext : IAsyncDisposable
    {
        private readonly string _rootTempDir;

        private IntegrationContext(
            string rootTempDir,
            OutboxRepository outbox,
            SyncEngineHostedService engine,
            RecordingApiClient apiClient)
        {
            _rootTempDir = rootTempDir;
            Outbox = outbox;
            Engine = engine;
            ApiClient = apiClient;
        }

        public OutboxRepository Outbox { get; }
        public SyncEngineHostedService Engine { get; }
        public RecordingApiClient ApiClient { get; }

        public static async Task<IntegrationContext> CreateAsync()
        {
            var rootTempDir = Path.Combine(Path.GetTempPath(), "pallet-manager-csharp-int", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(rootTempDir);
            var dbPath = Path.Combine(rootTempDir, "integration.db");

            var factory = new SqliteConnectionFactory(dbPath);
            var migrationDir = ResolveMigrationsDirectory();
            var migrations = new MigrationRunner(factory, migrationDir);
            await migrations.RunAsync();

            var outbox = new OutboxRepository(factory);
            var api = new RecordingApiClient();
            var auth = new FixedAuthService();
            var mappings = new InMemoryIdMappingRepository();
            var engine = new SyncEngineHostedService(outbox, api, auth, mappings);

            return new IntegrationContext(rootTempDir, outbox, engine, api);
        }

        public ValueTask DisposeAsync()
        {
            try
            {
                if (Directory.Exists(_rootTempDir))
                {
                    Directory.Delete(_rootTempDir, recursive: true);
                }
            }
            catch
            {
                // Best effort cleanup for test temp artifacts.
            }

            return ValueTask.CompletedTask;
        }

        private static string ResolveMigrationsDirectory()
        {
            var current = AppContext.BaseDirectory;
            for (var i = 0; i < 10; i++)
            {
                var candidate = Path.GetFullPath(Path.Combine(current, string.Join(Path.DirectorySeparatorChar, Enumerable.Repeat("..", i))));
                var migrations = Path.Combine(candidate, "src", "PalletManager.Infrastructure", "Persistence", "Migrations");
                if (Directory.Exists(migrations))
                {
                    return migrations;
                }
            }

            throw new DirectoryNotFoundException("Unable to locate migration directory for integration tests.");
        }
    }

    private sealed class RecordingApiClient : IApiClient
    {
        public Exception? PostError { get; set; }
        public List<PostCall> PostCalls { get; } = new();

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

            PostCalls.Add(new PostCall(path, JsonSerializer.Serialize(body ?? new { })));

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

    private sealed record PostCall(string Path, string BodyJson);

    private sealed class FixedAuthService : IAuthService
    {
        public Task<string?> GetTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
        public Task SetTokenAsync(string? token, CancellationToken ct = default) => Task.CompletedTask;
        public Task ClearSessionAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class InMemoryIdMappingRepository : IIdMappingRepository
    {
        public Task<int?> ResolveRemoteIdAsync(string entityType, int localId, CancellationToken ct = default) =>
            Task.FromResult<int?>(null);

        public Task SaveMappingAsync(string entityType, int localId, int remoteId, CancellationToken ct = default) =>
            Task.CompletedTask;
    }
}
