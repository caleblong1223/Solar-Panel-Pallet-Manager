using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class SettingsViewModel : ViewModelBase
{
    private readonly IRuntimeSettingsService _settingsService;
    private readonly IConnectivityService _connectivityService;
    private readonly ISyncEngine _syncEngine;

    private string _primaryApiBaseUrl = "http://127.0.0.1:8000/api/v1";
    private string _fallbackApiBaseUrl = "http://localhost:8000/api/v1";
    private bool _lockToLocalBackend;
    private bool _isBusy;
    private string _statusMessage = string.Empty;
    private string _backendMessage = "Checking local backend...";
    private bool? _backendHealthy;
    private string _syncSummary = "Sync: Idle | Pending: 0 | Review: 0";
    private readonly IDisposable _syncSubscription;

    public SettingsViewModel(
        IRuntimeSettingsService settingsService,
        IConnectivityService connectivityService,
        ISyncEngine syncEngine)
    {
        _settingsService = settingsService;
        _connectivityService = connectivityService;
        _syncEngine = syncEngine;

        _syncSubscription = syncEngine.State.Subscribe(new DelegateObserver<SyncState>(state =>
        {
            SyncSummary = $"Sync: {(state.Syncing ? "Syncing" : "Idle")} | Pending: {state.PendingCount} | Review: {state.NeedsReviewCount} | Failed: {state.FailedCount}";
        }));
    }

    public string PrimaryApiBaseUrl
    {
        get => _primaryApiBaseUrl;
        set => SetProperty(ref _primaryApiBaseUrl, value);
    }

    public string FallbackApiBaseUrl
    {
        get => _fallbackApiBaseUrl;
        set => SetProperty(ref _fallbackApiBaseUrl, value);
    }

    public bool LockToLocalBackend
    {
        get => _lockToLocalBackend;
        private set => SetProperty(ref _lockToLocalBackend, value);
    }

    public bool IsBusy
    {
        get => _isBusy;
        private set => SetProperty(ref _isBusy, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public string BackendMessage
    {
        get => _backendMessage;
        private set => SetProperty(ref _backendMessage, value);
    }

    public bool? BackendHealthy
    {
        get => _backendHealthy;
        private set => SetProperty(ref _backendHealthy, value);
    }

    public string SyncSummary
    {
        get => _syncSummary;
        private set => SetProperty(ref _syncSummary, value);
    }

    public async Task LoadAsync(CancellationToken ct = default)
    {
        var settings = await _settingsService.GetAsync(ct);
        PrimaryApiBaseUrl = settings.PrimaryApiBaseUrl;
        FallbackApiBaseUrl = settings.FallbackApiBaseUrl ?? string.Empty;
        LockToLocalBackend = settings.LockToLocalBackend;
        StatusMessage = "Settings loaded.";
    }

    public async Task SaveAsync(CancellationToken ct = default)
    {
        IsBusy = true;
        try
        {
            var settings = new RuntimeSettings
            {
                PrimaryApiBaseUrl = NormalizeBaseUrl(PrimaryApiBaseUrl),
                FallbackApiBaseUrl = string.IsNullOrWhiteSpace(FallbackApiBaseUrl) ? null : NormalizeBaseUrl(FallbackApiBaseUrl),
                LockToLocalBackend = LockToLocalBackend,
            };

            var saved = await _settingsService.SaveAsync(settings, ct);
            PrimaryApiBaseUrl = saved.PrimaryApiBaseUrl;
            FallbackApiBaseUrl = saved.FallbackApiBaseUrl ?? string.Empty;
            StatusMessage = "Settings saved.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to save settings: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    public async Task TestPrimaryAsync(CancellationToken ct = default)
    {
        await TestAgainstAsync(NormalizeBaseUrl(PrimaryApiBaseUrl), "Primary", ct);
    }

    public async Task TestFallbackAsync(CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(FallbackApiBaseUrl))
        {
            StatusMessage = "Fallback URL is empty.";
            return;
        }

        await TestAgainstAsync(NormalizeBaseUrl(FallbackApiBaseUrl), "Fallback", ct);
    }

    public async Task RefreshBackendHealthAsync(CancellationToken ct = default)
    {
        try
        {
            var snapshot = await _connectivityService.ProbeAsync(ct);
            BackendHealthy = snapshot.Healthy;
            BackendMessage = string.IsNullOrWhiteSpace(snapshot.Message)
                ? $"Backend {snapshot.ActiveBaseUrl} ({snapshot.Mode})"
                : snapshot.Message;
        }
        catch (Exception ex)
        {
            BackendHealthy = false;
            BackendMessage = $"Backend check failed: {ex.Message}";
        }
    }

    public async Task TriggerSyncNowAsync(CancellationToken ct = default)
    {
        await _syncEngine.TriggerNowAsync(ct);
    }

    private async Task TestAgainstAsync(string baseUrl, string name, CancellationToken ct)
    {
        RuntimeSettings? original = null;
        IsBusy = true;
        try
        {
            original = await _settingsService.GetAsync(ct);
            var temp = new RuntimeSettings
            {
                PrimaryApiBaseUrl = baseUrl,
                FallbackApiBaseUrl = original.FallbackApiBaseUrl,
                LockToLocalBackend = original.LockToLocalBackend,
            };

            await _settingsService.SaveAsync(temp, ct);
            var snapshot = await _connectivityService.ProbeAsync(ct);
            BackendHealthy = snapshot.Healthy;
            BackendMessage = snapshot.Message;
            StatusMessage = snapshot.Healthy
                ? $"{name} server is reachable."
                : $"{name} server check failed: {snapshot.Message}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"{name} server test failed: {ex.Message}";
        }
        finally
        {
            if (original is not null)
            {
                try
                {
                    await _settingsService.SaveAsync(original, ct);
                }
                catch
                {
                    // Best effort restore so temporary test endpoint does not persist.
                }
            }

            IsBusy = false;
        }
    }

    private static string NormalizeBaseUrl(string raw)
    {
        var normalized = raw.Trim().TrimEnd('/');
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return "http://127.0.0.1:8000/api/v1";
        }

        if (!normalized.EndsWith("/api/v1", StringComparison.OrdinalIgnoreCase))
        {
            normalized = $"{normalized}/api/v1";
        }

        return normalized;
    }
}

internal sealed class DelegateObserver<T> : IObserver<T>
{
    private readonly Action<T> _onNext;

    public DelegateObserver(Action<T> onNext)
    {
        _onNext = onNext;
    }

    public void OnCompleted()
    {
    }

    public void OnError(Exception error)
    {
    }

    public void OnNext(T value)
    {
        _onNext(value);
    }
}
