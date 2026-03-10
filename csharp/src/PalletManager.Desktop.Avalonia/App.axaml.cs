using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using PalletManager.Desktop.Avalonia.Navigation;
using PalletManager.Desktop.Avalonia.ViewModels;

namespace PalletManager.Desktop.Avalonia;

public sealed partial class App : global::Avalonia.Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var provider = CompositionRoot.BuildServiceProvider();
            var vm = provider.GetRequiredService<AppShellViewModel>();
            desktop.MainWindow = new AppShellView
            {
                DataContext = vm,
            };
        }

        base.OnFrameworkInitializationCompleted();
    }
}
