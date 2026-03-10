#!/usr/bin/env bash
set -euo pipefail

RID="${1:-}"
ARTIFACT_DIR="${2:-}"
PUBLISH_DIR="${3:-}"
APP_NAME="PalletManager.Desktop.Avalonia"

decode_base64_to_file() {
  local input="$1"
  local output="$2"
  if base64 --help >/dev/null 2>&1 && base64 --help 2>&1 | grep -q -- "--decode"; then
    printf '%s' "$input" | base64 --decode > "$output"
  else
    printf '%s' "$input" | base64 -d > "$output"
  fi
}

if [[ -z "$RID" || -z "$ARTIFACT_DIR" ]]; then
  echo "Usage: bash csharp/scripts/signing-stub.sh <rid> <artifact-dir> [publish-dir]"
  exit 2
fi

if [[ ! -d "$ARTIFACT_DIR" ]]; then
  echo "[signing-stub] artifact directory does not exist: $ARTIFACT_DIR"
  exit 1
fi

echo "[signing-stub] rid: $RID"
echo "[signing-stub] artifact-dir: $ARTIFACT_DIR"
if [[ -n "$PUBLISH_DIR" ]]; then
  echo "[signing-stub] publish-dir: $PUBLISH_DIR"
fi

case "$RID" in
  osx-*)
    if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
      echo "[signing-stub] APPLE_SIGNING_IDENTITY missing; macOS signing skipped"
      exit 0
    fi

    if [[ -z "$PUBLISH_DIR" ]]; then
      echo "[signing-stub] publish-dir missing; macOS signing skipped"
      exit 0
    fi

    APP_PATH="$PUBLISH_DIR/$APP_NAME"
    if [[ ! -f "$APP_PATH" ]]; then
      echo "[signing-stub] macOS app artifact not found: $APP_PATH"
      exit 1
    fi

    if ! command -v codesign >/dev/null 2>&1; then
      echo "[signing-stub] codesign not available; macOS signing skipped"
      exit 0
    fi

    codesign --force --verify --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"
    echo "[signing-stub] macOS binary signed: $APP_PATH"

    if [[ -n "${APPLE_NOTARY_PROFILE:-}" ]] && command -v xcrun >/dev/null 2>&1; then
      if compgen -G "$ARTIFACT_DIR/*.zip" >/dev/null; then
        ARCHIVE="$(ls "$ARTIFACT_DIR"/*.zip | head -n 1)"
        xcrun notarytool submit "$ARCHIVE" --keychain-profile "$APPLE_NOTARY_PROFILE" --wait
        echo "[signing-stub] macOS notarization submitted: $ARCHIVE"
      else
        echo "[signing-stub] notarization skipped (no .zip archive in $ARTIFACT_DIR)"
      fi
    else
      echo "[signing-stub] notarization skipped (profile/tool unavailable)"
    fi
    ;;
  win-*)
    if [[ -z "${WINDOWS_CERT_BASE64:-}" || -z "${WINDOWS_CERT_PASSWORD:-}" ]]; then
      echo "[signing-stub] Windows signing secrets missing; signing skipped"
      exit 0
    fi

    if [[ -z "$PUBLISH_DIR" ]]; then
      echo "[signing-stub] publish-dir missing; Windows signing skipped"
      exit 0
    fi

    APP_PATH="$PUBLISH_DIR/$APP_NAME.exe"
    if [[ ! -f "$APP_PATH" ]]; then
      echo "[signing-stub] Windows app artifact not found: $APP_PATH"
      exit 1
    fi

    if ! command -v signtool >/dev/null 2>&1; then
      echo "[signing-stub] signtool not available; Windows signing skipped"
      exit 0
    fi

    CERT_PATH="$(mktemp "${TMPDIR:-/tmp}/pm-signing-cert-XXXXXX.pfx")"
    trap 'rm -f "$CERT_PATH"' EXIT
    decode_base64_to_file "$WINDOWS_CERT_BASE64" "$CERT_PATH"

    signtool sign \
      /f "$CERT_PATH" \
      /p "$WINDOWS_CERT_PASSWORD" \
      /tr http://timestamp.digicert.com \
      /td sha256 \
      /fd sha256 \
      "$APP_PATH"

    echo "[signing-stub] Windows executable signed: $APP_PATH"
    ;;
  linux-*)
    if [[ -z "${LINUX_GPG_PRIVATE_KEY:-}" ]]; then
      echo "[signing-stub] Linux signing key missing; signing skipped"
      exit 0
    fi

    if ! command -v gpg >/dev/null 2>&1; then
      echo "[signing-stub] gpg not available; Linux signing skipped"
      exit 0
    fi

    if ! compgen -G "$ARTIFACT_DIR/*" >/dev/null; then
      echo "[signing-stub] no artifacts to sign in $ARTIFACT_DIR"
      exit 1
    fi

    GPG_HOME="$(mktemp -d "${TMPDIR:-/tmp}/pm-gpg-XXXXXX")"
    trap 'rm -rf "$GPG_HOME"' EXIT

    printf '%s' "$LINUX_GPG_PRIVATE_KEY" | gpg --batch --homedir "$GPG_HOME" --import

    mapfile -t FILES < <(find "$ARTIFACT_DIR" -maxdepth 1 -type f | sort)
    for f in "${FILES[@]}"; do
      gpg --batch --yes --homedir "$GPG_HOME" --armor --detach-sign "$f"
      echo "[signing-stub] Linux artifact signed: $f.asc"
    done
    ;;
  *)
    echo "[signing-stub] unsupported rid: $RID"
    exit 2
    ;;
esac

echo "[signing-stub] completed (stub mode)"
