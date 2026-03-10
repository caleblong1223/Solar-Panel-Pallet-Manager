namespace PalletManager.Application.Contracts;

public interface ISystemLauncher
{
    Task OpenAsync(string target, CancellationToken ct = default);
}
