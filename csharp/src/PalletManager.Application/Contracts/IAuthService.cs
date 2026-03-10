namespace PalletManager.Application.Contracts;

public interface IAuthService
{
    Task<string?> GetTokenAsync(CancellationToken ct = default);
    Task SetTokenAsync(string? token, CancellationToken ct = default);
    Task ClearSessionAsync(CancellationToken ct = default);
}
