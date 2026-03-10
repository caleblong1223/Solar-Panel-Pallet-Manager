using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using PalletManager.Infrastructure.Persistence;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class OutboxRepository : IOutboxRepository
{
    private readonly SqliteConnectionFactory _factory;

    public OutboxRepository(SqliteConnectionFactory factory)
    {
        _factory = factory;
    }

    public async Task<IReadOnlyList<OutboxOperation>> ListAsync(CancellationToken ct = default)
    {
        var rows = new List<OutboxOperation>();
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT op_id, op_type, payload_json, state, attempt_count, last_error, last_error_code, next_retry_at, created_at, updated_at
FROM outbox_operations
ORDER BY created_at ASC;";

        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
        {
            rows.Add(new OutboxOperation
            {
                OpId = Guid.Parse(reader.GetString(0)),
                OpType = ParseOpType(reader.GetString(1)),
                PayloadJson = reader.GetString(2),
                State = ParseState(reader.GetString(3)),
                AttemptCount = reader.GetInt32(4),
                LastError = reader.IsDBNull(5) ? null : reader.GetString(5),
                LastErrorCode = reader.IsDBNull(6) ? null : reader.GetString(6),
                NextRetryAtUtc = reader.IsDBNull(7) ? null : DateTime.Parse(reader.GetString(7)),
                CreatedAtUtc = DateTime.Parse(reader.GetString(8)),
                UpdatedAtUtc = DateTime.Parse(reader.GetString(9)),
            });
        }

        return rows;
    }

    public async Task EnqueueAsync(OutboxOperation operation, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
INSERT INTO outbox_operations(op_id, op_type, payload_json, state, attempt_count, last_error, last_error_code, next_retry_at, created_at, updated_at)
VALUES ($op_id, $op_type, $payload_json, $state, $attempt_count, $last_error, $last_error_code, $next_retry_at, $created_at, $updated_at);";
        Bind(cmd, operation);
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task UpdateAsync(OutboxOperation operation, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
UPDATE outbox_operations SET
  op_type = $op_type,
  payload_json = $payload_json,
  state = $state,
  attempt_count = $attempt_count,
  last_error = $last_error,
  last_error_code = $last_error_code,
  next_retry_at = $next_retry_at,
  updated_at = $updated_at
WHERE op_id = $op_id;";
        Bind(cmd, operation);
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task RemoveAsync(Guid opId, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = "DELETE FROM outbox_operations WHERE op_id = $op_id;";
        cmd.Parameters.AddWithValue("$op_id", opId.ToString());
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task MarkNeedsReviewAsync(Guid opId, string reason, string? errorCode, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
UPDATE outbox_operations
SET state = 'needs_review',
    last_error = $last_error,
    last_error_code = $last_error_code,
    next_retry_at = NULL,
    updated_at = $updated_at
WHERE op_id = $op_id;";
        cmd.Parameters.AddWithValue("$op_id", opId.ToString());
        cmd.Parameters.AddWithValue("$last_error", reason);
        cmd.Parameters.AddWithValue("$last_error_code", (object?)errorCode ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
        await cmd.ExecuteNonQueryAsync(ct);
    }

    private static void Bind(Microsoft.Data.Sqlite.SqliteCommand cmd, OutboxOperation operation)
    {
        cmd.Parameters.AddWithValue("$op_id", operation.OpId.ToString());
        cmd.Parameters.AddWithValue("$op_type", ToDbOpType(operation.OpType));
        cmd.Parameters.AddWithValue("$payload_json", NormalizeJson(operation.PayloadJson));
        cmd.Parameters.AddWithValue("$state", operation.State == OutboxState.NeedsReview ? "needs_review" : "pending");
        cmd.Parameters.AddWithValue("$attempt_count", operation.AttemptCount);
        cmd.Parameters.AddWithValue("$last_error", (object?)operation.LastError ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$last_error_code", (object?)operation.LastErrorCode ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$next_retry_at", operation.NextRetryAtUtc?.ToString("O") ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("$created_at", operation.CreatedAtUtc.ToString("O"));
        cmd.Parameters.AddWithValue("$updated_at", operation.UpdatedAtUtc.ToString("O"));
    }

    private static string NormalizeJson(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return "{}";
        }

        try
        {
            using var doc = JsonDocument.Parse(json);
            return JsonSerializer.Serialize(doc);
        }
        catch
        {
            return "{}";
        }
    }

    private static OperationType ParseOpType(string value)
    {
        return value switch
        {
            "pallet.create" => OperationType.PalletCreate,
            "pallet.item_add" => OperationType.PalletItemAdd,
            "pallet.item_remove" => OperationType.PalletItemRemove,
            "pallet.complete" => OperationType.PalletComplete,
            _ => OperationType.PalletCreate,
        };
    }

    private static string ToDbOpType(OperationType value)
    {
        return value switch
        {
            OperationType.PalletCreate => "pallet.create",
            OperationType.PalletItemAdd => "pallet.item_add",
            OperationType.PalletItemRemove => "pallet.item_remove",
            OperationType.PalletComplete => "pallet.complete",
            _ => "pallet.create",
        };
    }

    private static OutboxState ParseState(string value)
    {
        return value == "needs_review" ? OutboxState.NeedsReview : OutboxState.Pending;
    }
}
