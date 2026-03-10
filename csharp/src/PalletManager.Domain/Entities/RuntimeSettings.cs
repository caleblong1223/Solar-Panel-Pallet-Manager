namespace PalletManager.Domain.Entities;

public sealed class RuntimeSettings
{
    public string PrimaryApiBaseUrl { get; set; } = "http://127.0.0.1:8000/api/v1";
    public string? FallbackApiBaseUrl { get; set; } = "http://localhost:8000/api/v1";
    public bool LockToLocalBackend { get; set; }
}
