using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Infrastructure.Persistence;
using PalletManager.Infrastructure.Support;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class RuntimeSettingsRepository : IRuntimeSettingsService
{
    private readonly SqliteConnectionFactory _factory;
    private readonly ObservableValue<RuntimeSettings> _changes;

    public RuntimeSettingsRepository(SqliteConnectionFactory factory)
    {
        _factory = factory;
        _changes = new ObservableValue<RuntimeSettings>(new RuntimeSettings());
    }

    public IObservable<RuntimeSettings> Changes => _changes;

    public async Task<RuntimeSettings> GetAsync(CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var command = connection.CreateCommand();
        command.CommandText = @"
SELECT primary_api_base_url, fallback_api_base_url, lock_to_local_backend
FROM runtime_settings
WHERE id = 1;";

        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct))
        {
            var defaults = new RuntimeSettings
            {
                PrimaryApiBaseUrl = "http://127.0.0.1:8000/api/v1",
                FallbackApiBaseUrl = "http://localhost:8000/api/v1",
                LockToLocalBackend = false,
            };
            await SaveAsync(defaults, ct);
            return defaults;
        }

        var settings = new RuntimeSettings
        {
            PrimaryApiBaseUrl = reader.GetString(0),
            FallbackApiBaseUrl = reader.IsDBNull(1) ? null : reader.GetString(1),
            LockToLocalBackend = reader.GetInt64(2) == 1,
        };

        _changes.Set(settings);
        return settings;
    }

    public async Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var command = connection.CreateCommand();
        command.CommandText = @"
INSERT INTO runtime_settings(id, primary_api_base_url, fallback_api_base_url, lock_to_local_backend, updated_at)
VALUES (1, $primary, $fallback, $lock, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  primary_api_base_url = excluded.primary_api_base_url,
  fallback_api_base_url = excluded.fallback_api_base_url,
  lock_to_local_backend = excluded.lock_to_local_backend,
  updated_at = excluded.updated_at;";

        command.Parameters.AddWithValue("$primary", settings.PrimaryApiBaseUrl.TrimEnd('/'));
        command.Parameters.AddWithValue("$fallback", (object?)settings.FallbackApiBaseUrl?.TrimEnd('/') ?? DBNull.Value);
        command.Parameters.AddWithValue("$lock", settings.LockToLocalBackend ? 1 : 0);
        command.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
        await command.ExecuteNonQueryAsync(ct);

        _changes.Set(settings);
        return settings;
    }
}
