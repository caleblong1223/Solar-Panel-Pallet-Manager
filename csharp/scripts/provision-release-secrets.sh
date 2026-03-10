#!/usr/bin/env bash
set -euo pipefail

# Provisions GitHub Actions secrets required by csharp-release-stubs workflow.
# Values are read from env vars or optional file inputs.
#
# Required logical secrets:
# - APPLE_SIGNING_IDENTITY
# - APPLE_TEAM_ID
# - APPLE_NOTARY_PROFILE
# - WINDOWS_CERT_BASE64 (or WINDOWS_CERT_PFX_FILE path to convert to base64)
# - WINDOWS_CERT_PASSWORD
# - LINUX_GPG_PRIVATE_KEY (or LINUX_GPG_PRIVATE_KEY_FILE path)

REPO="${1:-}"

if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "[secrets] gh CLI is required"
  exit 1
fi

gh auth status >/dev/null

to_base64() {
  local file="$1"
  if base64 --help >/dev/null 2>&1 && base64 --help 2>&1 | grep -q -- "--wrap"; then
    base64 --wrap=0 "$file"
  else
    base64 < "$file" | tr -d '\n'
  fi
}

APPLE_SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
APPLE_TEAM_ID="${APPLE_TEAM_ID:-}"
APPLE_NOTARY_PROFILE="${APPLE_NOTARY_PROFILE:-}"
WINDOWS_CERT_BASE64="${WINDOWS_CERT_BASE64:-}"
WINDOWS_CERT_PASSWORD="${WINDOWS_CERT_PASSWORD:-}"
LINUX_GPG_PRIVATE_KEY="${LINUX_GPG_PRIVATE_KEY:-}"

if [[ -z "$WINDOWS_CERT_BASE64" && -n "${WINDOWS_CERT_PFX_FILE:-}" ]]; then
  if [[ ! -f "$WINDOWS_CERT_PFX_FILE" ]]; then
    echo "[secrets] WINDOWS_CERT_PFX_FILE not found: $WINDOWS_CERT_PFX_FILE"
    exit 1
  fi
  WINDOWS_CERT_BASE64="$(to_base64 "$WINDOWS_CERT_PFX_FILE")"
fi

if [[ -z "$LINUX_GPG_PRIVATE_KEY" && -n "${LINUX_GPG_PRIVATE_KEY_FILE:-}" ]]; then
  if [[ ! -f "$LINUX_GPG_PRIVATE_KEY_FILE" ]]; then
    echo "[secrets] LINUX_GPG_PRIVATE_KEY_FILE not found: $LINUX_GPG_PRIVATE_KEY_FILE"
    exit 1
  fi
  LINUX_GPG_PRIVATE_KEY="$(cat "$LINUX_GPG_PRIVATE_KEY_FILE")"
fi

set_secret_if_present() {
  local key="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    echo "[secrets] $key: skipped (no value provided)"
    return 0
  fi
  printf '%s' "$value" | gh secret set "$key" --repo "$REPO"
  echo "[secrets] $key: set"
}

echo "[secrets] target repo: $REPO"
set_secret_if_present "APPLE_SIGNING_IDENTITY" "$APPLE_SIGNING_IDENTITY"
set_secret_if_present "APPLE_TEAM_ID" "$APPLE_TEAM_ID"
set_secret_if_present "APPLE_NOTARY_PROFILE" "$APPLE_NOTARY_PROFILE"
set_secret_if_present "WINDOWS_CERT_BASE64" "$WINDOWS_CERT_BASE64"
set_secret_if_present "WINDOWS_CERT_PASSWORD" "$WINDOWS_CERT_PASSWORD"
set_secret_if_present "LINUX_GPG_PRIVATE_KEY" "$LINUX_GPG_PRIVATE_KEY"

echo "[secrets] complete"
