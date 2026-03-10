using System.Collections.ObjectModel;
using System.Net.Http.Headers;
using System.Text.Json.Serialization;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class HistoryViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly IApiTokenProvider _authService;
    private readonly ILocalCacheRepository _cacheRepository;
    private readonly IRuntimeSettingsService _settingsService;
    private readonly ISystemLauncher _systemLauncher;
    private readonly ISpreadsheetService _spreadsheetService;
    private readonly IHttpClientFactory _httpClientFactory;

    private readonly List<Pallet> _allPallets = new();
    private string _query = string.Empty;
    private bool _exact;
    private string _datePreset = "today";
    private string _sortMode = "completed_desc";
    private bool _isLoading;
    private HistoryPalletRow? _selectedPallet;
    private string _selectedSummary = "Select a pallet to view details.";
    private string _statusMessage = string.Empty;

    private bool _isSpreadsheetEditorOpen;
    private bool _isSpreadsheetBusy;
    private int? _editingExportId;
    private string _editingExportFileName = string.Empty;
    private WorkbookEditModel? _editingWorkbook;
    private string _selectedEditingSheetName = string.Empty;
    private const int MaxEditableRows = 120;
    private const int MaxEditableColumns = 16;

    public HistoryViewModel(
        IApiClient apiClient,
        IApiTokenProvider authService,
        ILocalCacheRepository cacheRepository,
        IRuntimeSettingsService settingsService,
        ISystemLauncher systemLauncher,
        ISpreadsheetService spreadsheetService,
        IHttpClientFactory httpClientFactory)
    {
        _apiClient = apiClient;
        _authService = authService;
        _cacheRepository = cacheRepository;
        _settingsService = settingsService;
        _systemLauncher = systemLauncher;
        _spreadsheetService = spreadsheetService;
        _httpClientFactory = httpClientFactory;

        DatePresetOptions = new ObservableCollection<string> { "today", "week", "month", "year", "all" };
        SortModeOptions = new ObservableCollection<string>
        {
            "completed_desc", "completed_asc", "number_desc", "number_asc", "items_desc",
        };

        VisiblePallets = new ObservableCollection<HistoryPalletRow>();
        ExportRows = new ObservableCollection<HistoryExportRow>();
        EditingSheetNames = new ObservableCollection<string>();
        EditingRows = new ObservableCollection<SpreadsheetEditRow>();
        EditingColumnHeaders = new ObservableCollection<string>();
        EditingPinnedHeaderCells = new ObservableCollection<SpreadsheetEditCell>();
    }

    public ObservableCollection<string> DatePresetOptions { get; }
    public ObservableCollection<string> SortModeOptions { get; }
    public ObservableCollection<HistoryPalletRow> VisiblePallets { get; }
    public ObservableCollection<HistoryExportRow> ExportRows { get; }
    public ObservableCollection<string> EditingSheetNames { get; }
    public ObservableCollection<SpreadsheetEditRow> EditingRows { get; }
    public ObservableCollection<string> EditingColumnHeaders { get; }
    public ObservableCollection<SpreadsheetEditCell> EditingPinnedHeaderCells { get; }

    public string Query
    {
        get => _query;
        set => SetProperty(ref _query, value);
    }

    public bool Exact
    {
        get => _exact;
        set => SetProperty(ref _exact, value);
    }

    public string DatePreset
    {
        get => _datePreset;
        set => SetProperty(ref _datePreset, value);
    }

    public string SortMode
    {
        get => _sortMode;
        set => SetProperty(ref _sortMode, value);
    }

    public bool IsLoading
    {
        get => _isLoading;
        private set => SetProperty(ref _isLoading, value);
    }

    public HistoryPalletRow? SelectedPallet
    {
        get => _selectedPallet;
        set
        {
            if (!SetProperty(ref _selectedPallet, value))
            {
                return;
            }

            if (value is null)
            {
                SelectedSummary = "Select a pallet to view details.";
                ExportRows.Clear();
                return;
            }

            ExportRows.Clear();
            SelectedSummary = $"Pallet #{value.PalletNumber} | {value.TemplateType} | {value.ItemCount} panel(s)";
            _ = LoadDetailsAsync(value.Id);
        }
    }

    public string SelectedSummary
    {
        get => _selectedSummary;
        private set => SetProperty(ref _selectedSummary, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public bool IsSpreadsheetEditorOpen
    {
        get => _isSpreadsheetEditorOpen;
        private set => SetProperty(ref _isSpreadsheetEditorOpen, value);
    }

    public bool IsSpreadsheetBusy
    {
        get => _isSpreadsheetBusy;
        private set => SetProperty(ref _isSpreadsheetBusy, value);
    }

    public string EditingExportFileName
    {
        get => _editingExportFileName;
        private set => SetProperty(ref _editingExportFileName, value);
    }

    public string SelectedEditingSheetName
    {
        get => _selectedEditingSheetName;
        set
        {
            if (!SetProperty(ref _selectedEditingSheetName, value))
            {
                return;
            }

            BuildEditingRows();
            RaisePropertyChanged(nameof(EditingGridSummary));
        }
    }

    public string EditingWorkbookSummary
    {
        get
        {
            if (_editingWorkbook is null || _editingWorkbook.Sheets.Count == 0)
            {
                return "No workbook loaded.";
            }

            return $"Sheets: {_editingWorkbook.Sheets.Count} ({string.Join(", ", _editingWorkbook.Sheets.Select(s => s.Name).Take(4))}{(_editingWorkbook.Sheets.Count > 4 ? ", ..." : string.Empty)})";
        }
    }

    public string EditingGridSummary
    {
        get
        {
            var sheet = GetSelectedEditingSheet();
            if (sheet is null)
            {
                return "No sheet selected.";
            }

            var rowCount = sheet.Data.Count;
            var columnCount = sheet.Data.Count == 0 ? 0 : sheet.Data.Max(r => r.Count);
            var rowDisplay = Math.Min(rowCount, MaxEditableRows);
            var colDisplay = Math.Min(columnCount, MaxEditableColumns);
            return $"Editing {sheet.Name}: showing {rowDisplay}/{rowCount} rows and {colDisplay}/{columnCount} columns.";
        }
    }

    public async Task RefreshAsync(CancellationToken ct = default)
    {
        IsLoading = true;
        try
        {
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            List<Pallet> loaded;

            try
            {
                var response = await _apiClient.GetAsync<ApiPalletListResponse>("/pallets?status=completed&limit=200&offset=0", token, ct);
                loaded = response.Pallets.Select(MapPallet).ToList();
                if (loaded.Count == 0)
                {
                    var active = await _apiClient.GetAsync<ApiPalletListResponse>("/pallets?status=active&limit=200&offset=0", token, ct);
                    loaded = active.Pallets.Select(MapPallet).ToList();
                }

                foreach (var pallet in loaded)
                {
                    await _cacheRepository.UpsertPalletAsync(pallet, ct);
                }
                StatusMessage = $"Loaded {loaded.Count} pallet(s) from API.";
            }
            catch
            {
                loaded = (await _cacheRepository.GetPalletsAsync("completed", ct)).ToList();
                if (loaded.Count == 0)
                {
                    loaded = (await _cacheRepository.GetPalletsAsync("active", ct)).ToList();
                }
                StatusMessage = "Using cached history (offline).";
            }

            _allPallets.Clear();
            _allPallets.AddRange(loaded);
            ApplyFilters();
        }
        finally
        {
            IsLoading = false;
        }
    }

    public void ApplyFilters()
    {
        var previouslySelected = VisiblePallets.Where(r => r.IsSelected).Select(r => r.Id).ToHashSet();
        IEnumerable<Pallet> filtered = _allPallets;

        if (DatePreset != "all")
        {
            var now = DateTime.Now;
            DateTime from = DatePreset switch
            {
                "today" => new DateTime(now.Year, now.Month, now.Day, 0, 0, 0, DateTimeKind.Local),
                "week" => StartOfWeek(now),
                "month" => new DateTime(now.Year, now.Month, 1),
                "year" => new DateTime(now.Year, 1, 1),
                _ => DateTime.MinValue,
            };

            filtered = filtered.Where(p => (p.CompletedAtUtc ?? p.CreatedAtUtc).ToLocalTime() >= from);
        }

        var q = Query.Trim().ToUpperInvariant();
        if (!string.IsNullOrWhiteSpace(q))
        {
            filtered = filtered.Where(p =>
            {
                var template = (p.TemplateType ?? string.Empty).ToUpperInvariant();
                var palletNumber = p.PalletNumber.ToString();
                if (Exact)
                {
                    return p.Items.Any(i => i.Serial.Equals(q, StringComparison.OrdinalIgnoreCase)) ||
                           palletNumber == q ||
                           template == q;
                }

                return p.Items.Any(i => i.Serial.Contains(q, StringComparison.OrdinalIgnoreCase)) ||
                       palletNumber.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                       template.Contains(q, StringComparison.OrdinalIgnoreCase);
            });
        }

        filtered = SortMode switch
        {
            "completed_asc" => filtered.OrderBy(p => p.CompletedAtUtc ?? p.CreatedAtUtc),
            "number_asc" => filtered.OrderBy(p => p.PalletNumber),
            "number_desc" => filtered.OrderByDescending(p => p.PalletNumber),
            "items_desc" => filtered.OrderByDescending(p => p.ItemCount),
            _ => filtered.OrderByDescending(p => p.CompletedAtUtc ?? p.CreatedAtUtc),
        };

        VisiblePallets.Clear();
        foreach (var pallet in filtered)
        {
            VisiblePallets.Add(new HistoryPalletRow(
                pallet.Id,
                pallet.PalletNumber,
                pallet.TemplateType ?? "-",
                pallet.ItemCount,
                (pallet.CompletedAtUtc ?? pallet.CreatedAtUtc).ToLocalTime(),
                pallet.Status,
                previouslySelected.Contains(pallet.Id)));
        }
    }

    public async Task DeleteSelectedPalletAsync(CancellationToken ct = default)
    {
        if (SelectedPallet is null)
        {
            return;
        }

        try
        {
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            await _apiClient.DeleteAsync($"/pallets/{SelectedPallet.Id}", token, null, ct);

            _allPallets.RemoveAll(p => p.Id == SelectedPallet.Id);
            SelectedPallet = null;
            ExportRows.Clear();
            ApplyFilters();
            StatusMessage = "Pallet deleted.";
        }
        catch (Exception ex)
        {
            StatusMessage = string.IsNullOrWhiteSpace(ex.Message) ? "Failed to delete pallet." : ex.Message;
        }
    }

    public async Task OpenExportAsync(int exportId, string format, CancellationToken ct = default)
    {
        var settings = await _settingsService.GetAsync(ct);
        var baseUrl = (settings.PrimaryApiBaseUrl ?? "http://127.0.0.1:8000/api/v1").TrimEnd('/');
        var url = $"{baseUrl}/exports/{exportId}/download?format={format}";
        await _systemLauncher.OpenAsync(url, ct);
    }

    public async Task MergeSelectedPalletsAsync(CancellationToken ct = default)
    {
        var selectedIds = VisiblePallets.Where(r => r.IsSelected).Select(r => r.Id).ToList();
        if (selectedIds.Count < 2)
        {
            StatusMessage = "Select at least 2 pallets to merge.";
            return;
        }

        try
        {
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            var exportIds = new List<int>();

            foreach (var palletId in selectedIds)
            {
                var response = await _apiClient.GetAsync<ApiExportListResponse>($"/exports?pallet_id={palletId}&limit=50&offset=0", token, ct);
                var first = response.Exports.FirstOrDefault();
                if (first is not null)
                {
                    exportIds.Add(first.Id);
                }
            }

            var uniqueExportIds = exportIds.Distinct().ToList();
            if (uniqueExportIds.Count < 2)
            {
                StatusMessage = "Need at least 2 pallets with exports to merge.";
                return;
            }

            var settings = await _settingsService.GetAsync(ct);
            var baseUrl = (settings.PrimaryApiBaseUrl ?? "http://127.0.0.1:8000/api/v1").TrimEnd('/');
            var query = string.Join("&", uniqueExportIds.Select(id => $"export_id={id}"));
            var endpoint = $"{baseUrl}/exports/merge-pdf?{query}";
            await _systemLauncher.OpenAsync(endpoint, ct);
            StatusMessage = $"Opened merged PDF for {uniqueExportIds.Count} exports.";
        }
        catch (Exception ex)
        {
            StatusMessage = string.IsNullOrWhiteSpace(ex.Message) ? "Failed to merge selected pallets." : ex.Message;
        }
    }

    public async Task StartSpreadsheetEditAsync(int exportId, CancellationToken ct = default)
    {
        var export = ExportRows.FirstOrDefault(e => e.Id == exportId);
        if (export is null)
        {
            StatusMessage = "Select a valid export first.";
            return;
        }

        IsSpreadsheetBusy = true;
        try
        {
            var settings = await _settingsService.GetAsync(ct);
            var baseUrl = (settings.PrimaryApiBaseUrl ?? "http://127.0.0.1:8000/api/v1").TrimEnd('/');
            var endpoint = $"{baseUrl}/exports/{exportId}/download?format=xlsx";
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;

            var client = _httpClientFactory.CreateClient(nameof(HistoryViewModel));
            using var request = new HttpRequestMessage(HttpMethod.Get, endpoint);
            if (!string.IsNullOrWhiteSpace(token))
            {
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            }

            using var response = await client.SendAsync(request, ct);
            response.EnsureSuccessStatusCode();
            var bytes = await response.Content.ReadAsByteArrayAsync(ct);

            _editingWorkbook = await _spreadsheetService.LoadAsync(bytes, ct);
            _editingExportId = exportId;
            EditingExportFileName = export.FileName;
            IsSpreadsheetEditorOpen = true;
            BuildEditingSheetList();
            BuildEditingRows();
            RaisePropertyChanged(nameof(EditingWorkbookSummary));
            RaisePropertyChanged(nameof(EditingGridSummary));
            StatusMessage = "Spreadsheet loaded for editing.";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to open spreadsheet: {ex.Message}";
        }
        finally
        {
            IsSpreadsheetBusy = false;
        }
    }

    public async Task SaveSpreadsheetEditsAsync(CancellationToken ct = default)
    {
        if (!IsSpreadsheetEditorOpen || _editingWorkbook is null || !_editingExportId.HasValue)
        {
            return;
        }

        IsSpreadsheetBusy = true;
        try
        {
            var serializedWorkbook = await _spreadsheetService.SaveAsync(_editingWorkbook, ct);
            var token = await _authService.GetBearerTokenAsync(ct) ?? string.Empty;
            var payload = new
            {
                workbook_size_bytes = serializedWorkbook.Length,
                sheets = _editingWorkbook.Sheets.Select(sheet => new
                {
                    name = sheet.Name,
                    data = sheet.Data.Select(row => row.ToArray()).ToArray(),
                }).ToArray(),
            };

            _ = await _apiClient.PostAsync<object>($"/exports/{_editingExportId.Value}/apply-edits", payload, token, null, ct);
            StatusMessage = $"Spreadsheet changes saved ({serializedWorkbook.Length} bytes).";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to save spreadsheet: {ex.Message}";
        }
        finally
        {
            IsSpreadsheetBusy = false;
        }
    }

    public void CloseSpreadsheetEditor()
    {
        IsSpreadsheetEditorOpen = false;
        _editingExportId = null;
        _editingWorkbook = null;
        EditingExportFileName = string.Empty;
        EditingSheetNames.Clear();
        EditingRows.Clear();
        EditingColumnHeaders.Clear();
        EditingPinnedHeaderCells.Clear();
        SelectedEditingSheetName = string.Empty;
        RaisePropertyChanged(nameof(EditingWorkbookSummary));
        RaisePropertyChanged(nameof(EditingGridSummary));
    }

    private void BuildEditingSheetList()
    {
        EditingSheetNames.Clear();
        if (_editingWorkbook is null)
        {
            SelectedEditingSheetName = string.Empty;
            return;
        }

        foreach (var sheet in _editingWorkbook.Sheets)
        {
            EditingSheetNames.Add(sheet.Name);
        }

        SelectedEditingSheetName = EditingSheetNames.FirstOrDefault() ?? string.Empty;
    }

    private void BuildEditingRows()
    {
        EditingRows.Clear();
        EditingColumnHeaders.Clear();
        EditingPinnedHeaderCells.Clear();
        var sheet = GetSelectedEditingSheet();
        if (sheet is null)
        {
            return;
        }

        var rowCount = Math.Min(sheet.Data.Count, MaxEditableRows);
        var maxColumns = sheet.Data.Count == 0 ? 0 : Math.Min(sheet.Data.Max(r => r.Count), MaxEditableColumns);
        for (var colIndex = 0; colIndex < maxColumns; colIndex++)
        {
            EditingColumnHeaders.Add(ColumnLabelFromIndex(colIndex));
        }

        if (rowCount > 0)
        {
            for (var colIndex = 0; colIndex < maxColumns; colIndex++)
            {
                var currentValue = colIndex < sheet.Data[0].Count ? sheet.Data[0][colIndex] : string.Empty;
                var localCol = colIndex;
                EditingPinnedHeaderCells.Add(new SpreadsheetEditCell(currentValue, value => UpdateEditingCell(sheet, 0, localCol, value)));
            }
        }

        for (var rowIndex = 1; rowIndex < rowCount; rowIndex++)
        {
            var row = new SpreadsheetEditRow(rowIndex + 1);
            for (var colIndex = 0; colIndex < maxColumns; colIndex++)
            {
                var currentValue = colIndex < sheet.Data[rowIndex].Count ? sheet.Data[rowIndex][colIndex] : string.Empty;
                var localRow = rowIndex;
                var localCol = colIndex;
                row.Cells.Add(new SpreadsheetEditCell(currentValue, value => UpdateEditingCell(sheet, localRow, localCol, value)));
            }

            EditingRows.Add(row);
        }
    }

    private void UpdateEditingCell(WorkbookSheet sheet, int rowIndex, int columnIndex, string value)
    {
        while (sheet.Data.Count <= rowIndex)
        {
            sheet.Data.Add(new List<string>());
        }

        var row = sheet.Data[rowIndex];
        while (row.Count <= columnIndex)
        {
            row.Add(string.Empty);
        }

        row[columnIndex] = value;
    }

    private WorkbookSheet? GetSelectedEditingSheet()
    {
        if (_editingWorkbook is null || string.IsNullOrWhiteSpace(SelectedEditingSheetName))
        {
            return null;
        }

        return _editingWorkbook.Sheets.FirstOrDefault(s => s.Name == SelectedEditingSheetName);
    }

    private static string ColumnLabelFromIndex(int index)
    {
        var value = index + 1;
        var label = string.Empty;
        while (value > 0)
        {
            var remainder = (value - 1) % 26;
            label = (char)('A' + remainder) + label;
            value = (value - 1) / 26;
        }

        return label;
    }

    private async Task LoadDetailsAsync(int palletId)
    {
        var token = await _authService.GetBearerTokenAsync() ?? string.Empty;

        try
        {
            var detail = await _apiClient.GetAsync<ApiPallet>($"/pallets/{palletId}", token);
            var mappedDetail = MapPallet(detail);
            var index = _allPallets.FindIndex(p => p.Id == palletId);
            if (index >= 0)
            {
                _allPallets[index] = mappedDetail;
            }
            else
            {
                _allPallets.Add(mappedDetail);
            }

            SelectedSummary = $"Pallet #{mappedDetail.PalletNumber} | {mappedDetail.TemplateType ?? "Unknown"} | {mappedDetail.ItemCount} panel(s)";
            await _cacheRepository.UpsertPalletAsync(mappedDetail);
        }
        catch
        {
            var pallet = _allPallets.FirstOrDefault(p => p.Id == palletId);
            if (pallet is not null)
            {
                SelectedSummary = $"Pallet #{pallet.PalletNumber} | {pallet.TemplateType ?? "Unknown"} | {pallet.ItemCount} panel(s)";
            }
            else
            {
                SelectedSummary = "Select a pallet to view details.";
            }
        }

        try
        {
            var exportsResponse = await _apiClient.GetAsync<ApiExportListResponse>($"/exports?pallet_id={palletId}&limit=50&offset=0", token);
            ExportRows.Clear();
            foreach (var export in exportsResponse.Exports)
            {
                ExportRows.Add(new HistoryExportRow(
                    export.Id,
                    export.FileName,
                    export.TemplateType,
                    export.PackoutDate,
                    export.CreatedAt));
            }

            var mapped = exportsResponse.Exports.Select(MapExport).ToList();
            await _cacheRepository.UpsertExportsAsync(mapped);
        }
        catch
        {
            var cached = await _cacheRepository.GetExportsByPalletAsync(palletId);
            ExportRows.Clear();
            foreach (var export in cached)
            {
                ExportRows.Add(new HistoryExportRow(
                    export.Id,
                    export.FileName,
                    export.TemplateType,
                    export.PackoutDate?.ToString("yyyy-MM-dd"),
                    export.CreatedAtUtc));
            }
        }

        ApplyFilters();
    }

    private static DateTime StartOfWeek(DateTime now)
    {
        var day = (int)now.DayOfWeek;
        if (day == 0)
        {
            day = 7;
        }

        var date = now.Date.AddDays(-(day - 1));
        return new DateTime(date.Year, date.Month, date.Day, 0, 0, 0, DateTimeKind.Local);
    }

    private static Pallet MapPallet(ApiPallet dto)
    {
        return new Pallet
        {
            Id = dto.Id,
            PalletNumber = dto.PalletNumber,
            Status = dto.Status,
            TemplateType = dto.TemplateType,
            MaxPanels = dto.MaxPanels,
            CustomerId = dto.CustomerId,
            CreatedAtUtc = dto.CreatedAt,
            CompletedAtUtc = dto.CompletedAt,
            DeletedAtUtc = dto.DeletedAt,
            ItemCount = dto.ItemCount,
            Items = dto.Items.Select(i => new PalletItem
            {
                Id = i.Id,
                Serial = i.Serial,
                SlotIndex = i.SlotIndex,
                AddedAtUtc = i.AddedAt,
            }).ToList(),
        };
    }

    private static ExportRecord MapExport(ApiExport dto)
    {
        return new ExportRecord
        {
            Id = dto.Id,
            PalletId = dto.PalletId,
            TemplateType = dto.TemplateType,
            PackoutDate = string.IsNullOrWhiteSpace(dto.PackoutDate) ? null : DateOnly.Parse(dto.PackoutDate),
            ObjectKey = dto.ObjectKey,
            FileName = dto.FileName,
            MimeType = dto.MimeType,
            SizeBytes = dto.SizeBytes,
            ChecksumSha256 = dto.ChecksumSha256,
            CreatedAtUtc = dto.CreatedAt,
        };
    }

    private sealed class ApiPalletListResponse
    {
        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("pallets")]
        public List<ApiPallet> Pallets { get; set; } = new();
    }

    private sealed class ApiPallet
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("pallet_number")]
        public int PalletNumber { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = "active";

        [JsonPropertyName("template_type")]
        public string? TemplateType { get; set; }

        [JsonPropertyName("max_panels")]
        public int MaxPanels { get; set; }

        [JsonPropertyName("customer_id")]
        public int? CustomerId { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("completed_at")]
        public DateTime? CompletedAt { get; set; }

        [JsonPropertyName("deleted_at")]
        public DateTime? DeletedAt { get; set; }

        [JsonPropertyName("item_count")]
        public int ItemCount { get; set; }

        [JsonPropertyName("items")]
        public List<ApiPalletItem> Items { get; set; } = new();
    }

    private sealed class ApiPalletItem
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("serial")]
        public string Serial { get; set; } = string.Empty;

        [JsonPropertyName("slot_index")]
        public int SlotIndex { get; set; }

        [JsonPropertyName("added_at")]
        public DateTime AddedAt { get; set; }
    }

    private sealed class ApiExportListResponse
    {
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

        [JsonPropertyName("packout_date")]
        public string? PackoutDate { get; set; }

        [JsonPropertyName("object_key")]
        public string ObjectKey { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("mime_type")]
        public string MimeType { get; set; } = "application/pdf";

        [JsonPropertyName("size_bytes")]
        public long? SizeBytes { get; set; }

        [JsonPropertyName("checksum_sha256")]
        public string? ChecksumSha256 { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }
}

