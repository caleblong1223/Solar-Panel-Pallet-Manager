# Scripts Guide

Quick reference for all scripts in the Pallet Manager project.

## 🎯 Quick Start

### For End Users
**You don't need to run any scripts!** Just install the application using the provided installers.

### For Developers

**Most Common Tasks:**

1. **Build installers:**
   ```bash
   # macOS
   ./scripts/install_all.sh
   
   # Windows
   scripts\install_all_windows.bat
   ```

2. **Release new version:**
   ```bash
   ./scripts/release.sh 1.0.1
   ```

---

## 📦 Build Scripts

### macOS

#### `scripts/install_all.sh` ⭐ **RECOMMENDED**
**One-command installer creator**
- Builds the macOS app
- Creates professional .pkg installer
- Creates DMG file (alternative distribution)
- **Output:** `dist/PalletManager-Installer.pkg` and `dist/PalletManager-Installer.dmg`

```bash
./scripts/install_all.sh
```

#### `scripts/build_macos.sh`
**Build the app only**
- Creates `dist/Pallet Manager.app`
- Does not create installers

```bash
./scripts/build_macos.sh
```

#### `scripts/create_macos_installer.sh`
**Create .pkg installer only**
- Requires app to be built first
- Creates `dist/PalletManager-Installer.pkg`

```bash
./scripts/create_macos_installer.sh
```

#### `scripts/create_dmg.sh`
**Create DMG file only**
- Requires app to be built first
- Creates `dist/PalletManager-Installer.dmg`

```bash
./scripts/create_dmg.sh
```

### Windows

#### `scripts/install_all_windows.bat` ⭐ **RECOMMENDED**
**One-command installer creator**
- Sets up Python and dependencies (if needed)
- Builds the Windows .exe
- Creates professional installer
- **Output:** `dist/Pallet Manager-Setup.exe`

```bash
scripts\install_all_windows.bat
```

#### `scripts/build_windows.bat`
**Build the .exe only**
- Auto-installs compile dependencies (from `requirements.txt` + explicit build packages)
- Verifies PDF and build imports (`reportlab`, `PyPDF2`, `PyInstaller`, etc.)
- Creates `dist/Pallet Manager.exe`
- Does not create installer

```bash
scripts\build_windows.bat
# Optional:
# scripts\build_windows.bat --deps-only
# scripts\build_windows.bat --no-clean
# scripts\build_windows.bat --skip-sumatra
```

#### `scripts/setup_windows.bat`
**Setup Python and dependencies**
- Checks for Python installation
- Installs pip if needed
- Installs all project dependencies
- Installs PyInstaller

```bash
scripts\setup_windows.bat
```

#### `scripts/create_windows_installer.bat`
**Create installer only**
- Requires .exe to be built first
- Creates `dist/Pallet Manager-Setup.exe`

```bash
scripts\create_windows_installer.bat
```

---

## 🚀 Release Scripts

### `scripts/release.sh` ⭐ **RECOMMENDED FOR RELEASES**
**Complete release workflow**
- Updates version numbers across all files
- Builds macOS installer
- Builds Windows installer (if on Windows)
- Guides you through creating update info

```bash
./scripts/release.sh 1.0.1
```

### `scripts/update_version.py`
**Update version numbers only**
- Updates `app/version.py`
- Updates `setup.py` (macOS)
- Does not build anything

```bash
python scripts/update_version.py 1.0.1
```

---

## 🔧 Utility Scripts

### `scripts/create_icons.sh`
**Create application icons**
- Converts PNG to .icns (macOS) and .ico (Windows)
- Requires source PNG image

```bash
./scripts/create_icons.sh icons/Pallet\ icon.png
```

### `scripts/create_update_info.py`
**Create update info file**
- Interactive script to create `update_info.json`
- For distributing updates to users

```bash
python scripts/create_update_info.py
```

### `scripts/add_python_to_path.bat` (Windows)
**Add Python to PATH**
- Helper script for Windows
- Run as administrator
- Adds Python to system PATH

```bash
scripts\add_python_to_path.bat
```

### `scripts/setup_windows_debug.bat` (Windows)
**Debug version of setup script**
- Shows detailed output
- Useful for troubleshooting setup issues

```bash
scripts\setup_windows_debug.bat
```

---

## 📋 Common Workflows

### First Time Setup (Windows)

```bash
# 1. Setup Python and dependencies
scripts\setup_windows.bat

# 2. Build installer
scripts\install_all_windows.bat
```

### Building for Distribution

**macOS:**
```bash
./scripts/install_all.sh
```

**Windows:**
```bash
scripts\install_all_windows.bat
```

### Releasing a New Version

```bash
# One command does everything
./scripts/release.sh 1.0.2
```

Or step by step:
```bash
# 1. Update version
python scripts/update_version.py 1.0.2

# 2. Build macOS
./scripts/install_all.sh

# 3. Build Windows (on Windows machine)
scripts\install_all_windows.bat

# 4. Create update info (optional)
python scripts/create_update_info.py
```

### Just Testing the App

**Run from source:**
```bash
python app/pallet_builder_gui.py
```

**Or build and test:**
```bash
# macOS
./scripts/build_macos.sh
open "dist/Pallet Manager.app"

# Windows
scripts\build_windows.bat
dist\Pallet Manager.exe
```

---

## 🎯 Which Script Should I Run?

| Goal | Script to Run |
|------|--------------|
| **Build macOS installer** | `./scripts/install_all.sh` |
| **Build Windows installer** | `scripts\install_all_windows.bat` |
| **Release new version** | `./scripts/release.sh 1.0.1` |
| **Just build app (no installer)** | `./scripts/build_macos.sh` or `scripts\build_windows.bat` |
| **Create icons** | `./scripts/create_icons.sh <image.png>` |
| **Setup Windows environment** | `scripts\setup_windows.bat` |
| **Test app from source** | `python app/pallet_builder_gui.py` |

---

## 📁 Output Locations

After running build scripts, you'll find:

- **macOS:**
  - `dist/Pallet Manager.app` - Application bundle
  - `dist/PalletManager-Installer.pkg` - Professional installer
  - `dist/PalletManager-Installer.dmg` - DMG file

- **Windows:**
  - `dist/Pallet Manager.exe` - Standalone executable
  - `dist/Pallet Manager-Setup.exe` - Installer

---

## ⚠️ Troubleshooting

**Script not found:**
- Make sure you're in the project root directory
- Use `./scripts/` prefix for macOS/Linux
- Use `scripts\` prefix for Windows

**Permission denied:**
```bash
chmod +x scripts/*.sh  # macOS/Linux
```

**Python not found:**
- Run `scripts\setup_windows.bat` (Windows)
- Or install Python manually

**Dependencies missing:**
- Run `scripts\setup_windows.bat` (Windows)
- Or `pip install -r requirements.txt`


