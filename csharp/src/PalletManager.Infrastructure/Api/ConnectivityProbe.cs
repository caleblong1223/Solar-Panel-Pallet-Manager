using System.Net.Http.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Domain.Enums;
using PalletManager.Infrastructure.Support;

namespace PalletManager.Infrastructure.Api;

public sealed class ConnectivityProbe : IConnectivityService
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IRuntimeSettingsService _settingsService;
    private readonly EndpointResolver _resolver;
    private readonly ObservableValue<ConnectivitySnapshot> _status;

    public ConnectivityProbe(IHttpClientFactory httpClientFactory, IRuntimeSettingsService settingsService, EndpointResolver resolver)
    {
        _httpClientFactory = httpClientFactory;
        _settingsService = settingsService;
        _resolver = resolver;

        _status = new ObservableValue<ConnectivitySnapshot>(new ConnectivitySnapshot
        {
            Mode = ConnectionMode.Degraded,
            ActiveBaseUrl = string.Empty,
            Healthy = false,
            Message = "Not checked yet",
            CheckedAtUtc = DateTime.UtcNow,
        });
    }

    public IObservable<ConnectivitySnapshot> StatusChanges => _status;

    public async Task<ConnectivitySnapshot> ProbeAsync(CancellationToken ct = default)
    {
        var client = _httpClientFactory.CreateClient(nameof(ConnectivityProbe));
        client.Timeout = TimeSpan.FromSeconds(3);

        var candidates = await _resolver.ResolveCandidatesAsync(_settingsService, ct);
        foreach (var baseUrl in candidates)
        {
            try
            {
                var response = await client.GetFromJsonAsync<HealthResponse>($"{baseUrl}/health/live", ct);
                if (response?.Status == "ok")
                {
                    var ok = new ConnectivitySnapshot
                    {
                        Mode = ConnectionMode.Online,
                        ActiveBaseUrl = baseUrl,
                        Healthy = true,
                        Message = "Connection successful",
                        CheckedAtUtc = DateTime.UtcNow,
                    };
                    _status.Set(ok);
                    return ok;
                }
            }
            catch
            {
                // Try next candidate.
            }
        }

        var failed = new ConnectivitySnapshot
        {
            Mode = ConnectionMode.OfflineCached,
            ActiveBaseUrl = string.Empty,
            Healthy = false,
            Message = "All endpoints unreachable. Running in offline-capable mode.",
            CheckedAtUtc = DateTime.UtcNow,
        };
        _status.Set(failed);
        return failed;
    }

    private sealed class HealthResponse
    {
        public string Status { get; set; } = string.Empty;
    }
}
