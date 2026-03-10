#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "./.dotnet/dotnet" ]]; then
  DOTNET="./.dotnet/dotnet"
  DOTNET_ROOT="$ROOT_DIR/.dotnet"
else
  DOTNET="dotnet"
  DOTNET_PATH="$(command -v "$DOTNET")"
  DOTNET_ROOT="$(cd "$(dirname "$DOTNET_PATH")/.." && pwd)"
fi

RID="${1:-}"
CONFIGURATION="${CONFIGURATION:-Release}"
TFM="net8.0"
PROJECT="src/PalletManager.Desktop.Avalonia/PalletManager.Desktop.Avalonia.csproj"

if [[ -z "$RID" ]]; then
  echo "Usage: bash csharp/scripts/package-smoke.sh <rid>"
  echo "Example RIDs: linux-x64, osx-arm64, win-x64"
  exit 2
fi

OUT_DIR="$ROOT_DIR/artifacts/publish/$RID"
APP_NAME="PalletManager.Desktop.Avalonia"

echo "[package-smoke] using: $DOTNET"
echo "[package-smoke] rid: $RID"
echo "[package-smoke] output: $OUT_DIR"

rm -rf "$OUT_DIR"

"$DOTNET" restore "$PROJECT" -nologo
"$DOTNET" publish "$PROJECT" \
  -c "$CONFIGURATION" \
  -f "$TFM" \
  -r "$RID" \
  --self-contained false \
  -p:UseAppHost=true \
  -o "$OUT_DIR" \
  -nologo

if [[ "$RID" == win-* ]]; then
  APP_PATH="$OUT_DIR/$APP_NAME.exe"
else
  APP_PATH="$OUT_DIR/$APP_NAME"
fi
APP_DLL_PATH="$OUT_DIR/$APP_NAME.dll"

if [[ ! -f "$APP_PATH" ]]; then
  echo "[package-smoke] expected app artifact missing: $APP_PATH"
  exit 1
fi

if [[ ! -f "$APP_DLL_PATH" ]]; then
  echo "[package-smoke] expected app dll missing: $APP_DLL_PATH"
  exit 1
fi

for migration in "001_init.sql" "002_indexes.sql"; do
  if [[ ! -f "$OUT_DIR/Persistence/Migrations/$migration" ]]; then
    echo "[package-smoke] missing migration asset: $migration"
    exit 1
  fi
done

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
    echo "[package-smoke] smoke launch output missing PM_SMOKE_OK marker"
    echo "$SMOKE_OUTPUT"
    exit 1
  fi
  echo "[package-smoke] launch/open/close smoke: passed"
else
  echo "[package-smoke] launch smoke skipped (host $(uname -s) does not match RID $RID)"
fi

echo "[package-smoke] success for $RID"
echo "[package-smoke] verified:"
echo "  - app artifact: $APP_PATH"
echo "  - migrations: 001_init.sql, 002_indexes.sql"
