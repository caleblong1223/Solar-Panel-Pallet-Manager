using ClosedXML.Excel;
using PalletManager.Infrastructure.Spreadsheet;
using Xunit;
using System.Diagnostics;

namespace PalletManager.UnitTests.Spreadsheet;

public sealed class OpenXmlSpreadsheetServiceTests
{
    [Fact]
    public async Task SaveAndLoadAsync_RoundtripsWorkbookStructureAndValues()
    {
        var service = new OpenXmlSpreadsheetService();
        var sourceBytes = BuildWorkbookBytes();

        var loaded = await service.LoadAsync(sourceBytes);
        loaded.Sheets[0].Data[1][1] = "UPDATED";
        loaded.Sheets[1].Data.Add(new List<string> { "A3", "B3" });

        var savedBytes = await service.SaveAsync(loaded);
        var reloaded = await service.LoadAsync(savedBytes);

        Assert.Equal(2, reloaded.Sheets.Count);
        Assert.Equal("DATA", reloaded.Sheets[0].Name);
        Assert.Equal("SUMMARY", reloaded.Sheets[1].Name);
        Assert.Equal("Serial", reloaded.Sheets[0].Data[0][0]);
        Assert.Equal("UPDATED", reloaded.Sheets[0].Data[1][1]);
        Assert.Equal("A3", reloaded.Sheets[1].Data[2][0]);
        Assert.Equal("B3", reloaded.Sheets[1].Data[2][1]);
    }

    [Fact]
    public async Task SaveAndLoadAsync_LargeWorkbookCompletesWithinBudget()
    {
        var service = new OpenXmlSpreadsheetService();
        var sourceBytes = BuildLargeWorkbookBytes(rows: 400, columns: 24, sheets: 3);

        var loadWatch = Stopwatch.StartNew();
        var loaded = await service.LoadAsync(sourceBytes);
        loadWatch.Stop();

        var saveWatch = Stopwatch.StartNew();
        var savedBytes = await service.SaveAsync(loaded);
        saveWatch.Stop();

        Assert.Equal(3, loaded.Sheets.Count);
        Assert.True(savedBytes.Length > 0);
        Assert.True(loadWatch.Elapsed < TimeSpan.FromSeconds(5), $"Load exceeded budget: {loadWatch.Elapsed}.");
        Assert.True(saveWatch.Elapsed < TimeSpan.FromSeconds(5), $"Save exceeded budget: {saveWatch.Elapsed}.");
    }

    [Fact]
    public async Task SaveAsync_NormalizesDuplicateAndInvalidSheetNames()
    {
        var service = new OpenXmlSpreadsheetService();
        var workbook = await service.LoadAsync(BuildWorkbookBytes());

        workbook.Sheets[0].Name = "A/Very:Long?Sheet*Name[invalid]1234567890";
        workbook.Sheets[1].Name = "A/Very:Long?Sheet*Name[invalid]1234567890";

        var bytes = await service.SaveAsync(workbook);
        var roundtrip = await service.LoadAsync(bytes);

        Assert.Equal(2, roundtrip.Sheets.Count);
        Assert.NotEqual(roundtrip.Sheets[0].Name, roundtrip.Sheets[1].Name);
        Assert.True(roundtrip.Sheets.All(s => s.Name.Length <= 31));
        Assert.True(roundtrip.Sheets.All(s => !s.Name.Contains('/')));
    }

    [Fact]
    public async Task SaveAndLoadAsync_PreservesFormulaCellsAsFormulas()
    {
        var service = new OpenXmlSpreadsheetService();
        var sourceBytes = BuildWorkbookWithFormulaBytes();

        var loaded = await service.LoadAsync(sourceBytes);
        var summary = loaded.Sheets.First(s => s.Name == "SUMMARY");
        Assert.Equal("=COUNTA(DATA!A2:A10)", summary.Data[1][1]);

        loaded.Sheets.First(s => s.Name == "DATA").Data[1][1] = "420.5";
        var saved = await service.SaveAsync(loaded);
        var reloaded = await service.LoadAsync(saved);
        var reloadedSummary = reloaded.Sheets.First(s => s.Name == "SUMMARY");

        Assert.Equal("=COUNTA(DATA!A2:A10)", reloadedSummary.Data[1][1]);
    }

    private static byte[] BuildWorkbookBytes()
    {
        using var workbook = new XLWorkbook();

        var data = workbook.AddWorksheet("DATA");
        data.Cell(1, 1).Value = "Serial";
        data.Cell(1, 2).Value = "Pm";
        data.Cell(2, 1).Value = "SN-1001";
        data.Cell(2, 2).Value = "415.9";

        var summary = workbook.AddWorksheet("SUMMARY");
        summary.Cell(1, 1).Value = "Metric";
        summary.Cell(1, 2).Value = "Value";
        summary.Cell(2, 1).Value = "Total";
        summary.Cell(2, 2).Value = "1";

        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }

    private static byte[] BuildLargeWorkbookBytes(int rows, int columns, int sheets)
    {
        using var workbook = new XLWorkbook();
        for (var sheetIndex = 0; sheetIndex < sheets; sheetIndex++)
        {
            var worksheet = workbook.AddWorksheet($"Sheet{sheetIndex + 1}");
            for (var row = 1; row <= rows; row++)
            {
                for (var col = 1; col <= columns; col++)
                {
                    worksheet.Cell(row, col).Value = $"R{row}C{col}";
                }
            }
        }

        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }

    private static byte[] BuildWorkbookWithFormulaBytes()
    {
        using var workbook = new XLWorkbook();
        var data = workbook.AddWorksheet("DATA");
        data.Cell(1, 1).Value = "Serial";
        data.Cell(1, 2).Value = "Pm";
        data.Cell(2, 1).Value = "SN-7001";
        data.Cell(2, 2).Value = "410.2";

        var summary = workbook.AddWorksheet("SUMMARY");
        summary.Cell(1, 1).Value = "Metric";
        summary.Cell(1, 2).Value = "Value";
        summary.Cell(2, 1).Value = "Count";
        summary.Cell(2, 2).FormulaA1 = "COUNTA(DATA!A2:A10)";

        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }
}
