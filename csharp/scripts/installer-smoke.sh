#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "./.dotnet/dotnet" ]]; then
  DOTNET="./.dotnet/dotnet"
  DOTNET_ROOT="$ROOT_DIR/.dotnet"
else
  DOTNET="dotnet"
  DOTNET_PATH="$(command -v dotnet)"
  DOTNET_ROOT="$(cd "$(dirname "$DOTNET_PATH")/.." && pwd)"
fi

RID="${1:-}"
APP_NAME="PalletManager.Desktop.Avalonia"
PUBLISH_DIR="${2:-$ROOT_DIR/artifacts/publish/$RID}"
INSTALLER_DIR="$ROOT_DIR/artifacts/installers/$RID"
SMOKE_DIR="$ROOT_DIR/artifacts/install-smoke/$RID"
STAGING_DIR="$ROOT_DIR/artifacts/installer-staging/$RID"
PACKAGE_ROOT_NAME="PalletManager"

if [[ -z "$RID" ]]; then
  echo "Usage: bash csharp/scripts/installer-smoke.sh <rid> [publish-dir]"
  exit 2
fi

if [[ ! -d "$PUBLISH_DIR" ]]; then
  echo "[installer-smoke] publish directory does not exist: $PUBLISH_DIR"
  exit 1
fi

mkdir -p "$INSTALLER_DIR" "$SMOKE_DIR" "$STAGING_DIR"
rm -rf "$INSTALLER_DIR"/* "$SMOKE_DIR"/* "$STAGING_DIR"/*
mkdir -p "$STAGING_DIR/$PACKAGE_ROOT_NAME"
cp -R "$PUBLISH_DIR"/. "$STAGING_DIR/$PACKAGE_ROOT_NAME/"

if [[ "$RID" == win-* ]]; then
  ARCHIVE_PATH="$INSTALLER_DIR/${APP_NAME}-${RID}.zip"
  if command -v powershell >/dev/null 2>&1; then
    if command -v cygpath >/dev/null 2>&1; then
      PS_STAGING_DIR="$(cygpath -w "$STAGING_DIR")"
      PS_ARCHIVE_PATH="$(cygpath -w "$ARCHIVE_PATH")"
    else
      PS_STAGING_DIR="$STAGING_DIR"
      PS_ARCHIVE_PATH="$ARCHIVE_PATH"
    fi
    powershell -NoProfile -Command \
      "Compress-Archive -Path '${PS_STAGING_DIR}\\${PACKAGE_ROOT_NAME}\\*' -DestinationPath '${PS_ARCHIVE_PATH}' -Force" >/dev/null
  elif command -v zip >/dev/null 2>&1; then
    (
      cd "$STAGING_DIR/$PACKAGE_ROOT_NAME"
      zip -rq "$ARCHIVE_PATH" .
    )
  else
    echo "[installer-smoke] neither powershell nor zip is available for windows archive creation"
    exit 1
  fi
else
  ARCHIVE_PATH="$INSTALLER_DIR/${APP_NAME}-${RID}.tar.gz"
  tar -C "$STAGING_DIR" -czf "$ARCHIVE_PATH" "$PACKAGE_ROOT_NAME"
fi

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  echo "[installer-smoke] installer artifact missing: $ARCHIVE_PATH"
  exit 1
fi

INSTALL_DIR="$SMOKE_DIR/install-root"
mkdir -p "$INSTALL_DIR"

if [[ "$RID" == win-* ]]; then
  if command -v powershell >/dev/null 2>&1; then
    if command -v cygpath >/dev/null 2>&1; then
      PS_ARCHIVE_PATH="$(cygpath -w "$ARCHIVE_PATH")"
      PS_INSTALL_DIR="$(cygpath -w "$INSTALL_DIR")"
    else
      PS_ARCHIVE_PATH="$ARCHIVE_PATH"
      PS_INSTALL_DIR="$INSTALL_DIR"
    fi
    powershell -NoProfile -Command \
      "Expand-Archive -Path '${PS_ARCHIVE_PATH}' -DestinationPath '${PS_INSTALL_DIR}' -Force" >/dev/null
  elif command -v unzip >/dev/null 2>&1; then
    unzip -q "$ARCHIVE_PATH" -d "$INSTALL_DIR"
  else
    echo "[installer-smoke] neither powershell nor unzip is available for windows archive extraction"
    exit 1
  fi
else
  tar -C "$INSTALL_DIR" -xzf "$ARCHIVE_PATH"
fi

if [[ "$RID" == win-* ]]; then
  APP_PATH="$INSTALL_DIR/$APP_NAME.exe"
  APP_DLL_PATH="$INSTALL_DIR/$APP_NAME.dll"
else
  APP_PATH="$INSTALL_DIR/$PACKAGE_ROOT_NAME/$APP_NAME"
  APP_DLL_PATH="$INSTALL_DIR/$PACKAGE_ROOT_NAME/$APP_NAME.dll"
fi

if [[ ! -f "$APP_PATH" ]]; then
  echo "[installer-smoke] installed app missing: $APP_PATH"
  exit 1
fi

if [[ ! -f "$APP_DLL_PATH" ]]; then
  echo "[installer-smoke] installed app dll missing: $APP_DLL_PATH"
  exit 1
fi

host_matches_rid() {
  local host
  host="$(uname -s)"

  if [[ "$RID" == linux-* && "$host" == "Linux" ]]; then
    return 0
  fi

  if [[ "$RID" == osx-* && "$host" == "Darwin" ]]; then
    return 0
  fi

  if [[ "$RID" == win-* && "$host" == *"NT"* ]]; then
    return 0
  fi

  return 1
}

if host_matches_rid; then
  SMOKE_OUTPUT="$(DOTNET_ROOT="$DOTNET_ROOT" DOTNET_ROOT_ARM64="$DOTNET_ROOT" "$DOTNET" "$APP_DLL_PATH" --smoke 2>&1)"
  if [[ "$SMOKE_OUTPUT" != *"PM_SMOKE_OK"* ]]; then
    echo "[installer-smoke] installed app did not return smoke marker"
    echo "$SMOKE_OUTPUT"
    exit 1
  fi
else
  echo "[installer-smoke] launch smoke skipped (host $(uname -s) does not match RID $RID)"
fi

rm -rf "$INSTALL_DIR"
if [[ -d "$INSTALL_DIR" ]]; then
  echo "[installer-smoke] uninstall cleanup failed: $INSTALL_DIR"
  exit 1
fi

echo "[installer-smoke] success for $RID"
echo "[installer-smoke] verified:"
echo "  - installer artifact: $ARCHIVE_PATH"
if host_matches_rid; then
  echo "  - install smoke launch marker: PM_SMOKE_OK"
else
  echo "  - install smoke launch marker: skipped (host/rid mismatch)"
fi
echo "  - uninstall cleanup: passed"
