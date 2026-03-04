#!/bin/bash
# One-command installer creator for macOS
# Builds app and creates professional installer

set -e

echo "========================================"
echo "Pallet Manager - Complete Installer Creator"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Step 1: Build the app
echo "Step 1/3: Building application..."
cd "$PROJECT_ROOT"
"$SCRIPT_DIR/build_macos.sh"

# Step 2: Create .pkg installer
echo ""
echo "Step 2/3: Creating installer package..."
"$SCRIPT_DIR/create_macos_installer.sh"

# Step 3: Also create DMG (for alternative distribution)
echo ""
echo "Step 3/3: Creating DMG (alternative distribution)..."
"$SCRIPT_DIR/create_dmg.sh"

echo ""
echo "========================================"
echo "✅ All Installers Ready!"
echo "========================================"
echo ""
echo "📦 Professional Installer:"
echo "   dist/PalletManager-Installer.pkg"
echo "   → Double-click to run installation wizard"
echo ""
echo "📦 Alternative DMG:"
echo "   dist/PalletManager-Installer.dmg"
echo "   → Drag-and-drop installation"
echo ""
echo "💡 The .pkg installer is recommended for end users"
echo "   as it provides a professional installation wizard."
echo ""

