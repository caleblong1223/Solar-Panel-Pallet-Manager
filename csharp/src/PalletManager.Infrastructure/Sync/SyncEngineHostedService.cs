using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using PalletManager.Domain.Errors;
using PalletManager.Infrastructure.Support;

namespace PalletManager.Infrastructure.Sync;

public sealed class SyncEngineHostedService : ISyncEngine
{
    private readonly IOutboxRepository _outboxRepository;
    private readonly IApiClient _apiClient;
    private readonly IAuthService _authService;
    private readonly IIdMappingRepository _idMappingRepository;
    private readonly ObservableValue<SyncState> _state;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly Timer _timer;

    public SyncEngineHostedService(
        IOutboxRepository outboxRepository,
        IApiClient apiClient,
        IAuthService authService,
        IIdMappingRepository idMappingRepository)
    {
        _outboxRepository = outboxRepository;
        _apiClient = apiClient;
        _authService = authService;
        _idMappingRepository = idMappingRepository;

        _state = new ObservableValue<SyncState>(new SyncState
        {
            Syncing = false,
            LastSyncAtUtc = null,
            PendingCount = 0,
            FailedCount = 0,
            NeedsReviewCount = 0,
        });

        _timer = new Timer(_ => _ = TriggerNowAsync(), null, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(10));
    }

    public IObservable<SyncState> State => _state;

    public async Task TriggerNowAsync(CancellationToken ct = default)
    {
        if (!await _gate.WaitAsync(0, ct))
        {
            return;
        }

        try
        {
            await ReplayInternalAsync(ct);
        }
        finally
        {
            _gate.Release();
        }
    }

    private async Task ReplayInternalAsync(CancellationToken ct)
    {
        await PublishStateAsync(syncing: true, ct);

        var token = await _authService.GetTokenAsync(ct) ?? string.Empty;
        var operations = await _outboxRepository.ListAsync(ct);

        foreach (var operation in operations)
        {
            if (ct.IsCancellationRequested)
            {
                break;
            }

            if (operation.State == OutboxState.NeedsReview)
            {
                continue;
            }

            if (!IsRetryReady(operation))
            {
                continue;
            }

            try
            {
                await ReplayOperationAsync(operation, token, ct);
                await _outboxRepository.RemoveAsync(operation.OpId, ct);
            }
            catch (ApiError apiError) when (apiError.StatusCode is 409 or 422)
            {
                await _outboxRepository.MarkNeedsReviewAsync(operation.OpId, apiError.Message, apiError.ErrorCode, ct);
            }
            catch (ApiError apiError) when (
                operation.OpType == OperationType.PalletItemRemove &&
                (apiError.StatusCode == 404 || string.Equals(apiError.ErrorCode, "PALLET_ITEM_NOT_FOUND", StringComparison.OrdinalIgnoreCase)))
            {
                // Item already absent remotely; treat as replay success.
                await _outboxRepository.RemoveAsync(operation.OpId, ct);
            }
            catch (Exception ex)
            {
                var updated = new OutboxOperation
                {
                    OpId = operation.OpId,
                    OpType = operation.OpType,
                    PayloadJson = operation.PayloadJson,
                    State = operation.State,
                    AttemptCount = operation.AttemptCount + 1,
                    LastError = ex.Message,
                    LastErrorCode = ex is ApiError api ? api.ErrorCode : null,
                    NextRetryAtUtc = DateTime.UtcNow.Add(BackoffPolicy.ForAttempt(operation.AttemptCount + 1)),
                    CreatedAtUtc = operation.CreatedAtUtc,
                    UpdatedAtUtc = DateTime.UtcNow,
                };
                await _outboxRepository.UpdateAsync(updated, ct);
            }
        }

        await PublishStateAsync(syncing: false, ct);
    }

