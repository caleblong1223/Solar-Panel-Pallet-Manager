# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the project root directory
# Use current working directory since build script cd's to project root
project_root = Path.cwd()

# Define data files to include
datas = [
    # Include the entire data directory (contains templates, configurations, etc.)
    (str(project_root / 'data'), 'data'),
    # Include assets
    (str(project_root / 'assets'), 'assets'),
    # Include docs if needed
    (str(project_root / 'docs'), 'docs'),
]

# Define binaries (external tools like SumatraPDF)
binaries = []
sumatra_path = project_root / 'tools' / 'SumatraPDF' / 'SumatraPDF.exe'
if sumatra_path.exists():
    binaries.append((str(sumatra_path), 'tools/SumatraPDF/'))

# Define hidden imports (modules that PyInstaller might miss)
hiddenimports = [
    # Standard library modules that PyInstaller sometimes misses
    'secrets',  # Required by numpy.random
    'hashlib',  # Required by various modules
    'ssl',      # Required for network operations
    'urllib.request',  # Required for downloads
    'json',     # Required for JSON operations
    'csv',      # Required for CSV operations
    'xml.etree.ElementTree',  # Required by openpyxl
    'email',    # Required by reportlab for PDF generation
    'email.utils',  # Required by reportlab
    'email.header',  # Required by reportlab
    'email.mime',   # Required by reportlab
    'email.message',  # Required by reportlab
    'email.parser',  # Required by reportlab
    'email.generator',  # Required by reportlab
    'email.encoders',  # Required by reportlab
    'email.base64mime',  # Required by reportlab
    'email.quoprimime',  # Required by reportlab
    'smtplib',      # Required for email operations
    'imaplib',      # Required for email operations
    'calendar',     # Required by reportlab
    'gzip',         # Required for compressed operations
    'base64',       # Required by reportlab for encoding
    'uu',           # Required by reportlab for encoding
    'binascii',     # Required by reportlab for binary operations
    # HTTP and network modules
    'http',
    'http.client',
    'http.server',
    'http.cookies',
    'http.cookiejar',
    'urllib',
    'urllib.parse',
    'urllib.error',
    'socket',
    'select',
    # Core system modules
    'threading',
    'multiprocessing',
    'subprocess',
    'tempfile',
    'shutil',
    'glob',
    'fnmatch',
    'linecache',
    'tokenize',
    'keyword',
    'ast',
    'inspect',
    'dis',
    'opcode',
    'copyreg',
    'copy',
    'pprint',
    'reprlib',
    'enum',
    'numbers',
    'math',
    'cmath',
    'decimal',
    'fractions',
    'random',
    'statistics',
    # Collections and utilities
    'collections',
    'collections.abc',
    'functools',
    'operator',
    'itertools',
    'contextlib',
    'warnings',
    'weakref',
    'gc',
    # System and platform modules
    'sys',
    'builtins',
    'types',
    'platform',
    'errno',
    'ctypes',
    # Platform-specific modules
    'msvcrt',  # Windows-specific
    'nt',      # Windows-specific
    'posix',   # Unix-specific
    # pandas and related
    'pandas',
    'pandas._libs.tslibs',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.tzconversion',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.parsing',
    'pandas.io.excel',
    'pandas.io.excel._openpyxl',
    'pandas.io.excel._base',
    # openpyxl
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.cell.cell',
    'openpyxl.worksheet',
    'openpyxl.workbook',
    # dateutil
    'dateutil',
    'dateutil.parser',
    'dateutil.relativedelta',
    # yaml
    'yaml',
    # tkinter
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    # app modules
    'app.pallet_builder_gui',
    'app.serial_database',
    'app.pallet_manager',
    'app.workbook_utils',
    'app.pallet_exporter',
    'app.pallet_history_window',
    'app.customer_manager',
    'app.version',
    'app.path_utils',
    'app.debug_logger',
    'app.archive_manager',
    'app.tool_runner',
    'app.import_sunsim',
    'app.resource_manager',
    'app.update_checker',
    # Optional modules (handle gracefully if not available)
    'reportlab',
    'reportlab.lib.pagesizes',
    'reportlab.pdfgen.canvas',
    'PIL',
    'PIL.Image',
    'jinja2',
]

# Define what to exclude to reduce size
excludes = [
    # Large unused packages
    'matplotlib',
    'scipy',
    'numpy.testing',
    'pandas.tests',
    'openpyxl.tests',
    'pytest',
    'IPython',
    'jupyter',
    'notebook',
    'setuptools',
    'distutils',
    # Don't exclude email anymore since reportlab needs it
    # 'email',
    'http',
    'urllib3',
    'xmlrpc',
    'pydoc',
    'doctest',
    'unittest',
    'test',
    'sqlite3',
    'multiprocessing',
    'concurrent.futures',
    'PyQt5',
    'PyQt6',
    'PySide6',
    'PySide2',
    'wx',
    'kivy',
]

a = Analysis(
    ['launch_app.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],  # Don't use custom hooks - using direct hiddenimports instead
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Pallet Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/PalletManager.ico',
)