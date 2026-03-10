namespace PalletManager.Application.Contracts;

public interface IApiClient
{
    Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default);
    Task<T> PostAsync<T>(
        string path,
        object? body = null,
        string? token = null,
        IDictionary<string, string>? headers = null,
        CancellationToken ct = default);
    Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default);
    Task DeleteAsync(
        string path,
        string? token = null,
        IDictionary<string, string>? headers = null,
        CancellationToken ct = default);
}
