"""
Setup script for py2app (macOS packaging)
Build with: python setup.py py2app
"""

import sys
from pathlib import Path

# Ensure project root is on path so app.version is importable at build time
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from setuptools import setup
from app.version import VERSION

APP = ['app/pallet_builder_gui.py']
DATA_FILES = [
    # Include reference workbooks for first-time setup (26, 30, 35)
    ('reference_workbook', [
        'data/EXCEL/26.xlsx',
        'data/EXCEL/30.xlsx',
        'data/EXCEL/35.xlsx',
    ]),
    # Include app icon assets (same as 1.1) for window/dock icon at runtime
    ('assets', ['assets/PalletManager.ico', 'assets/PalletManager.icns', 'assets/Pallet icon.png']),
]

# Check if reportlab is available (optional dependency)
try:
    import reportlab
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Build packages list
packages_list = [
    'openpyxl',
    'pandas',
    'dateutil',
    'yaml',
    'tkinter',
]

# Build includes list
includes_list = [
    # openpyxl
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.cell.cell',
    # pandas - include all necessary submodules
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.tzconversion',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.parsing',
    'pandas._libs.testing',
    'pandas._testing',
    'pandas._testing.asserters',
    'pandas.io.excel',
    'pandas.io.excel._openpyxl',
    # python-dateutil
    'dateutil',
    'dateutil.parser',
    'dateutil.relativedelta',
    # pyyaml
    'yaml',
    # Standard library modules that pandas needs
    'cmath',
    'math',
    'decimal',
    'fractions',
]

# Add reportlab only if available
if HAS_REPORTLAB:
    packages_list.append('reportlab')
    includes_list.extend([
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.pdfgen.canvas',
    ])

OPTIONS = {
    'argv_emulation': False,  # Disable for faster startup
    'packages': packages_list,
    'includes': includes_list,
    'excludes': [
        # Exclude unnecessary modules to reduce size and improve performance
        'matplotlib',
        'scipy',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'distutils',
        'email',
        'http',
        'urllib3',
        'xmlrpc',
        'pydoc',
        'doctest',
        'unittest',
        'test',
        'numpy.tests',
        'pandas.tests',
        'pandas.plotting',  # Not used in this app
        'pandas.io.clipboard',  # Not used
        'openpyxl.tests',
        'sqlite3',  # Not used
        # 'multiprocessing',  # Required by py2app boot process - DO NOT EXCLUDE
        'concurrent.futures',  # Not used
        # GUI frameworks not used (we use tkinter)
        # Note: PyQt6 may still be included by py2app recipes, removed in post-build
        'PyQt5',
        'PySide6',
        'PySide2',
        'wx',
        'kivy',
        # PostgreSQL / backend (not needed for desktop GUI; avoids Mach-O relocate error)
        'psycopg',
        'psycopg2',
        'psycopg_binary',
    ],
    'site_packages': True,  # Include site-packages but exclude large unused packages
    'semi_standalone': False,  # Fully standalone bundle (better performance)
    'use_pythonpath': True,  # Use Python path
    'strip': True,  # Strip debug symbols for smaller size and faster loading
    'iconfile': 'assets/PalletManager.icns',  # Application icon (same as 1.1)
    'plist': {
        'CFBundleName': 'Pallet Manager',
        'CFBundleDisplayName': f'Pallet Manager {VERSION}',
        'CFBundleGetInfoString': f'Pallet Manager {VERSION} - Pallet Builder for Solar Panel Management',
        'CFBundleIdentifier': 'com.crossroads.palletmanager',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13',  # macOS High Sierra or later
        'LSRequiresNativeExecution': True,  # Prefer native execution (ARM64)
    },
    'optimize': 2,  # Maximum bytecode optimization
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

