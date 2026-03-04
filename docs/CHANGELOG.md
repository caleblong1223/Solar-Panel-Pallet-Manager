# Pallet Manager Version 1.1.0 - Changelog

**Release Date:** January 6, 2026  
**Previous Version:** 1.0.0

---

## 📋 Overview

Version 1.1.0 introduces significant improvements to the Pallet History interface, enhanced filtering and search capabilities, pallet management features, and improved data import handling. This release focuses on improving user workflow efficiency and data management.

---

## ✨ New Features

### 1. Enhanced Pallet History Interface

#### Filter Layout Reorganization
- **All filters now in a single row** for better space utilization
  - Date Filter (All, Today, This Week, This Month, This Year)
  - Customer Filter (dropdown with "ALL" option)
  - Barcode Search (real-time search field)
- **"Select All" checkbox repositioned** below filters, aligned to the left for better accessibility

#### Customer Filter
- **New customer filter dropdown** in Pallet History window
- Defaults to "ALL" to show all pallets
- Filters pallets by the customer they were designated for at export
- Automatically updates customer list from customer database
- Works seamlessly with other filters (date, barcode search)

#### Barcode Search Functionality
- **Real-time barcode search** with 300ms debounce for performance
- Searches through all serial numbers (barcodes) in all pallets
- Case-insensitive partial matching (e.g., typing "ABC" finds "ABC123", "XABC", etc.)
- **Auto-selection feature**: When search narrows down to exactly one pallet:
  - Automatically selects the pallet
  - Checks its checkbox
  - Highlights it visually
  - Scrolls it into view
  - Shows full details in the details panel
- Displays search result count messages
- Works in combination with date and customer filters

### 2. Sortable Table Headers

- **Clickable column headers** for sorting pallet history:
  - **Pallet #**: Sorts numerically by pallet number
  - **Completed**: Sorts chronologically by completion date
  - **File Name**: Sorts alphabetically by filename
- **Visual sort indicators**: ▲ for ascending, ▼ for descending
- **Toggle behavior**: Clicking the same column toggles between ascending/descending
- Clicking a different column sorts that column ascending
- Handles empty data and invalid formats gracefully

### 3. File Existence Filtering

- **Automatic filtering** of pallets whose exported files no longer exist
- Searches multiple locations:
  - Absolute file paths
  - Relative paths in PALLETS directory
  - Date-based subdirectories (e.g., `PALLETS/6-Jan-26/`)
- **Graceful error handling** for:
  - Missing PALLETS directory
  - Permission errors
  - Corrupted file paths
- Keeps pallets that haven't been exported yet (no exported_file)
- Prevents confusion from "ghost" pallets with missing files

### 4. Delete Pallet Functionality

- **New "Delete Pallet" button** in Pallet History window (red, styled for destructive action)
- **Comprehensive deletion process**:
  1. Deletes the physical export file (if it exists)
  2. Removes the pallet from history database
  3. Allows serial numbers to be scanned again onto new pallets
- **Smart file location search**:
  - Handles absolute and relative paths
  - Searches date subdirectories if direct path doesn't exist
- **Safety features**:
  - Confirmation dialog with detailed information
  - Only allows deleting one pallet at a time
  - Graceful error handling if file deletion fails
  - Continues with history removal even if file deletion fails
- **User feedback**: Clear success/error messages

### 5. Improved Data Import Handling

- **Copy instead of move** for sun simulator data imports
  - Original file now stays in its original location
  - Copy is created in IMPORTED DATA folder
  - Preserves file metadata (timestamps, permissions) using `shutil.copy2()`
  - Handles duplicate filenames by appending numbers (e.g., `filename_1.xlsx`)
- **Better file management**: Users can keep original files while having organized copies

---

## 🐛 Bug Fixes

### 1. Directory Access Error Handling
- **Fixed**: Potential crashes when PALLETS directory doesn't exist or has permission issues
- **Solution**: Added `pallets_dir.exists()` checks and try/except blocks for `PermissionError` and `OSError`
- **Locations**: File filtering logic and delete function

### 2. Lambda Closure Issue in Auto-Select
- **Fixed**: Potential issue with lambda capturing wrong pallet reference
- **Solution**: Used default parameter to properly capture pallet value in closure
- **Location**: Auto-select function for barcode search

### 3. Empty Tree Sorting
- **Fixed**: Potential error when sorting empty table
- **Solution**: Added check for empty tree before attempting sort
- **Location**: Sort function for table headers

### 4. File Path Resolution
- **Improved**: Better handling of various file path formats
- **Added**: Multiple fallback strategies for finding files
- **Enhanced**: Error messages for file not found scenarios

---

## 🔧 Technical Improvements

### Code Quality
- **Enhanced error handling** throughout pallet history operations
- **Improved exception handling** for file operations
- **Better logging** for debugging file access issues
- **Graceful degradation** when operations fail

### Performance
- **Debounced search** (300ms) to prevent excessive filtering during typing
- **Chunked table population** for better UI responsiveness
- **Efficient file existence checks** with multiple fallback strategies

### User Experience
- **Clear visual feedback** for all operations
- **Informative error messages** with specific error codes where applicable
- **Consistent UI behavior** across all features
- **Intuitive filter combinations** (date + customer + barcode)

---

## 📝 Detailed Feature Descriptions

