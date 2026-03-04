#!/bin/bash
# Create a professional macOS .pkg installer
# This creates a proper installer wizard that users can double-click

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="Pallet Manager"
APP_BUNDLE="Pallet Manager.app"
PKG_NAME="PalletManager-Installer"
VERSION="1.0.0"

echo "========================================"
echo "Creating macOS Installer Package (.pkg)"
echo "========================================"
echo ""

# Check if app exists
if [ ! -d "dist/${APP_BUNDLE}" ]; then
    echo "ERROR: ${APP_BUNDLE} not found in dist/ folder"
    echo "Please run ./scripts/build_macos.sh first"
    exit 1
fi

# Clean up old installer if it exists
if [ -f "dist/${PKG_NAME}.pkg" ]; then
    echo "Removing old installer..."
    rm "dist/${PKG_NAME}.pkg"
fi

# Create temporary directory structure
TEMP_PKG_DIR="dist/pkg_build"
rm -rf "${TEMP_PKG_DIR}"
mkdir -p "${TEMP_PKG_DIR}/Applications"

# Copy app to Applications folder structure
echo "Preparing installer package..."
cp -R "dist/${APP_BUNDLE}" "${TEMP_PKG_DIR}/Applications/"

# Create distribution.xml for installer
cat > "${TEMP_PKG_DIR}/distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>${APP_NAME} ${VERSION}</title>
    <organization>com.crossroads</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" rootVolumeOnly="true"/>
    <welcome file="welcome.html" mime-type="text/html"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    <pkg-ref id="com.crossroads.palletmanager"/>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="com.crossroads.palletmanager"/>
    </choices-outline>
    <choice id="com.crossroads.palletmanager" visible="false">
        <pkg-ref id="com.crossroads.palletmanager"/>
    </choice>
    <pkg-ref id="com.crossroads.palletmanager" version="${VERSION}" onConclusion="none">${APP_NAME}.pkg</pkg-ref>
</installer-gui-script>
EOF

# Create welcome message
cat > "${TEMP_PKG_DIR}/welcome.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome</title>
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; }
        h1 { color: #333; }
        p { line-height: 1.6; }
    </style>
</head>
<body>
    <h1>Welcome to Pallet Manager</h1>
    <p>This installer will guide you through the installation of Pallet Manager.</p>
    <p><strong>What will be installed:</strong></p>
    <ul>
        <li>Pallet Manager application</li>
        <li>All required dependencies</li>
    </ul>
    <p><strong>Requirements:</strong></p>
    <ul>
        <li>macOS 10.13 (High Sierra) or later</li>
        <li>No Python installation required</li>
    </ul>
    <p>Click "Continue" to proceed with the installation.</p>
</body>
</html>
EOF

# Create conclusion message
cat > "${TEMP_PKG_DIR}/conclusion.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Installation Complete</title>
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; }
        h1 { color: #28a745; }
        p { line-height: 1.6; }
    </style>
</head>
<body>
    <h1>Installation Complete!</h1>
    <p>Pallet Manager has been successfully installed in your Applications folder.</p>
    <p><strong>Next steps:</strong></p>
    <ol>
        <li>Open the Applications folder</li>
        <li>Double-click "Pallet Manager" to launch</li>
        <li>If macOS blocks the app, right-click → Open → Open</li>
    </ol>
    <p>The app will automatically create the following folders when you first run it:</p>
    <ul>
        <li>PALLETS/</li>
        <li>IMPORTED DATA/</li>
        <li>SUN SIMULATOR DATA/</li>
        <li>EXCEL/</li>
        <li>LOGS/</li>
    </ul>
    <p>Thank you for installing Pallet Manager!</p>
</body>
</html>
EOF

# Build the component package
echo "Building component package..."
pkgbuild --root "${TEMP_PKG_DIR}" \
    --identifier "com.crossroads.palletmanager" \
    --version "${VERSION}" \
    --install-location "/" \
    --scripts "$PROJECT_ROOT/installer_scripts" \
    "${TEMP_PKG_DIR}/${APP_NAME}.pkg"

# Build the distribution package (installer)
echo "Creating installer package..."
productbuild --distribution "${TEMP_PKG_DIR}/distribution.xml" \
    --package-path "${TEMP_PKG_DIR}" \
    --resources "${TEMP_PKG_DIR}" \
    "dist/${PKG_NAME}.pkg"

# Clean up
rm -rf "${TEMP_PKG_DIR}"

echo ""
echo "========================================"
echo "✅ Installer Package Created!"
echo "========================================"
echo ""
echo "📦 Installer location: dist/${PKG_NAME}.pkg"
echo ""
echo "📋 To install:"
echo "   1. Double-click: ${PKG_NAME}.pkg"
echo "   2. Follow the installation wizard"
echo "   3. Enter your password when prompted"
echo "   4. Done! App will be in Applications"
echo ""
echo "💡 This is a professional installer that users can"
echo "   double-click and follow a simple wizard."
echo ""

