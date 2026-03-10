using System.Collections.ObjectModel;
using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using System.Text.Json.Serialization;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class BuilderViewModel : ViewModelBase
{
    private readonly IBuilderDraftRepository _draftRepository;
    private readonly IOutboxRepository _outboxRepository;
    private readonly IClock _clock;
    private readonly IApiClient _apiClient;
    private readonly IApiTokenProvider _authService;
    private readonly HashSet<string> _fallbackSerials = new(StringComparer.OrdinalIgnoreCase);

    private Pallet? _activePallet;
    private string _serialInput = string.Empty;
    private string _selectedTemplateType = "200WT";
    private int _selectedPalletSize = 25;
    private string _palletNumberDraft = "1";
    private string _statusMessage = string.Empty;
    private DateOnly _packoutDate = DateOnly.FromDateTime(DateTime.UtcNow);
    private int _draftSeed = -1;
    private bool _isMissingSimPromptOpen;
    private string _missingSimSerial = string.Empty;
    private string _missingSimCancelText = "Keep it off the pallet";
    private string? _pendingSerialForDecision;

    public BuilderViewModel(
        IBuilderDraftRepository draftRepository,
        IOutboxRepository outboxRepository,
        IClock clock,
        IApiClient apiClient,
        IApiTokenProvider authService)
    {
        _draftRepository = draftRepository;
        _outboxRepository = outboxRepository;
        _clock = clock;
        _apiClient = apiClient;
        _authService = authService;

        TemplateOptions = new ObservableCollection<string>
        {
            "200WT", "220WT", "220M6", "330WT", "450WT", "450BT",
        };

        PalletSizeOptions = new ObservableCollection<int> { 25, 26, 30, 35 };
        Items = new ObservableCollection<PalletItem>();

        LoadDraft();
    }

    public ObservableCollection<string> TemplateOptions { get; }
    public ObservableCollection<int> PalletSizeOptions { get; }
    public ObservableCollection<PalletItem> Items { get; }

    public bool HasActivePallet => _activePallet is not null;
    public int FallbackSerialCount => _fallbackSerials.Count;

    public string SelectedTemplateType
    {
        get => _selectedTemplateType;
        set
        {
            if (SetProperty(ref _selectedTemplateType, value))
            {
                _ = PersistDraftAsync();
            }
        }
    }

    public int SelectedPalletSize
    {
        get => _selectedPalletSize;
        set
        {
            if (value <= 0)
            {
                return;
            }

            if (_activePallet is not null && value < _activePallet.ItemCount)
            {
                StatusMessage = $"Pallet size cannot be lower than current panel count ({_activePallet.ItemCount})";
                return;
            }

            if (SetProperty(ref _selectedPalletSize, value))
            {
                if (_activePallet is not null)
                {
                    _activePallet.MaxPanels = value;
                    RaisePropertyChanged(nameof(ActiveSummary));
                }

                _ = PersistDraftAsync();
            }
        }
    }

    public string PalletNumberDraft
    {
        get => _palletNumberDraft;
        set
        {
            if (SetProperty(ref _palletNumberDraft, value))
            {
                _ = PersistDraftAsync();
            }
        }
    }

    public string PackoutDate
    {
        get => _packoutDate.ToString("yyyy-MM-dd");
        set
        {
            if (!DateOnly.TryParse(value, out var parsed))
            {
                return;
            }

            _packoutDate = parsed;
            RaisePropertyChanged();
            _ = PersistDraftAsync();
        }
    }

    public string SerialInput
    {
        get => _serialInput;
        set => SetProperty(ref _serialInput, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public bool IsMissingSimPromptOpen
    {
        get => _isMissingSimPromptOpen;
        private set => SetProperty(ref _isMissingSimPromptOpen, value);
    }

    public string MissingSimSerial
    {
        get => _missingSimSerial;
        private set => SetProperty(ref _missingSimSerial, value);
    }

    public string MissingSimCancelText
    {
        get => _missingSimCancelText;
        private set => SetProperty(ref _missingSimCancelText, value);
    }

    public string ActiveSummary
    {
        get
        {
            if (_activePallet is null)
            {
                return "No active pallet.";
            }

            var remaining = Math.Max(0, _activePallet.MaxPanels - _activePallet.ItemCount);
            return $"Pallet #{_activePallet.PalletNumber} • {_activePallet.ItemCount}/{_activePallet.MaxPanels} • {remaining} remaining";
        }
    }

    public async Task StartNewPalletAsync(CancellationToken ct = default)
    {
        var nextNumber = int.TryParse(PalletNumberDraft, out var parsed) && parsed > 0 ? parsed : Math.Abs(_draftSeed);

        _activePallet = new Pallet
        {
            Id = _draftSeed,
            PalletNumber = nextNumber,
            Status = "active",
            TemplateType = SelectedTemplateType,
            MaxPanels = SelectedPalletSize,
            CreatedAtUtc = _clock.UtcNow,
            ItemCount = 0,
            Items = new List<PalletItem>(),
        };

        await EnqueueAsync(OperationType.PalletCreate, new Dictionary<string, object?>
        {
            ["local_pallet_id"] = _activePallet.Id,
            ["max_panels"] = _activePallet.MaxPanels,
            ["template_type"] = _activePallet.TemplateType,
            ["customer_id"] = _activePallet.CustomerId,
        }, ct);

        _draftSeed -= 1;
        StatusMessage = $"Pallet #{_activePallet.PalletNumber} started.";

        Items.Clear();
        SerialInput = string.Empty;

        RaisePropertyChanged(nameof(HasActivePallet));
        RaisePropertyChanged(nameof(ActiveSummary));

        await PersistDraftAsync(ct);
    }

    public async Task AddSerialAsync(CancellationToken ct = default)
    {
        if (_activePallet is null)
        {
            StatusMessage = "Start a pallet first.";
            return;
        }

        var serial = SerialInput.Trim().ToUpperInvariant();
        if (string.IsNullOrWhiteSpace(serial))
        {
            return;
        }

        if (_activePallet.Items.Any(i => string.Equals(i.Serial, serial, StringComparison.OrdinalIgnoreCase)))
        {
            StatusMessage = "Serial already on pallet.";
            return;
        }

        if (_activePallet.ItemCount >= _activePallet.MaxPanels)
        {
            StatusMessage = "Pallet is full. Complete it first.";
            return;
        }

        var simResult = await TryHasSimulatorDataAsync(serial, ct);
        if (simResult == false)
        {
            _pendingSerialForDecision = serial;
            MissingSimSerial = serial;
            MissingSimCancelText = "Keep it off the pallet";
            IsMissingSimPromptOpen = true;
            return;
        }

        if (simResult is null)
        {
            StatusMessage = "Could not validate simulator data right now; you can still continue.";
        }

        await AddSerialInternalAsync(serial, allowMissingSimData: false, ct);
    }

    public async Task RemoveSerialAsync(int itemId, CancellationToken ct = default)
    {
        if (_activePallet is null)
        {
            return;
        }

        var removed = _activePallet.Items.FirstOrDefault(i => i.Id == itemId);

        _activePallet.Items = _activePallet.Items
            .Where(i => i.Id != itemId)
            .Select((i, idx) =>
            {
                i.SlotIndex = idx + 1;
                return i;
            })
            .ToList();

        _activePallet.ItemCount = _activePallet.Items.Count;

        if (removed is not null)
        {
            _fallbackSerials.Remove(removed.Serial);
            await EnqueueAsync(OperationType.PalletItemRemove, new Dictionary<string, object?>
            {
                ["pallet_id"] = _activePallet.Id,
                ["item_id"] = removed.Id,
                ["serial"] = removed.Serial,
            }, ct);
        }

        Items.Clear();
        foreach (var item in _activePallet.Items)
        {
            Items.Add(item);
        }

        RaisePropertyChanged(nameof(ActiveSummary));
        RaisePropertyChanged(nameof(FallbackSerialCount));
        StatusMessage = "Removed.";
        await PersistDraftAsync(ct);
    }

    public async Task CompleteDraftAsync(CancellationToken ct = default)
    {
        if (_activePallet is not null && _activePallet.ItemCount > 0)
        {
            await EnqueueAsync(OperationType.PalletComplete, new Dictionary<string, object?>
            {
                ["pallet_id"] = _activePallet.Id,
            }, ct);
        }

        _fallbackSerials.Clear();
        _activePallet = null;
        Items.Clear();
        ClearMissingSimPrompt();
        StatusMessage = "Pallet completed (queued for sync).";
        RaisePropertyChanged(nameof(HasActivePallet));
        RaisePropertyChanged(nameof(ActiveSummary));
        RaisePropertyChanged(nameof(FallbackSerialCount));
        await _draftRepository.ClearAsync(ct);
    }

    public async Task ResolveMissingSimDecisionAsync(bool useFallback, CancellationToken ct = default)
    {
        var serial = _pendingSerialForDecision;
        if (string.IsNullOrWhiteSpace(serial))
        {
            ClearMissingSimPrompt();
            return;
        }

        ClearMissingSimPrompt();
        if (!useFallback)
        {
            StatusMessage = $"Panel {serial} not added: no sun simulator data in database.";
            return;
        }

        await AddSerialInternalAsync(serial, allowMissingSimData: true, ct);
    }

    private void LoadDraft()
    {
        var draft = _draftRepository.GetAsync().GetAwaiter().GetResult();
        if (draft is null)
        {
            return;
        }

        SelectedTemplateType = draft.TemplateType;
        SelectedPalletSize = draft.PalletSize;
        PalletNumberDraft = draft.PalletNumberDraft ?? PalletNumberDraft;
        _packoutDate = draft.PackoutDate;
        _fallbackSerials.Clear();
        foreach (var serial in draft.FallbackSerials.Where(s => !string.IsNullOrWhiteSpace(s)))
        {
            _fallbackSerials.Add(serial.Trim().ToUpperInvariant());
        }
        RaisePropertyChanged(nameof(PackoutDate));

        _activePallet = draft.ActivePallet;
        Items.Clear();
        if (_activePallet is not null)
        {
            foreach (var item in _activePallet.Items.OrderBy(i => i.SlotIndex))
            {
                Items.Add(item);
            }
        }

        RaisePropertyChanged(nameof(HasActivePallet));
        RaisePropertyChanged(nameof(ActiveSummary));
        RaisePropertyChanged(nameof(FallbackSerialCount));
    }

    private Task PersistDraftAsync(CancellationToken ct = default)
    {
        var draft = new BuilderDraft
        {
            ActivePallet = _activePallet,
            SelectedCustomerId = null,
            TemplateType = SelectedTemplateType,
            PalletSize = SelectedPalletSize,
            PackoutDate = _packoutDate,
            PalletNumberDraft = PalletNumberDraft,
            FallbackSerials = _fallbackSerials.OrderBy(s => s).ToList(),
        };

        return _draftRepository.SaveAsync(draft, ct);
    }

    private async Task AddSerialInternalAsync(string serial, bool allowMissingSimData, CancellationToken ct)
    {
        if (_activePallet is null)
        {
            return;
        }

        if (_activePallet.Items.Any(i => string.Equals(i.Serial, serial, StringComparison.OrdinalIgnoreCase)))
        {
            StatusMessage = "Serial already on pallet.";
            return;
        }

        if (_activePallet.ItemCount >= _activePallet.MaxPanels)
        {
            StatusMessage = "Pallet is full. Complete it first.";
            return;
        }

        var item = new PalletItem
        {
            Id = -(_activePallet.Items.Count + 1),
            Serial = serial,
            SlotIndex = _activePallet.Items.Count + 1,
            AddedAtUtc = _clock.UtcNow,
        };

        _activePallet.Items.Add(item);
        _activePallet.ItemCount = _activePallet.Items.Count;

        await EnqueueAsync(OperationType.PalletItemAdd, new Dictionary<string, object?>
        {
            ["pallet_id"] = _activePallet.Id,
            ["serial"] = serial,
            ["allow_missing_sim_data"] = allowMissingSimData,
        }, ct);

        if (allowMissingSimData)
        {
            _fallbackSerials.Add(serial);
        }
        else
        {
            _fallbackSerials.Remove(serial);
        }

        Items.Add(item);
        SerialInput = string.Empty;

        RaisePropertyChanged(nameof(ActiveSummary));
        RaisePropertyChanged(nameof(FallbackSerialCount));
        StatusMessage = allowMissingSimData ? "Added with generated theoretical values." : "Added.";
        await PersistDraftAsync(ct);
    }

    private async Task<bool?> TryHasSimulatorDataAsync(string serial, CancellationToken ct)
    {
        try
        {
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            var path = $"/barcodes/search?q={Uri.EscapeDataString(serial)}&exact=true&limit=200&offset=0";
            var response = await _apiClient.GetAsync<BarcodeSearchResponse>(path, token, ct);
            return response.Results.Any(r =>
                string.Equals(r.Source, "sim_panel", StringComparison.OrdinalIgnoreCase) &&
                string.Equals(r.Serial, serial, StringComparison.OrdinalIgnoreCase));
        }
        catch
        {
            return null;
        }
    }

    private void ClearMissingSimPrompt()
    {
        _pendingSerialForDecision = null;
        IsMissingSimPromptOpen = false;
        MissingSimSerial = string.Empty;
        MissingSimCancelText = "Keep it off the pallet";
    }

    private Task EnqueueAsync(OperationType opType, object payload, CancellationToken ct)
    {
        var op = new OutboxOperation
        {
            OpId = Guid.NewGuid(),
            OpType = opType,
            PayloadJson = JsonSerializer.Serialize(payload),
            State = OutboxState.Pending,
            AttemptCount = 0,
            LastError = null,
            LastErrorCode = null,
            NextRetryAtUtc = null,
            CreatedAtUtc = _clock.UtcNow,
            UpdatedAtUtc = _clock.UtcNow,
        };

        return _outboxRepository.EnqueueAsync(op, ct);
    }

    private sealed class BarcodeSearchResponse
    {
        [JsonPropertyName("results")]
        public List<BarcodeSearchResult> Results { get; set; } = new();
    }

    private sealed class BarcodeSearchResult
    {
        [JsonPropertyName("source")]
        public string Source { get; set; } = string.Empty;

        [JsonPropertyName("serial")]
        public string Serial { get; set; } = string.Empty;
    }
}
