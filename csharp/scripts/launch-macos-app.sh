#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RID="${1:-osx-arm64}"
APP_NAME="PalletManager.Desktop.Avalonia"
APP_BUNDLE_PATH="$ROOT_DIR/artifacts/app/$RID/${APP_NAME}.app"
APP_LAUNCHER_PATH="$APP_BUNDLE_PATH/Contents/MacOS/PalletManagerLauncher"
PUBLISH_DIR="$ROOT_DIR/artifacts/publish/$RID"

if [[ "$RID" != osx-* ]]; then
  echo "Usage: bash csharp/scripts/launch-macos-app.sh [osx-rid]"
  echo "Example RID: osx-arm64"
  exit 2
fi

if [[ ! -f "$APP_LAUNCHER_PATH" ]]; then
  if [[ ! -d "$PUBLISH_DIR" ]]; then
    echo "[launch-macos-app] no publish output found for $RID; running package smoke build"
    bash "$ROOT_DIR/scripts/package-smoke.sh" "$RID"
  else
    echo "[launch-macos-app] app bundle missing; rebuilding from existing publish output"
    bash "$ROOT_DIR/scripts/build-macos-app.sh" "$RID" "$PUBLISH_DIR"
  fi
fi

xattr -cr "$APP_BUNDLE_PATH" >/dev/null 2>&1 || true
open "$APP_BUNDLE_PATH"

echo "[launch-macos-app] opened: $APP_BUNDLE_PATH"
