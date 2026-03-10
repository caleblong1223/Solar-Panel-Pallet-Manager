using ClosedXML.Excel;
using PalletManager.Infrastructure.Spreadsheet;
using Xunit;

namespace PalletManager.ParityTests.Spreadsheet;

public sealed class ExportSpreadsheetParityTests
{
    [Fact]
    public void GoldenCsvFixture_ParsesWithExpectedShape()
    {
        var rows = ReadCsvMatrix("export_golden.csv");
        Assert.Equal(5, rows.Count);
        Assert.Equal(7, rows[0].Count);
        Assert.Equal("SerialNo", rows[0][0]);
        Assert.Equal("SN-2403004", rows[4][0]);
    }

    [Fact]
    public async Task GoldenXlsxRoundtrip_AfterEdit_MatchesExpectedFixtureAtCellLevel()
    {
        var service = new OpenXmlSpreadsheetService();
        var baselineRows = ReadCsvMatrix("export_golden.csv");
        var expectedRows = ReadCsvMatrix("export_golden_expected_after_edit.csv");

        var sourceBytes = BuildWorkbookFromRows("DATA", baselineRows);
        var loaded = await service.LoadAsync(sourceBytes);

        loaded.Sheets[0].Data[2][3] = "412.4";

        var savedBytes = await service.SaveAsync(loaded);
        var reloaded = await service.LoadAsync(savedBytes);
        var actualRows = reloaded.Sheets[0].Data;

        Assert.Equal(expectedRows.Count, actualRows.Count);
        for (var row = 0; row < expectedRows.Count; row++)
        {
            Assert.Equal(expectedRows[row].Count, actualRows[row].Count);
            for (var col = 0; col < expectedRows[row].Count; col++)
            {
                Assert.Equal(expectedRows[row][col], actualRows[row][col]);
            }
        }

        Assert.Equal("410.2", actualRows[1][3]);
        Assert.Equal("412.4", actualRows[2][3]);
        Assert.Equal("411.0", actualRows[3][3]);
    }

    [Fact]
    public async Task ProductionLikeWorkbook_AfterEdit_MatchesExpectedCellContracts_AndPreservesFormulas()
    {
        var service = new OpenXmlSpreadsheetService();
        var sourceBytes = BuildProductionLikeWorkbook();
        var loaded = await service.LoadAsync(sourceBytes);

        var dataSheet = loaded.Sheets.First(s => s.Name == "DATA");
        dataSheet.Data[2][1] = "415.0";

        var savedBytes = await service.SaveAsync(loaded);
        var reloaded = await service.LoadAsync(savedBytes);
        var expectedCells = ReadExpectedCells("production_like_expected_after_edit.cells");

        foreach (var expected in expectedCells)
        {
            var actual = ReadCellByAddress(reloaded, expected.Key);
            Assert.Equal(expected.Value, actual);
        }

        Assert.Equal("=COUNTA(DATA!A2:A200)", ReadCellByAddress(reloaded, "SUMMARY!B2"));
        Assert.Equal("=AVERAGE(DATA!B2:B200)", ReadCellByAddress(reloaded, "SUMMARY!B3"));
    }

    private static byte[] BuildWorkbookFromRows(string sheetName, IReadOnlyList<IReadOnlyList<string>> rows)
    {
        using var workbook = new XLWorkbook();
        var worksheet = workbook.AddWorksheet(sheetName);
        for (var row = 0; row < rows.Count; row++)
        {
            for (var col = 0; col < rows[row].Count; col++)
            {
                worksheet.Cell(row + 1, col + 1).Value = rows[row][col];
            }
        }

        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }

    private static List<List<string>> ReadCsvMatrix(string fileName)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "exports", fileName);
        var lines = File.ReadAllLines(path);
        return lines
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .Select(line => line.Split(',').Select(cell => cell.Trim()).ToList())
            .ToList();
    }

    private static byte[] BuildProductionLikeWorkbook()
    {
        using var workbook = new XLWorkbook();

        var data = workbook.AddWorksheet("DATA");
        data.Cell(1, 1).Value = "SerialNo";
        data.Cell(1, 2).Value = "Pm";
        data.Cell(1, 3).Value = "Voc";
        data.Cell(1, 4).Value = "Isc";
        data.Cell(1, 5).Value = "Vpm";
        data.Cell(2, 1).Value = "SN-9001";
        data.Cell(2, 2).Value = "410.2";
        data.Cell(2, 3).Value = "49.8";
        data.Cell(2, 4).Value = "10.12";
        data.Cell(2, 5).Value = "41.0";
        data.Cell(3, 1).Value = "SN-9002";
        data.Cell(3, 2).Value = "409.1";
        data.Cell(3, 3).Value = "49.5";
        data.Cell(3, 4).Value = "10.05";
        data.Cell(3, 5).Value = "40.8";
        data.Cell(8, 1).Value = "SN-9008";
        data.Cell(8, 2).Value = "407.7";
        data.Cell(8, 3).Value = "49.2";
        data.Cell(8, 4).Value = "9.98";
        data.Cell(8, 5).Value = "40.4";

        var summary = workbook.AddWorksheet("SUMMARY");
        summary.Cell(1, 1).Value = "Metric";
        summary.Cell(1, 2).Value = "Value";
        summary.Cell(2, 1).Value = "Count";
        summary.Cell(2, 2).FormulaA1 = "COUNTA(DATA!A2:A200)";
        summary.Cell(3, 1).Value = "AvgPm";
        summary.Cell(3, 2).FormulaA1 = "AVERAGE(DATA!B2:B200)";

        var audit = workbook.AddWorksheet("AUDIT");
        audit.Cell(1, 1).Value = "Note";
        audit.Cell(1, 2).Value = "Stamp";
        audit.Cell(2, 1).Value = "Imported";
        audit.Cell(2, 2).Value = "2026-03-10T08:30:00Z";

        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }

    private static Dictionary<string, string> ReadExpectedCells(string fileName)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "exports", fileName);
        return File
            .ReadAllLines(path)
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .Select(line => line.Split('|', 2))
            .ToDictionary(parts => parts[0].Trim(), parts => parts.Length > 1 ? parts[1] : string.Empty);
    }

    private static string ReadCellByAddress(PalletManager.Domain.Entities.WorkbookEditModel workbook, string qualifiedAddress)
    {
        var parts = qualifiedAddress.Split('!', 2);
        var sheetName = parts[0];
        var cellAddress = parts[1].ToUpperInvariant();
        var sheet = workbook.Sheets.First(s => s.Name == sheetName);

        var columnLetters = new string(cellAddress.TakeWhile(char.IsLetter).ToArray());
        var rowDigits = new string(cellAddress.SkipWhile(char.IsLetter).ToArray());
        var rowIndex = int.Parse(rowDigits) - 1;
        var columnIndex = ColumnIndexFromLabel(columnLetters) - 1;

        if (rowIndex < 0 || rowIndex >= sheet.Data.Count)
        {
            return string.Empty;
        }

        var row = sheet.Data[rowIndex];
        if (columnIndex < 0 || columnIndex >= row.Count)
        {
            return string.Empty;
        }

        return row[columnIndex];
    }

    private static int ColumnIndexFromLabel(string label)
    {
        var result = 0;
        foreach (var c in label)
        {
            result = (result * 26) + (c - 'A' + 1);
        }

        return result;
    }
}
