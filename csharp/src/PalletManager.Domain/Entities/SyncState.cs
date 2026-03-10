namespace PalletManager.Domain.Entities;

public sealed class SyncState
{
    public bool Syncing { get; set; }
    public DateTime? LastSyncAtUtc { get; set; }
    public int PendingCount { get; set; }
    public int FailedCount { get; set; }
    public int NeedsReviewCount { get; set; }
}
