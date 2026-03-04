#!/usr/bin/env python3
"""
Path Utilities - Handles path resolution for both development and packaged environments

This module provides utilities to correctly resolve paths whether the application
is running as a script or as a packaged executable.
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional


def is_packaged() -> bool:
    """
    Check if the application is running as a packaged executable.
    
    Returns:
        True if running as packaged executable (PyInstaller, py2app, etc.)
        False if running as a Python script
    """
    # PyInstaller sets sys.frozen to True
    if getattr(sys, 'frozen', False):
        return True
    
    # Check if running from a .app bundle (macOS)
    if sys.platform == 'darwin':
        if '.app/Contents' in sys.executable or '.app/Contents' in __file__:
            return True
    
    # Check if running from .exe (Windows)
    if sys.platform == 'win32':
        if sys.executable.endswith('.exe') and 'python' not in sys.executable.lower():
            return True
    
    return False


def get_base_dir() -> Path:
    """
    Get the base directory of the application.
    
    In development: Returns the project root directory
    In packaged: Returns a writable directory for data files
    
    For macOS apps in /Applications/, uses ~/Documents/Pallet Manager/
    For other locations, uses directory containing the app
    
    Returns:
        Path to the base directory
    """
    # Check for PyInstaller first (sys._MEIPASS is set during extraction)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller (Windows/Linux): executable is in dist/, base is executable's parent
        # For one-file builds, sys._MEIPASS is temp extraction dir (don't use)
        # For one-dir builds, sys._MEIPASS is the _internal dir (don't use)
        # We want the directory containing the executable
        return Path(sys.executable).parent
    
    # Check for py2app (macOS .app bundle)
    if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
        # py2app: sys.executable points to executable inside .app/Contents/MacOS/
        exe_path = Path(sys.executable)
        if '.app/Contents' in str(exe_path):
            # Navigate up from .app/Contents/MacOS/executable to .app/../
            # Structure: /path/to/Pallet Manager.app/Contents/MacOS/pallet_builder_gui
            app_dir = exe_path
            while app_dir.name != 'Contents' and app_dir.parent != app_dir:
                app_dir = app_dir.parent
            if app_dir.name == 'Contents':
                # app_dir is Contents/, parent is .app/, parent.parent is base dir
                app_bundle_dir = app_dir.parent.parent  # .app/../
                
                # If app is in /Applications/, use user's Documents folder instead
                # (Applications folder is not writable)
                if str(app_bundle_dir) == '/Applications' or app_bundle_dir.parent.name == 'Applications':
                    # Use ~/Documents/Pallet Manager/ for data files
                    documents_dir = Path.home() / 'Documents' / 'Pallet Manager'
                    documents_dir.mkdir(parents=True, exist_ok=True)
                    return documents_dir
                
                # If app is in a writable location, use that directory
                # Check if we can write to the directory
                try:
                    test_file = app_bundle_dir / '.pallet_manager_test'
                    test_file.touch()
                    test_file.unlink()
                    # Directory is writable, use it
                    return app_bundle_dir
                except (PermissionError, OSError):
                    # Directory is not writable, use Documents instead
                    documents_dir = Path.home() / 'Documents' / 'Pallet Manager'
                    documents_dir.mkdir(parents=True, exist_ok=True)
                    return documents_dir
        
        # Fallback: if not in .app structure, use executable's parent
        return exe_path.parent
    
    # Check for other packaged formats
    if is_packaged():
        # Windows .exe or other formats
        return Path(sys.executable).parent
    
    # Development: return project root (parent of app directory)
    # This file is in app/, so parent.parent is project root
    return Path(__file__).parent.parent


def get_app_dir() -> Path:
    """
    Get the app directory (where Python modules are located).
    
    In development: Returns app/ directory
    In packaged: Returns the same as base_dir (executable directory)
    
    Returns:
        Path to the app directory
    """
    if is_packaged():
        # When packaged, app code is bundled with executable
        # Use base_dir as app_dir
        return get_base_dir()
    else:
        # Development: app/ directory
        return Path(__file__).parent


def resolve_project_path(relative_path: str) -> Path:
    """
    Resolve a path relative to the project root.
    
    Args:
        relative_path: Path relative to project root (e.g., "PALLETS/history.json")
    
    Returns:
        Absolute Path to the resolved location
    """
    base_dir = get_base_dir()
    return (base_dir / relative_path).resolve()


def get_resource_path(relative_path: str) -> Path:
    """
    Get path to a resource file (for bundled resources in packaged apps).
    
    Args:
        relative_path: Path relative to project root
    
    Returns:
        Path to the resource file
    """
    if is_packaged():
        # In packaged app, resources are in the same directory as executable
        # or in a _internal/ subdirectory (PyInstaller)
        base = get_base_dir()
        
        # Try direct path first
        direct_path = base / relative_path
        if direct_path.exists():
            return direct_path
        
        # Try _internal/ subdirectory (PyInstaller)
        internal_path = base / "_internal" / relative_path
        if internal_path.exists():
            return internal_path
        
        # Return direct path even if it doesn't exist (will be created)
        return direct_path
    else:
        # Development: use project root
        return resolve_project_path(relative_path)


# Common project paths (cached for performance)
_base_dir_cache: Optional[Path] = None
_app_dir_cache: Optional[Path] = None


def get_base_dir_cached() -> Path:
    """Get base directory with caching for performance"""
    global _base_dir_cache
    if _base_dir_cache is None:
        _base_dir_cache = get_base_dir()
    return _base_dir_cache


def get_app_dir_cached() -> Path:
    """Get app directory with caching for performance"""
    global _app_dir_cache
    if _app_dir_cache is None:
        _app_dir_cache = get_app_dir()
    return _app_dir_cache


class FileMonitor:
    """
    Lightweight file change detection using modification time.

    Provides real-time file change detection with minimal performance impact.
    Uses file modification time (st_mtime) for change detection.
    """

    def __init__(self, file_path: Path, debug: bool = False):
        """
        Initialize file monitor.

        Args:
            file_path: Path to the file to monitor
            debug: Enable debug logging
        """
        self.file_path = file_path
        self.debug = debug
        self.last_mtime: Optional[float] = None
        self._update_mtime()
        self.change_count = 0

        if self.debug:
            print(f"DEBUG: FileMonitor initialized for {file_path}")

    def has_changed(self) -> bool:
        """
        Check if file has been modified since last check.

        Returns:
            True if file has changed, False otherwise
        """
        if not self.file_path.exists():
            if self.debug:
                print(f"DEBUG: File {self.file_path} does not exist")
            return False

        try:
            current_mtime = self.file_path.stat().st_mtime

            if self.last_mtime is None:
                # First check - initialize and return False (no change yet)
                self.last_mtime = current_mtime
                if self.debug:
                    print(f"DEBUG: Initial mtime for {self.file_path}: {current_mtime}")
                return False

            if current_mtime != self.last_mtime:
                self.change_count += 1
                if self.debug:
                    print(f"DEBUG: File {self.file_path} changed!")
                    print(f"  Old mtime: {self.last_mtime}")
                    print(f"  New mtime: {current_mtime}")
                    print(f"  Change count: {self.change_count}")
                self.last_mtime = current_mtime
                return True

            return False

        except (OSError, FileNotFoundError) as e:
            if self.debug:
                print(f"DEBUG: Error checking file {self.file_path}: {e}")
            return False

    def _update_mtime(self):
        """Update stored modification time"""
        if self.file_path.exists():
            try:
                self.last_mtime = self.file_path.stat().st_mtime
            except OSError:
                self.last_mtime = None

    def reset(self):
        """Reset the monitor (useful for testing)"""
        self.last_mtime = None
        self.change_count = 0
        self._update_mtime()

    def get_info(self) -> dict:
        """Get monitoring information for debugging"""
        return {
            'file_path': str(self.file_path),
            'last_mtime': self.last_mtime,
            'change_count': self.change_count,
            'exists': self.file_path.exists()
        }
