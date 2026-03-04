"""
Version information for Pallet Manager
Update this file when releasing new versions
"""

# Application version
VERSION = "2.0.0"
VERSION_MAJOR = 2
VERSION_MINOR = 0
VERSION_PATCH = 0

# Build information
BUILD_DATE = "2026-03-04"  # Update when building new version
BUILD_NUMBER = None  # Optional: Can be set during CI/CD

# Version string for display
VERSION_STRING = f"v{VERSION}"

def get_version():
    """Get the current version string"""
    return VERSION

def get_version_info():
    """Get detailed version information"""
    return {
        'version': VERSION,
        'major': VERSION_MAJOR,
        'minor': VERSION_MINOR,
        'patch': VERSION_PATCH,
        'build_date': BUILD_DATE,
        'build_number': BUILD_NUMBER,
        'version_string': VERSION_STRING,
    }

def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    def version_tuple(v):
        return tuple(map(int, v.split('.')))
    
    v1 = version_tuple(version1)
    v2 = version_tuple(version2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0