### Customer Filter Implementation

**How it works:**
1. Reads customer list from `CUSTOMERS/customers.xlsx`
2. Displays "ALL" option plus all customer display names
3. Filters pallets based on `customer.display_name` field stored at export
4. Updates automatically when customer list changes

**Customer Display Format:**
- Format: `"Name | Business"`
- Stored in pallet history when exported
- Used for filtering and display

### Barcode Search Implementation

**Search Algorithm:**
1. Converts search term to uppercase for case-insensitive matching
2. Searches through all `serial_numbers` in all visible pallets
3. Uses `in` operator for partial matching
4. Filters results in real-time as user types (with debounce)

**Auto-Selection Logic:**
1. Waits 100ms after table population for UI stability
2. Finds tree item matching pallet number
3. Selects item and updates checkbox state
4. Scrolls item into view
5. Shows details in left panel

### Sortable Headers Implementation

**Sort Logic:**
- **Pallet #**: Converts to integer, defaults to 0 for invalid values
- **Completed**: Parses date string (YYYY-MM-DD format), uses `datetime.min` for invalid dates
- **File Name**: Converts to string, handles missing values gracefully

**Visual Indicators:**
- ▲ (up arrow) = Ascending sort
- ▼ (down arrow) = Descending sort
- Indicators update dynamically based on current sort column

### File Existence Filtering

**Search Strategy:**
1. Check if path is absolute → verify directly
2. If relative, try: `PALLETS/file_path`
3. If not found, try: `PALLETS/filename_only`
4. If still not found, search all date subdirectories
5. Skip pallet if file not found in any location

**Error Handling:**
- Handles missing directories gracefully
- Catches permission errors without crashing
- Logs warnings for debugging
- Continues processing other pallets

### Delete Pallet Process

**Deletion Steps:**
1. Get selected pallet from checkboxes or selection
2. Show confirmation dialog with details
3. Attempt to delete physical file:
   - Resolve file path (absolute/relative)
   - Search date subdirectories if needed
   - Delete file if found
4. Remove pallet from `pallet_history.json`
5. Save updated history
6. Refresh display
7. Show success/error message

**Serial Reuse:**
- When pallet is deleted, serial numbers are no longer tracked
- `is_serial_on_any_pallet()` will return `None` for these serials
- Serial numbers can be scanned again onto new pallets

---

## 🔄 Migration Notes

### For Users Upgrading from 1.0.0

**No action required** - all changes are backward compatible:
- Existing pallet history files work without modification
- Customer data format unchanged
- Export file structure unchanged
- All existing data is preserved

**New Features Available Immediately:**
- Customer filter will work with existing pallets (if they have customer data)
- Barcode search works with all historical pallets
- Sorting works with all existing data
- Delete function works on all pallets

### For Developers

**Code Changes:**
- New methods in `PalletHistoryWindow`:
  - `_sort_by_column()`
  - `_update_sort_indicators()`
  - `_auto_select_single_pallet()`
  - `delete_selected_pallet()`
  - `_on_search_changed()`
  - `_on_customer_filter_changed()`
- New method in `PalletManager`:
  - `delete_pallet()`
- Modified method in `SerialDatabase`:
  - `_move_to_imported_data()` now uses `copy2()` instead of `move()`

**Dependencies:**
- No new dependencies required
- All existing dependencies remain the same

---

## 📊 Statistics

- **New Features**: 5 major features
- **Bug Fixes**: 4 critical fixes
- **Code Files Modified**: 3 files
  - `app/pallet_history_window.py`
  - `app/pallet_manager.py`
  - `app/serial_database.py`
- **Lines of Code Added**: ~400+ lines
- **User-Facing Improvements**: 8 enhancements

---

## 🎯 User Benefits

1. **Faster Pallet Lookup**: Barcode search finds pallets instantly
2. **Better Organization**: Customer and date filters help find specific pallets
3. **Easier Data Management**: Sortable columns for quick organization
4. **Cleaner History**: Missing files automatically filtered out
5. **Error Recovery**: Delete function allows fixing mistakes
6. **Data Preservation**: Import copies instead of moves preserve originals
7. **Improved Workflow**: Auto-selection speeds up common tasks
8. **Better UX**: Intuitive filter layout and visual feedback

---

## 🔮 Future Considerations

**Potential Enhancements for Future Versions:**
- Bulk delete multiple pallets
- Export filtered results
- Advanced search with multiple criteria
- Pallet history export to CSV/Excel
- Undo functionality for deletions
- Search history/saved searches

---

## 📞 Support

If you encounter any issues with Version 1.1.0:
1. Check the [User Guide](docs/USER_GUIDE.md) for troubleshooting
2. Review error messages for specific error codes
3. Check application logs in `LOGS/` directory
4. Contact support with version number (1.1.0) and error details

---

## ✅ Testing Checklist

All features have been tested for:
- [x] Normal operation scenarios
- [x] Edge cases (empty data, missing files, etc.)
- [x] Error conditions (permission errors, missing directories)
- [x] Filter combinations (date + customer + search)
- [x] Cross-platform compatibility (Windows/macOS)
- [x] Backward compatibility with 1.0.0 data
- [x] Performance with large datasets
- [x] UI responsiveness during operations

---

**Version 1.1.0** - Ready for production use.

