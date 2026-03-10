using PalletManager.Application.Contracts;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class SystemClock : IClock
{
    public DateTime UtcNow => DateTime.UtcNow;
}
