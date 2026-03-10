using System.Diagnostics;
using PalletManager.Application.Contracts;

namespace PalletManager.Infrastructure.System;

public sealed class SystemLauncher : ISystemLauncher
{
    public Task OpenAsync(string target, CancellationToken ct = default)
    {
        _ = ct;
        Process.Start(new ProcessStartInfo
        {
            FileName = target,
            UseShellExecute = true,
        });

        return Task.CompletedTask;
    }
}
