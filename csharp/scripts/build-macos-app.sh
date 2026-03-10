#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RID="${1:-}"
PUBLISH_DIR="${2:-$ROOT_DIR/artifacts/publish/$RID}"
APP_NAME="PalletManager.Desktop.Avalonia"
APP_BUNDLE_NAME="${APP_NAME}.app"
APP_OUT_DIR="$ROOT_DIR/artifacts/app/$RID"
APP_BUNDLE_PATH="$APP_OUT_DIR/$APP_BUNDLE_NAME"
APP_PAYLOAD_DIR="$APP_BUNDLE_PATH/Contents/AppPayload"
APP_LAUNCHER_PATH="$APP_BUNDLE_PATH/Contents/MacOS/PalletManagerLauncher"
APP_VERSION="${APP_VERSION:-2.0.0}"
APP_BUNDLE_ID="${APP_BUNDLE_ID:-com.crossroads.palletmanager.csharp}"

if [[ -z "$RID" ]]; then
  echo "Usage: bash csharp/scripts/build-macos-app.sh <rid> [publish-dir]"
  echo "Example RID: osx-arm64"
  exit 2
fi

if [[ "$RID" != osx-* ]]; then
  echo "[build-macos-app] unsupported RID for .app packaging: $RID"
  exit 2
fi

if [[ ! -d "$PUBLISH_DIR" ]]; then
  echo "[build-macos-app] publish directory missing: $PUBLISH_DIR"
  exit 1
fi

if [[ ! -f "$PUBLISH_DIR/$APP_NAME.dll" ]]; then
  echo "[build-macos-app] expected app dll missing: $PUBLISH_DIR/$APP_NAME.dll"
  exit 1
fi

mkdir -p "$APP_OUT_DIR"
rm -rf "$APP_BUNDLE_PATH"
mkdir -p "$APP_BUNDLE_PATH/Contents/MacOS" "$APP_BUNDLE_PATH/Contents/Resources" "$APP_PAYLOAD_DIR"

cp -R "$PUBLISH_DIR"/. "$APP_PAYLOAD_DIR/"

cat >"$APP_LAUNCHER_PATH" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_PAYLOAD_DIR="$CONTENTS_DIR/AppPayload"
APP_DLL_PATH="$APP_PAYLOAD_DIR/PalletManager.Desktop.Avalonia.dll"

EMBEDDED_DOTNET_ROOT="$(cd "$CONTENTS_DIR/../../../../../.dotnet" 2>/dev/null && pwd || true)"
EMBEDDED_DOTNET="$EMBEDDED_DOTNET_ROOT/dotnet"

if [[ -x "$EMBEDDED_DOTNET" ]]; then
  DOTNET_CMD="$EMBEDDED_DOTNET"
  export DOTNET_ROOT="$EMBEDDED_DOTNET_ROOT"
  export DOTNET_ROOT_ARM64="$EMBEDDED_DOTNET_ROOT"
elif command -v dotnet >/dev/null 2>&1; then
  DOTNET_CMD="$(command -v dotnet)"
else
  osascript -e 'display dialog "No dotnet runtime found. Build via csharp/.dotnet bootstrap or install dotnet." buttons {"OK"} default button "OK"' >/dev/null 2>&1 || true
  exit 127
fi

exec "$DOTNET_CMD" "$APP_DLL_PATH" "$@"
EOF

chmod +x "$APP_LAUNCHER_PATH"

cat >"$APP_BUNDLE_PATH/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Pallet Manager</string>
  <key>CFBundleDisplayName</key><string>Pallet Manager</string>
  <key>CFBundleIdentifier</key><string>$APP_BUNDLE_ID</string>
  <key>CFBundleVersion</key><string>$APP_VERSION</string>
  <key>CFBundleShortVersionString</key><string>$APP_VERSION</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>PalletManagerLauncher</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

# Local dev build: clear quarantine and remove signatures to avoid stale/invalid code signature state.
xattr -cr "$APP_BUNDLE_PATH" >/dev/null 2>&1 || true
codesign --remove-signature "$APP_BUNDLE_PATH" >/dev/null 2>&1 || true

echo "[build-macos-app] success"
echo "[build-macos-app] app bundle: $APP_BUNDLE_PATH"
