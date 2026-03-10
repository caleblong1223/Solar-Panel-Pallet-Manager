using PalletManager.Domain.Enums;

namespace PalletManager.Domain.Entities;

public sealed class OutboxOperation
{
    public Guid OpId { get; set; }
    public OperationType OpType { get; set; }
    public string PayloadJson { get; set; } = "{}";
    public OutboxState State { get; set; } = OutboxState.Pending;
    public int AttemptCount { get; set; }
    public string? LastError { get; set; }
    public string? LastErrorCode { get; set; }
    public DateTime? NextRetryAtUtc { get; set; }
    public DateTime CreatedAtUtc { get; set; }
    public DateTime UpdatedAtUtc { get; set; }
}
