# ReportLab Installation Guide for Windows

## Why ReportLab is Required

ReportLab is **required** for PDF export functionality in the Pallet Manager application. The history window uses it to create PDF files from Excel pallet data.

## Automatic Installation

The build scripts now automatically install reportlab. Just run:

```cmd
scripts\build_windows.bat
```

Or for first-time setup:

```cmd
scripts\setup_windows.bat
```

## Manual Installation

If automatic installation fails, use the dedicated installer:

```cmd
scripts\install_reportlab.bat
```

This script:
- Upgrades pip to the latest version
- Installs build tools (setuptools, wheel)
- Attempts multiple installation methods
- Provides detailed error messages if it fails

## Common Installation Issues & Solutions

### 1. Missing C Compiler (Most Common)

**Problem:** ReportLab requires a C compiler to build on Windows.

**Solution:** Install Microsoft Visual C++ Build Tools:

1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer
3. Select "C++ build tools" workload
4. Install and restart your computer
5. Try installing reportlab again

**Alternative:** Install Visual Studio Community (free, includes build tools):
- Download from: https://visualstudio.microsoft.com/downloads/
- Select "Desktop development with C++" workload

### 2. Outdated pip

**Problem:** Old pip versions may not handle reportlab correctly.

**Solution:**
```cmd
python -m pip install --upgrade pip
python -m pip install reportlab
```

### 3. Network/Firewall Issues

**Problem:** Corporate firewalls or network restrictions block package downloads.

**Solution:**
```cmd
python -m pip install reportlab --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### 4. Permission Issues

**Problem:** Installation requires administrator privileges.

**Solution A - Run as Administrator:**
1. Right-click Command Prompt
2. Select "Run as administrator"
3. Run the installation command

**Solution B - Install for User Only:**
```cmd
python -m pip install --user reportlab
```

### 5. Multiple Python Versions

**Problem:** Installing to wrong Python version.

**Solution:** Use the specific Python version:
```cmd
py -3.11 -m pip install reportlab
```

Or use full path:
```cmd
C:\Python311\python.exe -m pip install reportlab
```

### 6. Antivirus Blocking

**Problem:** Antivirus software blocks the installation.

**Solution:**
- Temporarily disable antivirus during installation
- Add Python and pip to antivirus exclusions
- Whitelist the project folder

## Verification

After installation, verify it works:

```cmd
python -c "import reportlab; print('ReportLab version:', reportlab.Version)"
```

You should see the version number. If you get an error, reportlab is not installed correctly.

## Pre-built Wheels (Alternative)

If compilation fails, try installing pre-built wheels:

```cmd
python -m pip install reportlab --only-binary :all:
```

This downloads pre-compiled binaries instead of building from source.

## Still Having Issues?

1. **Check Python version:**
   ```cmd
   python --version
   ```
   Should be Python 3.11 or newer.

2. **Check pip version:**
   ```cmd
   python -m pip --version
   ```
   Should be pip 23.0 or newer.

3. **Try clean installation:**
   ```cmd
   python -m pip uninstall reportlab
   python -m pip install --no-cache-dir reportlab
   ```

4. **Check error messages:**
   - Copy the full error output
   - Look for specific error codes or messages
   - Search online for the specific error

5. **Use the debug installer:**
   ```cmd
   scripts\install_reportlab.bat
   ```
   This provides detailed diagnostics.

## Why ReportLab Needs a C Compiler

ReportLab includes C extensions for performance. These must be compiled during installation, which requires:
- Microsoft Visual C++ Build Tools (Windows)
- Or Visual Studio with C++ support

This is a one-time setup. Once installed, you can build Python applications that use reportlab without issues.

## Summary

**Quick Fix (Most Cases):**
1. Install Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Restart computer
3. Run: `scripts\install_reportlab.bat`

**If that doesn't work:**
- Use pre-built wheels: `python -m pip install reportlab --only-binary :all:`
- Or install Visual Studio Community instead


