# Project Structure

This document describes the organization of the Pallet Manager project.

## 📁 Directory Structure

```
.
├── app/                          # Application source code
│   ├── __init__.py
│   ├── pallet_builder_gui.py     # Main GUI application
│   ├── pallet_manager.py         # Pallet management logic
│   ├── pallet_exporter.py        # Excel export functionality
│   ├── pallet_history_window.py   # History viewer
│   ├── serial_database.py        # Serial number database
│   ├── workbook_utils.py         # Excel workbook utilities
│   ├── path_utils.py             # Path resolution utilities
│   ├── archive_manager.py        # Archive management
│   ├── import_sunsim.py          # Sun simulator import tool
│   ├── tool_runner.py            # Tool wrapper
│   ├── version.py                # Version information
│   ├── update_checker.py         # Update checking utilities
│   └── config.yaml               # Configuration file
│
├── scripts/                      # Build and utility scripts
│   ├── build_macos.sh            # Build macOS app
│   ├── build_windows.bat         # Build Windows app
│   ├── install_all.sh            # Complete macOS installer
│   ├── install_all_windows.bat   # Complete Windows installer
│   ├── create_macos_installer.sh # Create .pkg installer
│   ├── create_windows_installer.bat # Create .exe installer
│   ├── create_windows_installer.nsi # NSIS installer script
│   ├── create_dmg.sh             # Create DMG file
│   ├── setup_windows.bat         # Windows setup script
│   ├── postinstall               # macOS post-install script
│   ├── release.sh                # Release workflow
│   ├── update_version.py         # Version updater
│   ├── create_icons.sh           # Icon creation
│   └── create_update_info.py     # Update info creator
│
├── docs/                         # Documentation
│   ├── APP_OVERVIEW.md           # Complete application overview
│   ├── USER_GUIDE.md             # User installation and usage
│   ├── DEVELOPER_GUIDE.md        # Build and deployment guide
│   ├── PROJECT_STRUCTURE.md      # Directory organization
│   ├── SCRIPTS_GUIDE.md          # Scripts reference
│   ├── CHANGELOG.md              # Version history
│   ├── STABILITY_SAFEGUARDS.md   # Stability documentation
│   ├── DEPLOYMENT.md             # Deployment guide
│   ├── BUG_TESTING_PLAN.md       # Testing procedures
│   ├── PERFORMANCE_OPTIMIZATIONS.md
│   ├── PACKAGING_OPTIMIZATIONS.md
│   ├── REPORTLAB_INSTALLATION.md
│   ├── TROUBLESHOOTING.md
│   └── UPDATES.md
│
├── assets/                       # Application assets
│   ├── PalletManager.icns        # macOS icon
│   ├── PalletManager.ico         # Windows icon
│   └── Pallet icon.png           # Source icon
│
├── tools/                        # External tools and dependencies
│   ├── README.md
│   └── SumatraPDF/               # PDF viewer for Windows
│
├── data/                         # User data and runtime files
│   ├── CUSTOMERS/                # Customer database
│   ├── EXCEL/                    # Excel workbooks
│   ├── PALLETS/                  # Exported pallet files
│   ├── IMPORTED DATA/            # Processed simulator data
│   ├── SUN SIMULATOR DATA/       # Drop new simulator files here
│   └── LOGS/                     # Application logs
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_bugs.py              # Bug regression tests
│   ├── test_long_term_stability.py # Stability tests
│   ├── test_stress_simple.py     # Simple stress tests
│   ├── test_stress.py            # Full stress tests
│   └── verify_dependencies.py    # Dependency verification
│
├── README.md                     # Main project documentation
├── requirements.txt              # Python dependencies
├── setup.py                      # macOS build configuration
├── launch_app.py                 # Application launcher
└── [build files]                 # Generated during build
```

## 📋 File Organization

### Root Level
Only essential project files:
- Configuration files (`setup.py`, `pallet_builder.spec`)
- Documentation (`README.md`, `QUICK_START.md`)
- Dependencies (`requirements.txt`)
- Utilities (`verify_dependencies.py`)

### scripts/
All build, installer, and utility scripts:
- Build scripts
- Installer creation scripts
- Setup scripts
- Release workflow scripts
- Icon and update utilities

### docs/
All documentation:
- Installation guides
- Deployment guides
- Troubleshooting
- Update distribution

### app/
Application source code:
- Main application modules
- Utilities and helpers
- Configuration files

### Data Folders
User-generated data (not in version control):
- `EXCEL/` - Excel workbooks
- `PALLETS/` - Exported pallets
- `IMPORTED DATA/` - Processed data
- `SUN SIMULATOR DATA/` - Input files
- `LOGS/` - Log files

## 🗑️ Excluded from Version Control

The following are excluded (see `.gitignore`):
- `build/` - Build artifacts
- `dist/` - Distribution files
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python files
- User data files (Excel, pallets, etc.)
- Temporary files

## 📦 Build Outputs

After building, you'll find:
- `dist/Pallet Manager.app` - macOS application
- `dist/PalletManager-Installer.pkg` - macOS installer
- `dist/PalletManager-Installer.dmg` - macOS DMG
- `dist/Pallet Manager.exe` - Windows executable
- `dist/Pallet Manager-Setup.exe` - Windows installer

## 🔧 Common Operations

**Build installers:**
```bash
./scripts/install_all.sh          # macOS
scripts\install_all_windows.bat   # Windows
```

**Release new version:**
```bash
./scripts/release.sh 1.0.1
```

**Create icons:**
```bash
./scripts/create_icons.sh icons/Pallet\ icon.png
```

**Create update info:**
```bash
python scripts/create_update_info.py
```



