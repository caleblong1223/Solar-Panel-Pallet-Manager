# Deployment Guide - macOS and Windows

This guide explains how to package the Pallet Manager application for distribution on macOS and Windows.

## Prerequisites

### Required Software
- **Python 3.11+** installed on your system
- **pip** (Python package manager)

### Required Python Packages
Install the packaging tools:
```bash
# For Windows
pip install pyinstaller

# For macOS
pip install py2app

# Or install both if building for multiple platforms
pip install pyinstaller py2app
```

### Verify Dependencies
Before packaging, verify all dependencies are installed:
```bash
python verify_dependencies.py
```

This will check that all required packages (openpyxl, pandas, etc.) are available.

---

## Windows Deployment (.exe)

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Build the Executable
```bash
pyinstaller pallet_builder.spec
```

### Step 3: Find Your Executable
After building, the executable will be in:
```
dist/Pallet Manager.exe
```

### Step 4: Test the Executable
1. Navigate to the `dist/` folder
2. Double-click `Pallet Manager.exe` to test
3. Verify all features work correctly

### Step 5: Distribute
- Copy `Pallet Manager.exe` to the target Windows machine
- **No installation needed** - Just double-click to run
- **No Python installation required** on target machine
- **No dependencies to install** - All bundled in the executable
- See `WINDOWS_INSTALLATION.md` for detailed installation instructions

### Troubleshooting Windows
- **"ModuleNotFoundError"**: Run `python verify_dependencies.py` to check dependencies
- **Large file size**: This is normal (50-100 MB) - all dependencies are bundled
- **Antivirus warnings**: Some antivirus software may flag PyInstaller executables. This is a false positive.

---

## macOS Deployment (.app)

### Step 1: Install py2app
```bash
pip install py2app
```

### Step 2: Build the Application Bundle
```bash
python setup.py py2app
```

### Step 3: Find Your Application
After building, the application will be in:
```
dist/Pallet Manager.app
```

### Step 4: Test the Application
1. Navigate to the `dist/` folder
2. Double-click `Pallet Manager.app` to test
3. Verify all features work correctly

### Step 5: Distribute
- Copy `Pallet Manager.app` to the target Mac
- No Python installation required on target machine
- All dependencies are bundled in the app

### Step 6: Notarize (Optional but Recommended)
For distribution outside the App Store, you may need to notarize:
```bash
# Code sign the app (requires Apple Developer account)
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" "dist/Pallet Manager.app"

# Notarize (requires Apple Developer account)
xcrun notarytool submit "dist/Pallet Manager.app" --keychain-profile "notarytool-profile" --wait
```

### Troubleshooting macOS
- **"App is damaged"**: Right-click the app → Open (first time only) to bypass Gatekeeper
- **"ModuleNotFoundError"**: Run `python verify_dependencies.py` to check dependencies
- **Large file size**: This is normal (50-100 MB) - all dependencies are bundled

---

## Quick Build Scripts

### Windows Quick Build
Create a file `build_windows.bat`:
```batch
@echo off
echo Building Windows executable...
pip install pyinstaller
pyinstaller pallet_builder.spec
echo.
echo Build complete! Executable is in dist/Pallet Manager.exe
pause
```

### macOS Quick Build
Create a file `build_macos.sh`:
```bash
#!/bin/bash
echo "Building macOS application..."
pip install py2app
python setup.py py2app
echo ""
echo "Build complete! Application is in dist/Pallet Manager.app"
```

Make it executable:
```bash
chmod +x build_macos.sh
```

---

## Build Options

### One-File vs One-Folder

**Current Configuration: One-File**
- Single executable file
- Slower startup (extracts to temp directory)
- Easier distribution

**To Change to One-Folder** (faster startup):
- Edit `pallet_builder.spec`
- Change `EXE` section to use `COLLECT` instead
- See PyInstaller documentation for details

### Include Additional Files

To include data files (like config files), edit the spec files:

**Windows (`pallet_builder.spec`):**
```python
datas=[
    ('app/config.yaml', 'app'),  # Include config file
],
```

**macOS (`setup.py`):**
```python
DATA_FILES = [
    ('app', ['app/config.yaml']),
],
```

---

## Distribution Checklist

Before distributing your packaged application:

### Windows
- [ ] Test on clean Windows system (no Python installed)
- [ ] Verify all features work
- [ ] Test Excel file operations
- [ ] Test file scanning and import
- [ ] Test export functionality
- [ ] Check file size (should be 50-100 MB)
- [ ] Test on Windows 10 and Windows 11

### macOS
- [ ] Test on clean Mac (no Python installed)
- [ ] Verify all features work
- [ ] Test Excel file operations
- [ ] Test file scanning and import
- [ ] Test export functionality
- [ ] Check file size (should be 50-100 MB)
- [ ] Test on different macOS versions
- [ ] Code sign the application (optional)
- [ ] Notarize the application (optional, for distribution)

---

## File Locations After Build

### Windows
```
dist/
  └── Pallet Manager.exe  (single executable file)
```

### macOS
```
dist/
  └── Pallet Manager.app/  (application bundle)
      └── Contents/
          ├── MacOS/
          │   └── Pallet Manager  (executable)
          ├── Resources/
          └── Info.plist
```

---

## Common Issues

### "ModuleNotFoundError" After Packaging
**Solution**: Add the missing module to `hiddenimports` in `pallet_builder.spec` or `includes` in `setup.py`

### Application Won't Start
**Solution**: 
1. Check console output for errors
2. Run `python verify_dependencies.py` to verify dependencies
3. Check that all required files are included in the build

### Large File Size
**Solution**: This is normal. PyInstaller and py2app bundle the entire Python runtime and all dependencies. File size of 50-100 MB is expected.

### Slow Startup
**Solution**: 
- This is normal for one-file builds (extracts to temp directory)
- Consider using one-folder build for faster startup
- Startup time: 3-8 seconds is typical

---

## Advanced: Custom Icons

### Windows
1. Create or obtain an `.ico` file
2. Edit `pallet_builder.spec`:
   ```python
   icon='icon.ico',  # Add icon path
   ```

### macOS
1. Create or obtain an `.icns` file
2. Edit `setup.py`:
   ```python
   'iconfile': 'icon.icns',  # Add icon path
   ```

---

## Support

For issues with packaging:
1. Check the PyInstaller documentation: https://pyinstaller.org/
2. Check the py2app documentation: https://py2app.readthedocs.io/
3. Run `python verify_dependencies.py` to verify all dependencies
4. Check console output for specific error messages

---

## Summary

**Windows:**
```bash
pip install pyinstaller
pyinstaller pallet_builder.spec
# Executable: dist/Pallet Manager.exe
```

**macOS:**
```bash
pip install py2app
python setup.py py2app
# Application: dist/Pallet Manager.app
```

Both methods create standalone applications that don't require Python on the target machine!


