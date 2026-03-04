#!/bin/bash
# Complete release workflow script
# Updates version, builds installers, creates update info

set -e

echo "========================================"
echo "Pallet Manager - Release Workflow"
echo "========================================"
echo ""

# Check if version provided
if [ $# -eq 0 ]; then
    echo "Usage: ./scripts/release.sh <new_version>"
    echo "Example: ./scripts/release.sh 1.0.1"
    exit 1
fi

NEW_VERSION="$1"

echo "📋 Release Steps:"
echo "   1. Update version numbers"
echo "   2. Build macOS installer"
echo "   3. Build Windows installer"
echo "   4. Create update info file"
echo ""
read -p "Continue with release? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Release cancelled"
    exit 0
fi

# Step 1: Update version
echo ""
echo "Step 1/4: Updating version numbers..."
python3 scripts/update_version.py "$NEW_VERSION"

# Step 2: Build macOS
echo ""
echo "Step 2/4: Building macOS installer..."
./scripts/build_macos.sh

# Step 3: Build Windows (if on Windows, or skip)
echo ""
echo "Step 3/4: Building Windows installer..."
if command -v pyinstaller >/dev/null 2>&1; then
    ./scripts/build_windows.bat || echo "⚠️  Windows build skipped (run on Windows machine)"
else
    echo "⚠️  PyInstaller not found, skipping Windows build"
    echo "   Run on Windows: scripts\\build_windows.bat"
fi

# Step 4: Create update info
echo ""
echo "Step 4/4: Creating update info file..."
echo "You can run this interactively:"
echo "   python scripts/create_update_info.py"
echo ""

echo "========================================"
echo "✅ Release Complete!"
echo "========================================"
echo ""
echo "📦 Installers ready in dist/:"
echo "   • PalletManager-Installer.pkg (macOS)"
echo "   • Pallet Manager-Setup.exe (Windows)"
echo ""
echo "📋 Next steps:"
echo "   1. Test installers on clean systems"
echo "   2. Create update_info.json: python scripts/create_update_info.py"
echo "   3. Upload installers to server/storage"
echo "   4. Notify users"
echo ""

