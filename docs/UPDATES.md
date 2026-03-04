# Update Distribution Guide

This guide explains how to distribute updates to users who have installed Pallet Manager.

## Update Methods

### Method 1: Manual Download (Recommended for Small Teams)

**How it works:**
1. Build new version of the app
2. Update version number in `app/version.py`
3. Create new installer packages
4. Distribute installers to users
5. Users download and install manually

**Pros:**
- Simple and straightforward
- No server infrastructure needed
- Full control over distribution

**Cons:**
- Users must manually check for updates
- Requires user action to update

**Steps:**
1. Update version in `app/version.py`
2. Rebuild installers:
   ```bash
   # macOS
   ./scripts/install_all.sh
   
   # Windows
   scripts\install_all_windows.bat
   ```
3. Distribute new installers:
   - Email to users
   - Share via file server/cloud storage
   - Post on internal website

### Method 2: Update Check with Manual Download

**How it works:**
1. Host `update_info.json` on a server or share file
2. App checks for updates on startup (optional)
3. Notifies user if update available
4. User downloads and installs manually

**Setup:**
1. Create update info file:
   ```python
   from app.update_checker import create_update_info_file
   from pathlib import Path
   
   create_update_info_file(
       version="1.0.1",
       download_url_macos="https://yourserver.com/PalletManager-Installer.pkg",
       download_url_windows="https://yourserver.com/PalletManager-Setup.exe",
       release_notes="Bug fixes and performance improvements",
       critical=False
   )
   ```

2. Host the file:
   - Upload to web server
   - Or share via file server/cloud storage

3. Configure app to check (optional - can be added to GUI):
   ```python
   from app.update_checker import check_for_updates
   
   update_info = check_for_updates(
       update_url="https://yourserver.com/update_info.json"
   )
   ```

### Method 3: Automatic Updates (Advanced)

**Requires:**
- Update server infrastructure
- Code signing certificates
- More complex implementation

**Not currently implemented** - Can be added if needed.

## Version Management

### Updating Version Numbers

**Before each release:**

1. Update `app/version.py`:
   ```python
   VERSION = "1.0.1"  # Increment as needed
   VERSION_MAJOR = 1
   VERSION_MINOR = 0
   VERSION_PATCH = 1
   BUILD_DATE = "2026-01-15"
   ```

2. Update `setup.py`:
   ```python
   'CFBundleVersion': '1.0.1',
   'CFBundleShortVersionString': '1.0.1',
   ```

3. Update `pallet_builder.spec` (if version is in spec):
   - Version is typically in the executable name or metadata

### Version Numbering

Use semantic versioning:
- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

## Distribution Workflow

### Step-by-Step Update Process

1. **Development:**
   - Make changes
   - Test thoroughly
   - Update version number

2. **Build:**
   ```bash
   # macOS
   ./scripts/install_all.sh
   
   # Windows
   scripts\install_all_windows.bat
   ```

3. **Test:**
   - Test installers on clean systems
   - Verify all features work
   - Check version numbers display correctly

4. **Create Update Info (Optional):**
   ```python
   python3 -c "
   from app.update_checker import create_update_info_file
   from pathlib import Path
   
   create_update_info_file(
       version='1.0.1',
       download_url_macos='https://yourserver.com/PalletManager-Installer.pkg',
       download_url_windows='https://yourserver.com/PalletManager-Setup.exe',
       release_notes='Bug fixes and performance improvements',
       critical=False
   )
   "
   ```

5. **Distribute:**
   - Upload installers to server/cloud storage
   - Upload `update_info.json` (if using update checking)
   - Notify users via email/announcement

6. **User Installation:**
   - Users download new installer
   - Run installer (replaces old version)
   - Data folders remain intact

## Update Notification (Future Enhancement)

To add update checking to the GUI:

1. Add update check on startup (optional)
2. Show notification if update available
3. Provide download link
4. User installs manually

Example integration:
```python
from app.update_checker import check_for_updates
from tkinter import messagebox

def check_updates_on_startup():
    update_info = check_for_updates(
        update_url="https://yourserver.com/update_info.json"
    )
    
    if update_info:
        msg = f"Update available: {update_info['version']}\n\n"
        msg += f"{update_info['release_notes']}\n\n"
        msg += "Would you like to download it?"
        
        if messagebox.askyesno("Update Available", msg):
            # Open download URL
            import webbrowser
            webbrowser.open(update_info['download_url'])
```

## Best Practices

1. **Version Every Release:**
   - Always increment version number
   - Update build date
   - Document changes in release notes

2. **Test Before Distribution:**
   - Test on clean systems
   - Verify data migration (if any)
   - Check all features work

3. **Backward Compatibility:**
   - Try to maintain data file compatibility
   - Don't break existing workflows
   - Document breaking changes

4. **Communication:**
   - Notify users of updates
   - Provide release notes
   - Mark critical updates

5. **Data Preservation:**
   - Updates should preserve user data
   - Folders (PALLETS, EXCEL, etc.) remain intact
   - History files are preserved

## Update Info File Format

`update_info.json`:
```json
{
  "version": "1.0.1",
  "download_url_macos": "https://yourserver.com/PalletManager-Installer.pkg",
  "download_url_windows": "https://yourserver.com/PalletManager-Setup.exe",
  "release_notes": "Bug fixes and performance improvements",
  "critical": false,
  "release_date": "2026-01-15"
}
```

## Distribution Options

### Option 1: File Server/Cloud Storage
- Upload to shared drive
- Share link with users
- Simple, no infrastructure needed

### Option 2: Web Server
- Host installers on website
- Host `update_info.json`
- Enable update checking

### Option 3: Email Distribution
- Send installers via email
- Include release notes
- Good for small teams

### Option 4: Internal Software Portal
- Company software distribution system
- Centralized updates
- Version tracking

## Troubleshooting Updates

**User can't install update:**
- Ensure old app is closed
- Check file permissions
- Verify installer downloaded completely

**Data lost after update:**
- Updates should preserve data folders
- Check PALLETS/, EXCEL/, etc. folders
- Restore from backup if needed

**Version not updating:**
- Verify version in `app/version.py`
- Rebuild installers
- Check Info.plist (macOS) or version resource (Windows)

## Summary

**Recommended Approach for Most Cases:**
1. Update version number
2. Build new installers
3. Distribute via email/file server
4. Users install manually
5. (Optional) Add update checking for future versions

This provides a good balance of simplicity and control without requiring complex infrastructure.



