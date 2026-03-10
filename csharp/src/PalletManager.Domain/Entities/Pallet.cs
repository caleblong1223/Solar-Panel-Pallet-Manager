namespace PalletManager.Domain.Entities;

public sealed class Pallet
{
    public int Id { get; set; }
    public int PalletNumber { get; set; }
    public string Status { get; set; } = "active";
    public string? TemplateType { get; set; }
    public int MaxPanels { get; set; }
    public int? CustomerId { get; set; }
    public DateTime CreatedAtUtc { get; set; }
    public DateTime? CompletedAtUtc { get; set; }
    public DateTime? DeletedAtUtc { get; set; }
    public int ItemCount { get; set; }
    public List<PalletItem> Items { get; set; } = new();
}
