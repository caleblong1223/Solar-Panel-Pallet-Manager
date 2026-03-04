# Pallet Manager - Developer Guide

Complete guide for developers working on Pallet Manager.

## 📁 Project Structure

See [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) for detailed directory organization.

### Key Directories

- **`app/`** - Application source code
- **`scripts/`** - Build and utility scripts
- **`docs/`** - Documentation
- **`icons/`** - Application icons
- **`dist/`** - Build output (generated)
- **`build/`** - Build artifacts (generated)

---

## 🛠️ Development Setup

### Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)
- **Git** (for version control)

### Initial Setup

```bash
# Clone the repository (if applicable)
git clone <repository-url>
cd "Excel Script for Packout"

# Install dependencies
pip install -r requirements.txt

# Verify dependencies
python verify_dependencies.py

# Run from source
python app/pallet_builder_gui.py
```

### Optional Dependencies

```bash
# For PDF generation (optional)
pip install reportlab
```

---

## 📦 Building & Packaging

### Quick Build

**macOS:**
```bash
./scripts/install_all.sh
```

**Windows:**
```bash
scripts\install_all_windows.bat
```

### Step-by-Step Build

#### macOS

```bash
# 1. Build the app
./scripts/build_macos.sh

# 2. Create installer (optional)
./scripts/create_macos_installer.sh

# 3. Create DMG (optional)
./scripts/create_dmg.sh
```

#### Windows

```bash
# 1. Setup Python and dependencies
scripts\setup_windows.bat

# 2. Build the executable
scripts\build_windows.bat

# 3. Create installer (optional)
scripts\create_windows_installer.bat
```

### Build Configuration

**Windows:** `pallet_builder.spec` (PyInstaller configuration)
**macOS:** `setup.py` (py2app configuration)

See [PACKAGING_OPTIMIZATIONS.md](PACKAGING_OPTIMIZATIONS.md) for optimization details.

---

## 🚀 Release Process

### Automated Release

```bash
./scripts/release.sh 1.0.1
```

This script:
1. Updates version numbers
2. Builds macOS installer
3. Builds Windows installer (if on Windows)
4. Guides you through creating update info

### Manual Release

```bash
# 1. Update version
python scripts/update_version.py 1.0.1

# 2. Build macOS
./scripts/install_all.sh

# 3. Build Windows (on Windows machine)
scripts\install_all_windows.bat

# 4. Create update info (optional)
python scripts/create_update_info.py

# 5. Test installers
# 6. Distribute to users
```

---

## 📜 Scripts Reference

See [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md) for complete scripts documentation.

### Most Common Scripts

| Script | Purpose |
|--------|---------|
| `install_all.sh` | Build complete macOS installer |
| `install_all_windows.bat` | Build complete Windows installer |
| `release.sh` | Complete release workflow |
| `update_version.py` | Update version numbers |
| `create_icons.sh` | Generate application icons |

---

## 🧪 Testing

### Automated Tests

```bash
# Run bug tests
python test_bugs.py

# Verify dependencies
python verify_dependencies.py
```

### Manual Testing Checklist

1. **Installation:**
   - Test on clean system (no Python)
   - Verify all folders are created
   - Test on different OS versions

2. **Functionality:**
   - Barcode scanning
   - Pallet creation and export
   - History viewing
   - Excel operations

3. **Performance:**
   - Startup time
   - Response to rapid scanning
   - Large file handling

See [BUG_TESTING_PLAN.md](BUG_TESTING_PLAN.md) for detailed test plan.

---

## 📚 Documentation

### User Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide
- Installation instructions
- Usage instructions
- Troubleshooting

### Developer Documentation

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - This file
- **[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)** - Project organization
- **[SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md)** - Scripts reference
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide
- **[PACKAGING_OPTIMIZATIONS.md](PACKAGING_OPTIMIZATIONS.md)** - Optimization guide
- **[PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md)** - Performance tips
- **[UPDATES.md](UPDATES.md)** - Update distribution

---

## 🔧 Configuration

### Version Management

Version is managed in `app/version.py`:

```python
VERSION = "1.0.0"
BUILD_DATE = "2026-01-06"
```

Update with:
```bash
python scripts/update_version.py 1.0.1
```

### Application Configuration

Configuration files:
- `app/config.yaml` - Application configuration
- `pallet_builder.spec` - Windows build config
- `setup.py` - macOS build config

