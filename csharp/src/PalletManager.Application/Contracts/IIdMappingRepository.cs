namespace PalletManager.Application.Contracts;

public interface IIdMappingRepository
{
    Task<int?> ResolveRemoteIdAsync(string entityType, int localId, CancellationToken ct = default);
    Task SaveMappingAsync(string entityType, int localId, int remoteId, CancellationToken ct = default);
}
