#!/usr/bin/env python3
"""
Dependency Verification Script

Run this script before packaging to verify all dependencies are installed
and can be imported correctly.
"""

import sys
from typing import List, Tuple

def check_import(module_name: str, package_name: str = None) -> Tuple[bool, str]:
    """
    Check if a module can be imported.
    
    Args:
        module_name: Name of the module to import
        package_name: Display name (if different from module_name)
    
    Returns:
        (success: bool, message: str)
    """
    display_name = package_name or module_name
    try:
        __import__(module_name)
        return True, f"✅ {display_name}"
    except ImportError as e:
        return False, f"❌ {display_name}: {str(e)}"

def check_submodule(parent: str, submodule: str, package_name: str = None) -> Tuple[bool, str]:
    """
    Check if a submodule can be imported.
    
    Args:
        parent: Parent module name
        submodule: Submodule name (relative to parent)
        package_name: Display name
    
    Returns:
        (success: bool, message: str)
    """
    display_name = package_name or f"{parent}.{submodule}"
    try:
        parent_module = __import__(parent, fromlist=[submodule])
        getattr(parent_module, submodule)
        return True, f"✅ {display_name}"
    except (ImportError, AttributeError) as e:
        return False, f"❌ {display_name}: {str(e)}"

def main():
    """Verify all dependencies"""
    print("=" * 70)
    print("DEPENDENCY VERIFICATION")
    print("=" * 70)
    print()
    
    results: List[Tuple[bool, str]] = []
    
    # Core dependencies
    print("Core Dependencies:")
    print("-" * 70)
    
    results.append(check_import('openpyxl', 'openpyxl'))
    results.append(check_submodule('openpyxl', 'styles', 'openpyxl.styles'))
    results.append(check_submodule('openpyxl', 'utils', 'openpyxl.utils'))
    results.append(check_submodule('openpyxl', 'cell', 'openpyxl.cell.cell'))
    
    results.append(check_import('pandas', 'pandas'))
    results.append(check_submodule('pandas._libs', 'tslibs', 'pandas._libs.tslibs'))
    
    results.append(check_import('dateutil', 'python-dateutil'))
    results.append(check_submodule('dateutil', 'parser', 'dateutil.parser'))
    
    results.append(check_import('yaml', 'pyyaml'))
    
    print()
    print("Optional Dependencies:")
    print("-" * 70)
    
    results.append(check_import('reportlab', 'reportlab (optional)'))
    if results[-1][0]:
        results.append(check_submodule('reportlab.lib', 'pagesizes', 'reportlab.lib.pagesizes'))
        results.append(check_submodule('reportlab.pdfgen', 'canvas', 'reportlab.pdfgen.canvas'))
    
    print()
    print("Standard Library (should always be available):")
    print("-" * 70)
    
    results.append(check_import('tkinter', 'tkinter'))
    results.append(check_submodule('tkinter', 'ttk', 'tkinter.ttk'))
    results.append(check_submodule('tkinter', 'messagebox', 'tkinter.messagebox'))
    results.append(check_submodule('tkinter', 'filedialog', 'tkinter.filedialog'))
    
    # Print all results
    print()
    print("=" * 70)
    print("RESULTS:")
    print("=" * 70)
    
    all_passed = True
    for success, message in results:
        print(message)
        if not success:
            all_passed = False
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("✅ ALL DEPENDENCIES VERIFIED!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME DEPENDENCIES MISSING!")
        print("=" * 70)
        print()
        print("Install missing dependencies with:")
        print("  pip install -r requirements.txt")
        print("  pip install reportlab  # Optional")
        return 1

if __name__ == '__main__':
    sys.exit(main())





