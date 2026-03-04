#!/usr/bin/env python3
"""
Helper script to create update_info.json file for distribution
Usage: python scripts/create_update_info.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add app directory to path
sys.path.insert(0, str(PROJECT_ROOT / "app"))

from app.update_checker import create_update_info_file
from app.version import get_version

def main():
    print("=" * 70)
    print("Create Update Info File")
    print("=" * 70)
    print()
    
    current_version = get_version()
    print(f"Current version: {current_version}")
    print()
    
    # Get new version
    new_version = input(f"Enter new version (current: {current_version}): ").strip()
    if not new_version:
        new_version = current_version
    
    # Get download URLs
    print()
    print("Enter download URLs (or press Enter to skip):")
    url_macos = input("macOS installer URL: ").strip()
    url_windows = input("Windows installer URL: ").strip()
    
    # Get release notes
    print()
    print("Enter release notes (press Enter twice to finish):")
    release_notes_lines = []
    while True:
        line = input()
        if not line and release_notes_lines and not release_notes_lines[-1]:
            break
        release_notes_lines.append(line)
    
    release_notes = "\n".join(release_notes_lines).strip()
    
    # Critical update?
    print()
    critical_input = input("Is this a critical update? (y/N): ").strip().lower()
    critical = critical_input in ('y', 'yes')
    
    # Create update info file in project root
    output_path = PROJECT_ROOT / "update_info.json"
    create_update_info_file(
        version=new_version,
        download_url_macos=url_macos or "",
        download_url_windows=url_windows or "",
        release_notes=release_notes,
        critical=critical,
        output_path=output_path
    )
    
    print()
    print("=" * 70)
    print("✅ Update info file created!")
    print("=" * 70)
    print()
    print(f"File: {output_path.absolute()}")
    print()
    print("Next steps:")
    print("1. Upload installers to your server/storage")
    print("2. Update URLs in update_info.json if needed")
    print("3. Upload update_info.json to your server")
    print("4. Notify users of the update")
    print()

if __name__ == "__main__":
    main()

