using PalletManager.Application.Contracts;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class AnonymousApiTokenProvider : IApiTokenProvider
{
    public Task<string?> GetBearerTokenAsync(CancellationToken ct = default)
    {
        return Task.FromResult<string?>(null);
    }
}
