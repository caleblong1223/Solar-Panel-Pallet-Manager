#!/usr/bin/env python3
"""
Launcher script for Pallet Manager
Run this to start the application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

print("=" * 70)
print("Pallet Manager - Starting Application")
print("=" * 70)
print()

try:
    from app.pallet_builder_gui import main
    print("✅ Application module loaded")
    print("✅ Starting GUI window...")
    print()
    print("The application window should appear now.")
    print("If you don't see it:")
    print("  • Check your Dock for a Python window")
    print("  • Check behind other windows (Cmd+Tab)")
    print("  • Look for 'Pallet Manager' in the menu bar")
    print()
    main()
except KeyboardInterrupt:
    print("\nApplication closed by user")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit...")



