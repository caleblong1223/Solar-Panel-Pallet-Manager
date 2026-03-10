using Microsoft.Data.Sqlite;

namespace PalletManager.Infrastructure.Persistence;

public sealed class MigrationRunner
{
    private readonly SqliteConnectionFactory _factory;
    private readonly string _migrationDirectory;

    public MigrationRunner(SqliteConnectionFactory factory, string migrationDirectory)
    {
        _factory = factory;
        _migrationDirectory = migrationDirectory;
    }

    public async Task RunAsync(CancellationToken ct = default)
    {
        var files = Directory
            .GetFiles(_migrationDirectory, "*.sql", SearchOption.TopDirectoryOnly)
            .OrderBy(static path => path, StringComparer.Ordinal)
            .ToList();

        await using var connection = await _factory.OpenAsync(ct);
        await EnsureMigrationsTableAsync(connection, ct);

        foreach (var filePath in files)
        {
            var fileName = Path.GetFileName(filePath);
            if (!TryGetVersion(fileName, out var version))
            {
                continue;
            }

            if (await IsAppliedAsync(connection, version, ct))
            {
                continue;
            }

            var sql = await File.ReadAllTextAsync(filePath, ct);
            await using var command = connection.CreateCommand();
            command.CommandText = sql;
            await command.ExecuteNonQueryAsync(ct);

            await using var insert = connection.CreateCommand();
            insert.CommandText = "INSERT INTO schema_migrations(version, applied_at) VALUES ($version, $applied_at);";
            insert.Parameters.AddWithValue("$version", version);
            insert.Parameters.AddWithValue("$applied_at", DateTime.UtcNow.ToString("O"));
            await insert.ExecuteNonQueryAsync(ct);
        }
    }

    private static async Task EnsureMigrationsTableAsync(SqliteConnection connection, CancellationToken ct)
    {
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);";
        await cmd.ExecuteNonQueryAsync(ct);
    }

    private static bool TryGetVersion(string fileName, out int version)
    {
        version = 0;
        var parts = fileName.Split('_', StringSplitOptions.RemoveEmptyEntries);
        return parts.Length > 0 && int.TryParse(parts[0], out version);
    }

    private static async Task<bool> IsAppliedAsync(SqliteConnection connection, int version, CancellationToken ct)
    {
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT 1 FROM schema_migrations WHERE version = $version LIMIT 1;";
        cmd.Parameters.AddWithValue("$version", version);
        var result = await cmd.ExecuteScalarAsync(ct);
        return result is not null;
    }
}
