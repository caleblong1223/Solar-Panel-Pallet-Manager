using System.Collections.ObjectModel;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.Support;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class AppShellViewModel : ViewModelBase
{
    private NavigationItem _selectedNavigationItem;
    private string _connectionSummary = "Connection: Online";
    private string _syncSummary = "Sync: Idle | Pending: 0 | Review: 0";
    private readonly IDisposable _connectivitySubscription;
    private readonly IDisposable _syncSubscription;
    private readonly Timer _refreshTimer;

    public AppShellViewModel(
        IConnectivityService connectivityService,
        ISyncEngine syncEngine,
        SyncIssuesViewModel syncIssues,
        BuilderViewModel builder,
        HistoryViewModel history,
        CustomersViewModel customers,
        ImportSimulatorViewModel importSimulator,
        ExportsLibraryViewModel exportsLibrary,
        SettingsViewModel settings)
    {
        SyncIssues = syncIssues;
        Builder = builder;
        History = history;
        Customers = customers;
        ImportSimulator = importSimulator;
        ExportsLibrary = exportsLibrary;
        Settings = settings;

        NavigationItems = new ObservableCollection<NavigationItem>
        {
            new("Builder", "Live pallet building and scan workflow."),
            new("History", "Pallet history search and export tooling."),
            new("Import", "Sun simulator import and serial verification."),
            new("Exports", "Search and open generated export files."),
            new("Customers", "Customer records management and archive flow."),
            new("Settings", "Runtime connectivity, sync, and health settings."),
            new("Sync Issues", "Conflict resolution for queued operations."),
        };

        _selectedNavigationItem = NavigationItems[0];

        _connectivitySubscription = connectivityService.StatusChanges.Subscribe(new Observer<ConnectivitySnapshot>(snapshot =>
        {
            var modeText = snapshot.Mode switch
            {
                ConnectionMode.Online => "Online",
                ConnectionMode.OfflineCached => "Offline (cached)",
                _ => "Degraded",
            };
            ConnectionSummary = $"Connection: {modeText}";
        }));

        _syncSubscription = syncEngine.State.Subscribe(new Observer<SyncState>(state =>
        {
            SyncSummary = $"Sync: {(state.Syncing ? "Syncing" : "Idle")} | Pending: {state.PendingCount} | Review: {state.NeedsReviewCount}";
        }));

        _refreshTimer = new Timer(async _ =>
        {
            try
            {
                await connectivityService.ProbeAsync();
                await syncEngine.TriggerNowAsync();
                if (IsSyncIssuesSelected)
                {
                    await SyncIssues.RefreshAsync();
                }
            }
            catch
            {
                // Keep shell stable; surfaced states are best effort.
            }
        }, null, TimeSpan.Zero, TimeSpan.FromSeconds(10));
    }

    public ObservableCollection<NavigationItem> NavigationItems { get; }
    public SyncIssuesViewModel SyncIssues { get; }
    public BuilderViewModel Builder { get; }
    public HistoryViewModel History { get; }
    public CustomersViewModel Customers { get; }
    public ImportSimulatorViewModel ImportSimulator { get; }
    public ExportsLibraryViewModel ExportsLibrary { get; }
    public SettingsViewModel Settings { get; }

    public NavigationItem SelectedNavigationItem
    {
        get => _selectedNavigationItem;
        set
        {
            if (!SetProperty(ref _selectedNavigationItem, value))
            {
                return;
            }

            RaisePropertyChanged(nameof(SelectedTitle));
            RaisePropertyChanged(nameof(SelectedDescription));
            RaisePropertyChanged(nameof(IsSyncIssuesSelected));
            RaisePropertyChanged(nameof(IsBuilderSelected));
            RaisePropertyChanged(nameof(IsHistorySelected));
            RaisePropertyChanged(nameof(IsCustomersSelected));
            RaisePropertyChanged(nameof(IsImportSelected));
            RaisePropertyChanged(nameof(IsExportsSelected));
            RaisePropertyChanged(nameof(IsSettingsSelected));
            RaisePropertyChanged(nameof(IsDefaultWorkspaceSelected));

            if (IsSyncIssuesSelected)
            {
                _ = SyncIssues.RefreshAsync();
            }

            if (IsHistorySelected)
            {
                _ = History.RefreshAsync();
            }

            if (IsCustomersSelected)
            {
                _ = Customers.RefreshAsync();
            }

            if (IsExportsSelected)
            {
                _ = ExportsLibrary.SearchAsync();
            }

            if (IsSettingsSelected)
            {
                _ = Settings.LoadAsync();
                _ = Settings.RefreshBackendHealthAsync();
            }

        }
    }

    public bool IsSyncIssuesSelected => SelectedNavigationItem.Title == "Sync Issues";
    public bool IsBuilderSelected => SelectedNavigationItem.Title == "Builder";
    public bool IsHistorySelected => SelectedNavigationItem.Title == "History";
    public bool IsCustomersSelected => SelectedNavigationItem.Title == "Customers";
    public bool IsImportSelected => SelectedNavigationItem.Title == "Import";
    public bool IsExportsSelected => SelectedNavigationItem.Title == "Exports";
    public bool IsSettingsSelected => SelectedNavigationItem.Title == "Settings";
    public bool IsDefaultWorkspaceSelected => !IsSyncIssuesSelected && !IsBuilderSelected && !IsHistorySelected && !IsCustomersSelected && !IsImportSelected && !IsExportsSelected && !IsSettingsSelected;

    public string SelectedTitle => SelectedNavigationItem.Title;
    public string SelectedDescription => SelectedNavigationItem.Description;

    public string ConnectionSummary
    {
        get => _connectionSummary;
        set => SetProperty(ref _connectionSummary, value);
    }

    public string SyncSummary
    {
        get => _syncSummary;
        set => SetProperty(ref _syncSummary, value);
    }
}

public sealed record NavigationItem(string Title, string Description);
