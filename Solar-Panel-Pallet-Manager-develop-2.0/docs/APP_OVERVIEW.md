# Pallet Manager - Complete Application Overview

## 📋 Table of Contents

1. [What is Pallet Manager?](#what-is-pallet-manager)
2. [What Problem Does It Solve?](#what-problem-does-it-solve)
3. [Who Uses This Application?](#who-uses-this-application)
4. [How It Works - Complete Overview](#how-it-works---complete-overview)
5. [Detailed Workflow](#detailed-workflow)
6. [Key Features Explained](#key-features-explained)
7. [Technical Architecture](#technical-architecture)
8. [Data Flow](#data-flow)
9. [File Structure and Organization](#file-structure-and-organization)

---

## What is Pallet Manager?

**Pallet Manager** is a professional desktop application designed for **solar panel packout operations**. It streamlines the process of tracking solar panels as they're assembled onto shipping pallets, automatically managing data, and generating organized export files.

### Core Purpose

The application serves as a **digital pallet tracking system** that:

- **Tracks solar panels** as they're scanned and added to pallets
- **Manages pallet data** in an organized, searchable format
- **Integrates with Excel workbooks** for seamless data management
- **Exports pallet information** in organized, date-based folders
- **Maintains complete history** of all pallets built over time

### What Makes It Special

- **Offline Operation**: Works completely offline - no internet connection required
- **Barcode Integration**: Designed for barcode scanners - scan panels directly into pallets
- **Excel Integration**: Automatically updates Excel workbooks with panel data
- **Professional Packaging**: Standalone applications for macOS and Windows - no Python installation needed
- **User-Friendly**: Simple interface designed for operators on the production floor

---

## What Problem Does It Solve?

### The Challenge

In solar panel packout operations, operators need to:

1. **Track panels** as they're assembled onto pallets (typically 25 panels per pallet)
2. **Record serial numbers** for each panel on each pallet
3. **Maintain accurate records** for shipping, quality control, and inventory
4. **Export pallet data** in organized formats for documentation
5. **Search and retrieve** historical pallet information

**Traditional methods** (paper logs, manual Excel entry) are:
- ❌ Error-prone (typos, missing data)
- ❌ Time-consuming (manual data entry)
- ❌ Difficult to search (paper files, scattered Excel files)
- ❌ Hard to maintain (lost files, inconsistent formats)

### The Solution

Pallet Manager provides:

- ✅ **Automated tracking** - Scan barcodes directly into the system
- ✅ **Error prevention** - Validates serial numbers and prevents duplicates
- ✅ **Time savings** - No manual data entry required
- ✅ **Organized storage** - Automatic date-based folder organization
- ✅ **Easy searching** - Built-in history viewer with filters
- ✅ **Consistent format** - Standardized Excel exports

---

## Who Uses This Application?

### Primary Users

1. **Packout Operators**
   - Scan panel barcodes during pallet assembly
   - Build pallets by scanning 25 panels per pallet
   - Export completed pallets for documentation

2. **Production Supervisors**
   - Monitor pallet building progress
   - Review pallet history and exports
   - Generate reports from exported data

3. **Quality Control Staff**
   - Verify panel serial numbers on pallets
   - Cross-reference pallet exports with physical pallets
   - Track panel history for quality audits

### Use Cases

- **Daily Packout Operations**: Operators scan panels and build pallets throughout the day
- **Pallet Completion**: When a pallet reaches 25 panels, export it for shipping documentation
- **Historical Lookup**: Search for specific panels or pallets from previous days/weeks/months
- **Data Export**: Generate Excel files for external systems, reports, or documentation
- **Quality Audits**: Review pallet history to verify panel assignments and track issues

---

## How It Works - Complete Overview

### High-Level Process

```
1. Operator launches application
   ↓
2. Application finds Excel workbook (automatically)
   ↓
3. Operator scans panel barcodes
   ↓
4. Application validates each barcode
   ↓
5. Valid panels are added to current pallet
   ↓
6. When pallet reaches 25 panels, operator exports it
   ↓
7. Exported pallet is saved with date/timestamp
   ↓
8. History is updated for future reference
```

### Key Components

1. **Main GUI Window** - The interface operators interact with
2. **Pallet Manager** - Tracks pallets and serial numbers
3. **Excel Integration** - Reads from and updates Excel workbooks
4. **Pallet Exporter** - Creates organized export files
5. **History System** - Maintains searchable pallet records
6. **Serial Database** - Validates and tracks panel serial numbers

---

## Detailed Workflow

### Starting a New Pallet

1. **Application Launch**
   - App starts and automatically searches for Excel workbook
   - Looks for `CURRENT.xlsx` or most recent `BUILD YYYY Q-X.xlsx` file
   - If found, loads workbook data
   - If not found, shows helpful error message with instructions

2. **Pallet Initialization**
   - App automatically creates a new pallet number
   - Pallet numbers increment sequentially (1, 2, 3, ...)
   - Current pallet starts empty (0 panels)

3. **Ready for Scanning**
   - Barcode entry field is focused and ready
   - Status shows "Ready to scan"
   - Export button is disabled (no panels yet)

### Scanning Panels

1. **Barcode Entry**
   - Operator scans panel barcode (or types manually)
   - Barcode is automatically captured in the entry field
   - App processes the barcode immediately

2. **Validation Process**
   - App checks if barcode format is valid
   - If using Excel integration: Looks up panel in workbook's DATA sheet
   - If using database: Checks serial database
   - Validates panel type and electrical values (if available)

3. **Adding to Pallet**
   - If valid: Panel is added to current pallet
   - Panel count increases (1, 2, 3, ... up to 25)
   - Panel appears in the visual slot display
   - Status shows success message
   - Export button becomes enabled (after first panel)

4. **Error Handling**
   - If invalid: Error message is displayed
   - Barcode entry is cleared
   - Operator can scan again
   - Status shows specific error (e.g., "Serial not found in workbook")

### Pallet Completion

1. **25th Panel Added**
   - App detects pallet is full (25 panels)
   - Status shows "Pallet is full!"
   - Export button is highlighted

2. **Warning on 26th Scan**
   - If operator tries to scan a 26th panel:
   - Warning dialog appears: "Pallet is full (25 panels)"
   - Message instructs to export before scanning more
   - Prevents accidental overflow

3. **Export Process**
   - Operator clicks "Export Pallet" button
   - App prompts for panel type (if not already set)
   - Export file is created in organized folder structure:
     ```
     PALLETS/
       └── 6-Jan-26/          (Date folder)
           └── Pallet_001_2025-01-06_14-30-00.xlsx
     ```
   - Pallet is saved to history
   - New pallet automatically starts
   - Export button is disabled again

### History and Search

1. **Viewing History**
   - Click "View History" button
   - History window opens showing all pallets
   - Displays: Pallet number, date, panel count, panel type

2. **Filtering Options**
   - **All** - Shows all pallets
   - **Today** - Only today's pallets
   - **This Week** - Last 7 days
   - **This Month** - Current month
   - **This Year** - Current year

3. **Searching**
   - Type in search box to filter pallets
   - Searches across pallet numbers, dates, and serial numbers
   - Results update in real-time

4. **Exporting from History**
   - Select one or more pallets (checkboxes)
   - Click "Export Selected" button
   - Selected pallets are exported to Excel files
   - Files saved in same date-organized structure

---

## Key Features Explained

### 1. Barcode Scanning Integration

**What it does:**
- Accepts input from barcode scanners (or manual keyboard entry)
- Automatically processes scanned barcodes
- Validates barcode format and content

**How it works:**
- Barcode scanner acts like a keyboard
- When scanner reads a barcode, it "types" the serial number
- App captures the input and processes it immediately
- No special scanner configuration needed

**Benefits:**
- Fast data entry (no typing required)
- Reduced errors (scanner accuracy vs. manual typing)
- Hands-free operation (scan and go)

### 2. Excel Workbook Integration

**What it does:**
- Automatically finds and loads Excel workbooks
- Reads panel data from workbook's DATA sheet
- Validates serial numbers against workbook data
- Can update workbook with pallet information (optional)

**How it works:**
1. App searches for Excel files in `data/EXCEL/` folder
2. Looks for `CURRENT.xlsx` (pointer file) first
3. If not found, finds most recent `BUILD YYYY Q-X.xlsx` file
4. Opens workbook and reads DATA sheet
5. Creates lookup table of serial numbers and panel data
6. Validates scanned barcodes against this data

**Workbook Structure:**
```
Excel Workbook (located in data/EXCEL/)
├── DATA Sheet
│   ├── Column B: SerialNo (panel serial numbers)
│   ├── Column C: Date
│   ├── Column D: TTime
│   ├── Column H: Pm (power)
│   ├── Column I: Isc (current)
│   ├── Column J: Voc (voltage)
│   ├── Column K: Ipm
│   └── Column L: Vpm
└── PALLET SHEET (optional - for pallet tracking)
```

**Benefits:**
- Single source of truth (Excel workbook)
- Automatic validation (panels must exist in workbook)
- Access to panel electrical data (if needed)
- Familiar format (operators already use Excel)

### 3. Pallet Management System

**What it does:**
- Tracks pallets with unique numbers
- Stores serial numbers for each panel on each pallet
- Maintains pallet metadata (date, panel type, etc.)
- Prevents duplicate panels on same pallet

**How it works:**
- Each pallet has:
  - **Pallet Number**: Sequential (1, 2, 3, ...)
  - **Serial Numbers**: List of 25 panel serial numbers
  - **Creation Date**: When pallet was started
  - **Completion Date**: When pallet was exported
  - **Panel Type**: Type of panels (200W, 220W, 325W, etc.)

**Data Storage:**
- Pallet data stored in JSON format
- File: `PALLETS/pallet_history.json`
- Human-readable and editable (if needed)
- Automatic backups and versioning

**Benefits:**
- Complete audit trail
- Easy to search and retrieve
- Prevents data loss
- Supports historical analysis

### 4. Organized Export System

**What it does:**
- Exports pallet data to Excel files
- Organizes files by date automatically
- Creates standardized file names
- Includes all pallet information

**How it works:**
1. When pallet is exported:
   - Creates date folder: `data/PALLETS/6-Jan-26/`
   - Generates filename: `Pallet_001_2025-01-06_14-30-00.xlsx`
   - Includes:
     - Pallet number
     - Date and time
     - All 25 serial numbers
     - Panel type
     - Metadata

2. File naming convention:
   ```
   Pallet_{number}_{date}_{time}.xlsx
   Example: Pallet_001_2025-01-06_14-30-00.xlsx
   ```

3. Folder structure:
   ```
   PALLETS/
   ├── 6-Jan-26/
   │   ├── Pallet_001_2025-01-06_14-30-00.xlsx
   │   ├── Pallet_002_2025-01-06_15-45-00.xlsx
   │   └── Pallet_003_2025-01-06_16-20-00.xlsx
   ├── 7-Jan-26/
   │   └── Pallet_004_2025-01-07_09-15-00.xlsx
   └── ...
   ```

**Benefits:**
- Easy to find files (organized by date)
- Standardized format (consistent naming)
- Complete information (all data included)
- Professional appearance (ready for distribution)

### 5. History Viewer and Search

**What it does:**
- Displays all pallets in a searchable table
- Allows filtering by date range
- Enables bulk export of selected pallets
- Shows pallet details and statistics

**How it works:**
1. **History Window:**
   - Table view with columns:
     - Select (checkbox)
     - Pallet Number
     - Date
     - Panel Count
     - Panel Type
   - Sortable columns
   - Scrollable for large datasets

2. **Date Filtering:**
   - Radio buttons for quick filters:
     - All (no filter)
     - Today (current day)
     - This Week (last 7 days)
     - This Month (current month)
     - This Year (current year)

3. **Search Functionality:**
   - Text search box
   - Searches across all columns
   - Real-time filtering
   - Case-insensitive

4. **Bulk Operations:**
   - Select multiple pallets (checkboxes)
   - "Select All" checkbox in header
   - Export selected pallets at once
   - Delete selected pallets (with confirmation)

**Benefits:**
- Quick access to historical data
- Easy to find specific pallets
- Bulk operations save time
- Professional data management

### 6. Serial Number Validation

**What it does:**
- Validates barcode format
- Checks if serial number exists in workbook/database
- Prevents duplicate panels on same pallet
- Provides helpful error messages

**How it works:**
1. **Format Validation:**
   - Checks barcode matches expected pattern
   - Validates length and character types
   - Rejects obviously invalid formats

2. **Existence Check:**
   - If using Excel: Looks up serial in DATA sheet
   - If using database: Queries serial database
   - Returns error if serial not found

3. **Duplicate Prevention:**
   - Checks if serial already on current pallet
   - Prevents same panel being added twice
   - Shows error: "Serial already on this pallet"

4. **Error Messages:**
   - Clear, actionable messages
   - Tells operator what went wrong
   - Suggests how to fix the issue

**Benefits:**
- Prevents data errors
- Catches mistakes early
- Maintains data integrity
- User-friendly error handling

---

## Technical Architecture

### Application Structure

```
Pallet Manager Application
│
├── Main GUI (pallet_builder_gui.py)
│   ├── User Interface (Tkinter)
│   ├── Event Handling
│   └── User Input Processing
│
├── Pallet Manager (pallet_manager.py)
│   ├── Pallet Creation
│   ├── Serial Number Tracking
│   └── History Management
│
├── Excel Integration (workbook_utils.py)
│   ├── Workbook Discovery
│   ├── Data Reading
│   └── Serial Validation
│
├── Pallet Exporter (pallet_exporter.py)
│   ├── Excel File Generation
│   ├── Folder Organization
│   └── File Naming
│
├── History Viewer (pallet_history_window.py)
│   ├── Data Display
│   ├── Filtering
│   └── Search
│
└── Serial Database (serial_database.py)
    ├── Serial Validation
    └── Database Management
```

### Technology Stack

- **Language**: Python 3.11+
- **GUI Framework**: Tkinter (built into Python)
- **Excel Library**: openpyxl (reads/writes Excel files)
- **Data Processing**: pandas (data manipulation)
- **Packaging**: 
  - macOS: py2app (creates .app bundles)
  - Windows: PyInstaller (creates .exe files)

### Data Storage

1. **Pallet History**: JSON file (`pallet_history.json`)
   - Human-readable format
   - Easy to backup and restore
   - Supports manual editing if needed

2. **Exported Pallets**: Excel files in date folders
   - Standard Excel format (.xlsx)
   - Compatible with all Excel versions
   - Can be opened in other applications

3. **Configuration**: YAML files (if used)
   - Application settings
   - Panel type configurations
   - User preferences

### Platform Support

- **macOS**: 
  - Native .app bundle
  - Professional .pkg installer
  - DMG disk image
  - Universal binary (Intel + Apple Silicon)

- **Windows**:
  - Standalone .exe executable
  - Professional NSIS installer
  - No Python installation required

---

## Data Flow

### Complete Data Journey

```
1. Sun Simulator Export File
   ↓
2. Import Process (optional - separate tool)
   ↓
3. Excel Workbook (DATA sheet updated)
   ↓
4. Pallet Manager (reads workbook)
   ↓
5. Operator Scans Barcode
   ↓
6. Validation (checks workbook/database)
   ↓
7. Add to Pallet (stored in memory)
   ↓
8. Pallet Completion (25 panels)
   ↓
9. Export to Excel File
   ↓
10. Save to History (JSON)
   ↓
11. Organized File Storage (date folders)
```

### Data Validation Flow

```
Barcode Scanned
    ↓
Format Check
    ↓
[Valid Format?]
    ├─ No → Error: "Invalid barcode format"
    └─ Yes ↓
        Lookup in Workbook/Database
        ↓
        [Found?]
        ├─ No → Error: "Serial not found"
        └─ Yes ↓
            Check if Already on Pallet
            ↓
            [Duplicate?]
            ├─ Yes → Error: "Serial already on pallet"
            └─ No ↓
                Add to Pallet
                ↓
                Success!
```

---

## File Structure and Organization

### Application Files (Created Automatically)

```
Pallet Manager/
│
├── data/                             # User data and runtime files
│   ├── PALLETS/                      # Pallet exports
│   │   ├── pallet_history.json       # History database
│   │   ├── 6-Jan-26/                 # Date folders
│   │   │   ├── Pallet_001_2025-01-06_14-30-00.xlsx
│   │   │   └── Pallet_002_2025-01-06_15-45-00.xlsx
│   │   └── 7-Jan-26/
│   │       └── Pallet_003_2025-01-07_09-15-00.xlsx
│   │
│   ├── EXCEL/                        # Excel workbooks
│   │   ├── CURRENT.xlsx              # Pointer to current workbook
│   │   └── BUILD 2025 Q-1.xlsx       # Quarterly workbooks
│   │
│   ├── IMPORTED DATA/                # Processed simulator data
│   │   └── (processed files)
│   │
│   ├── SUN SIMULATOR DATA/           # Drop new files here
│   │   └── (simulator export files)
│   │
│   └── LOGS/                         # Application logs
│       └── (log files)
│
├── docs/                             # Documentation
├── scripts/                          # Build scripts
├── assets/                           # Application assets
└── [other folders]
```

### File Locations

**macOS:**
- If installed in `/Applications`: `~/Documents/Pallet Manager/`
- If run from source: Project directory
- Data files: `~/Documents/Pallet Manager/data/`

**Windows:**
- Same directory as the application executable
- Or user's Documents folder (depending on installation)
- Data files: Same location as executable + `data/` subfolder

### File Naming Conventions

- **Pallet Exports**: `Pallet_{number}_{date}_{time}.xlsx`
- **History File**: `pallet_history.json`
- **Date Folders**: `{day}-{month}-{year}/` (e.g., `6-Jan-26/`)
- **Excel Workbooks**: `BUILD {year} Q-{quarter}.xlsx`

---

## Summary

**Pallet Manager** is a comprehensive solution for solar panel packout operations that:

- ✅ **Automates** pallet tracking with barcode scanning
- ✅ **Integrates** seamlessly with existing Excel workflows
- ✅ **Organizes** data in professional, date-based folder structures
- ✅ **Maintains** complete history for auditing and reporting
- ✅ **Validates** data to prevent errors
- ✅ **Exports** standardized Excel files for distribution
- ✅ **Works offline** - no internet connection required
- ✅ **Runs standalone** - no Python installation needed

The application transforms manual, error-prone processes into automated, reliable workflows, saving time and ensuring data accuracy in solar panel packout operations.

---

## Additional Resources

- **[User Guide](docs/USER_GUIDE.md)** - Installation and usage instructions
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Build and deployment information
- **[Project Structure](PROJECT_STRUCTURE.md)** - Detailed directory organization
- **[Scripts Guide](SCRIPTS_GUIDE.md)** - Available scripts and tools

---

*Last Updated: January 2025*

