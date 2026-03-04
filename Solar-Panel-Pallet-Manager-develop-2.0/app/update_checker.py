"""
Update checker for Pallet Manager
Checks for available updates from a remote source or local file
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any
from app.version import get_version, compare_versions

# Update check URL (can be configured)
# For now, using a simple approach - can be extended to use a server
UPDATE_CHECK_URL = None  # Set to your update server URL if available
UPDATE_INFO_FILE = None  # Local file path for update info (alternative)


def check_for_updates(
    current_version: Optional[str] = None,
    update_url: Optional[str] = None,
    local_file: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Check for available updates.
    
    Args:
        current_version: Current version (defaults to app version)
        update_url: URL to check for updates (optional)
        local_file: Local file path with update info (optional)
    
    Returns:
        Dict with update info if update available, None otherwise
        Format: {
            'version': '1.0.1',
            'available': True,
            'download_url': 'https://...',
            'release_notes': '...',
            'critical': False
        }
    """
    if current_version is None:
        current_version = get_version()
    
    # Try remote URL first
    if update_url:
        try:
            update_info = check_remote_updates(update_url, current_version)
            if update_info:
                return update_info
        except Exception as e:
            print(f"Could not check remote updates: {e}")
    
    # Try local file
    if local_file and local_file.exists():
        try:
            update_info = check_local_updates(local_file, current_version)
            if update_info:
                return update_info
        except Exception as e:
            print(f"Could not check local updates: {e}")
    
    return None


def check_remote_updates(url: str, current_version: str) -> Optional[Dict[str, Any]]:
    """Check for updates from a remote URL"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return parse_update_info(data, current_version)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"Error checking remote updates: {e}")
        return None


def check_local_updates(file_path: Path, current_version: str) -> Optional[Dict[str, Any]]:
    """Check for updates from a local JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return parse_update_info(data, current_version)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading local update info: {e}")
        return None


def parse_update_info(data: Dict[str, Any], current_version: str) -> Optional[Dict[str, Any]]:
    """Parse update information and check if update is available"""
    if not isinstance(data, dict):
        return None
    
    latest_version = data.get('version')
    if not latest_version:
        return None
    
    # Compare versions
    if compare_versions(current_version, latest_version) < 0:
        return {
            'version': latest_version,
            'available': True,
            'download_url': data.get('download_url'),
            'download_url_macos': data.get('download_url_macos'),
            'download_url_windows': data.get('download_url_windows'),
            'release_notes': data.get('release_notes', ''),
            'critical': data.get('critical', False),
            'release_date': data.get('release_date'),
        }
    
    return None


def create_update_info_file(
    version: str,
    download_url_macos: str,
    download_url_windows: str,
    release_notes: str = "",
    critical: bool = False,
    output_path: Path = Path("update_info.json")
):
    """
    Create an update info JSON file for distribution.
    
    This can be hosted on a server or distributed with the app.
    """
    update_info = {
        'version': version,
        'download_url_macos': download_url_macos,
        'download_url_windows': download_url_windows,
        'release_notes': release_notes,
        'critical': critical,
        'release_date': None,  # Can be set automatically
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(update_info, f, indent=2)
    
    print(f"Update info file created: {output_path}")
    return output_path



