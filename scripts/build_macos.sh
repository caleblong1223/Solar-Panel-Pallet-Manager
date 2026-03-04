#!/bin/bash
# Build macOS application bundle for Pallet Manager
# Run this script to create Pallet Manager.app

echo "========================================"
echo "Building Pallet Manager for macOS"
echo "========================================"
echo ""

# Check if py2app is installed
python3 -c "import py2app" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing py2app..."
    pip3 install py2app
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install py2app"
        exit 1
    fi
fi

# Check if reportlab is installed (required for PDF creation)
python3 -c "import reportlab" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: reportlab is not installed. PDF creation will not work."
    echo "Installing reportlab..."
    pip3 install reportlab
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install reportlab. Please install manually:"
        echo "  pip3 install reportlab"
        exit 1
    fi
fi

# Check if jinja2 is installed (dependency of pandas/reportlab)
python3 -c "import jinja2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing jinja2..."
    pip3 install jinja2
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install jinja2. Please install manually:"
        echo "  pip3 install jinja2"
        exit 1
    fi
fi

# Verify dependencies
echo "Verifying dependencies..."
python3 verify_dependencies.py
if [ $? -ne 0 ]; then
    echo "WARNING: Some dependencies may be missing"
    echo "Continuing anyway..."
    echo ""
fi

# Detect architecture and build optimized version
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "Building for ARM64 (Apple Silicon) - Native optimization"
    ARCHFLAGS="-arch arm64" python3 setup.py py2app
elif [ "$ARCH" = "x86_64" ]; then
    echo "Building for x86_64 (Intel Mac) - Native optimization"
    ARCHFLAGS="-arch x86_64" python3 setup.py py2app
else
    echo "Building universal binary (fallback)"
    python3 setup.py py2app
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    exit 1
fi

# Remove PyQt6 to reduce app size (not used - we use tkinter)
echo ""
echo "Removing unused PyQt6 (saves ~220MB)..."
if [ -d "dist/Pallet Manager.app/Contents/Resources/lib/python3.11/PyQt6" ]; then
    rm -rf "dist/Pallet Manager.app/Contents/Resources/lib/python3.11/PyQt6"
    echo "✅ Removed PyQt6"
else
    echo "ℹ️  PyQt6 not found (already removed or not included)"
fi

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""
echo "Application location: dist/Pallet Manager.app"
echo ""
echo "📦 To create an easy installer DMG, run:"
echo "   ./scripts/create_dmg.sh"
echo ""
echo "🚀 Or run the complete installer (build + DMG):"
echo "   ./scripts/install_all.sh"
echo ""
echo "You can now distribute this app to Mac computers."
echo "No Python installation required on target machines."
echo ""



