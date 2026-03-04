# Pallet Manager - Complete User Guide

This guide covers everything you need to know to install and use Pallet Manager.

## 📥 Installation

### macOS Installation

#### Option 1: Professional Installer (.pkg) - Recommended

1. **Download** `PalletManager-Installer.pkg`
2. **Double-click** the .pkg file
3. **Follow the wizard:**
   - Click "Continue" on the welcome screen
   - Review the license (if shown)
   - Select installation location (default: Applications)
   - Enter your password when prompted
   - Wait for installation to complete
4. **Launch** from Applications folder

#### Option 2: DMG File (Drag-and-Drop)

1. **Download** `PalletManager-Installer.dmg`
2. **Double-click** the DMG file
3. **Drag** "Pallet Manager.app" to the Applications folder (or any location)
4. **Launch** from Applications folder

#### First Launch on macOS

If macOS blocks the app:
1. **Right-click** "Pallet Manager" → Select "Open"
2. **Click "Open"** in the security dialog
3. This only needs to be done once

**Alternative:** Go to System Settings → Privacy & Security → Click "Open Anyway"

### Windows Installation

1. **Download** `Pallet Manager-Setup.exe`
2. **Double-click** the installer
3. **Follow the wizard:**
   - Click "Next" on the welcome screen
   - Review the license
   - Choose installation location (default: Program Files)
   - Select components (all selected by default)
   - Click "Install"
   - Wait for installation to complete
   - Click "Finish"
4. **Launch** from Start Menu or Desktop shortcut

**Note:** The installer requires administrator privileges. You may be prompted for permission.

---

## 🎯 First-Time Setup

### Automatic Folder Creation

When you first run the app, it automatically creates these folders:

