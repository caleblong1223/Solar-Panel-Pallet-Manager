#!/usr/bin/env python3
"""
Resource Manager - Ensures proper cleanup and prevents resource leaks

Provides context managers and utilities for safe resource handling.
"""

import gc
import sys
from typing import Optional, Callable, Any
from contextlib import contextmanager
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceLimits:
    """Monitor and enforce resource limits to prevent crashes"""
    
    MAX_MEMORY_MB = 500  # Maximum memory usage before warning
    MAX_CACHE_SIZE = 1000  # Maximum cache entries
    
    @staticmethod
    def check_memory_usage() -> Optional[float]:
        """Check current memory usage in MB. Returns None if psutil unavailable."""
        if not PSUTIL_AVAILABLE:
            return None
        
        try:
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb
        except Exception:
            return None
    
    @staticmethod
    def should_gc() -> bool:
        """Determine if garbage collection should be run"""
        memory_mb = ResourceLimits.check_memory_usage()
        if memory_mb is None:
            return False
        return memory_mb > ResourceLimits.MAX_MEMORY_MB * 0.8  # 80% threshold
    
    @staticmethod
    def force_gc_if_needed():
        """Force garbage collection if memory usage is high"""
        if ResourceLimits.should_gc():
            gc.collect()


@contextmanager
def safe_workbook(workbook_path: Path, read_only: bool = True, **kwargs):
    """
    Context manager for safely opening and closing workbooks.
    Ensures workbook is always closed even if exceptions occur.
    
    Usage:
        with safe_workbook(path) as wb:
            # Use workbook
            pass
        # Workbook automatically closed
    """
    from openpyxl import load_workbook
    
    wb = None
    try:
        wb = load_workbook(workbook_path, read_only=read_only, **kwargs)
        yield wb
    except Exception as e:
        raise e
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass  # Ignore errors during cleanup


@contextmanager
def safe_file_operation(operation: Callable, cleanup: Optional[Callable] = None):
    """
    Context manager for safe file operations with cleanup.
    
    Usage:
        with safe_file_operation(lambda: open('file.txt'), lambda f: f.close()) as f:
            # Use file
            pass
    """
    resource = None
    try:
        resource = operation()
        yield resource
    except Exception as e:
        raise e
    finally:
        if cleanup and resource is not None:
            try:
                cleanup(resource)
            except Exception:
                pass


def safe_operation(operation: Callable, error_handler: Optional[Callable] = None, default: Any = None):
    """
    Safely execute an operation with error handling.
    Returns default value if operation fails.
    
    Args:
        operation: Function to execute
        error_handler: Optional function to handle errors (receives exception)
        default: Value to return if operation fails
        
    Returns:
        Result of operation or default if failed
    """
    try:
        return operation()
    except Exception as e:
        if error_handler:
            try:
                error_handler(e)
            except Exception:
                pass
        return default


def validate_input(serial: Optional[str], max_length: int = 100) -> Optional[str]:
    """
    Validate and sanitize input serial number.
    
    Args:
        serial: Input serial number
        max_length: Maximum allowed length
        
    Returns:
        Sanitized serial or None if invalid
    """
    if not serial:
        return None
    
    # Convert to string and strip whitespace
    serial_str = str(serial).strip()
    
    # Check length
    if len(serial_str) > max_length:
        return None
    
    # Check for null bytes or other dangerous characters
    if '\x00' in serial_str:
        return None
    
    return serial_str if serial_str else None


def bounds_check(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None, default: Optional[float] = None) -> Optional[float]:
    """
    Check if numeric value is within bounds.
    
    Args:
        value: Value to check
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        default: Default value if out of bounds
        
    Returns:
        Value if in bounds, default otherwise
    """
    try:
        num_val = float(value)
        if min_val is not None and num_val < min_val:
            return default
        if max_val is not None and num_val > max_val:
            return default
        return num_val
    except (ValueError, TypeError):
        return default


def limit_cache_size(cache: dict, max_size: int = 1000):
    """
    Limit cache size by removing oldest entries.
    
    Args:
        cache: Cache dictionary to limit
        max_size: Maximum number of entries
    """
    if len(cache) > max_size:
        # Remove oldest entries (simple FIFO - remove first 20%)
        to_remove = len(cache) - max_size
        keys_to_remove = list(cache.keys())[:to_remove]
        for key in keys_to_remove:
            del cache[key]


def safe_list_access(lst: list, index: int, default: Any = None) -> Any:
    """
    Safely access list element with bounds checking.
    
    Args:
        lst: List to access
        index: Index to access
        default: Value to return if index out of range
        
    Returns:
        Element at index or default
    """
    if not isinstance(lst, list):
        return default
    if 0 <= index < len(lst):
        return lst[index]
    return default


def safe_dict_access(dct: dict, key: Any, default: Any = None) -> Any:
    """
    Safely access dictionary element.
    
    Args:
        dct: Dictionary to access
        key: Key to access
        default: Value to return if key not found
        
    Returns:
        Value at key or default
    """
    if not isinstance(dct, dict):
        return default
    return dct.get(key, default)









