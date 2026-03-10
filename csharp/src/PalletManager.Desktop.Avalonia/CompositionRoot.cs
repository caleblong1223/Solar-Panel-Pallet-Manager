using Microsoft.Extensions.DependencyInjection;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Infrastructure.Api;
using PalletManager.Infrastructure.Persistence;
using PalletManager.Infrastructure.Persistence.Repositories;
using PalletManager.Infrastructure.Spreadsheet;
using PalletManager.Infrastructure.Sync;
using PalletManager.Infrastructure.System;

namespace PalletManager.Desktop.Avalonia;

public static class CompositionRoot
{
    private static ServiceProvider? _provider;

    public static ServiceProvider BuildServiceProvider()
    {
        if (_provider is not null)
        {
            return _provider;
        }

        var services = new ServiceCollection();

        services.AddHttpClient();

        var appDataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "PalletManager2",
            "csharp");
        Directory.CreateDirectory(appDataDir);
        var dbPath = Path.Combine(appDataDir, "pallet-manager.db");
        var migrationDir = Path.Combine(AppContext.BaseDirectory, "Persistence", "Migrations");

        var connectionFactory = new SqliteConnectionFactory(dbPath);
        services.AddSingleton(connectionFactory);

        var migrationRunner = new MigrationRunner(connectionFactory, migrationDir);
        // Avoid sync-over-async deadlock on UI startup by running migrations on a threadpool thread.
        Task.Run(() => migrationRunner.RunAsync()).GetAwaiter().GetResult();

        services.AddSingleton<EndpointResolver>();
        services.AddSingleton<IApiClient, HttpApiClient>();
        services.AddSingleton<IConnectivityService, ConnectivityProbe>();
        services.AddSingleton<IRuntimeSettingsService, RuntimeSettingsRepository>();

        services.AddSingleton<IApiTokenProvider, AnonymousApiTokenProvider>();
        services.AddSingleton<IOutboxRepository, OutboxRepository>();
        services.AddSingleton<ILocalCacheRepository, LocalCacheRepository>();
        services.AddSingleton<IBuilderDraftRepository, BuilderDraftRepository>();
        services.AddSingleton<IIdMappingRepository, IdMappingRepository>();

        services.AddSingleton<ISyncEngine, SyncEngineHostedService>();
        services.AddSingleton<ISpreadsheetService, OpenXmlSpreadsheetService>();
        services.AddSingleton<ISystemLauncher, SystemLauncher>();
        services.AddSingleton<IClock, SystemClock>();

        services.AddSingleton<SyncIssuesViewModel>();
        services.AddSingleton<BuilderViewModel>();
        services.AddSingleton<HistoryViewModel>();
        services.AddSingleton<CustomersViewModel>();
        services.AddSingleton<ImportSimulatorViewModel>();
        services.AddSingleton<ExportsLibraryViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<AppShellViewModel>();

        _provider = services.BuildServiceProvider();
        return _provider;
    }
}
