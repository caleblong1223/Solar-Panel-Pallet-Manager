using System.Collections.ObjectModel;
using System.Globalization;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using ClosedXML.Excel;
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
    private double _uploadProgressPercent;
    private string _uploadProgressText = "Idle";

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

    public double UploadProgressPercent
    {
        get => _uploadProgressPercent;
        private set => SetProperty(ref _uploadProgressPercent, value);
    }

    public string UploadProgressText
    {
        get => _uploadProgressText;
        private set => SetProperty(ref _uploadProgressText, value);
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
            UploadProgressPercent = 0;
            UploadProgressText = "Preparing uploads...";

            for (var index = 0; index < selectedPaths.Count; index++)
            {
                var path = selectedPaths[index];
                UploadProgressText = $"Uploading {index + 1} / {selectedPaths.Count}: {Path.GetFileName(path)}";
                var row = await UploadSingleAsync(path, candidates, index, selectedPaths.Count, ct);
                UploadResults.Add(row);
                UploadProgressPercent = ((double)(index + 1) / selectedPaths.Count) * 100.0;
            }

            var successCount = UploadResults.Count(r => r.BatchId.HasValue);
            var failureCount = UploadResults.Count(r => !string.IsNullOrWhiteSpace(r.Error));
            StatusMessage = $"Imported {successCount} file(s), failed {failureCount}.";
            UploadProgressText = "Upload complete.";
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

    private async Task<ImportUploadResultRow> UploadSingleAsync(
        string path,
        IReadOnlyList<string> candidates,
        int fileIndex,
        int totalFiles,
        CancellationToken ct)
    {
        var (fileName, fileBytes, selectionNote) = await BuildPrioritizedUploadPayloadAsync(path, ct);
        var client = _httpClientFactory.CreateClient(nameof(ImportSimulatorViewModel));

        Exception? lastError = null;
        foreach (var baseUrl in candidates)
        {
            ct.ThrowIfCancellationRequested();
            var endpoint = $"{baseUrl.TrimEnd('/')}/simulator/imports/anonymous";
            try
            {
                using var content = new MultipartFormDataContent();
                using var fileContent = new ProgressableStreamContent(
                    new MemoryStream(fileBytes),
                    32 * 1024,
                    bytesSent =>
                    {
                        var normalized = fileBytes.Length <= 0
                            ? 0.0
                            : Math.Clamp((double)bytesSent / fileBytes.Length, 0.0, 1.0);
                        var aggregate = ((double)fileIndex + normalized) / Math.Max(1, totalFiles);
                        UploadProgressPercent = aggregate * 100.0;
                    });
                fileContent.Headers.ContentType = new MediaTypeHeaderValue("text/csv");
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
                    selectionNote is null ? batch.Status : $"{batch.Status} ({selectionNote})",
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

    private async Task<(string FileName, byte[] Bytes, string? SelectionNote)> BuildPrioritizedUploadPayloadAsync(string path, CancellationToken ct)
    {
        var fileName = Path.GetFileName(path);
        var bytes = await File.ReadAllBytesAsync(path, ct);
        var extension = Path.GetExtension(fileName).ToLowerInvariant();
        if (extension is not (".csv" or ".xlsx" or ".xlsm"))
        {
            return (fileName, bytes, null);
        }

        if (!TryReadTabularRows(fileName, bytes, out var headers, out var rows))
        {
            return (fileName, bytes, null);
        }

        if (!TryPrioritizeRows(headers, rows, out var prioritized, out var selectedCount, out var totalCount))
        {
            return (fileName, bytes, null);
        }

        var csvBytes = WriteCsv(headers, prioritized);
        var outFileName = $"{Path.GetFileNameWithoutExtension(fileName)}.prioritized.csv";
        var note = $"prioritized {selectedCount}/{totalCount} serial rows";
        return (outFileName, csvBytes, note);
    }

    private static bool TryPrioritizeRows(
        IReadOnlyList<string> headers,
        IReadOnlyList<IReadOnlyList<string>> rows,
        out List<IReadOnlyList<string>> prioritizedRows,
        out int selectedCount,
        out int totalCount)
    {
        prioritizedRows = new List<IReadOnlyList<string>>();
        selectedCount = 0;
        totalCount = 0;

        var serialCol = FindColumn(headers, "serial", "serialno", "serialnumber", "barcode", "modulesn");
        var wattsCol = FindColumn(headers, "pm", "pmax", "pmaxw", "watts", "power");
        var panelTypeCol = FindColumn(headers, "paneltype", "type", "template", "moduletype");
        var tsCol = FindColumn(headers, "testtimestamp", "timestamp", "datetime", "dateandtime");
        var dateCol = FindColumn(headers, "date");
        var timeCol = FindColumn(headers, "time", "ttime", "testtime");

        if (serialCol < 0)
        {
            return false;
        }

        var bestBySerial = new Dictionary<string, RankedRow>(StringComparer.OrdinalIgnoreCase);
        var passThrough = new List<IReadOnlyList<string>>();

        foreach (var row in rows)
        {
            var serialRaw = ReadCell(row, serialCol);
            var serial = (serialRaw ?? string.Empty).Trim().ToUpperInvariant();
            if (string.IsNullOrWhiteSpace(serial))
            {
                passThrough.Add(row);
                continue;
            }

            totalCount += 1;
            var pm = TryParseDouble(ReadCell(row, wattsCol));
            var ts = ParseTimestamp(ReadCell(row, tsCol), ReadCell(row, dateCol), ReadCell(row, timeCol));
            var panelType = ParsePanelType(ReadCell(row, panelTypeCol), serial, pm);
            var inSpec = IsInSpec(panelType, pm);
            var candidate = new RankedRow(row, inSpec, ts);
            if (!bestBySerial.TryGetValue(serial, out var current) || candidate.CompareTo(current) > 0)
            {
                bestBySerial[serial] = candidate;
            }
        }

        prioritizedRows.AddRange(bestBySerial.Values
            .OrderByDescending(v => v.TestTimestamp ?? DateTime.MinValue)
            .Select(v => v.Row));
        prioritizedRows.AddRange(passThrough);
        selectedCount = bestBySerial.Count;
        return true;
    }

    private static bool TryReadTabularRows(
        string fileName,
        byte[] bytes,
        out List<string> headers,
        out List<IReadOnlyList<string>> rows)
    {
        headers = new List<string>();
        rows = new List<IReadOnlyList<string>>();
        try
        {
            var extension = Path.GetExtension(fileName).ToLowerInvariant();
            if (extension == ".csv")
            {
                var text = Encoding.UTF8.GetString(bytes);
                var parsed = ParseCsv(text);
                if (parsed.Count == 0)
                {
                    return false;
                }

                headers = parsed[0];
                rows = parsed.Skip(1).Cast<IReadOnlyList<string>>().ToList();
                return true;
            }

            using var stream = new MemoryStream(bytes);
            using var workbook = new XLWorkbook(stream);
            var sheet = workbook.Worksheets.FirstOrDefault();
            if (sheet is null)
            {
                return false;
            }

            var used = sheet.RangeUsed();
            if (used is null)
            {
                return false;
            }

            var firstRow = used.FirstRow().RowNumber();
            var lastRow = used.LastRow().RowNumber();
            var firstCol = used.FirstColumn().ColumnNumber();
            var lastCol = used.LastColumn().ColumnNumber();

            for (var col = firstCol; col <= lastCol; col++)
            {
                headers.Add(sheet.Cell(firstRow, col).GetFormattedString());
            }

            for (var row = firstRow + 1; row <= lastRow; row++)
            {
                var values = new List<string>(lastCol - firstCol + 1);
                for (var col = firstCol; col <= lastCol; col++)
                {
                    values.Add(sheet.Cell(row, col).GetFormattedString());
                }

                rows.Add(values);
            }

            return headers.Count > 0;
        }
        catch
        {
            return false;
        }
    }

    private static List<List<string>> ParseCsv(string text)
    {
        var rows = new List<List<string>>();
        var row = new List<string>();
        var cell = new StringBuilder();
        var inQuotes = false;

        for (var i = 0; i < text.Length; i++)
        {
            var c = text[i];
            if (inQuotes)
            {
                if (c == '"' && i + 1 < text.Length && text[i + 1] == '"')
                {
                    cell.Append('"');
                    i++;
                }
                else if (c == '"')
                {
                    inQuotes = false;
                }
                else
                {
                    cell.Append(c);
                }
                continue;
            }

            if (c == '"')
            {
                inQuotes = true;
                continue;
            }

            if (c == ',')
            {
                row.Add(cell.ToString());
                cell.Clear();
                continue;
            }

            if (c == '\r')
            {
                continue;
            }

            if (c == '\n')
            {
                row.Add(cell.ToString());
                cell.Clear();
                rows.Add(row);
                row = new List<string>();
                continue;
            }

            cell.Append(c);
        }

        if (cell.Length > 0 || row.Count > 0)
        {
            row.Add(cell.ToString());
            rows.Add(row);
        }

        return rows;
    }

    private static byte[] WriteCsv(IReadOnlyList<string> headers, IReadOnlyList<IReadOnlyList<string>> rows)
    {
        var sb = new StringBuilder();
        AppendCsvRow(sb, headers);
        foreach (var row in rows)
        {
            AppendCsvRow(sb, row);
        }

        return Encoding.UTF8.GetBytes(sb.ToString());
    }

    private static void AppendCsvRow(StringBuilder sb, IReadOnlyList<string> row)
    {
        for (var i = 0; i < row.Count; i++)
        {
            if (i > 0)
            {
                sb.Append(',');
            }

            var value = row[i] ?? string.Empty;
            var escaped = value.Replace("\"", "\"\"");
            var requiresQuotes = escaped.Contains(',') || escaped.Contains('\n') || escaped.Contains('\r') || escaped.Contains('"');
            sb.Append(requiresQuotes ? $"\"{escaped}\"" : escaped);
        }

        sb.Append('\n');
    }

    private static int FindColumn(IReadOnlyList<string> headers, params string[] aliases)
    {
        var normalizedAliases = aliases.Select(a => NormalizeHeader(a)).ToHashSet(StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i < headers.Count; i++)
        {
            var key = NormalizeHeader(headers[i]);
            if (normalizedAliases.Contains(key))
            {
                return i;
            }
        }

        for (var i = 0; i < headers.Count; i++)
        {
            var key = NormalizeHeader(headers[i]);
            if (aliases.Any(a => key.Contains(NormalizeHeader(a), StringComparison.OrdinalIgnoreCase)))
            {
                return i;
            }
        }

        return -1;
    }

    private static string NormalizeHeader(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        var chars = value
            .Trim()
            .ToLowerInvariant()
            .Where(ch => char.IsLetterOrDigit(ch))
            .ToArray();
        return new string(chars);
    }

    private static string? ReadCell(IReadOnlyList<string> row, int index)
    {
        return index >= 0 && index < row.Count ? row[index] : null;
    }

    private static double? TryParseDouble(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        var cleaned = new string(value.Where(ch => char.IsDigit(ch) || ch is '.' or '-' or '+').ToArray());
        if (double.TryParse(cleaned, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static DateTime? ParseTimestamp(string? timestamp, string? date, string? time)
    {
        if (!string.IsNullOrWhiteSpace(timestamp) &&
            DateTime.TryParse(timestamp, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out var parsedTs))
        {
            return parsedTs;
        }

        var combined = $"{date} {time}".Trim();
        if (!string.IsNullOrWhiteSpace(combined) &&
            DateTime.TryParse(combined, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out var parsedCombined))
        {
            return parsedCombined;
        }

        return null;
    }

    private static int? ParsePanelType(string? panelTypeRaw, string serial, double? pm)
    {
        if (!string.IsNullOrWhiteSpace(panelTypeRaw))
        {
            var digits = new string(panelTypeRaw.Where(char.IsDigit).ToArray());
            if (int.TryParse(digits, out var parsed) && PanelTypeRanges.ContainsKey(parsed))
            {
                return parsed;
            }
        }

        if (serial.StartsWith("CRS", StringComparison.OrdinalIgnoreCase) && serial.Length >= 10)
        {
            if (int.TryParse(serial.Substring(7, 3), out var parsed3) && PanelTypeRanges.ContainsKey(parsed3))
            {
                return parsed3;
            }
        }

        if (serial.StartsWith("CRS", StringComparison.OrdinalIgnoreCase) && serial.Length >= 9)
        {
            if (int.TryParse(serial.Substring(7, 2), out var parsed2) && PanelTypeRanges.ContainsKey(parsed2))
            {
                return parsed2;
            }
        }

        if (pm.HasValue)
        {
            var match = PanelTypeRanges
                .Where(kvp => pm.Value >= kvp.Value.Min && pm.Value <= kvp.Value.Max)
                .OrderBy(kvp => Math.Abs(pm.Value - ((kvp.Value.Min + kvp.Value.Max) / 2.0)))
                .Select(kvp => (int?)kvp.Key)
                .FirstOrDefault();
            return match;
        }

        return null;
    }

    private static bool IsInSpec(int? panelType, double? pm)
    {
        if (!panelType.HasValue || !pm.HasValue)
        {
            return false;
        }

        if (!PanelTypeRanges.TryGetValue(panelType.Value, out var range))
        {
            return false;
        }

        return pm.Value >= range.Min && pm.Value <= range.Max;
    }

    private static readonly Dictionary<int, (double Min, double Max)> PanelTypeRanges = new()
    {
        [200] = (195, 206),
        [220] = (214, 227),
        [325] = (316, 335),
        [330] = (325, 345.05),
        [335] = (325, 345.05),
        [380] = (369, 391.4),
        [385] = (375, 396.55),
        [390] = (379, 401.7),
        [395] = (384, 406.85),
        [450] = (439, 463.5),
    };

    private readonly record struct RankedRow(IReadOnlyList<string> Row, bool InSpec, DateTime? TestTimestamp)
    {
        public int CompareTo(RankedRow other)
        {
            var inSpecCompare = InSpec.CompareTo(other.InSpec);
            if (inSpecCompare != 0)
            {
                return inSpecCompare;
            }

            var thisTs = TestTimestamp ?? DateTime.MinValue;
            var otherTs = other.TestTimestamp ?? DateTime.MinValue;
            return thisTs.CompareTo(otherTs);
        }
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

internal sealed class ProgressableStreamContent : HttpContent
{
    private readonly Stream _source;
    private readonly int _bufferSize;
    private readonly Action<long> _progress;

    public ProgressableStreamContent(Stream source, int bufferSize, Action<long> progress)
    {
        _source = source;
        _bufferSize = bufferSize;
        _progress = progress;
    }

    protected override bool TryComputeLength(out long length)
    {
        if (_source.CanSeek)
        {
            length = _source.Length;
            return true;
        }

        length = -1;
        return false;
    }

    protected override async Task SerializeToStreamAsync(Stream stream, TransportContext? context)
    {
        if (_source.CanSeek)
        {
            _source.Position = 0;
        }

        var buffer = new byte[_bufferSize];
        long total = 0;
        int read;
        while ((read = await _source.ReadAsync(buffer.AsMemory(0, buffer.Length))) > 0)
        {
            await stream.WriteAsync(buffer.AsMemory(0, read));
            total += read;
            _progress(total);
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _source.Dispose();
        }

        base.Dispose(disposing);
    }
}
