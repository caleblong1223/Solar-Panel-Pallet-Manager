using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface IConnectivityService
{
    Task<ConnectivitySnapshot> ProbeAsync(CancellationToken ct = default);
    IObservable<ConnectivitySnapshot> StatusChanges { get; }
}