public sealed class HistoryPalletRow : ViewModelBase
{
    public HistoryPalletRow(int id, int palletNumber, string templateType, int itemCount, DateTime completedOrCreated, string status, bool isSelected)
    {
        Id = id;
        PalletNumber = palletNumber;
        TemplateType = templateType;
        ItemCount = itemCount;
        CompletedOrCreated = completedOrCreated;
        Status = status;
        _isSelected = isSelected;
    }

    private bool _isSelected;

    public int Id { get; }
    public int PalletNumber { get; }
    public string TemplateType { get; }
    public int ItemCount { get; }
    public DateTime CompletedOrCreated { get; }
    public string Status { get; }

    public bool IsSelected
    {
        get => _isSelected;
        set => SetProperty(ref _isSelected, value);
    }
}

public sealed record HistoryExportRow(
    int Id,
    string FileName,
    string TemplateType,
    string? PackoutDate,
    DateTime CreatedAtUtc);

public sealed class SpreadsheetEditRow
{
    public SpreadsheetEditRow(int rowNumber)
    {
        RowNumber = rowNumber;
        Cells = new ObservableCollection<SpreadsheetEditCell>();
    }

    public int RowNumber { get; }
    public ObservableCollection<SpreadsheetEditCell> Cells { get; }
}

public sealed class SpreadsheetEditCell : ViewModelBase
{
    private readonly Action<string> _onChanged;
    private string _value;

    public SpreadsheetEditCell(string value, Action<string> onChanged)
    {
        _value = value;
        _onChanged = onChanged;
    }

    public string Value
    {
        get => _value;
        set
        {
            if (!SetProperty(ref _value, value))
            {
                return;
            }

            _onChanged(value);
        }
    }
}
