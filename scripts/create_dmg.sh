#!/bin/bash
# Create a DMG (disk image) for easy macOS installation
# This creates a professional installer package

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="Pallet Manager"
APP_BUNDLE="Pallet Manager.app"
DMG_NAME="PalletManager-Installer"
VERSION="1.0.0"

echo "========================================"
echo "Creating macOS Installer DMG"
echo "========================================"
echo ""

# Check if app exists
if [ ! -d "dist/${APP_BUNDLE}" ]; then
    echo "ERROR: ${APP_BUNDLE} not found in dist/ folder"
    echo "Please run ./scripts/build_macos.sh first"
    exit 1
fi

# Clean up old DMG if it exists
if [ -f "dist/${DMG_NAME}.dmg" ]; then
    echo "Removing old DMG..."
    rm "dist/${DMG_NAME}.dmg"
fi

# Create a temporary directory for DMG contents
TEMP_DMG_DIR="dist/dmg_contents"
rm -rf "${TEMP_DMG_DIR}"
mkdir -p "${TEMP_DMG_DIR}"

# Copy app to temp directory
echo "Preparing DMG contents..."
cp -R "dist/${APP_BUNDLE}" "${TEMP_DMG_DIR}/"

# Create Applications symlink (for drag-and-drop)
ln -s /Applications "${TEMP_DMG_DIR}/Applications"

# Create README with installation instructions
cat > "${TEMP_DMG_DIR}/📖 INSTALL INSTRUCTIONS.txt" << 'EOF'
═══════════════════════════════════════════════════════════════
  Pallet Manager - Installation Instructions
═══════════════════════════════════════════════════════════════

QUICK INSTALL (3 Steps):

1. Drag "Pallet Manager.app" to the "Applications" folder
   (or to any location you prefer)

2. Open Applications folder and double-click "Pallet Manager"

3. If macOS blocks the app:
   • Right-click "Pallet Manager" → Select "Open"
   • Click "Open" in the security dialog
   • (This only needs to be done once)

That's it! The app is ready to use.

═══════════════════════════════════════════════════════════════

WHAT HAPPENS NEXT:

When you first run the app, it will automatically create these
folders in the same directory as the app:

  • PALLETS/              - Exported pallet files
  • IMPORTED DATA/        - Processed simulator data
  • SUN SIMULATOR DATA/   - Drop new simulator files here
  • EXCEL/                - Your Excel workbooks go here
  • LOGS/                 - Application logs

NO PYTHON REQUIRED!
The app is completely self-contained. All dependencies are included.

═══════════════════════════════════════════════════════════════

NEED HELP?

If the app won't open:
  • Right-click the app → Select "Open"
  • Or go to System Settings → Privacy & Security → Open Anyway

For more help, see: MACOS_INSTALLATION.md

═══════════════════════════════════════════════════════════════
EOF

# Create the DMG with optimized compression
echo "Creating DMG file..."
# UDZO = Compressed (good balance of size and speed)
# Alternative: UDBZ = Better compression but slower
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "${TEMP_DMG_DIR}" \
    -ov -format UDZO \
    -fs HFS+ \
    -imagekey zlib-level=9 \
    "dist/${DMG_NAME}.dmg"

# Clean up temp directory
rm -rf "${TEMP_DMG_DIR}"

echo ""
echo "========================================"
echo "✅ DMG Created Successfully!"
echo "========================================"
echo ""
echo "📦 Installer location: dist/${DMG_NAME}.dmg"
echo ""
echo "📋 To distribute:"
echo "   1. Share the DMG file (${DMG_NAME}.dmg)"
echo "   2. Recipients double-click the DMG"
echo "   3. They drag the app to Applications"
echo "   4. Done!"
echo ""
echo "🔒 Note: First-time users may need to right-click → Open"
echo "   to bypass macOS Gatekeeper security."
echo ""

