using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface ISyncEngine
{
    Task TriggerNowAsync(CancellationToken ct = default);
    IObservable<SyncState> State { get; }
}
