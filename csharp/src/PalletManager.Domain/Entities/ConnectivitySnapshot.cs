using PalletManager.Domain.Enums;

namespace PalletManager.Domain.Entities;

public sealed class ConnectivitySnapshot
{
    public ConnectionMode Mode { get; set; } = ConnectionMode.Online;
    public string ActiveBaseUrl { get; set; } = string.Empty;
    public bool Healthy { get; set; }
    public string Message { get; set; } = string.Empty;
    public DateTime CheckedAtUtc { get; set; }
}
