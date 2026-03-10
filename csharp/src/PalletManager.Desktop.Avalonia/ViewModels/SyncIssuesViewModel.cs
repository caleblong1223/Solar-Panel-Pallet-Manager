using System.Collections.ObjectModel;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class SyncIssuesViewModel : ViewModelBase
{
    private readonly IOutboxRepository _outboxRepository;
    private readonly ISyncEngine _syncEngine;
    private bool _isSyncingNow;

    public SyncIssuesViewModel(IOutboxRepository outboxRepository, ISyncEngine syncEngine)
    {
        _outboxRepository = outboxRepository;
        _syncEngine = syncEngine;
        NeedsReview = new ObservableCollection<SyncIssueRow>();
        PendingErrors = new ObservableCollection<SyncIssueRow>();
    }

    public ObservableCollection<SyncIssueRow> NeedsReview { get; }
    public ObservableCollection<SyncIssueRow> PendingErrors { get; }

    public bool IsSyncingNow
    {
        get => _isSyncingNow;
        private set => SetProperty(ref _isSyncingNow, value);
    }

    public async Task RefreshAsync(CancellationToken ct = default)
    {
        var operations = await _outboxRepository.ListAsync(ct);

        NeedsReview.Clear();
        PendingErrors.Clear();

        foreach (var operation in operations.Where(static o => o.State == OutboxState.NeedsReview))
        {
            NeedsReview.Add(ToRow(operation));
        }

        foreach (var operation in operations.Where(static o => o.State == OutboxState.Pending && !string.IsNullOrWhiteSpace(o.LastError)))
        {
            PendingErrors.Add(ToRow(operation));
        }
    }

    public async Task RetryOperationAsync(Guid opId, CancellationToken ct = default)
    {
        var operations = await _outboxRepository.ListAsync(ct);
        var match = operations.FirstOrDefault(x => x.OpId == opId);
        if (match is null)
        {
            return;
        }

        var updated = new OutboxOperation
        {
            OpId = match.OpId,
            OpType = match.OpType,
            PayloadJson = match.PayloadJson,
            State = OutboxState.Pending,
            AttemptCount = match.AttemptCount,
            LastError = null,
            LastErrorCode = null,
            NextRetryAtUtc = null,
            CreatedAtUtc = match.CreatedAtUtc,
            UpdatedAtUtc = DateTime.UtcNow,
        };

        await _outboxRepository.UpdateAsync(updated, ct);
        await _syncEngine.TriggerNowAsync(ct);
        await RefreshAsync(ct);
    }

    public async Task DiscardOperationAsync(Guid opId, CancellationToken ct = default)
    {
        await _outboxRepository.RemoveAsync(opId, ct);
        await RefreshAsync(ct);
    }

    public async Task TriggerSyncNowAsync(CancellationToken ct = default)
    {
        IsSyncingNow = true;
        try
        {
            await _syncEngine.TriggerNowAsync(ct);
            await RefreshAsync(ct);
        }
        finally
        {
            IsSyncingNow = false;
        }
    }

    private static SyncIssueRow ToRow(OutboxOperation operation)
    {
        return new SyncIssueRow(
            operation.OpId,
            operation.OpType.ToString(),
            operation.State,
            operation.LastError,
            operation.LastErrorCode,
            operation.AttemptCount,
            operation.NextRetryAtUtc);
    }
}

public sealed record SyncIssueRow(
    Guid OpId,
    string OpType,
    OutboxState State,
    string? LastError,
    string? LastErrorCode,
    int AttemptCount,
    DateTime? NextRetryAtUtc);
