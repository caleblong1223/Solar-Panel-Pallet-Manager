using PalletManager.Application.Contracts;

namespace PalletManager.Infrastructure.Api;

public sealed class EndpointResolver
{
    public async Task<IReadOnlyList<string>> ResolveCandidatesAsync(IRuntimeSettingsService settingsService, CancellationToken ct = default)
    {
        var settings = await settingsService.GetAsync(ct);
        var raw = new[]
        {
            settings.PrimaryApiBaseUrl,
            settings.FallbackApiBaseUrl,
            "http://127.0.0.1:8000/api/v1",
            "http://localhost:8000/api/v1",
            "http://host.docker.internal:8000/api/v1",
        };

        var normalized = raw
            .Where(static x => !string.IsNullOrWhiteSpace(x))
            .Select(static x => x!.Trim().TrimEnd('/'))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        return normalized;
    }
}
