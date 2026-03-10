using ClosedXML.Excel;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;

namespace PalletManager.Infrastructure.Spreadsheet;

public sealed class OpenXmlSpreadsheetService : ISpreadsheetService
{
    public Task<WorkbookEditModel> LoadAsync(byte[] xlsxBytes, CancellationToken ct = default)
    {
        ct.ThrowIfCancellationRequested();

        if (xlsxBytes.Length == 0)
        {
            return Task.FromResult(new WorkbookEditModel());
        }

        using var stream = new MemoryStream(xlsxBytes);
        using var workbook = new XLWorkbook(stream);

        var model = new WorkbookEditModel();
        foreach (var worksheet in workbook.Worksheets)
        {
            ct.ThrowIfCancellationRequested();
            var sheet = new WorkbookSheet { Name = worksheet.Name };
            var usedRange = worksheet.RangeUsed();
            if (usedRange is null)
            {
                model.Sheets.Add(sheet);
                continue;
            }

            for (var row = usedRange.FirstRow().RowNumber(); row <= usedRange.LastRow().RowNumber(); row++)
            {
                var rowValues = new List<string>();
                for (var col = usedRange.FirstColumn().ColumnNumber(); col <= usedRange.LastColumn().ColumnNumber(); col++)
                {
                    ct.ThrowIfCancellationRequested();
                    var cellValue = ReadCell(worksheet.Cell(row, col));
                    rowValues.Add(cellValue);
                }
                sheet.Data.Add(rowValues);
            }

            model.Sheets.Add(sheet);
        }

        return Task.FromResult(model);
    }

    public Task<byte[]> SaveAsync(WorkbookEditModel workbook, CancellationToken ct = default)
    {
        ct.ThrowIfCancellationRequested();

        using var xlsx = new XLWorkbook();
        var usedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var sourceSheet in workbook.Sheets)
        {
            ct.ThrowIfCancellationRequested();
            var name = ToUniqueSheetName(sourceSheet.Name, usedNames);
            var worksheet = xlsx.AddWorksheet(name);

            for (var rowIndex = 0; rowIndex < sourceSheet.Data.Count; rowIndex++)
            {
                var row = sourceSheet.Data[rowIndex];
                for (var colIndex = 0; colIndex < row.Count; colIndex++)
                {
                    ct.ThrowIfCancellationRequested();
                    WriteCell(worksheet.Cell(rowIndex + 1, colIndex + 1), row[colIndex]);
                }
            }
        }

        if (xlsx.Worksheets.Count == 0)
        {
            xlsx.AddWorksheet("Sheet1");
        }

        using var stream = new MemoryStream();
        xlsx.SaveAs(stream);
        return Task.FromResult(stream.ToArray());
    }

    private static string ReadCell(IXLCell cell)
    {
        if (cell.HasFormula)
        {
            return $"={cell.FormulaA1}";
        }

        return cell.GetFormattedString();
    }

    private static void WriteCell(IXLCell cell, string value)
    {
        if (!string.IsNullOrEmpty(value) && value.StartsWith('='))
        {
            cell.FormulaA1 = value[1..];
            return;
        }

        cell.Value = value;
    }

    private static string ToUniqueSheetName(string requestedName, ISet<string> usedNames)
    {
        var invalidCharacters = new[] { ':', '\\', '/', '?', '*', '[', ']' };
        var baseName = string.IsNullOrWhiteSpace(requestedName) ? "Sheet" : requestedName.Trim();
        foreach (var invalid in invalidCharacters)
        {
            baseName = baseName.Replace(invalid, '_');
        }

        if (baseName.Length > 31)
        {
            baseName = baseName[..31];
        }

        if (baseName.Length == 0)
        {
            baseName = "Sheet";
        }

        var candidate = baseName;
        var suffix = 1;
        while (!usedNames.Add(candidate))
        {
            var suffixText = $"_{suffix++}";
            var maxBaseLength = Math.Max(1, 31 - suffixText.Length);
            var truncatedBase = baseName.Length > maxBaseLength ? baseName[..maxBaseLength] : baseName;
            candidate = truncatedBase + suffixText;
        }

        return candidate;
    }
}