    private async Task ReplayOperationAsync(OutboxOperation operation, string token, CancellationToken ct)
    {
        using var payload = ParsePayload(operation.PayloadJson);
        var root = payload.RootElement;

        switch (operation.OpType)
        {
            case OperationType.PalletCreate:
            {
                var localPalletId = ReadInt(root, "local_pallet_id")
                    ?? ReadInt(root, "localPalletId")
                    ?? ReadInt(root, "pallet_id")
                    ?? throw new InvalidOperationException("pallet.create missing local_pallet_id");
                var maxPanels = ReadInt(root, "max_panels")
                    ?? ReadInt(root, "maxPanels")
                    ?? throw new InvalidOperationException("pallet.create missing max_panels");
                var templateType = ReadString(root, "template_type") ?? ReadString(root, "templateType");
                var customerId = ReadInt(root, "customer_id") ?? ReadInt(root, "customerId");

                var created = await _apiClient.PostAsync<PalletCreateResponse>(
                    "/pallets",
                    new Dictionary<string, object?>
                    {
                        ["max_panels"] = maxPanels,
                        ["template_type"] = templateType,
                        ["customer_id"] = customerId,
                    },
                    token,
                    new Dictionary<string, string>
                    {
                        ["X-Client-Operation-Id"] = operation.OpId.ToString(),
                    },
                    ct);

                if (created.Id > 0)
                {
                    await _idMappingRepository.SaveMappingAsync("pallet", localPalletId, created.Id, ct);
                }

                return;
            }

            case OperationType.PalletItemAdd:
            {
                var rawPalletId = ReadInt(root, "pallet_id")
                    ?? ReadInt(root, "palletId")
                    ?? throw new InvalidOperationException("pallet.item_add missing pallet_id");
                var palletId = await ResolvePalletIdAsync(rawPalletId, ct);
                var serial = (ReadString(root, "serial") ?? string.Empty).Trim().ToUpperInvariant();
                if (string.IsNullOrWhiteSpace(serial))
                {
                    throw new InvalidOperationException("pallet.item_add missing serial");
                }

                var allowMissing = ReadBool(root, "allow_missing_sim_data")
                    ?? ReadBool(root, "allowMissingSimData")
                    ?? false;

                _ = await _apiClient.PostAsync<object>(
                    $"/pallets/{palletId}/items",
                    new Dictionary<string, object?>
                    {
                        ["serial"] = serial,
                        ["allow_missing_sim_data"] = allowMissing,
                    },
                    token,
                    new Dictionary<string, string>
                    {
                        ["X-Client-Operation-Id"] = operation.OpId.ToString(),
                    },
                    ct);
                return;
            }

            case OperationType.PalletItemRemove:
            {
                var rawPalletId = ReadInt(root, "pallet_id")
                    ?? ReadInt(root, "palletId")
                    ?? throw new InvalidOperationException("pallet.item_remove missing pallet_id");
                var palletId = await ResolvePalletIdAsync(rawPalletId, ct);
                var itemId = ReadInt(root, "item_id") ?? ReadInt(root, "itemId") ?? -1;

                if (itemId <= 0)
                {
                    var serial = (ReadString(root, "serial") ?? string.Empty).Trim().ToUpperInvariant();
                    if (string.IsNullOrWhiteSpace(serial))
                    {
                        throw new InvalidOperationException("pallet.item_remove missing item_id and serial fallback");
                    }

                    var pallet = await _apiClient.GetAsync<ApiPalletDetail>($"/pallets/{palletId}", token, ct);
                    var matched = pallet.Items.FirstOrDefault(i => string.Equals(i.Serial, serial, StringComparison.OrdinalIgnoreCase));
                    if (matched is null)
                    {
                        // Already absent remotely; treat as success.
                        return;
                    }

                    itemId = matched.Id;
                }

                await _apiClient.DeleteAsync(
                    $"/pallets/{palletId}/items/{itemId}",
                    token,
                    new Dictionary<string, string>
                    {
                        ["X-Client-Operation-Id"] = operation.OpId.ToString(),
                    },
                    ct);
                return;
            }

            case OperationType.PalletComplete:
            {
                var rawPalletId = ReadInt(root, "pallet_id")
                    ?? ReadInt(root, "palletId")
                    ?? throw new InvalidOperationException("pallet.complete missing pallet_id");
                var palletId = await ResolvePalletIdAsync(rawPalletId, ct);

                _ = await _apiClient.PostAsync<object>(
                    $"/pallets/{palletId}/complete",
                    null,
                    token,
                    new Dictionary<string, string>
                    {
                        ["X-Client-Operation-Id"] = operation.OpId.ToString(),
                    },
                    ct);
                return;
            }

            default:
                throw new InvalidOperationException($"Unsupported operation type {operation.OpType}");
        }
    }

    private async Task<int> ResolvePalletIdAsync(int rawPalletId, CancellationToken ct)
    {
        if (rawPalletId > 0)
        {
            return rawPalletId;
        }

        var mapped = await _idMappingRepository.ResolveRemoteIdAsync("pallet", rawPalletId, ct);
        if (!mapped.HasValue || mapped.Value <= 0)
        {
            throw new InvalidOperationException($"Unable to resolve local pallet id {rawPalletId}.");
        }

        return mapped.Value;
    }

    private async Task PublishStateAsync(bool syncing, CancellationToken ct)
    {
        var operations = await _outboxRepository.ListAsync(ct);
        var failed = operations.Count(static x => x.State == OutboxState.Pending && !string.IsNullOrWhiteSpace(x.LastError));
        var review = operations.Count(static x => x.State == OutboxState.NeedsReview);

        _state.Set(new SyncState
        {
            Syncing = syncing,
            LastSyncAtUtc = DateTime.UtcNow,
            PendingCount = operations.Count,
            FailedCount = failed,
            NeedsReviewCount = review,
        });
    }

    private static bool IsRetryReady(OutboxOperation operation)
    {
        return operation.NextRetryAtUtc is null || operation.NextRetryAtUtc <= DateTime.UtcNow;
    }

    private static JsonDocument ParsePayload(string payloadJson)
    {
        if (string.IsNullOrWhiteSpace(payloadJson))
        {
            return JsonDocument.Parse("{}");
        }

        return JsonDocument.Parse(payloadJson);
    }

    private static int? ReadInt(JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var value))
        {
            return null;
        }

        if (value.ValueKind == JsonValueKind.Number && value.TryGetInt32(out var i))
        {
            return i;
        }

        if (value.ValueKind == JsonValueKind.String && int.TryParse(value.GetString(), out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static string? ReadString(JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var value))
        {
            return null;
        }

        return value.ValueKind == JsonValueKind.String ? value.GetString() : value.ToString();
    }

    private static bool? ReadBool(JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var value))
        {
            return null;
        }

        return value.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.String when bool.TryParse(value.GetString(), out var parsed) => parsed,
            _ => null,
        };
    }

    private sealed class PalletCreateResponse
    {
        public int Id { get; set; }
    }

    private sealed class ApiPalletDetail
    {
        public List<ApiPalletItem> Items { get; set; } = new();
    }

    private sealed class ApiPalletItem
    {
        public int Id { get; set; }
        public string Serial { get; set; } = string.Empty;
    }
}
