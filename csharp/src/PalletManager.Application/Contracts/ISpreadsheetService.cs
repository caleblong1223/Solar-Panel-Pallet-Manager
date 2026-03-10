using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface ISpreadsheetService
{
    Task<WorkbookEditModel> LoadAsync(byte[] xlsxBytes, CancellationToken ct = default);
    Task<byte[]> SaveAsync(WorkbookEditModel workbook, CancellationToken ct = default);
}
