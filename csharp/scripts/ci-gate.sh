#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "./.dotnet/dotnet" ]]; then
  DOTNET="./.dotnet/dotnet"
else
  DOTNET="dotnet"
fi

echo "[csharp-gate] using: $DOTNET"
echo "[csharp-gate] integration tests"
"$DOTNET" test tests/PalletManager.IntegrationTests/PalletManager.IntegrationTests.csproj -nologo

echo "[csharp-gate] unit tests"
"$DOTNET" test tests/PalletManager.UnitTests/PalletManager.UnitTests.csproj -nologo

echo "[csharp-gate] parity tests"
"$DOTNET" test tests/PalletManager.ParityTests/PalletManager.ParityTests.csproj -nologo

echo "[csharp-gate] success"
