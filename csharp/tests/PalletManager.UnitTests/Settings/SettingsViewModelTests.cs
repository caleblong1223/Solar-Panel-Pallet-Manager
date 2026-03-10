using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using Xunit;

namespace PalletManager.UnitTests.Settings;

public sealed class SettingsViewModelTests
{
    [Fact]
    public async Task LoadAsync_PopulatesSettingsFields()
    {
        var vm = CreateViewModel(new StubRuntimeSettingsService(), new StubConnectivityService(), new StubSyncEngine());

        await vm.LoadAsync();

        Assert.Equal("http://api.test/api/v1", vm.PrimaryApiBaseUrl);
        Assert.Equal("http://fallback.test/api/v1", vm.FallbackApiBaseUrl);
        Assert.Contains("loaded", vm.StatusMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task SaveAsync_NormalizesApiPathAndPersists()
    {
        var settings = new StubRuntimeSettingsService();
        var vm = CreateViewModel(settings, new StubConnectivityService(), new StubSyncEngine());
        vm.PrimaryApiBaseUrl = "http://new-api.test";
        vm.FallbackApiBaseUrl = "http://fallback-new.test/";

        await vm.SaveAsync();

        Assert.Equal("http://new-api.test/api/v1", settings.Current.PrimaryApiBaseUrl);
        Assert.Equal("http://fallback-new.test/api/v1", settings.Current.FallbackApiBaseUrl);
        Assert.Equal("Settings saved.", vm.StatusMessage);
    }

    [Fact]
    public async Task RefreshBackendHealthAsync_MapsConnectivitySnapshot()
    {
        var connectivity = new StubConnectivityService
        {
            Snapshot = new ConnectivitySnapshot
            {
                Mode = ConnectionMode.Online,
                ActiveBaseUrl = "http://api.test/api/v1",
                Healthy = true,
                Message = "Healthy",
                CheckedAtUtc = DateTime.UtcNow,
            },
        };
        var vm = CreateViewModel(new StubRuntimeSettingsService(), connectivity, new StubSyncEngine());

        await vm.RefreshBackendHealthAsync();

        Assert.True(vm.BackendHealthy);
        Assert.Equal("Healthy", vm.BackendMessage);
    }

    [Fact]
    public async Task TriggerSyncNowAsync_CallsSyncEngine()
    {
        var sync = new StubSyncEngine();
        var vm = CreateViewModel(new StubRuntimeSettingsService(), new StubConnectivityService(), sync);

        await vm.TriggerSyncNowAsync();

        Assert.Equal(1, sync.TriggerCalls);
    }

    [Fact]
    public async Task TestPrimaryAsync_WhenProbeFails_RestoresOriginalSettings()
    {
        var settings = new StubRuntimeSettingsService();
        var connectivity = new StubConnectivityService { ThrowOnProbe = true };
        var vm = CreateViewModel(settings, connectivity, new StubSyncEngine());
        vm.PrimaryApiBaseUrl = "http://temporary.test";

        await vm.TestPrimaryAsync();

        Assert.Equal("http://api.test/api/v1", settings.Current.PrimaryApiBaseUrl);
        Assert.Contains("failed", vm.StatusMessage, StringComparison.OrdinalIgnoreCase);
    }

    private static SettingsViewModel CreateViewModel(
        IRuntimeSettingsService settingsService,
        IConnectivityService connectivityService,
        StubSyncEngine syncEngine)
    {
        return new SettingsViewModel(settingsService, connectivityService, syncEngine);
    }

    private sealed class StubRuntimeSettingsService : IRuntimeSettingsService
    {
        public RuntimeSettings Current { get; private set; } = new()
        {
            PrimaryApiBaseUrl = "http://api.test/api/v1",
            FallbackApiBaseUrl = "http://fallback.test/api/v1",
            LockToLocalBackend = false,
        };

        public Task<RuntimeSettings> GetAsync(CancellationToken ct = default) => Task.FromResult(Current);

        public Task<RuntimeSettings> SaveAsync(RuntimeSettings settings, CancellationToken ct = default)
        {
            Current = settings;
            return Task.FromResult(settings);
        }

        public IObservable<RuntimeSettings> Changes { get; } = new EmptyObservable<RuntimeSettings>();
    }

    private sealed class StubConnectivityService : IConnectivityService
    {
        public bool ThrowOnProbe { get; set; }
        public ConnectivitySnapshot Snapshot { get; set; } = new()
        {
            Mode = ConnectionMode.Online,
            ActiveBaseUrl = "http://api.test/api/v1",
            Healthy = true,
            Message = "OK",
            CheckedAtUtc = DateTime.UtcNow,
        };

        public Task<ConnectivitySnapshot> ProbeAsync(CancellationToken ct = default)
        {
            if (ThrowOnProbe)
            {
                throw new InvalidOperationException("Probe failed.");
            }

            return Task.FromResult(Snapshot);
        }

        public IObservable<ConnectivitySnapshot> StatusChanges { get; } = new EmptyObservable<ConnectivitySnapshot>();
    }

    private sealed class StubSyncEngine : ISyncEngine
    {
        public int TriggerCalls { get; private set; }
        public IObservable<SyncState> State { get; } = new EmptyObservable<SyncState>();

        public Task TriggerNowAsync(CancellationToken ct = default)
        {
            TriggerCalls += 1;
            return Task.CompletedTask;
        }
    }

    private sealed class EmptyObservable<T> : IObservable<T>
    {
        public IDisposable Subscribe(IObserver<T> observer) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
