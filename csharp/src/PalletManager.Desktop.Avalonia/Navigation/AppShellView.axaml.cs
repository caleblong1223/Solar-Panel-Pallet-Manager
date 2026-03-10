using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Markup.Xaml;
using Avalonia.Platform.Storage;
using PalletManager.Desktop.Avalonia.ViewModels;

namespace PalletManager.Desktop.Avalonia.Navigation;

public sealed partial class AppShellView : Window
{
    public AppShellView()
    {
        InitializeComponent();
    }

    private AppShellViewModel? Vm => DataContext as AppShellViewModel;

    private void InitializeComponent()
    {
        AvaloniaXamlLoader.Load(this);
    }

    private void OnApplyHistoryFiltersClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        Vm.History.ApplyFilters();
    }

    private async void OnRefreshHistoryClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.History.RefreshAsync();
    }

    private async void OnRefreshHistoryDetailsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.History.RefreshAsync();
    }

    private async void OnDeleteSelectedPalletClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.History.DeleteSelectedPalletAsync();
    }

    private async void OnMergeSelectedHistoryClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.History.MergeSelectedPalletsAsync();
    }

    private async void OnOpenExportPdfClicked(object? sender, RoutedEventArgs e)
    {
        await OpenExportClickedAsync(sender, "pdf");
    }

    private async void OnOpenExportXlsxClicked(object? sender, RoutedEventArgs e)
    {
        await OpenExportClickedAsync(sender, "xlsx");
    }

    private async Task OpenExportClickedAsync(object? sender, string format)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var exportId))
        {
            await Vm.History.OpenExportAsync(exportId, format);
        }
    }

    private async void OnEditExportSpreadsheetClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var exportId))
        {
            await Vm.History.StartSpreadsheetEditAsync(exportId);
        }
    }

    private async void OnSaveSpreadsheetEditsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.History.SaveSpreadsheetEditsAsync();
    }

    private void OnCloseSpreadsheetEditorClicked(object? sender, RoutedEventArgs e)
    {
        Vm?.History.CloseSpreadsheetEditor();
    }

    private async void OnRefreshSyncIssuesClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.SyncIssues.RefreshAsync();
    }

    private async void OnSyncNowClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.SyncIssues.TriggerSyncNowAsync();
    }

    private async void OnRetryOpClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (button.Tag is Guid id)
        {
            await Vm.SyncIssues.RetryOperationAsync(id);
            return;
        }

        if (Guid.TryParse(button.Tag?.ToString(), out var parsed))
        {
            await Vm.SyncIssues.RetryOperationAsync(parsed);
        }
    }

    private async void OnDiscardOpClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (button.Tag is Guid id)
        {
            await Vm.SyncIssues.DiscardOperationAsync(id);
            return;
        }

        if (Guid.TryParse(button.Tag?.ToString(), out var parsed))
        {
            await Vm.SyncIssues.DiscardOperationAsync(parsed);
        }
    }

    private async void OnStartBuilderClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Builder.StartNewPalletAsync();
    }

    private async void OnAddSerialClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Builder.AddSerialAsync();
    }

    private async void OnRemoveSerialClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var itemId))
        {
            await Vm.Builder.RemoveSerialAsync(itemId);
        }
    }

    private async void OnCompleteBuilderClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Builder.CompleteDraftAsync();
    }

    private async void OnKeepOffPalletClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Builder.ResolveMissingSimDecisionAsync(useFallback: false);
    }

    private async void OnUseGeneratedValuesClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Builder.ResolveMissingSimDecisionAsync(useFallback: true);
    }

    private async void OnRefreshCustomersClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Customers.RefreshAsync();
    }

    private async void OnSaveCustomerClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Customers.SaveAsync();
    }

    private void OnNewCustomerClicked(object? sender, RoutedEventArgs e)
    {
        Vm?.Customers.StartCreate();
    }

    private void OnEditCustomerClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var customerId))
        {
            Vm.Customers.StartEdit(customerId);
        }
    }

    private async void OnArchiveCustomerClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var customerId))
        {
            await Vm.Customers.ArchiveAsync(customerId);
        }
    }

    private async void OnBrowseSimulatorFilesClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null || StorageProvider is null)
        {
            return;
        }

        var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Choose simulator files",
            AllowMultiple = true,
            FileTypeFilter = new List<FilePickerFileType>
            {
                new("Simulator Files")
                {
                    Patterns = new[] { "*.csv", "*.xlsx", "*.xls" },
                },
            },
        });

        var paths = files
            .Select(f => f.Path.LocalPath)
            .Where(path => !string.IsNullOrWhiteSpace(path))
            .Cast<string>()
            .ToList();
        if (paths.Count > 0)
        {
            Vm.ImportSimulator.SetUploadPaths(paths);
        }
    }

    private async void OnUploadSimulatorFilesClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.ImportSimulator.UploadAsync();
    }

    private async void OnSearchSimulatorSerialClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.ImportSimulator.SearchAsync();
    }

    private async void OnSearchExportsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.ExportsLibrary.SearchAsync();
    }

    private async void OnOpenExportLibraryPdfClicked(object? sender, RoutedEventArgs e)
    {
        await OpenExportLibraryClickedAsync(sender, "pdf");
    }

    private async void OnOpenExportLibraryXlsxClicked(object? sender, RoutedEventArgs e)
    {
        await OpenExportLibraryClickedAsync(sender, "xlsx");
    }

    private async Task OpenExportLibraryClickedAsync(object? sender, string format)
    {
        if (Vm is null || sender is not Button button)
        {
            return;
        }

        if (int.TryParse(button.Tag?.ToString(), out var exportId))
        {
            await Vm.ExportsLibrary.OpenExportAsync(exportId, format);
        }
    }

    private async void OnSaveSettingsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Settings.SaveAsync();
    }

    private async void OnTestPrimarySettingsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Settings.TestPrimaryAsync();
    }

    private async void OnTestFallbackSettingsClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Settings.TestFallbackAsync();
    }

    private async void OnRefreshBackendHealthClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Settings.RefreshBackendHealthAsync();
    }

    private async void OnTriggerSettingsSyncNowClicked(object? sender, RoutedEventArgs e)
    {
        if (Vm is null)
        {
            return;
        }

        await Vm.Settings.TriggerSyncNowAsync();
    }
}
