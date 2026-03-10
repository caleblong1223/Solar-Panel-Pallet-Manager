namespace PalletManager.Domain.Entities;

public sealed class BuilderDraft
{
    public Pallet? ActivePallet { get; set; }
    public List<string> FallbackSerials { get; set; } = new();
    public int? SelectedCustomerId { get; set; }
    public string TemplateType { get; set; } = "200WT";
    public int PalletSize { get; set; } = 25;
    public DateOnly PackoutDate { get; set; } = DateOnly.FromDateTime(DateTime.UtcNow);
    public string? PalletNumberDraft { get; set; }
}
