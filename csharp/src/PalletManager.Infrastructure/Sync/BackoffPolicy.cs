namespace PalletManager.Infrastructure.Sync;

public static class BackoffPolicy
{
    public static TimeSpan ForAttempt(int attempt)
    {
        var safeAttempt = Math.Max(1, attempt);
        var ms = Math.Min(60_000, 1_000 * safeAttempt);
        return TimeSpan.FromMilliseconds(ms);
    }
}
