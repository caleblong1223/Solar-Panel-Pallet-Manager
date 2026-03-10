using PalletManager.Domain.Entities;

namespace PalletManager.Application.Contracts;

public interface IBuilderDraftRepository
{
    Task<BuilderDraft?> GetAsync(CancellationToken ct = default);
    Task SaveAsync(BuilderDraft draft, CancellationToken ct = default);
    Task ClearAsync(CancellationToken ct = default);
}
