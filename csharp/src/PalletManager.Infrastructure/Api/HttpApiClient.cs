using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Errors;

namespace PalletManager.Infrastructure.Api;

public sealed class HttpApiClient : IApiClient
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IRuntimeSettingsService _settingsService;
    private readonly EndpointResolver _resolver;

    public HttpApiClient(IHttpClientFactory httpClientFactory, IRuntimeSettingsService settingsService, EndpointResolver resolver)
    {
        _httpClientFactory = httpClientFactory;
        _settingsService = settingsService;
        _resolver = resolver;
    }

    public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        => SendAsync<T>(HttpMethod.Get, path, null, token, null, ct);

    public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        => SendAsync<T>(HttpMethod.Post, path, body, token, headers, ct);

    public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default)
        => SendAsync<T>(HttpMethod.Patch, path, body, token, null, ct);

    public async Task DeleteAsync(
        string path,
        string? token = null,
        IDictionary<string, string>? headers = null,
        CancellationToken ct = default)
    {
        _ = await SendAsync<object>(HttpMethod.Delete, path, null, token, headers, ct);
    }

    private async Task<T> SendAsync<T>(
        HttpMethod method,
        string path,
        object? body,
        string? token,
        IDictionary<string, string>? headers,
        CancellationToken ct)
    {
        var client = _httpClientFactory.CreateClient(nameof(HttpApiClient));
        client.Timeout = TimeSpan.FromSeconds(6);

        var isAbsolute = path.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                         path.StartsWith("https://", StringComparison.OrdinalIgnoreCase);

        var candidates = isAbsolute
            ? new[] { path.TrimEnd('/') }
            : (await _resolver.ResolveCandidatesAsync(_settingsService, ct)).Select(baseUrl => $"{baseUrl}{path}").ToArray();

        Exception? last = null;
        for (var i = 0; i < candidates.Length; i++)
        {
            var endpoint = candidates[i];
            using var request = new HttpRequestMessage(method, endpoint);

            if (!string.IsNullOrWhiteSpace(token))
            {
                request.Headers.Authorization = new global::System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token);
            }

            if (headers is not null)
            {
                foreach (var pair in headers)
                {
                    request.Headers.TryAddWithoutValidation(pair.Key, pair.Value);
                }
            }

            if (body is not null)
            {
                var json = JsonSerializer.Serialize(body);
                request.Content = new StringContent(json, Encoding.UTF8, "application/json");
            }

            try
            {
                using var response = await client.SendAsync(request, ct);
                if (!response.IsSuccessStatusCode)
                {
                    var text = await response.Content.ReadAsStringAsync(ct);
                    if ((int)response.StatusCode >= 500 && i < candidates.Length - 1)
                    {
                        last = new HttpRequestException($"Server error {(int)response.StatusCode} at {endpoint}");
                        continue;
                    }

                    throw new ApiError(
                        string.IsNullOrWhiteSpace(text) ? $"{method} {path} failed" : text,
                        (int)response.StatusCode,
                        method.Method,
                        path);
                }

                if (typeof(T) == typeof(object))
                {
                    return default!;
                }

                if (response.Content.Headers.ContentLength == 0)
                {
                    return default!;
                }

                var result = await response.Content.ReadFromJsonAsync<T>(cancellationToken: ct);
                return result is null ? default! : result;
            }
            catch (Exception ex) when (i < candidates.Length - 1)
            {
                last = ex;
            }
        }

        throw last ?? new HttpRequestException($"{method} {path} failed against all configured endpoints.");
    }
}
