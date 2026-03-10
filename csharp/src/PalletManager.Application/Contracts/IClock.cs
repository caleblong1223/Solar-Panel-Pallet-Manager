namespace PalletManager.Application.Contracts;

public interface IClock
{
    DateTime UtcNow { get; }
}
