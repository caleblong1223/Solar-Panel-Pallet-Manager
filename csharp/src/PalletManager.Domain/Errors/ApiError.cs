namespace PalletManager.Domain.Errors;

public sealed class ApiError : Exception
{
    public int StatusCode { get; }
    public string Method { get; }
    public string Path { get; }
    public string? ErrorCode { get; }

    public ApiError(string message, int statusCode, string method, string path, string? errorCode = null)
        : base(message)
    {
        StatusCode = statusCode;
        Method = method;
        Path = path;
        ErrorCode = errorCode;
    }
}
