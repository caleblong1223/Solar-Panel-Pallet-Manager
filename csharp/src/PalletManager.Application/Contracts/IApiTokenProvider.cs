namespace PalletManager.Application.Contracts;

public interface IApiTokenProvider
{
    Task<string?> GetBearerTokenAsync(CancellationToken ct = default);
}
