using PalletManager.Application.Contracts;
using PalletManager.Infrastructure.Persistence;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class IdMappingRepository : IIdMappingRepository
{
    private readonly SqliteConnectionFactory _factory;

    public IdMappingRepository(SqliteConnectionFactory factory)
    {
        _factory = factory;
    }

    public async Task<int?> ResolveRemoteIdAsync(string entityType, int localId, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT remote_id
FROM id_mappings
WHERE entity_type = $entity_type AND local_id = $local_id
LIMIT 1;";
        cmd.Parameters.AddWithValue("$entity_type", entityType);
        cmd.Parameters.AddWithValue("$local_id", localId);

        var result = await cmd.ExecuteScalarAsync(ct);
        if (result is null || result == DBNull.Value)
        {
            return null;
        }

        return Convert.ToInt32(result);
    }

    public async Task SaveMappingAsync(string entityType, int localId, int remoteId, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
INSERT INTO id_mappings(entity_type, local_id, remote_id, created_at)
VALUES ($entity_type, $local_id, $remote_id, $created_at)
ON CONFLICT(entity_type, local_id) DO UPDATE SET
  remote_id = excluded.remote_id;";

        cmd.Parameters.AddWithValue("$entity_type", entityType);
        cmd.Parameters.AddWithValue("$local_id", localId);
        cmd.Parameters.AddWithValue("$remote_id", remoteId);
        cmd.Parameters.AddWithValue("$created_at", DateTime.UtcNow.ToString("O"));
        await cmd.ExecuteNonQueryAsync(ct);
    }
}
