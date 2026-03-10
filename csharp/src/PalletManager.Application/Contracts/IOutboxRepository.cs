using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface IOutboxRepository
{
    Task<IReadOnlyList<OutboxOperation>> ListAsync(CancellationToken ct = default);
    Task EnqueueAsync(OutboxOperation operation, CancellationToken ct = default);
    Task UpdateAsync(OutboxOperation operation, CancellationToken ct = default);
    Task RemoveAsync(Guid opId, CancellationToken ct = default);
    Task MarkNeedsReviewAsync(Guid opId, string reason, string? errorCode, CancellationToken ct = default);
}
