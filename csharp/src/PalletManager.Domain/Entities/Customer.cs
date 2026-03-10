namespace PalletManager.Domain.Entities;

public sealed class Customer
{
    public int Id { get; set; }
    public string DisplayName { get; set; } = string.Empty;
    public string? ContactName { get; set; }
    public string? BusinessName { get; set; }
    public string? Email { get; set; }
    public string? Phone { get; set; }
    public string? Address { get; set; }
    public string? City { get; set; }
    public string? State { get; set; }
    public string? ZipCode { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTime? CreatedAtUtc { get; set; }
}