- **data/PALLETS/** - Exported pallet files
- **data/IMPORTED DATA/** - Processed simulator data
- **data/SUN SIMULATOR DATA/** - Drop new simulator files here
- **data/EXCEL/** - Your Excel workbooks
- **data/LOGS/** - Application logs

**Location:**
- **macOS:** `~/Documents/Pallet Manager/` (if installed in Applications)
- **Windows:** Same directory as the application

### Setting Up Your Data

1. **Place Excel workbooks** in the `data/EXCEL/` folder:
   - `CURRENT.xlsx` (optional - points to current workbook)
   - `BUILD YYYY Q-X.xlsx` (your quarterly pallet workbooks)

2. **Drop sun simulator files** in `SUN SIMULATOR DATA/` folder:
   - The app will automatically process these files
   - Processed data goes to `IMPORTED DATA/`

3. **Start using the app!**

---

## 💻 Using the Application

### Building a Pallet

1. **Launch** Pallet Manager
2. **Scan barcodes** using your barcode scanner:
   - The app automatically validates each barcode
   - Valid panels are added to the current pallet
   - Invalid barcodes show an error message

3. **Monitor progress:**
   - Current pallet number is displayed
   - Panel count shows how many panels are on the pallet
   - Status messages indicate success or errors

4. **When pallet is full (25 panels):**
   - Status message appears: "Pallet is full! Click 'Export Pallet' to export."
   - Click **"Export Pallet"** button to save the pallet

### Exporting a Pallet

1. **Click "Export Pallet"** button (when pallet is full or manually)
2. **Select panel type** (200W, 220W, 325W, etc.)
3. **Pallet is exported** to `data/PALLETS/[Date]/` folder
4. **Excel file is created** with all panel information
5. **Display is cleared** - ready for next pallet

**Note:** After export, you must manually click "New Pallet" to start a new pallet.

### Viewing Pallet History

1. **Click "Pallet History"** button
2. **Browse** all exported pallets
3. **Select pallets** using checkboxes
4. **View details** by clicking on a pallet
5. **Export selected pallets** to PDF or print Excel files

### Importing Sun Simulator Data

1. **Drop simulator files** in `SUN SIMULATOR DATA/` folder
2. The app automatically processes files on startup
3. **Processed data** is saved to `IMPORTED DATA/`
4. **Database is updated** for barcode validation

---

## 🆘 Troubleshooting

This section covers common issues and their solutions. For more detailed troubleshooting, see the specific sections below.

### Application Won't Start

**macOS:**
- **"App is damaged"** or **"Cannot be opened":**
  - Right-click the app → Select "Open"
  - Or go to System Settings → Privacy & Security → Click "Open Anyway"
  - This is a one-time security check

**Windows:**
- **"Windows protected your PC":**
  - Click "More info"
  - Click "Run anyway"
  - This may happen if the app isn't code-signed

### Folders Not Created

**Problem:** App says folders don't exist

**Solution:**
- Check that you have write permissions in the app directory
- On macOS, if installed in `/Applications`, folders are created in `~/Documents/Pallet Manager/`
- Try running the app as administrator (Windows)

### Barcode Not Recognized

**Problem:** "Serial number not found in database"

**Solutions:**
1. **Import simulator data first:**
   - Drop simulator file in `SUN SIMULATOR DATA/` folder
   - Restart the app to process the file

2. **Check barcode format:**
   - Should be 12+ characters
   - Should start with panel type (200, 220, 325, etc.)

3. **Verify database:**
   - Check `IMPORTED DATA/` folder has processed files
   - Check `data/PALLETS/serial_database.xlsx` exists

### Excel File Locked

**Problem:** "Excel workbook is open or locked"

**Solution:**
- Close Excel if it's open
- Check that no other process is using the file
- Try again after a few seconds

### Export Folder Not Found

**Problem:** "Export folder does not exist"

**Solution:**
- The app should create folders automatically
- Check write permissions in the app directory
- On macOS, check `~/Documents/Pallet Manager/` if app is in Applications

### Application Crashes

**Problem:** App closes unexpectedly

**Solutions:**
1. **Check logs:**
   - Look in `data/LOGS/` folder for error messages

2. **Verify data files:**
   - Check that Excel files aren't corrupted
   - Verify simulator data files are valid

3. **Reinstall:**
   - Uninstall the application
   - Download fresh installer
   - Reinstall

### Performance Issues

**Problem:** App is slow or laggy

**Solutions:**
1. **Close other applications** to free up memory
2. **Check disk space** - ensure you have enough free space
3. **Restart the application**
4. **Check for large Excel files** - very large workbooks may slow down operations

---

## ❓ Frequently Asked Questions

### Do I need Python installed?

**No!** The packaged application includes everything needed. Python is only required if you're running from source code.

### Where are my files stored?

**macOS:**
- If app is in `/Applications`: `~/Documents/Pallet Manager/`
- Otherwise: Same directory as the app

**Windows:**
- Same directory as the application (usually `Program Files\Pallet Manager\`)

### Can I move the data folders?

Yes, but you'll need to update the app configuration. It's recommended to keep them in the default location.

### How do I update the application?

1. Download the new installer
2. Run the installer (it will update the existing installation)
3. Your data files are preserved

### Can I use this offline?

Yes! The application works completely offline. No internet connection is required.

### What Excel formats are supported?

- `.xlsx` (Excel 2007+)
- `.xlsm` (Excel macro-enabled)

### How many panels per pallet?

The standard is 25 panels per pallet. The app enforces this limit.

### Can I export multiple pallets at once?

Yes! Use the "Pallet History" feature to select multiple pallets and export them together.

---

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check the logs:**
   - Look in `data/LOGS/` folder for detailed error messages

2. **Review this guide:**
   - Make sure you've followed all setup steps

3. **Contact support:**
   - Include log files and a description of the issue

---

## 📝 Tips & Best Practices

1. **Regular backups:**
   - Periodically backup your `data/EXCEL/` and `data/PALLETS/` folders

2. **Organize files:**
   - Keep simulator files in `SUN SIMULATOR DATA/` until processed
   - Move processed files to archive if needed

3. **Monitor logs:**
   - Check `data/LOGS/` folder if you encounter issues
   - Logs contain detailed information about operations

4. **Keep Excel closed:**
   - Close Excel when using the app to avoid file locking issues

5. **Validate barcodes:**
   - Ensure simulator data is imported before scanning
   - This ensures all barcodes can be validated

---

## 🎉 You're Ready!

You now have everything you need to use Pallet Manager effectively. If you have questions or encounter issues, refer back to this guide or check the troubleshooting section.

