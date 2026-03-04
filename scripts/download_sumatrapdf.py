#!/usr/bin/env python3
"""Download SumatraPDF portable for bundling with Pallet Manager."""

import sys
import urllib.request
import urllib.error
import zipfile
import ssl
import json
from pathlib import Path

LATEST_RELEASE_API = "https://api.github.com/repos/sumatrapdfreader/sumatrapdf/releases/latest"
TARGET_DIR = Path("external_tools/SumatraPDF")
ZIP_PATH = TARGET_DIR / "SumatraPDF.zip"
EXE_PATH = TARGET_DIR / "SumatraPDF.exe"

def _install_unsafe_ssl_opener():
    """Support environments that need unverified SSL (corporate proxies)."""
    ssl_context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    urllib.request.install_opener(opener)


def _resolve_download_url():
    """Get latest 64-bit portable SumatraPDF asset URL from GitHub release API."""
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "User-Agent": "PalletManager-BuildScript",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release_data = json.loads(response.read().decode("utf-8"))

    tag = release_data.get("tag_name", "latest")
    for asset in release_data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith("-64.zip") and "sumatrapdf" in name.lower():
            return asset.get("browser_download_url"), tag, name

    raise RuntimeError("No 64-bit portable ZIP asset found in latest release.")


def _download_with_progress(url, destination):
    def show_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, (downloaded / total_size) * 100)
            sys.stdout.write(f"\r  Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, destination, show_progress)
    print("\n")


def _print_manual_download_help():
    print("\nPlease download manually:")
    print("1. Go to: https://www.sumatrapdfreader.org/download-free-pdf-viewer")
    print("2. Download the 64-bit portable version")
    print(f"3. Extract SumatraPDF.exe to: {TARGET_DIR}")


def download_sumatra():
    """Download and extract SumatraPDF."""
    try:
        TARGET_DIR.mkdir(parents=True, exist_ok=True)

        if EXE_PATH.exists():
            print(f"✓ SumatraPDF already exists: {EXE_PATH}")
            return True

        _install_unsafe_ssl_opener()
        download_url, release_tag, asset_name = _resolve_download_url()
        print(f"Downloading SumatraPDF ({release_tag})...")
        print(f"Asset: {asset_name}")
        print(f"URL: {download_url}")

        _download_with_progress(download_url, ZIP_PATH)

        print("Extracting SumatraPDF...")
        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(TARGET_DIR)

        ZIP_PATH.unlink(missing_ok=True)

        if EXE_PATH.exists():
            print("✓ SumatraPDF downloaded successfully!")
            print(f"  Location: {EXE_PATH}")
            return True

        print("✗ SumatraPDF.exe not found after extraction")
        print("Files extracted:")
        for file_path in TARGET_DIR.glob("*"):
            print(f"  - {file_path.name}")
        return False

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as err:
        print(f"✗ Network error downloading SumatraPDF: {err}")
        _print_manual_download_help()
        return False
    except Exception as err:
        print(f"✗ Error downloading SumatraPDF: {err}")
        _print_manual_download_help()
        return False

if __name__ == "__main__":
    success = download_sumatra()
    sys.exit(0 if success else 1)
