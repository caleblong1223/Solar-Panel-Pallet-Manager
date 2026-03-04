#!/usr/bin/env python3
"""
Update version numbers across all configuration files
Usage: python scripts/update_version.py <new_version>
Example: python scripts/update_version.py 1.0.1
"""

import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.version import VERSION

def update_version_in_file(file_path: Path, new_version: str, pattern: str, replacement: str):
    """Update version in a file using regex pattern"""
    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    new_content = re.sub(pattern, replacement, content)
    
    if content != new_content:
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✅ Updated {file_path.name}")
        return True
    else:
        print(f"⚠️  No changes needed in {file_path.name}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_version.py <new_version>")
        print(f"Current version: {VERSION}")
        print()
        print("Example: python scripts/update_version.py 1.0.1")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    # Validate version format (basic check)
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(f"Error: Invalid version format: {new_version}")
        print("Expected format: X.Y.Z (e.g., 1.0.1)")
        sys.exit(1)
    
    print("=" * 70)
    print("Updating Version Numbers")
    print("=" * 70)
    print(f"Current version: {VERSION}")
    print(f"New version: {new_version}")
    print()
    
    # Update app/version.py
    version_file = project_root / "app" / "version.py"
    version_parts = new_version.split('.')
    
    version_content = version_file.read_text(encoding='utf-8')
    version_content = re.sub(r"VERSION = \"[^\"]+\"", f'VERSION = "{new_version}"', version_content)
    version_content = re.sub(r"VERSION_MAJOR = \d+", f"VERSION_MAJOR = {version_parts[0]}", version_content)
    version_content = re.sub(r"VERSION_MINOR = \d+", f"VERSION_MINOR = {version_parts[1]}", version_content)
    version_content = re.sub(r"VERSION_PATCH = \d+", f"VERSION_PATCH = {version_parts[2]}", version_content)
    version_file.write_text(version_content, encoding='utf-8')
    print(f"✅ Updated app/version.py")
    
    # Update setup.py (macOS)
    setup_file = project_root / "setup.py"
    update_version_in_file(
        setup_file,
        new_version,
        r"'CFBundleVersion': '[^']+'",
        f"'CFBundleVersion': '{new_version}'"
    )
    update_version_in_file(
        setup_file,
        new_version,
        r"'CFBundleShortVersionString': '[^']+'",
        f"'CFBundleShortVersionString': '{new_version}'"
    )
    
    print()
    print("=" * 70)
    print("✅ Version Update Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Rebuild installers:")
    print("   macOS: ./scripts/build_macos.sh")
    print("   Windows: scripts\\build_windows.bat")
    print()
    print("2. Create update_info.json (optional):")
    print("   python scripts/create_update_info.py")
    print()

if __name__ == "__main__":
    main()

