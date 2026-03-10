namespace PalletManager.Domain.Entities;

public sealed class ExportRecord
{
    public int Id { get; set; }
    public int PalletId { get; set; }
    public string TemplateType { get; set; } = string.Empty;
    public DateOnly? PackoutDate { get; set; }
    public string ObjectKey { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public string MimeType { get; set; } = "application/pdf";
    public long? SizeBytes { get; set; }
    public string? ChecksumSha256 { get; set; }
    public DateTime CreatedAtUtc { get; set; }
}
