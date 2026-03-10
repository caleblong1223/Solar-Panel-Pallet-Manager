namespace PalletManager.Domain.Entities;

public sealed class PalletItem
{
    public int Id { get; set; }
    public string Serial { get; set; } = string.Empty;
    public int SlotIndex { get; set; }
    public DateTime AddedAtUtc { get; set; }
}
