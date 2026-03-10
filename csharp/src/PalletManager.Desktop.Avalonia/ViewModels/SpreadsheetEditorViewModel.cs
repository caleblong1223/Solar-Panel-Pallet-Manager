using System.Collections.ObjectModel;
using PalletManager.Domain.Entities;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class SpreadsheetEditorViewModel : ViewModelBase
{
    private WorkbookEditModel? _workbook;
    private string _selectedSheetName = string.Empty;
    private string _status = "No workbook loaded.";

    public SpreadsheetEditorViewModel()
    {
        SheetNames = new ObservableCollection<string>();
    }

    public ObservableCollection<string> SheetNames { get; }

    public string SelectedSheetName
    {
        get => _selectedSheetName;
        set
        {
            if (!SetProperty(ref _selectedSheetName, value))
            {
                return;
            }

            RaisePropertyChanged(nameof(SelectedSheet));
        }
    }

    public WorkbookSheet? SelectedSheet
    {
        get
        {
            if (_workbook is null || string.IsNullOrWhiteSpace(SelectedSheetName))
            {
                return null;
            }

            return _workbook.Sheets.FirstOrDefault(s => s.Name == SelectedSheetName);
        }
    }

    public string Status
    {
        get => _status;
        private set => SetProperty(ref _status, value);
    }

    public void Load(WorkbookEditModel workbook)
    {
        _workbook = workbook;
        SheetNames.Clear();
        foreach (var sheet in workbook.Sheets)
        {
            SheetNames.Add(sheet.Name);
        }

        SelectedSheetName = SheetNames.FirstOrDefault() ?? string.Empty;
        Status = workbook.Sheets.Count == 0 ? "Workbook has no sheets." : $"Loaded {workbook.Sheets.Count} sheet(s).";
        RaisePropertyChanged(nameof(SelectedSheet));
    }

    public void SetCell(int rowIndex, int columnIndex, string value)
    {
        var sheet = SelectedSheet;
        if (sheet is null || rowIndex < 0 || columnIndex < 0)
        {
            return;
        }

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
        Status = $"Updated {sheet.Name} R{rowIndex + 1}C{columnIndex + 1}.";
        RaisePropertyChanged(nameof(SelectedSheet));
    }
}
