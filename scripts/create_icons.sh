#!/bin/bash
# Create application icons from source image
# Usage: ./scripts/create_icons.sh <source_image.png>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <source_image.png>"
    echo ""
    echo "This script creates .icns (macOS) and .ico (Windows) icon files"
    echo "from a source PNG image."
    exit 1
fi

SOURCE_IMAGE="$1"

if [ ! -f "$SOURCE_IMAGE" ]; then
    echo "Error: Source image '$SOURCE_IMAGE' not found"
    exit 1
fi

echo "========================================"
echo "Creating Application Icons"
echo "========================================"
echo ""

# Create icons directory
mkdir -p icons

# macOS .icns creation
echo "Creating macOS icon (.icns)..."
ICONSET_DIR="icons/PalletManager.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

# Create all required icon sizes for macOS
sips -z 16 16     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null 2>&1
sips -z 32 32     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null 2>&1
sips -z 32 32     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null 2>&1
sips -z 64 64     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null 2>&1
sips -z 128 128   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null 2>&1
sips -z 256 256   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null 2>&1
sips -z 256 256   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null 2>&1
sips -z 512 512   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null 2>&1
sips -z 512 512   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null 2>&1
sips -z 1024 1024 "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null 2>&1

# Convert iconset to .icns
iconutil -c icns "$ICONSET_DIR" -o "icons/PalletManager.icns"
rm -rf "$ICONSET_DIR"

echo "✅ Created: icons/PalletManager.icns"

# Windows .ico creation (requires ImageMagick or sips)
echo ""
echo "Creating Windows icon (.ico)..."
if command -v convert >/dev/null 2>&1; then
    # Use ImageMagick if available
    convert "$SOURCE_IMAGE" -resize 256x256 -define icon:auto-resize=256,128,64,48,32,16 "icons/PalletManager.ico"
    echo "✅ Created: icons/PalletManager.ico (using ImageMagick)"
elif command -v sips >/dev/null 2>&1; then
    # Use sips to create multiple sizes, then combine (basic approach)
    # Note: sips can't directly create .ico, but we can create the PNGs
    echo "⚠️  ImageMagick not found. Creating PNG files for manual .ico conversion."
    echo "   Install ImageMagick: brew install imagemagick"
    echo "   Or use an online converter to create .ico from PNG"
    sips -z 256 256 "$SOURCE_IMAGE" --out "icons/PalletManager_256.png" >/dev/null 2>&1
    sips -z 128 128 "$SOURCE_IMAGE" --out "icons/PalletManager_128.png" >/dev/null 2>&1
    sips -z 64 64   "$SOURCE_IMAGE" --out "icons/PalletManager_64.png" >/dev/null 2>&1
    sips -z 48 48   "$SOURCE_IMAGE" --out "icons/PalletManager_48.png" >/dev/null 2>&1
    sips -z 32 32   "$SOURCE_IMAGE" --out "icons/PalletManager_32.png" >/dev/null 2>&1
    sips -z 16 16   "$SOURCE_IMAGE" --out "icons/PalletManager_16.png" >/dev/null 2>&1
    echo "✅ Created PNG files in icons/ directory"
else
    echo "⚠️  Neither ImageMagick nor sips found. Cannot create .ico file."
fi

echo ""
echo "========================================"
echo "✅ Icons Created!"
echo "========================================"
echo ""
echo "📁 Icons location: icons/"
echo ""
echo "📋 Next steps:"
echo "   1. Icons are ready in icons/ directory"
echo "   2. setup.py and pallet_builder.spec already configured"
echo "   3. Rebuild the applications:"
echo "      macOS: ./scripts/build_macos.sh"
echo "      Windows: scripts\\build_windows.bat"
echo ""

