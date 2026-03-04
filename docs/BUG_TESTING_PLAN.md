# Bug Testing Plan

Comprehensive testing plan for Pallet Manager application.

## 🎯 Critical Areas to Test

### 1. Folder Creation & Path Resolution

**Test Cases:**
- [ ] **macOS - App in /Applications/**
  - Launch app from /Applications/
  - Verify folders created in `~/Documents/Pallet Manager/`
  - Verify all 5 folders exist (PALLETS, IMPORTED DATA, SUN SIMULATOR DATA, EXCEL, LOGS)
  
- [ ] **macOS - App in custom location**
  - Move app to Desktop
  - Launch app
  - Verify folders created next to .app bundle
  - Verify folders are writable

- [ ] **Windows - App in Program Files**
  - Install app to default location
  - Launch app
  - Verify folders created next to .exe
  - Verify folders are writable

- [ ] **Windows - App in custom location**
  - Install app to custom folder
  - Launch app
  - Verify folders created correctly

- [ ] **Edge Case: No write permissions**
  - Try to create folders in read-only location
  - Verify error message is user-friendly
  - Verify app handles gracefully

### 2. Pallet Full Handling

**Test Cases:**
- [ ] **Scan 25th panel**
  - Add 24 panels to pallet
  - Scan 25th panel
  - Verify it's added successfully
  - Verify pallet shows as full (25/25)

- [ ] **Try to scan 26th panel**
  - With full pallet (25 panels)
  - Try to scan another barcode
  - Verify warning message appears
  - Verify barcode is NOT added
  - Verify "Export Pallet" button is visible/enabled

- [ ] **Export full pallet**
  - Create full pallet
  - Click "Export Pallet"
  - Verify export succeeds
  - Verify pallet is cleared
  - Verify NO new pallet is auto-created
  - Verify "New Pallet" button is NOT present

### 3. Barcode Validation

**Test Cases:**
- [ ] **Valid barcode**
  - Scan valid serial number
  - Verify it's added to pallet
  - Verify success message

- [ ] **Invalid barcode format**
  - Scan invalid format (too short, wrong characters)
  - Verify error message
  - Verify barcode is NOT added

- [ ] **Duplicate barcode**
  - Scan same barcode twice
  - Verify duplicate warning
  - Verify second scan is NOT added

- [ ] **Barcode not in database**
  - Scan barcode not in serial database
  - Verify warning message
  - Verify it's still added (if allowed)

- [ ] **Empty barcode**
  - Try to scan empty string
  - Verify handled gracefully

### 4. Excel File Operations

**Test Cases:**
- [ ] **Export to Excel**
  - Create pallet with panels
  - Export pallet
  - Verify Excel file is created
  - Verify file is in correct date folder
  - Verify file contains all panel data

- [ ] **Excel file locked**
  - Open exported Excel file in Excel
  - Try to export again (same pallet)
  - Verify error handling
  - Verify user-friendly error message

- [ ] **Missing workbook**
  - Remove CURRENT.xlsx
  - Try to export pallet
  - Verify error handling
  - Verify app doesn't crash

- [ ] **Invalid Excel file**
  - Corrupt Excel file
  - Try to read/import
  - Verify error handling

- [ ] **Large pallet export**
  - Create pallet with 25 panels
  - Export
  - Verify all data is correct
  - Verify file opens correctly

### 5. Serial Database Operations

**Test Cases:**
- [ ] **Database file missing**
  - Remove serial_database.xlsx
  - Launch app
  - Verify database is created automatically
  - Verify app doesn't crash

- [ ] **Database locked**
  - Open serial_database.xlsx in Excel
  - Try to validate barcode
  - Verify error handling
  - Verify app doesn't crash

- [ ] **Import simulator data**
  - Drop file in SUN SIMULATOR DATA/
  - Run import tool
  - Verify data is imported
  - Verify database is updated

- [ ] **Large database**
  - Import many records
  - Verify performance is acceptable
  - Verify validation still works

### 6. Pallet History

**Test Cases:**
- [ ] **View history**
  - Create and export multiple pallets
  - Open pallet history
  - Verify all pallets are listed
  - Verify dates are correct

- [ ] **Select pallets**
  - Open history
  - Select multiple pallets with checkboxes
  - Verify selection works
  - Verify "Select All" works

- [ ] **Create PDF & Print**
  - Select pallets
  - Click "Create PDF & Print"
  - Verify PDF is created (if reportlab installed)
  - Verify fallback to Excel printing works

- [ ] **Empty history**
  - Delete all pallets
  - Open history
  - Verify empty state is handled

### 7. UI Responsiveness

**Test Cases:**
- [ ] **Rapid barcode scanning**
  - Scan barcodes quickly (10+ in a row)
  - Verify UI doesn't freeze
  - Verify all barcodes are processed

- [ ] **Large pallet display**
  - Create pallet with 25 panels
  - Verify scrolling works
  - Verify display is responsive

- [ ] **History window performance**
  - Create 50+ pallets
  - Open history
  - Verify window opens quickly
  - Verify selection is responsive

### 8. Error Recovery

**Test Cases:**
- [ ] **Network drive disconnection**
  - If using network drive
  - Disconnect during operation
  - Verify error handling
  - Verify data is not lost

- [ ] **Disk full**
  - Fill disk to capacity
  - Try to export pallet
  - Verify error message
  - Verify app doesn't crash

- [ ] **Permission changes**
  - Change folder permissions mid-operation
  - Try to continue
  - Verify error handling

### 9. Cross-Platform Differences

**Test Cases:**
- [ ] **Path handling**
  - Test on macOS
  - Test on Windows
  - Verify paths are handled correctly
  - Verify no platform-specific bugs

- [ ] **File permissions**
  - Test on macOS (different permission model)
  - Test on Windows
  - Verify consistent behavior

### 10. Edge Cases

**Test Cases:**
- [ ] **Empty pallet export**
  - Try to export empty pallet
  - Verify handled gracefully

- [ ] **Special characters in barcodes**
  - Test barcodes with special characters
  - Verify handled correctly

- [ ] **Very long serial numbers**
  - Test extremely long serial numbers
  - Verify validation works

- [ ] **Unicode characters**
  - Test barcodes with Unicode
  - Verify handled correctly

- [ ] **Concurrent access**
  - Open app twice (if possible)
  - Verify no file locking issues

## 🧪 Automated Test Scripts

### Quick Test Checklist

Run these tests before each release:

1. **Installation Test**
   - [ ] Install on clean macOS system
   - [ ] Install on clean Windows system
   - [ ] Verify folders are created
   - [ ] Verify app launches

2. **Basic Functionality**
   - [ ] Scan valid barcode → Added to pallet
   - [ ] Scan duplicate → Warning shown
   - [ ] Fill pallet to 25 → Full message shown
   - [ ] Export pallet → Excel file created
   - [ ] View history → Pallet listed

3. **Error Handling**
   - [ ] Missing Excel file → Error message
   - [ ] Locked file → Error message
   - [ ] Invalid barcode → Error message

## 📋 Test Execution

### Before Release

1. Run all critical test cases
2. Test on both macOS and Windows
3. Test on clean systems (no existing data)
4. Test with existing data
5. Test error scenarios
6. Verify all error messages are user-friendly

### Regression Testing

After each bug fix:
- [ ] Test the specific bug fix
- [ ] Test related functionality
- [ ] Run quick test checklist

## 🐛 Known Issues to Monitor

- Folder creation in /Applications/ (fixed - now uses Documents)
- UI lag during history selection (fixed - using checkboxes)
- Pallet full auto-creation (fixed - removed auto-creation)

## 📝 Test Results Template

```
Test Date: [Date]
Tester: [Name]
Platform: [macOS/Windows]
Version: [Version]

Results:
- Test Case 1: [PASS/FAIL] - [Notes]
- Test Case 2: [PASS/FAIL] - [Notes]
...

Issues Found:
- [Issue description]
- [Steps to reproduce]
- [Severity: Critical/High/Medium/Low]
```