---

## 📦 Deployment

### Distribution Methods

1. **Direct Distribution:**
   - Share installer files directly
   - Users install manually

2. **Update System:**
   - Use `update_info.json` for update checking
   - See [UPDATES.md](UPDATES.md) for details

3. **Automatic Updates:**
   - Implement update checker in app
   - Download and install updates automatically

### Deployment Checklist

**Before Distribution:**
- [ ] Test on clean systems (no Python)
- [ ] Verify all features work
- [ ] Test on multiple OS versions
- [ ] Check file sizes are reasonable
- [ ] Verify installers work correctly
- [ ] Test uninstallation
- [ ] Create update info (if using update system)

**Distribution:**
- [ ] Package installers
- [ ] Create distribution package
- [ ] Test download and installation
- [ ] Provide installation instructions
- [ ] Set up update distribution (if applicable)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guide.

---

## 🎨 Icons

### Creating Icons

```bash
./scripts/create_icons.sh icons/Pallet\ icon.png
```

This creates:
- `icons/PalletManager.icns` (macOS)
- `icons/PalletManager.ico` (Windows)

### Icon Requirements

- **Source:** PNG image, preferably 512x512 or larger
- **macOS:** .icns format (created automatically)
- **Windows:** .ico format (created automatically)

---

## ⚡ Performance Optimization

### Current Optimizations

- **Windows:** Strip debug symbols, optimized excludes
- **macOS:** Maximum bytecode optimization, native ARM64
- **Both:** Extensive module exclusions, optimized imports

See [PACKAGING_OPTIMIZATIONS.md](PACKAGING_OPTIMIZATIONS.md) for details.

### Performance Tips

1. **Use caching** for frequently accessed data
2. **Lazy load** heavy components
3. **Batch operations** when possible
4. **Optimize Excel operations** (read_only mode)
5. **Throttle UI updates** for better responsiveness

See [PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md) for details.

---

## 🐛 Debugging

### Running from Source

```bash
# macOS/Linux
python app/pallet_builder_gui.py

# Windows
python app\pallet_builder_gui.py
```

### Debug Mode

Add debug flags or logging:
```python
# In app code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Checking Logs

Logs are in `LOGS/` folder:
- `import_log.txt` - Import operations
- Application logs (if implemented)

---

## 📝 Code Style

### Python Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Document functions and classes
- Keep functions focused and small

### File Organization

- One class per file (when possible)
- Group related functionality
- Use clear, descriptive names

---

## 🔄 Update Distribution

### Creating Update Info

```bash
python scripts/create_update_info.py
```

This creates `update_info.json` with:
- Version information
- Download URLs
- Release notes

### Update Checking

The app includes `app/update_checker.py` for checking updates.

See [UPDATES.md](UPDATES.md) for complete update distribution guide.

---

## 🆘 Troubleshooting Development Issues

### Build Failures

**"ModuleNotFoundError":**
- Run `python verify_dependencies.py`
- Install missing dependencies
- Check `hiddenimports` in spec files

**"ImportError":**
- Verify all dependencies are installed
- Check Python version (3.11+)
- Review import statements

### Packaging Issues

**Large file size:**
- Normal for Python apps (150-200 MB)
- All dependencies are bundled
- See optimization guide for size reduction

**Slow startup:**
- Normal for one-file builds
- Consider one-dir build for faster startup
- Check for unnecessary imports

### Testing Issues

**Tests fail:**
- Check Python version
- Verify dependencies installed
- Review test code for issues

---

## 📖 Additional Resources

- **PyInstaller Docs:** https://pyinstaller.org/
- **py2app Docs:** https://py2app.readthedocs.io/
- **Tkinter Docs:** https://docs.python.org/3/library/tkinter.html
- **openpyxl Docs:** https://openpyxl.readthedocs.io/
- **pandas Docs:** https://pandas.pydata.org/

---

## 🎯 Next Steps

1. **Review project structure** - Understand the codebase
2. **Set up development environment** - Install dependencies
3. **Run the app** - Test from source
4. **Make changes** - Implement features or fixes
5. **Test thoroughly** - Run automated and manual tests
6. **Build and test** - Create installers and test
7. **Release** - Follow release process

---

## 📞 Support

For development questions or issues:
1. Check this guide
2. Review code comments
3. Check logs for errors
4. Review related documentation

---

Happy coding! 🚀



