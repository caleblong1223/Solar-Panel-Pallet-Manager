namespace PalletManager.Domain.Entities;

public sealed class WorkbookEditModel
{
    public List<WorkbookSheet> Sheets { get; set; } = new();
}

public sealed class WorkbookSheet
{
    public string Name { get; set; } = string.Empty;
    public List<List<string>> Data { get; set; } = new();
}
