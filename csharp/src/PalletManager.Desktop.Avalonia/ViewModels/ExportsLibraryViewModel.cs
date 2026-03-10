using System.Collections.ObjectModel;
using System.Text.Json.Serialization;
using PalletManager.Application.Contracts;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class ExportsLibraryViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly IAuthService _authService;
    private readonly IRuntimeSettingsService _settingsService;
    private readonly ISystemLauncher _systemLauncher;

    private string _palletNumber = string.Empty;
    private string _templateType = string.Empty;
    private string _createdFrom = string.Empty;
    private string _createdTo = string.Empty;
    private bool _isLoading;
    private string _statusMessage = string.Empty;

    public ExportsLibraryViewModel(
        IApiClient apiClient,
        IAuthService authService,
        IRuntimeSettingsService settingsService,
        ISystemLauncher systemLauncher)
    {
        _apiClient = apiClient;
        _authService = authService;
        _settingsService = settingsService;
        _systemLauncher = systemLauncher;

        TemplateOptions = new ObservableCollection<string>
        {
            string.Empty, "200WT", "220WT", "220M6", "330WT", "450WT", "450BT",
        };
        Results = new ObservableCollection<ExportLibraryRow>();
    }

    public ObservableCollection<string> TemplateOptions { get; }
    public ObservableCollection<ExportLibraryRow> Results { get; }

    public string PalletNumber
    {
        get => _palletNumber;
        set => SetProperty(ref _palletNumber, value);
    }

    public string TemplateType
    {
        get => _templateType;
        set => SetProperty(ref _templateType, value);
    }

    public string CreatedFrom
    {
        get => _createdFrom;
        set => SetProperty(ref _createdFrom, value);
    }

    public string CreatedTo
    {
        get => _createdTo;
        set => SetProperty(ref _createdTo, value);
    }

    public bool IsLoading
    {
        get => _isLoading;
        private set => SetProperty(ref _isLoading, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public async Task SearchAsync(CancellationToken ct = default)
    {
        int? palletId = null;
        if (!string.IsNullOrWhiteSpace(PalletNumber))
        {
            if (!int.TryParse(PalletNumber.Trim(), out var parsed) || parsed <= 0)
            {
                StatusMessage = "Pallet number must be a positive number.";
                return;
            }

            palletId = parsed;
        }

        IsLoading = true;
        try
        {
            var token = await _authService.GetTokenAsync(ct) ?? string.Empty;
            var query = BuildQuery(palletId, TemplateType, CreatedFrom, CreatedTo);
            var response = await _apiClient.GetAsync<ExportListResponse>($"/exports?{query}", token, ct);

            Results.Clear();
            foreach (var row in response.Exports)
            {
                Results.Add(new ExportLibraryRow(
                    row.Id,
                    row.PalletId,
                    row.TemplateType,
                    row.FileName,
                    row.SizeBytes,
                    row.CreatedAt));
            }

            StatusMessage = response.Total == 0
                ? "No exports found for the given filters."
                : $"Found {response.Total} export(s).";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to load exports: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    public async Task OpenExportAsync(int exportId, string format, CancellationToken ct = default)
    {
        var settings = await _settingsService.GetAsync(ct);
        var baseUrl = (settings.PrimaryApiBaseUrl ?? "http://127.0.0.1:8000/api/v1").TrimEnd('/');
        var endpoint = $"{baseUrl}/exports/{exportId}/download?format={format}";
        await _systemLauncher.OpenAsync(endpoint, ct);
        StatusMessage = $"Opened export #{exportId} ({format.ToUpperInvariant()}).";
    }

    private static string BuildQuery(int? palletId, string templateType, string createdFrom, string createdTo)
    {
        var values = new List<string>();
        if (palletId.HasValue)
        {
            values.Add($"pallet_id={palletId.Value}");
        }

        if (!string.IsNullOrWhiteSpace(templateType))
        {
            values.Add($"template_type={Uri.EscapeDataString(templateType.Trim())}");
        }

        if (DateOnly.TryParse(createdFrom, out var from))
        {
            values.Add($"created_from={Uri.EscapeDataString(from.ToString("yyyy-MM-dd"))}T00%3A00%3A00");
        }

        if (DateOnly.TryParse(createdTo, out var to))
        {
            values.Add($"created_to={Uri.EscapeDataString(to.ToString("yyyy-MM-dd"))}T23%3A59%3A59");
        }

        values.Add("limit=100");
        values.Add("offset=0");

        return string.Join("&", values);
    }

    private sealed class ExportListResponse
    {
        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("exports")]
        public List<ApiExport> Exports { get; set; } = new();
    }

    private sealed class ApiExport
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("pallet_id")]
        public int PalletId { get; set; }

        [JsonPropertyName("template_type")]
        public string TemplateType { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("size_bytes")]
        public long? SizeBytes { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }
}

public sealed record ExportLibraryRow(
    int Id,
    int PalletId,
    string TemplateType,
    string FileName,
    long? SizeBytes,
    DateTime CreatedAtUtc);
