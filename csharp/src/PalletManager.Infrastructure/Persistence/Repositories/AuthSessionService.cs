using PalletManager.Application.Contracts;
using PalletManager.Infrastructure.Persistence;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class AuthSessionService : IAuthService
{
    private readonly SqliteConnectionFactory _factory;

    public AuthSessionService(SqliteConnectionFactory factory)
    {
        _factory = factory;
    }

    public async Task<string?> GetTokenAsync(CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT access_token FROM auth_session WHERE id = 1;";
        var result = await cmd.ExecuteScalarAsync(ct);
        return result == null || result == DBNull.Value ? null : Convert.ToString(result);
    }

    public async Task SetTokenAsync(string? token, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
INSERT INTO auth_session(id, access_token, user_json, session_mode, updated_at)
VALUES (1, $token, NULL, CASE WHEN $token IS NULL THEN 'anonymous' ELSE 'authenticated' END, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  access_token = excluded.access_token,
  session_mode = excluded.session_mode,
  updated_at = excluded.updated_at;";
        cmd.Parameters.AddWithValue("$token", (object?)token ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public Task ClearSessionAsync(CancellationToken ct = default)
    {
        return SetTokenAsync(null, ct);
    }
}
