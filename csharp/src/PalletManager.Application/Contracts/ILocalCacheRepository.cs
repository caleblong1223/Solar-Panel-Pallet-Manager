using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface ILocalCacheRepository
{
    Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default);
    Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default);

    Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default);
    Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default);

    Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default);
    Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default);
}
