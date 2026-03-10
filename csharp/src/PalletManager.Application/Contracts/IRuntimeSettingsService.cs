using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface IRuntimeSettingsService
{
    Task<RuntimeSettings> GetAsync(CancellationToken ct = default);
    Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default);
    IObservable<RuntimeSettings> Changes { get; }
}
