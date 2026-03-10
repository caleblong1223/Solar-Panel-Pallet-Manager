using System.Collections.ObjectModel;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class ImportSimulatorViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly IApiTokenProvider _authService;
    private readonly IRuntimeSettingsService _settingsService;
    private readonly IHttpClientFactory _httpClientFactory;

    private string _uploadPathsInput = string.Empty;
    private string _searchSerial = string.Empty;
    private string _statusMessage = string.Empty;
    private bool _isUploading;
    private bool _isSearching;
    private bool _hasSearched;

    public ImportSimulatorViewModel(
        IApiClient apiClient,
        IApiTokenProvider authService,
        IRuntimeSettingsService settingsService,
        IHttpClientFactory httpClientFactory)
    {
        _apiClient = apiClient;
        _authService = authService;
        _settingsService = settingsService;
        _httpClientFactory = httpClientFactory;
        UploadResults = new ObservableCollection<ImportUploadResultRow>();
        SearchResults = new ObservableCollection<ImportSearchResultRow>();
    }

    public ObservableCollection<ImportUploadResultRow> UploadResults { get; }
    public ObservableCollection<ImportSearchResultRow> SearchResults { get; }

    public string UploadPathsInput
    {
        get => _uploadPathsInput;
        set => SetProperty(ref _uploadPathsInput, value);
    }

    public string SearchSerial
    {
        get => _searchSerial;
        set => SetProperty(ref _searchSerial, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public bool IsUploading
    {
        get => _isUploading;
        private set => SetProperty(ref _isUploading, value);
    }

    public bool IsSearching
    {
        get => _isSearching;
        private set => SetProperty(ref _isSearching, value);
    }

    public bool HasSearched
    {
        get => _hasSearched;
        private set => SetProperty(ref _hasSearched, value);
    }

    public void SetUploadPaths(IEnumerable<string> paths)
    {
        var distinct = paths
            .Select(p => p.Trim())
            .Where(p => !string.IsNullOrWhiteSpace(p))
            .Distinct(StringComparer.OrdinalIgnoreCase);
        UploadPathsInput = string.Join(Environment.NewLine, distinct);
    }

    public async Task UploadAsync(CancellationToken ct = default)
    {
        var selectedPaths = ParseUploadPaths(UploadPathsInput)
            .Where(File.Exists)
            .ToList();

        if (selectedPaths.Count == 0)
        {
            StatusMessage = "Choose at least one simulator file first.";
            return;
        }

        IsUploading = true;
        try
        {
            UploadResults.Clear();
            var settings = await _settingsService.GetAsync(ct);
            var candidates = BuildUploadCandidates(settings);

            foreach (var path in selectedPaths)
            {
                var row = await UploadSingleAsync(path, candidates, ct);
                UploadResults.Add(row);
            }

            var successCount = UploadResults.Count(r => r.BatchId.HasValue);
            var failureCount = UploadResults.Count(r => !string.IsNullOrWhiteSpace(r.Error));
            StatusMessage = $"Imported {successCount} file(s), failed {failureCount}.";
        }
        finally
        {
            IsUploading = false;
        }
    }

    public async Task SearchAsync(CancellationToken ct = default)
    {
        var serial = SearchSerial.Trim();
        if (string.IsNullOrWhiteSpace(serial))
        {
            StatusMessage = "Enter a serial to search.";
            return;
        }

        IsSearching = true;
        try
        {
            SearchResults.Clear();
            HasSearched = false;

            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            var query = $"q={Uri.EscapeDataString(serial)}&exact=false&limit=50&offset=0&sort=created_at&order=desc";
            var response = await _apiClient.GetAsync<BarcodeSearchResponse>($"/barcodes/search?{query}", token, ct);

            foreach (var result in response.Results.Where(r => string.Equals(r.Source, "sim_panel", StringComparison.OrdinalIgnoreCase)))
            {
                SearchResults.Add(new ImportSearchResultRow(
                    result.Serial,
                    result.SimTestTimestamp,
                    BuildElectricalSummary(result)));
            }

            HasSearched = true;
            StatusMessage = SearchResults.Count == 0
                ? "No Sun Simulator data found for this serial."
                : $"Found {SearchResults.Count} Sun Simulator record(s).";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Search failed: {ex.Message}";
        }
        finally
        {
            IsSearching = false;
        }
    }

    private async Task<ImportUploadResultRow> UploadSingleAsync(string path, IReadOnlyList<string> candidates, CancellationToken ct)
    {
        var fileName = Path.GetFileName(path);
        var fileBytes = await File.ReadAllBytesAsync(path, ct);
        var client = _httpClientFactory.CreateClient(nameof(ImportSimulatorViewModel));

        Exception? lastError = null;
        foreach (var baseUrl in candidates)
        {
            ct.ThrowIfCancellationRequested();
            var endpoint = $"{baseUrl.TrimEnd('/')}/simulator/imports/anonymous";
            try
            {
                using var content = new MultipartFormDataContent();
                using var fileContent = new ByteArrayContent(fileBytes);
                content.Add(fileContent, "file", fileName);

                using var response = await client.PostAsync(endpoint, content, ct);
                if (!response.IsSuccessStatusCode)
                {
                    var detail = await response.Content.ReadAsStringAsync(ct);
                    throw new HttpRequestException($"Upload failed ({(int)response.StatusCode}): {detail}");
                }

                var json = await response.Content.ReadAsStringAsync(ct);
                var batch = JsonSerializer.Deserialize<ImportBatchResponse>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                });
                if (batch is null)
                {
                    throw new InvalidOperationException("Invalid import response.");
                }

                return new ImportUploadResultRow(
                    fileName,
                    batch.Id,
                    batch.Status,
                    batch.RowsImported,
                    batch.RowsRejected,
                    batch.RowsTotal,
                    null);
            }
            catch (Exception ex)
            {
                lastError = ex;
            }
        }

        return new ImportUploadResultRow(
            fileName,
            null,
            "failed",
            null,
            null,
            null,
            lastError?.Message ?? "Import upload failed.");
    }

    private static IReadOnlyList<string> BuildUploadCandidates(RuntimeSettings settings)
    {
        return new[]
        {
            settings.PrimaryApiBaseUrl,
            settings.FallbackApiBaseUrl,
            "http://127.0.0.1:8000/api/v1",
            "http://localhost:8000/api/v1",
            "http://host.docker.internal:8000/api/v1",
        }
        .Where(url => !string.IsNullOrWhiteSpace(url))
        .Select(url => url!.TrimEnd('/'))
        .Distinct(StringComparer.OrdinalIgnoreCase)
        .ToList();
    }

    private static IEnumerable<string> ParseUploadPaths(string raw)
    {
        return raw
            .Split(new[] { '\r', '\n', ';', ',' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(p => p.Trim().Trim('"'));
    }

    private static string BuildElectricalSummary(BarcodeSearchResult row)
    {
        var values = new List<string>();
        if (row.SimWatts.HasValue) values.Add($"Pm: {row.SimWatts.Value:F2}");
        if (row.SimIsc.HasValue) values.Add($"Isc: {row.SimIsc.Value:F2}");
        if (row.SimVoc.HasValue) values.Add($"Voc(V): {row.SimVoc.Value:F2}");
        if (row.SimImp.HasValue) values.Add($"Ipm: {row.SimImp.Value:F2}");
        if (row.SimVmp.HasValue) values.Add($"Vpm(V): {row.SimVmp.Value:F2}");
        return string.Join(" | ", values);
    }

    private sealed class ImportBatchResponse
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = "unknown";

        [JsonPropertyName("rows_total")]
        public int? RowsTotal { get; set; }

        [JsonPropertyName("rows_imported")]
        public int? RowsImported { get; set; }

        [JsonPropertyName("rows_rejected")]
        public int? RowsRejected { get; set; }
    }

    private sealed class BarcodeSearchResponse
    {
        [JsonPropertyName("results")]
        public List<BarcodeSearchResult> Results { get; set; } = new();
    }

    private sealed class BarcodeSearchResult
    {
        [JsonPropertyName("source")]
        public string Source { get; set; } = string.Empty;

        [JsonPropertyName("serial")]
        public string Serial { get; set; } = string.Empty;

        [JsonPropertyName("sim_test_timestamp")]
        public string? SimTestTimestamp { get; set; }

        [JsonPropertyName("sim_watts")]
        public double? SimWatts { get; set; }

        [JsonPropertyName("sim_voc")]
        public double? SimVoc { get; set; }

        [JsonPropertyName("sim_isc")]
        public double? SimIsc { get; set; }

        [JsonPropertyName("sim_vmp")]
        public double? SimVmp { get; set; }

        [JsonPropertyName("sim_imp")]
        public double? SimImp { get; set; }
    }
}

public sealed record ImportUploadResultRow(
    string FileName,
    int? BatchId,
    string Status,
    int? RowsImported,
    int? RowsRejected,
    int? RowsTotal,
    string? Error);

public sealed record ImportSearchResultRow(
    string Serial,
    string? SimTestTimestamp,
    string ElectricalSummary);
