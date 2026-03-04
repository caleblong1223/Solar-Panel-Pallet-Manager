#!/usr/bin/env python3
"""
Pallet Builder GUI - Main window for live pallet building

Provides a Tkinter-based GUI for operators to scan barcodes and build pallets.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
import subprocess
import platform
import sys
import os
import atexit
import tempfile
import time

# Lazy imports for heavy libraries (optimized for packaging)
# openpyxl and pandas will be imported only when needed

from app.path_utils import get_base_dir, resolve_project_path, get_base_dir_cached, is_packaged, get_resource_path
from app.pallet_manager import PalletManager
from app.workbook_utils import find_pallet_workbook, validate_serial
from app.pallet_exporter import PalletExporter
from app.pallet_history_window import PalletHistoryWindow
from app.serial_database import SerialDatabase
from app.version import get_version, get_version_info
from app.customer_manager import CustomerManager

# Import for validation functions
try:
    from app import import_sunsim
except ImportError:
    import_sunsim = None


def is_dark_mode():
    """Detect system dark mode on macOS or Windows (fast check with 0.1s timeout)"""
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        try:
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True,
                timeout=0.1  # Very fast timeout - defaults command is instant
            )
            return result.returncode == 0 and 'Dark' in result.stdout
        except Exception:
            pass
    
    elif system == 'Windows':
        try:
            import winreg
            # Check Windows registry for dark mode setting
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return value == 0  # 0 = Dark mode, 1 = Light mode
        except (OSError, FileNotFoundError, ImportError):
            pass  # Fallback to light mode if registry read fails
    
    return False  # Default to light mode for other OS or if detection fails


class PalletBuilderGUI:
    """Main GUI window for pallet building"""
    
    def __init__(self, root: Optional[tk.Tk] = None):
        """
        Initialize the GUI application.
        
        Args:
            root: Optional Tk root window (creates new if None)
        """
        self.root = root if root else tk.Tk()
        version = get_version()
        self.root.title(f"Pallet Manager - {version}")
        
        # Set window icon (for taskbar/titlebar)
        try:
            from app.path_utils import get_base_dir
            import sys
            
            # Try to find icon file
            if getattr(sys, 'frozen', False):
                # Running as exe - icon is bundled
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller onefile
                    icon_path = Path(sys._MEIPASS) / 'icons' / 'PalletManager.ico'
                else:
                    # PyInstaller onedir
                    icon_path = Path(sys.executable).parent / 'icons' / 'PalletManager.ico'
            else:
                # Running from source
                icon_path = get_base_dir() / 'icons' / 'PalletManager.ico'
            
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                # Try PNG fallback
                png_path = icon_path.with_suffix('.png')
                if png_path.exists():
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
        except Exception as e:
            print(f"Could not set window icon: {e}")
        
        # macOS-specific settings
        if platform.system() == 'Darwin':
            try:
                # Enable fullscreen button on macOS
                self.root.tk.call('::tk::unsupported::MacWindowStyle', 'style', self.root._w, 'document', 'closeBox collapseBox resizable zoomBox')
            except Exception:
                pass  # Ignore if this fails on older macOS versions
        
        # Start maximized/fullscreen on all platforms (deferred to avoid blocking)
        def maximize_window():
            try:
                if platform.system() == 'Windows':
                    # Windows: use state zoomed
                    self.root.state('zoomed')
                elif platform.system() == 'Darwin':
                    # macOS: maximize to full screen (not fullscreen mode, just maximized)
                    # Get screen dimensions
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    # Set geometry to fill screen (accounting for menu bar and dock)
                    self.root.geometry(f"{screen_width}x{screen_height-100}+0+0")
                    # Note: -zoomed attribute doesn't work reliably on macOS, using geometry instead
                else:
                    # Linux: try zoomed state
                    try:
                        self.root.attributes('-zoomed', 1)  # Use 1 instead of True for Tk compatibility
                    except:
                        # Fallback: maximize manually
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
            except Exception as e:
                # Fallback to default size if maximizing fails
                print(f"Could not maximize window: {e}")
                self.root.geometry("900x750")
        
        # Set initial size, then maximize after window is shown
        self.root.geometry("900x750")
        self.root.after(1, maximize_window)
        
        # Set window icon for taskbar (Windows) and dock (macOS)
        self._set_window_icon()
        
        # Handle window close event to clean up lock file
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Initialize managers (will be set in setup)
        self.pallet_manager: Optional[PalletManager] = None
        self.workbook_path: Optional[Path] = None
        self.current_pallet: Optional[dict] = None
        self.pallet_exporter: Optional[PalletExporter] = None
        self.serial_db: Optional[SerialDatabase] = None
        self.use_database: bool = False  # Whether to use database instead of workbook
        self._init_error: Optional[str] = None
        self.panel_type: Optional[str] = None  # Panel type selected during export
        
        # Panel capacity setting (default 25, persists across sessions)
        self.max_panels = self._load_max_panels_setting()
        self.max_panels_var: Optional[tk.IntVar] = None  # Will be set in setup_ui
        
        # Active customer tracking (default: Josh Atwood | Future Solutions)
        self.active_customer_display: Optional[str] = None
        
        # UI Components (will be created in setup_ui)
        self.pallet_label: Optional[tk.Label] = None
        self.scan_entry: Optional[tk.Entry] = None
        self.slots_canvas: Optional[tk.Canvas] = None
        self.slots_scrollable: Optional[tk.Frame] = None
        self.slot_widgets: list = []
        self.status_label: Optional[tk.Label] = None
        self.action_frame: Optional[tk.Frame] = None
        self.active_customer_label: Optional[tk.Label] = None
        self.active_customer_var: Optional[tk.StringVar] = None
        self.active_customer_menu: Optional[tk.OptionMenu] = None

        # Window references for singleton behavior
        self.history_window: Optional[tk.Toplevel] = None
        self.customer_window: Optional[tk.Toplevel] = None
        
        # Always show splash screen for professional startup experience
        project_root = get_base_dir()
        marker_file = project_root / ".initialized"
        is_first_launch = not marker_file.exists()
        
        # Show splash screen on every launch
        self._show_splash_screen(is_first_launch)
        
        # Initialize after splash is shown
        if is_first_launch:
            # First launch: detailed progress updates
            self.root.after(100, lambda: self._initialize_with_progress())
        else:
            # Normal launch: quick initialization with splash
            self.root.after(100, lambda: self._initialize_with_splash())
    
    def _set_window_icon(self):
        """Set the window icon for taskbar/dock and window title bar"""
        try:
            import platform
            from PIL import Image, ImageTk
            
            system = platform.system()
            icon_set = False
            
            if system == 'Windows':
                # Windows: use .ico file for window title bar and taskbar
                # Try multiple paths to find the icon
                icon_paths = [
                    get_resource_path('icons/PalletManager.ico'),
                    get_base_dir() / 'icons' / 'PalletManager.ico',
                    Path(sys.executable).parent / 'icons' / 'PalletManager.ico',
                    Path(sys.executable).parent / '_internal' / 'icons' / 'PalletManager.ico',
                ]
                
                for icon_path in icon_paths:
                    if icon_path.exists():
                        try:
                            # Set icon for window title bar and taskbar
                            self.root.iconbitmap(str(icon_path))
                            # Also try setting as PhotoImage for better compatibility
                            try:
                                img = Image.open(icon_path)
                                photo = ImageTk.PhotoImage(img)
                                self.root.iconphoto(False, photo)
                            except Exception:
                                pass  # Fallback to iconbitmap only
                            icon_set = True
                            print(f"Set window icon from: {icon_path}")
                            break
                        except Exception as e:
                            print(f"Failed to set icon from {icon_path}: {e}")
                            continue
                
                if not icon_set:
                    print(f"Warning: Could not find PalletManager.ico. Tried: {[str(p) for p in icon_paths]}")
                    
            elif system == 'Darwin':
                # macOS: use .icns file
                icon_paths = [
                    get_resource_path('icons/PalletManager.icns'),
                    get_base_dir() / 'icons' / 'PalletManager.icns',
                    Path(sys.executable).parent / 'icons' / 'PalletManager.icns',
                ]
                
                for icon_path in icon_paths:
                    if icon_path.exists():
                        try:
                            # macOS: iconbitmap works for .icns files
                            self.root.iconbitmap(str(icon_path))
                            icon_set = True
                            print(f"Set window icon from: {icon_path}")
                            break
                        except Exception as e:
                            print(f"Failed to set icon from {icon_path}: {e}")
                            continue
            else:
                # Linux: try to use PNG or ICO
                icon_paths = [
                    get_resource_path('icons/PalletManager.png'),
                    get_base_dir() / 'icons' / 'PalletManager.png',
                    get_resource_path('icons/PalletManager.ico'),
                    get_base_dir() / 'icons' / 'PalletManager.ico',
                ]
                
                for icon_path in icon_paths:
                    if icon_path.exists():
                        try:
                            img = Image.open(icon_path)
                            photo = ImageTk.PhotoImage(img)
                            self.root.iconphoto(True, photo)
                            icon_set = True
                            print(f"Set window icon from: {icon_path}")
                            break
                        except Exception as e:
                            print(f"Failed to set icon from {icon_path}: {e}")
                            continue
                            
        except ImportError:
            # PIL/Pillow not available - try basic iconbitmap only
            try:
                system = platform.system()
                if system == 'Windows':
                    icon_paths = [
                        get_resource_path('icons/PalletManager.ico'),
                        get_base_dir() / 'icons' / 'PalletManager.ico',
                        Path(sys.executable).parent / 'icons' / 'PalletManager.ico',
                    ]
                    for icon_path in icon_paths:
                        if icon_path.exists():
                            self.root.iconbitmap(str(icon_path))
                            print(f"Set window icon from: {icon_path} (basic method)")
                            break
            except Exception as e:
                print(f"Error setting window icon (basic method): {e}")
        except Exception as e:
            # Log error but don't crash - app will still work
            print(f"Error setting window icon: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_splash_screen(self, is_first_launch: bool):
        """Show splash screen on every launch"""
        # Create splash window (centered, on top)
        splash = tk.Toplevel(self.root)
        splash.title("Pallet Manager")
        
        # Remove window decorations BEFORE setting geometry (order matters on macOS)
        try:
            splash.overrideredirect(True)
        except Exception as e:
            print(f"Warning: Could not set overrideredirect: {e}")
        
        splash.geometry("500x250")
        splash.resizable(0, 0)  # Use 0 instead of False for Tk compatibility
        
        # Center the window
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() // 2) - (500 // 2)
        y = (splash.winfo_screenheight() // 2) - (250 // 2)
        splash.geometry(f"500x250+{x}+{y}")
        
        # Make it stay on top
        try:
            splash.attributes("-topmost", 1)  # Use 1 instead of True for Tk compatibility
        except Exception:
            pass  # Ignore if this fails
        
        # Configure style
        bg_color = "#2C3E50"
        splash.config(bg=bg_color)
        
        # Logo/Title
        version = get_version()
        
        title_label = tk.Label(
            splash,
            text="Pallet Manager",
            font=("Arial", 24, "bold"),
            bg=bg_color,
            fg="white"
        )
        title_label.pack(pady=(40, 10))
        
        version_label = tk.Label(
            splash,
            text=f"Version {version}",
            font=("Arial", 12),
            bg=bg_color,
            fg="#BDC3C7"
        )
        version_label.pack(pady=(0, 30))
        
        # Loading message
        status_text = "Initializing for first time..." if is_first_launch else "Loading..."
        self._splash_status = tk.StringVar(value=status_text)
        status_label = tk.Label(
            splash,
            textvariable=self._splash_status,
            font=("Arial", 11),
            bg=bg_color,
            fg="#ECF0F1"
        )
        status_label.pack(pady=(0, 15))
        
        # Progress bar
        progress_frame = tk.Frame(splash, bg=bg_color)
        progress_frame.pack(pady=(0, 20), padx=40, fill=tk.X)
        
        self._splash_canvas = tk.Canvas(
            progress_frame,
            height=20,
            bg="#34495E",
            highlightthickness=0
        )
        self._splash_canvas.pack(fill=tk.X)
        
        # Progress bar fill
        self._splash_progress = 0
        self._splash_max = 420  # Width minus padding
        
        # Store reference
        self._splash_window = splash
        self._loading_window = splash  # Keep for compatibility
        self._progress_canvas_ref = self._splash_canvas  # Keep for compatibility
        
        # Update display
        splash.update()
    
    def _update_loading_progress(self, progress: int, message: str):
        """
        Update loading screen progress bar and message.
        
        Args:
            progress: Progress percentage (0-100)
            message: Status message to display
        """
        # Support both old and new variable names
        if hasattr(self, '_splash_status') and self._splash_status:
            self._splash_status.set(message)
        elif hasattr(self, '_loading_status') and self._loading_status:
            self._loading_status.set(message)
        
        canvas = None
        if hasattr(self, '_splash_canvas') and self._splash_canvas:
            canvas = self._splash_canvas
        elif hasattr(self, '_progress_canvas_ref') and self._progress_canvas_ref:
            canvas = self._progress_canvas_ref
        
        if canvas:
            # Calculate width based on progress
            width = int((progress / 100.0) * self._splash_max)
            width = max(0, min(width, self._splash_max))
            
            # Clear and redraw progress bar
            canvas.delete("all")
            if width > 0:
                canvas.create_rectangle(
                    0, 0, width, 20,
                    fill="#3498DB",
                    outline=""
                )
            
            # Update display
            if hasattr(self, '_splash_window') and self._splash_window:
                self._splash_window.update()
            elif hasattr(self, '_loading_window') and self._loading_window:
                self._loading_window.update()
    
    def _close_loading_screen(self):
        """Close the loading screen"""
        if hasattr(self, '_splash_window') and self._splash_window:
            try:
                self._splash_window.destroy()
            except Exception:
                pass
            self._splash_window = None
        if hasattr(self, '_loading_window') and self._loading_window:
            try:
                self._loading_window.destroy()
            except Exception:
                pass
            self._loading_window = None
    
    def _initialize_with_progress(self):
        """Initialize components with progress updates on loading screen"""
        try:
            project_root = get_base_dir()
            
            # Step 1: Create folders (10-40%)
            self._update_loading_progress(10, "Creating project folders...")
            self._ensure_required_folders(project_root)
            
            self._update_loading_progress(20, "Setting up PALLETS folder...")
            self.root.update()
            time.sleep(0.1)  # Small delay for visual feedback
            
            self._update_loading_progress(30, "Setting up EXCEL folder...")
            self.root.update()
            time.sleep(0.1)
            
            self._update_loading_progress(40, "Setting up data folders...")
            self.root.update()
            time.sleep(0.1)
            
            # Step 2: Initialize PalletManager (50%)
            self._update_loading_progress(50, "Initializing pallet manager...")
            history_file = project_root / "PALLETS" / "pallet_history.json"
            self.pallet_manager = PalletManager(history_file, defer_load=True)
            self.root.update()
            
            # Step 3: Initialize SerialDatabase (60%)
            self._update_loading_progress(60, "Initializing serial database...")
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            imported_data_dir = project_root / "IMPORTED DATA"
            # Master sun simulator data now lives in IMPORTED DATA/MASTER/
            master_data_file = imported_data_dir / "MASTER" / "sun_simulator_data.xlsx"
            self.serial_db = SerialDatabase(db_file, imported_data_dir, master_data_file, defer_init=True)
            self.root.update()
            
            # Step 4: Setup workbook (70%)
            self._update_loading_progress(70, "Setting up workbook...")
            excel_dir = project_root / "EXCEL"
            self._ensure_reference_workbook(excel_dir)
            self.root.update()
            
            # Step 5: Initialize CustomerManager (80%)
            self._update_loading_progress(80, "Initializing customer manager...")
            customers_dir = project_root / "CUSTOMERS"
            customers_dir.mkdir(parents=True, exist_ok=True)
            customer_excel_file = customers_dir / "customers.xlsx"
            self.customer_manager = CustomerManager(customer_excel_file)
            self.root.update()
            
            # Step 6: Find workbook (90%)
            self._update_loading_progress(90, "Locating workbook...")
            current_workbook = excel_dir / "CURRENT.xlsx"
            if current_workbook.exists():
                self.workbook_path = current_workbook
            else:
                self.workbook_path = None
            self.use_database = True
            self.pallet_exporter = None
            self.root.update()
            
            # Step 7: Complete (100%)
            self._update_loading_progress(100, "Setup complete!")
            self.root.update()
            time.sleep(0.3)  # Brief pause to show completion
            
            # Create marker file to indicate initialization is complete
            marker_file = project_root / ".initialized"
            try:
                marker_file.touch()
                print(f"Created initialization marker file: {marker_file}")
            except Exception as e:
                print(f"Warning: Could not create marker file: {e}")
            
            # Close loading screen and setup UI
            self._close_loading_screen()
            
            # Setup main UI
            self.setup_ui()
            self.start_new_pallet()
            
            # Defer heavy workbook search
            self.root.after(100, self._find_workbook_async)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("Full error traceback:")
            print(error_details)
            self._init_error = str(e)
            self._close_loading_screen()
            self._show_init_error()
    
    def _initialize_with_splash(self):
        """Initialize components with splash screen (normal launch)"""
        try:
            # Step 1: Initialize components (0-70%)
            self._update_loading_progress(10, "Loading components...")
            
            if not self._initialize_components():
                self._close_loading_screen()
                self._show_init_error()
                return
            
            self._update_loading_progress(40, "Setting up interface...")
            
            # Step 2: Setup UI (70-90%)
            self.setup_ui()
            self._update_loading_progress(70, "Loading data...")
            
            # Step 3: Start new pallet (90-100%)
            self.start_new_pallet()
            self._update_loading_progress(90, "Finalizing...")
            
            # Brief pause to show completion
            time.sleep(0.3)
            self._update_loading_progress(100, "Ready!")
            time.sleep(0.2)
            
            # Close splash and show main window
            self._close_loading_screen()
            
            # Defer heavy workbook search
            self.root.after(100, self._find_workbook_async)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("Full error traceback:")
            print(error_details)
            self._init_error = str(e)
            self._close_loading_screen()
            self._show_init_error()
    
    def _show_init_error(self):
        """Show initialization error in the main window"""
        error_frame = tk.Frame(self.root, bg="white")
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(
            error_frame,
            text="⚠️ Initialization Failed",
            font=("Arial", 16, "bold"),
            fg="red",
            bg="white"
        ).pack(pady=20)
        
        # Determine error message (use path_utils for packaging compatibility)
        project_root = get_base_dir()
        excel_dir = project_root / "EXCEL"
        
        if self._init_error:
            # Exception occurred
            error_text = (
                f"Error: {self._init_error}\n\n"
                "Please check that:\n"
                "  • Python 3.11 is installed\n"
                "  • All required files are in place\n"
                "  • You have read/write permissions"
            )
        else:
            # Workbook not found
            error_text = (
                "Could not find pallet workbook.\n\n"
                "Please ensure one of the following:\n"
                "  • data/EXCEL/CURRENT.xlsx exists, OR\n"
                "  • A BUILD YYYY Q-X.xlsx file is in the EXCEL folder\n\n"
                "After placing the workbook, close this window\n"
                "and launch Pallet Manager again."
            )
        
        tk.Label(
            error_frame,
            text=error_text,
            font=("Arial", 11),
            justify=tk.LEFT,
            bg="white",
            wraplength=500
        ).pack(pady=10, padx=20)
        
        # Show path info
        path_info = f"EXCEL directory: {excel_dir}\n"
        path_info += f"Directory exists: {excel_dir.exists()}\n"
        if excel_dir.exists():
            xlsx_files = list(excel_dir.glob("*.xlsx"))
            path_info += f"Excel files found: {len(xlsx_files)}"
            if xlsx_files:
                path_info += "\nFiles:"
                for f in xlsx_files[:5]:
                    path_info += f"\n  - {f.name}"
        
        tk.Label(
            error_frame,
            text=path_info,
            font=("Courier", 9),
            fg="gray",
            bg="white",
            justify=tk.LEFT
        ).pack(pady=10)
        
        tk.Button(
            error_frame,
            text="Close",
            command=self.root.destroy,
            font=("Arial", 11),
            width=15
        ).pack(pady=20)
    
    def _initialize_components(self) -> bool:
        """Initialize PalletManager and find workbook. Returns True if successful."""
        try:
            # Determine project root (use path_utils for packaging compatibility)
            project_root = get_base_dir()
            
            # Ensure all required folders exist
            self._ensure_required_folders(project_root)
            
            # Initialize PalletManager (lightweight - just sets up file path)
            history_file = project_root / "PALLETS" / "pallet_history.json"
            # Defer actual data loading to after UI is shown
            self.pallet_manager = PalletManager(history_file, defer_load=True)
            
            # Initialize SerialDatabase (Excel-based database with electrical values)
            # Defer heavy initialization to after UI loads
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            imported_data_dir = project_root / "IMPORTED DATA"
            master_data_file = imported_data_dir / "sun_simulator_data.xlsx"
            # Defer database file operations
            self.serial_db = SerialDatabase(db_file, imported_data_dir, master_data_file, defer_init=True)
            
            # Load data asynchronously after UI is shown
            self.root.after(50, self._load_data_async)
            
            # Always use database for validation if SerialDatabase is available
            # (Workbook is only needed for export, not validation)
            self.use_database = True
            
            # Try to find workbook (needed for export, but not for validation)
            # Defer heavy file operations to after UI is shown
            excel_dir = project_root / "EXCEL"
            current_workbook = excel_dir / "CURRENT.xlsx"
            
            # Quick check first (fast path)
            if current_workbook.exists():
                self.workbook_path = current_workbook
            else:
                # Defer expensive glob/stat operations
                self.workbook_path = None
                # Will be found asynchronously after UI loads
            
            # PalletExporter will be initialized asynchronously after workbook is found
            self.pallet_exporter = None
            
            # Initialize CustomerManager (uses Excel file in CUSTOMERS folder)
            customers_dir = project_root / "CUSTOMERS"
            customers_dir.mkdir(parents=True, exist_ok=True)
            customer_excel_file = customers_dir / "customers.xlsx"
            self.customer_manager = CustomerManager(customer_excel_file)
            
            return True
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            # Print full traceback to console for debugging
            print("Full error traceback:")
            print(error_details)
            # Store error for display in _show_init_error
            self._init_error = str(e)
            return False
    
    def _ensure_required_folders(self, project_root: Path):
        """Ensure all required folders exist (creates if missing)"""
        try:
            # Ensure project_root exists and is writable
            project_root.mkdir(parents=True, exist_ok=True)
            
            # PALLETS folder (for exports and history)
            pallets_dir = project_root / "PALLETS"
            pallets_dir.mkdir(parents=True, exist_ok=True)
            
            # IMPORTED DATA folder (for processed simulator files)
            imported_data_dir = project_root / "IMPORTED DATA"
            imported_data_dir.mkdir(parents=True, exist_ok=True)
            
            # SUN SIMULATOR DATA folder (for dropping new simulator files)
            sun_sim_dir = project_root / "SUN SIMULATOR DATA"
            sun_sim_dir.mkdir(parents=True, exist_ok=True)
            
            # EXCEL folder (for workbook files)
            excel_dir = project_root / "EXCEL"
            excel_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy reference workbook if EXCEL folder is empty or has no workbooks
            self._ensure_reference_workbook(excel_dir)
            
            # LOGS folder (for log files)
            logs_dir = project_root / "LOGS"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # CUSTOMERS folder (for customer Excel file)
            customers_dir = project_root / "CUSTOMERS"
            customers_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify folders were created
            required_folders = [pallets_dir, imported_data_dir, sun_sim_dir, excel_dir, logs_dir, customers_dir]
            missing_folders = [f for f in required_folders if not f.exists()]
            
            if missing_folders:
                error_msg = f"Failed to create required folders: {[str(f) for f in missing_folders]}"
                print(f"ERROR: {error_msg}")
                raise RuntimeError(error_msg)
            
        except PermissionError as e:
            error_msg = (
                f"Permission denied creating folders in: {project_root}\n"
                f"Error: {e}\n\n"
                f"Please ensure you have write permissions to this location, "
                f"or move the app to a writable location."
            )
            print(f"ERROR: {error_msg}")
            if self.root:
                messagebox.showerror(
                    "Permission Error",
                    error_msg,
                    parent=self.root
                )
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Could not create required folders: {e}"
            print(f"ERROR: {error_msg}")
            if self.root:
                messagebox.showerror(
                    "Folder Creation Error",
                    f"{error_msg}\n\nPlease check permissions and try again.",
                    parent=self.root
                )
            raise RuntimeError(error_msg) from e
    
    def _ensure_reference_workbook(self, excel_dir: Path):
        """
        Copy reference workbook to EXCEL folder if no workbooks exist.
        Also ensure CURRENT.xlsx exists (create it if missing).
        This ensures the app works out of the box after installation.
        """
        try:
            import shutil
            
            # Debug logging for Windows troubleshooting
            print("\n" + "="*70)
            print("DEBUG: _ensure_reference_workbook() called")
            print("="*70)
            print(f"Excel directory: {excel_dir}")
            print(f"Excel dir exists: {excel_dir.exists()}")
            print(f"Is packaged: {is_packaged()}")
            print(f"sys.executable: {sys.executable}")
            if hasattr(sys, '_MEIPASS'):
                print(f"sys._MEIPASS: {sys._MEIPASS}")
            print("="*70)
            
            # Check if any workbooks exist (excluding CURRENT.xlsx and temp files)
            existing_workbooks = list(excel_dir.glob("*.xlsx"))
            existing_workbooks = [f for f in existing_workbooks 
                                 if not f.name.startswith("~$") 
                                 and f.name != "CURRENT.xlsx"]
            print(f"Existing workbooks in EXCEL: {[f.name for f in existing_workbooks]}")
            
            # Try to find reference workbook in packaged app
            reference_workbook = None
            
            # In packaged app, reference workbook is in reference_workbook/ subdirectory
            if is_packaged():
                # PyInstaller (Windows/Linux): Check _MEIPASS (temp extraction dir for onefile)
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller onefile mode - data files extracted to temp dir
                    meipass_path = Path(sys._MEIPASS) / "reference_workbook" / "BUILD 10-12-25.xlsx"
                    if meipass_path.exists():
                        reference_workbook = meipass_path
                        print(f"Found reference workbook in _MEIPASS: {meipass_path}")
                
                # py2app (macOS): Resources are in Contents/Resources/
                if not reference_workbook:
                    exe_dir = Path(sys.executable).parent
                    resources_dir = exe_dir.parent / "Resources"
                    ref_path = resources_dir / "reference_workbook" / "BUILD 10-12-25.xlsx"
                    if ref_path.exists():
                        reference_workbook = ref_path
                        print(f"Found reference workbook in Resources: {ref_path}")
                
                # Fallback: Try _internal subdirectory (PyInstaller onedir mode)
                if not reference_workbook:
                    exe_dir = Path(sys.executable).parent
                    internal_path = exe_dir / "_internal" / "reference_workbook" / "BUILD 10-12-25.xlsx"
                    if internal_path.exists():
                        reference_workbook = internal_path
                        print(f"Found reference workbook in _internal: {internal_path}")
            
            # In development, check project EXCEL folder
            if not reference_workbook:
                dev_excel = Path(__file__).parent.parent / "EXCEL" / "BUILD 10-12-25.xlsx"
                if dev_excel.exists():
                    reference_workbook = dev_excel
            
            # Copy reference workbook if no workbooks exist
            print(f"\nChecking if we need to copy reference workbook...")
            print(f"  existing_workbooks: {len(existing_workbooks)}")
            print(f"  reference_workbook: {reference_workbook}")
            print(f"  reference exists: {reference_workbook.exists() if reference_workbook else 'N/A'}")
            
            if not existing_workbooks and reference_workbook and reference_workbook.exists():
                # Copy BUILD workbook
                build_target = excel_dir / "BUILD 10-12-25.xlsx"
                if not build_target.exists():
                    print(f"  → Copying BUILD workbook to: {build_target}")
                    shutil.copy2(reference_workbook, build_target)
                    print(f"  ✅ Copied reference workbook successfully!")
                else:
                    print(f"  ℹ️  BUILD workbook already exists, skipping")
            
            # Always ensure CURRENT.xlsx exists (create it if missing)
            current_target = excel_dir / "CURRENT.xlsx"
            print(f"\nChecking CURRENT.xlsx...")
            print(f"  Target: {current_target}")
            print(f"  Exists: {current_target.exists()}")
            
            if not current_target.exists():
                # Try to use reference workbook if available
                if reference_workbook and reference_workbook.exists():
                    print(f"  → Creating CURRENT.xlsx from reference workbook")
                    shutil.copy2(reference_workbook, current_target)
                    print(f"  ✅ Created CURRENT.xlsx successfully!")
                    print(f"     Size: {current_target.stat().st_size} bytes")
                elif existing_workbooks:
                    # Use the most recent BUILD file if reference not available
                    latest_build = max(existing_workbooks, key=lambda p: p.stat().st_mtime)
                    print(f"  → Creating CURRENT.xlsx from {latest_build.name}")
                    shutil.copy2(latest_build, current_target)
                    print(f"  ✅ Created CURRENT.xlsx from existing BUILD file!")
                else:
                    print(f"  ❌ No reference workbook or existing BUILD files found!")
            else:
                print(f"  ℹ️  CURRENT.xlsx already exists, skipping")
            
            print("="*70 + "\n")
            
        except Exception as e:
            # Log error but don't fail - user can add reference workbook manually
            print(f"\n❌ ERROR in _ensure_reference_workbook: {e}")
            print(f"   Exception type: {type(e).__name__}")
            import traceback
            print(f"   Traceback:\n{traceback.format_exc()}")
            print("="*70)
            print("You can manually add a reference workbook to the EXCEL folder.")
    
    def setup_ui(self):
        """Create and layout all UI components"""
        # Header frame
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=5)
        
        # Left button frame (Restart & Refresh)
        left_button_frame = tk.Frame(header, bg=self.root.cget('bg'))
        left_button_frame.pack(side=tk.LEFT)
        
        # Use regular Button with explicit colors and relief for visibility
        restart_btn = tk.Button(left_button_frame, text="🔄 Restart", 
                                command=self.restart_application, width=10,
                                bg="#DC3545", fg="black", font=("Arial", 9, "bold"),
                                activebackground="#C82333", activeforeground="black",
                                relief=tk.RAISED, bd=2, cursor="hand2")
        restart_btn.pack(side=tk.LEFT, padx=2)
        
        refresh_btn = tk.Button(left_button_frame, text="♻️ Refresh", 
                                command=self.refresh_application, width=10,
                                bg="#17A2B8", fg="black", font=("Arial", 9, "bold"),
                                activebackground="#138496", activeforeground="black",
                                relief=tk.RAISED, bd=2, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        # Left info frame (app name only)
        left_info_frame = tk.Frame(header, bg=self.root.cget('bg'))
        left_info_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        version = get_version()
        tk.Label(left_info_frame, text=f"Pallet Manager {version}", 
                font=("Arial", 14, "bold"), bg=self.root.cget('bg')).pack(anchor=tk.W)
        
        tk.Label(header, text="Current Pallet:", 
                font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.pallet_label = tk.Label(header, text="#1", 
                                     font=("Arial", 10, "bold"))
        self.pallet_label.pack(side=tk.LEFT)
        
        # Panel type will be selected during export - no dropdown in main UI
        self.panel_type = None  # Will be set during export
        
        # Note: scan_entry will be enabled in start_new_pallet() if panel type is set
        
        # Button frame
        button_frame = tk.Frame(header)
        button_frame.pack(side=tk.RIGHT)
        
        tk.Button(button_frame, text="History", 
                 command=self.show_history, width=12).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text="Customer Management", 
                 command=self.show_settings, width=18).pack(side=tk.LEFT, padx=2)
        
        self.import_button = tk.Button(button_frame, text="Import Data", 
                                      command=self.import_data, width=12,
                                      state=tk.NORMAL)
        self.import_button.pack(side=tk.LEFT, padx=2)
        
        # Export button - always visible, enabled/disabled based on pallet state
        # Match styling of other buttons but with color to indicate state
        self.export_button = tk.Button(button_frame, text="Export Pallet", 
                                     command=self.export_pallet, width=12,
                                     state=tk.DISABLED, 
                                     bg="#2E7D32", fg="black",
                                     activebackground="#1B5E20", activeforeground="black",
                                     disabledforeground="black")
        self.export_button.pack(side=tk.LEFT, padx=2)
        
        # New Pallet button removed - all exports handled by Export Pallet button
        
        # Active customer display above scan area
        customer_display_frame = tk.Frame(self.root, bg=self.root.cget('bg'))
        customer_display_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        # Initialize active customer to default if not set
        if not self.active_customer_display and self.customer_manager:
            try:
                # Set default to Josh Atwood | Future Solutions (or first customer if default doesn't exist)
                customer_names = self.customer_manager.get_customer_names()
                if customer_names:
                    # Try to find "Josh Atwood | Future Solutions" or "Josh Atwood | Future Solutions Inc"
                    default_found = False
                    for name in customer_names:
                        if "Josh Atwood" in name and ("Future Solutions" in name):
                            self.active_customer_display = name
                            default_found = True
                            break
                    if not default_found:
                        self.active_customer_display = customer_names[0]
                else:
                    self.active_customer_display = "Josh Atwood | Future Solutions"
            except Exception:
                self.active_customer_display = "Josh Atwood | Future Solutions"
        
        tk.Label(customer_display_frame, text="Active Customer:", 
                font=("Arial", 10, "bold"), bg=self.root.cget('bg')).pack(side=tk.LEFT, padx=(0, 5))
        
        # Customer dropdown for changing active customer
        self.active_customer_var = tk.StringVar(value=self.active_customer_display or "Josh Atwood | Future Solutions")
        
        def update_active_customer(*args):
            """Update active customer when dropdown selection changes"""
            selected = self.active_customer_var.get()
            self.active_customer_display = selected
        
        # Attach trace to update active_customer_display when dropdown changes
        self.active_customer_var.trace('w', update_active_customer)
        
        # Get customer names for dropdown (use cached data if available)
        customer_names = []
        if self.customer_manager:
            try:
                # Don't force refresh on initial load - use cached data
                self.customer_manager.refresh_customers(force_reload=False)
                customer_names = self.customer_manager.get_customer_names()
                if not customer_names:
                    customer_names = ["Josh Atwood | Future Solutions"]
            except Exception:
                customer_names = ["Josh Atwood | Future Solutions"]
        else:
            customer_names = ["Josh Atwood | Future Solutions"]
        
        # Set initial value if it's not in the list
        if self.active_customer_var.get() not in customer_names and customer_names:
            self.active_customer_var.set(customer_names[0])
            self.active_customer_display = customer_names[0]
        
        self.active_customer_menu = tk.OptionMenu(customer_display_frame, self.active_customer_var, 
                                                  *customer_names)
        self.active_customer_menu.config(bg="white", fg="#2E7D32", font=("Arial", 10, "bold"),
                                        width=35, anchor=tk.W)
        self.active_customer_menu.pack(side=tk.LEFT, padx=(0, 5))
        
        # Keep label for reference (hidden but used for updates)
        self.active_customer_label = tk.Label(customer_display_frame, 
                                             text="", font=("Arial", 10), bg=self.root.cget('bg'))
        self.active_customer_label.pack_forget()  # Hidden, just for reference
        
        # Panel capacity toggle (25 or 26 panels) - below active customer
        panels_toggle_frame = tk.Frame(self.root, bg=self.root.cget('bg'))
        panels_toggle_frame.pack(fill=tk.X, padx=10, pady=(8, 0))
        
        # Create inner frame for better alignment
        panels_inner_frame = tk.Frame(panels_toggle_frame, bg=self.root.cget('bg'))
        panels_inner_frame.pack(anchor=tk.W)
        
        tk.Label(panels_inner_frame, text="Panel Capacity:", 
                font=("Arial", 10, "bold"), bg=self.root.cget('bg')).pack(side=tk.LEFT, padx=(0, 8))
        
        # Initialize max_panels_var
        self.max_panels_var = tk.IntVar(value=self.max_panels)
        
        # Radio buttons for panel capacity
        capacity_frame = tk.Frame(panels_inner_frame, bg=self.root.cget('bg'))
        capacity_frame.pack(side=tk.LEFT)
        
        tk.Radiobutton(
            capacity_frame,
            text="25 Panels",
            variable=self.max_panels_var,
            value=25,
            bg=self.root.cget('bg'),
            font=("Arial", 10),
            command=self._on_max_panels_changed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Radiobutton(
            capacity_frame,
            text="26 Panels",
            variable=self.max_panels_var,
            value=26,
            bg=self.root.cget('bg'),
            font=("Arial", 10),
            command=self._on_max_panels_changed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Radiobutton(
            capacity_frame,
            text="30 Panels",
            variable=self.max_panels_var,
            value=30,
            bg=self.root.cget('bg'),
            font=("Arial", 10),
            command=self._on_max_panels_changed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Radiobutton(
            capacity_frame,
            text="35 Panels",
            variable=self.max_panels_var,
            value=35,
            bg=self.root.cget('bg'),
            font=("Arial", 10),
            command=self._on_max_panels_changed,
        ).pack(side=tk.LEFT)
        
        # Scan area frame
        scan_frame = tk.Frame(self.root)
        scan_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(scan_frame, text="📍 SCAN BARCODE HERE", 
                font=("Arial", 12, "bold")).pack()
        
        self.scan_entry = tk.Entry(scan_frame, font=("Arial", 16))
        self.scan_entry.pack(fill=tk.X, pady=5)
        
        # Bind keyboard shortcuts for undo (only when scan_entry has focus)
        # Cmd+Z on Mac, Ctrl+Z on Windows/Linux
        # Tkinter Entry widgets have built-in undo support via edit_undo()
        def handle_undo(event):
            return self._undo_scan_entry()
        self.scan_entry.bind('<Command-z>', handle_undo)
        self.scan_entry.bind('<Control-z>', handle_undo)
        
        # Bind other events
        self.scan_entry.bind('<Return>', self.on_barcode_scanned)
        self.scan_entry.bind('<Escape>', lambda e: self.scan_entry.delete(0, tk.END))
        
        # Scan entry is always enabled - panel type selected during export
        self.scan_entry.focus()
        
        # Keyboard shortcuts
        self.root.bind('<Control-h>', lambda e: self.show_history())
        # Control-n shortcut removed - New Pallet button removed
        self.root.bind('<F5>', lambda e: self.update_slot_display())
        
        # Slots display area (scrollable)
        slots_frame = tk.LabelFrame(self.root, text="Pallet Slots", 
                                    font=("Arial", 10, "bold"))
        slots_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Canvas with scrollbar for slots (scrollable table)
        self.slots_canvas = tk.Canvas(slots_frame, bg="white", highlightthickness=0)
        self.slots_scrollbar = ttk.Scrollbar(slots_frame, orient="vertical", 
                                            command=self.slots_canvas.yview)
        self.slots_scrollable = tk.Frame(self.slots_canvas, bg="white")
        
        # Bind configure event to update scroll region when content changes
        self.slots_scrollable.bind(
            "<Configure>",
            lambda e: self.slots_canvas.configure(
                scrollregion=self.slots_canvas.bbox("all")
            )
        )
        
        # Create window in canvas for scrollable frame
        self.slots_canvas_window = self.slots_canvas.create_window((0, 0), window=self.slots_scrollable, 
                                        anchor="nw")
        
        # Configure scrollbar
        self.slots_canvas.configure(yscrollcommand=self.slots_scrollbar.set)
        
        # Bind mousewheel scrolling (works on Windows, macOS, Linux)
        def _on_mousewheel(event):
            self.slots_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mousewheel for different platforms
        self.slots_canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows
        self.slots_canvas.bind_all("<Button-4>", lambda e: self.slots_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        self.slots_canvas.bind_all("<Button-5>", lambda e: self.slots_canvas.yview_scroll(1, "units"))  # Linux scroll down
        
        # Update canvas width when window resizes
        def _configure_canvas(event):
            canvas_width = event.width
            self.slots_canvas.itemconfig(self.slots_canvas_window, width=canvas_width)
        
        self.slots_canvas.bind('<Configure>', _configure_canvas)
        
        # Pack canvas and scrollbar
        self.slots_canvas.pack(side="left", fill="both", expand=True)
        self.slots_scrollbar.pack(side="right", fill="y")
        
        # Status and action area
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text="Ready to scan", 
                                    font=("Arial", 10))
        self.status_label.pack()
        
        self.action_frame = tk.Frame(self.root)
        self.action_frame.pack(fill=tk.X, padx=10, pady=5)
    
    def _load_last_panel_type(self) -> str:
        """Load last selected panel type from config file"""
        try:
            project_root = get_base_dir()
            config_file = project_root / "PALLETS" / "panel_type_config.txt"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    last_type = f.read().strip()
                    if last_type in ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"]:
                        return last_type
        except Exception:
            pass
        return ""  # No default - user must select
    
    def _save_last_panel_type(self, panel_type: str):
        """Save selected panel type to config file - optimized for speed"""
        try:
            project_root = get_base_dir()
            config_file = project_root / "PALLETS" / "panel_type_config.txt"
            # Create parent directory if needed (fast check)
            if not config_file.parent.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
            # Write file (should be very fast for small text file)
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(panel_type)
        except Exception:
            pass  # Silently fail if can't save - don't block UI
    
    def _load_max_panels_setting(self) -> int:
        """Load max panels setting from file (default 25)"""
        try:
            project_root = get_base_dir()
            config_file = project_root / "PALLETS" / "max_panels.txt"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    value = int(f.read().strip())
                    # Validate: only allow known capacities
                    if value in [25, 26, 30, 35]:
                        return value
            # Default to 25 if file doesn't exist or invalid value
            return 25
        except Exception:
            # Default to 25 on any error
            return 25
    
    def _save_max_panels_setting(self, max_panels: int):
        """Save max panels setting to file"""
        try:
            project_root = get_base_dir()
            config_file = project_root / "PALLETS" / "max_panels.txt"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                f.write(str(max_panels))
        except Exception as e:
            # Log error but don't block user
            print(f"Warning: Could not save max_panels setting: {e}")
    
    def _update_customer_menu(self, force_refresh=False):
        """
        Update the customer dropdown menu with latest customers.
        Uses caching to avoid unnecessary menu rebuilds.
        
        Args:
            force_refresh: If True, bypass cache and refresh from file
        """
        if not self.active_customer_menu or not self.customer_manager:
            return
        
        try:
            # Refresh customers from database (will use cache if recent)
            self.customer_manager.refresh_customers(force_reload=force_refresh)
            customer_names = self.customer_manager.get_customer_names()
            
            if not customer_names:
                customer_names = ["Josh Atwood | Future Solutions"]
            
            # Get current selection
            current_selection = self.active_customer_var.get()
            
            # Check if menu needs updating by comparing current menu items
            menu = self.active_customer_menu["menu"]
            current_menu_items = []
            try:
                menu_index = 0
                while True:
                    try:
                        label = menu.entrycget(menu_index, "label")
                        current_menu_items.append(label)
                        menu_index += 1
                    except tk.TclError:
                        break
            except Exception:
                current_menu_items = []
            
            # Only rebuild menu if items have changed
            if set(current_menu_items) != set(customer_names):
                # Clear and rebuild menu
                menu.delete(0, "end")
                
                for name in customer_names:
                    menu.add_command(label=name, 
                                   command=lambda value=name: self.active_customer_var.set(value))
            
            # Restore selection if it still exists, otherwise use first
            if current_selection in customer_names:
                # Only update if different to avoid triggering trace
                if self.active_customer_var.get() != current_selection:
                    self.active_customer_var.set(current_selection)
                # Ensure active_customer_display is in sync
                if self.active_customer_display != current_selection:
                    self.active_customer_display = current_selection
            elif customer_names:
                # Current selection not found, default to first customer
                first_customer = customer_names[0]
                if self.active_customer_var.get() != first_customer:
                    self.active_customer_var.set(first_customer)
                self.active_customer_display = first_customer
        except Exception as e:
            print(f"Warning: Could not update customer menu: {e}")
    
    def _on_max_panels_changed(self, *args):
        """Handle max panels toggle change"""
        if self.max_panels_var:
            new_max = self.max_panels_var.get()
            if new_max != self.max_panels and new_max in [25, 26, 30, 35]:
                self.max_panels = new_max
                self._save_max_panels_setting(new_max)
                # Refresh slot display to show correct number of slots
                self.update_slot_display(force_update=True)
                # Update status if pallet exists
                if self.current_pallet:
                    count = len(self.current_pallet.get('serial_numbers', []))
                    if self.status_label:
                        self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black")

    def _get_template_workbook_for_capacity(self) -> Optional[Path]:
        """
        Select a template workbook based on the current panel capacity.
        
        Mapping:
        - 25 or 26 panels → EXCEL/26.xlsx
        - 30 panels       → EXCEL/30.xlsx
        - 35 panels       → EXCEL/35.xlsx
        
        If the specific template file does not exist, returns None and the
        exporter will fall back to its default source workbook.
        """
        try:
            # Derive project root and EXCEL directory in the same way we locate the main workbook
            if self.workbook_path and self.workbook_path.parent.name == "EXCEL":
                project_root = self.workbook_path.parent.parent
            else:
                project_root = get_base_dir()

            if self.max_panels in (25, 26):
                filename = "26.xlsx"
            elif self.max_panels == 30:
                filename = "30.xlsx"
            elif self.max_panels == 35:
                filename = "35.xlsx"
            else:
                return None

            candidates = [
                project_root / "data" / "EXCEL" / filename,
                get_resource_path(f"data/EXCEL/{filename}"),
                project_root / "EXCEL" / filename,
            ]
            for template_path in candidates:
                if template_path and template_path.exists():
                    return template_path
            return None
        except Exception:
            return None
    
    def _show_modal_error_dialog(self, title: str, message: str, error_type: str = "error"):
        """
        Show a modal error dialog that requires explicit dismissal.
        Prevents accidental dismissal during barcode scanning.
        """
        # Create modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()  # Make modal
        dialog.resizable(False, False)

        # Set appropriate icon based on error type
        if error_type == "warning":
            icon_text = "⚠️"
        else:
            icon_text = "❌"

        # Center the dialog
        dialog.geometry("400x200")
        dialog.geometry("+{}+{}".format(
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))

        # Create content
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Icon and title
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        icon_label = tk.Label(title_frame, text=icon_text, font=("Arial", 24))
        icon_label.pack(side=tk.LEFT, padx=(0, 10))

        title_label = tk.Label(title_frame, text=title, font=("Arial", 12, "bold"))
        title_label.pack(side=tk.LEFT)

        # Message
        message_label = tk.Label(main_frame, text=message, wraplength=350, justify=tk.LEFT)
        message_label.pack(fill=tk.X, pady=(0, 20))

        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # OK button
        ok_button = tk.Button(
            button_frame,
            text="OK",
            command=dialog.destroy,
            width=10,
            bg="#0078d4",
            fg="white",
            font=("Arial", 10, "bold")
        )
        ok_button.pack(side=tk.RIGHT)
        ok_button.focus_set()  # Focus on OK button

        # Bind Enter key to dismiss dialog
        def on_enter(event):
            dialog.destroy()

        dialog.bind('<Return>', on_enter)
        dialog.bind('<KP_Enter>', on_enter)  # Numpad Enter

        # Prevent other windows from being clicked
        dialog.focus_force()

        # Wait for dialog to close
        self.root.wait_window(dialog)

    def _select_panel_type_dialog(self, suggested_pallet_number: Optional[int] = None) -> Optional[tuple]:
        """
        Show dialog to select panel type, pallet number, and customer.
        
        Args:
            suggested_pallet_number: Suggested pallet number to pre-fill (defaults to current pallet number)
        
        Returns:
            Tuple of (panel_type, pallet_number, customer_display_name) or None if cancelled
        """
        # Create dialog window - minimal setup for instant display
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Panel Type, Pallet Number & Customer")
        dialog.transient(self.root)
        dialog.resizable(0, 0)  # Use 0 instead of False for Tk compatibility
        dialog.config(bg="white")
        
        # Use fixed position instead of calculating (faster - no screen size queries)
        # Increased height to accommodate customer field
        dialog.geometry("400x300+400+300")
        
        result = [None]  # Use list to allow modification in nested function
        
        # Main container
        main_frame = tk.Frame(dialog, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Panel Type Section
        tk.Label(main_frame, text="Select Panel Type:", 
                font=("Arial", 10, "bold"), fg="black", bg="white").pack(pady=(0, 5))
        
        # Panel type variable - start with default, load saved value asynchronously
        panel_type_var = tk.StringVar()
        panel_type_var.set("200WT")  # Default - will update if saved value exists
        
        # Dropdown - create immediately
        panel_type_menu = tk.OptionMenu(main_frame, panel_type_var,
                                        *["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"])
        panel_type_menu.config(bg="white", fg="black", 
                              activebackground="#E0E0E0", activeforeground="black",
                              takefocus=False)
        panel_type_menu.pack(pady=(0, 10))
        
        # Pallet Number Section
        pallet_frame = tk.Frame(main_frame, bg="white")
        pallet_frame.pack(pady=(5, 10))
        
        tk.Label(pallet_frame, text="Pallet Number:", 
                font=("Arial", 10, "bold"), fg="black", bg="white").pack(side=tk.LEFT, padx=(0, 5))
        
        # Determine suggested pallet number
        if suggested_pallet_number is None:
            if self.current_pallet:
                suggested_pallet_number = self.current_pallet.get('pallet_number', 1)
            else:
                suggested_pallet_number = 1
        
        pallet_number_var = tk.StringVar()
        pallet_number_var.set(str(suggested_pallet_number))
        
        pallet_number_entry = tk.Entry(pallet_frame, textvariable=pallet_number_var, 
                                       width=10, font=("Arial", 10))
        pallet_number_entry.pack(side=tk.LEFT)
        
        # Customer Section
        tk.Label(main_frame, text="Select Customer:", 
                font=("Arial", 10, "bold"), fg="black", bg="white").pack(pady=(10, 5))
        
        customer_var = tk.StringVar()
        # Refresh customers from Excel before showing dialog (use cache if recent)
        self.customer_manager.refresh_customers(force_reload=False)
        customer_names = self.customer_manager.get_customer_names()
        if not customer_names:
                messagebox.showerror(
                    "No Customers",
                    "No customers found. Please add at least one customer in Customer Management.",
                    parent=dialog
                )
                dialog.destroy()
                return None
        
        customer_var.set(customer_names[0])  # Default to first customer
        
        customer_menu = tk.OptionMenu(main_frame, customer_var, *customer_names)
        customer_menu.config(bg="white", fg="black", 
                            activebackground="#E0E0E0", activeforeground="black",
                            takefocus=False, width=35)
        customer_menu.pack(pady=(0, 10))
        
        # Buttons - create immediately
        button_frame = tk.Frame(main_frame, bg="white")
        button_frame.pack(pady=15)
        
        def confirm():
            try:
                selected_value = panel_type_var.get()
                pallet_number_str = pallet_number_var.get().strip()
                
                # Validate panel type
                if not selected_value or selected_value not in ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"]:
                    messagebox.showerror("Invalid Selection", 
                                       f"Invalid panel type: {selected_value}\n\n"
                                       "Please select a valid panel type.",
                                       parent=dialog)
                    return  # Don't close dialog if invalid
                
                # Validate pallet number
                try:
                    pallet_number = int(pallet_number_str)
                    if pallet_number < 1:
                        raise ValueError("Pallet number must be at least 1")
                except ValueError as e:
                    messagebox.showerror("Invalid Pallet Number", 
                                       f"Invalid pallet number: {pallet_number_str}\n\n"
                                       "Please enter a positive integer.",
                                       parent=dialog)
                    return  # Don't close dialog if invalid
                
                # Save panel type preference (fast operation)
                self._save_last_panel_type(selected_value)
                
                # Get selected customer
                customer_display_name = customer_var.get()
                
                # Return panel type, pallet number, and customer
                result[0] = (selected_value, pallet_number, customer_display_name)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process selection:\n{e}", parent=dialog)
                return
            
            # Release grab before destroying to prevent freezing
            try:
                dialog.grab_release()
            except Exception:
                pass
            
            # Only destroy the dialog, don't call quit() as it might affect main window
            dialog.destroy()
        
        def cancel():
            # Release grab before destroying to prevent freezing
            try:
                dialog.grab_release()
            except Exception:
                pass
            # Only destroy the dialog, don't call quit() as it might affect main window
            dialog.destroy()
        
        ok_btn = tk.Button(button_frame, text="OK", command=confirm, width=10,
                          bg="#4CAF50", fg="black", font=("Arial", 9, "bold"),
                          relief=tk.RAISED, bd=2, cursor="hand2",
                          activebackground="#45a049", activeforeground="black")
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=cancel, width=10,
                              bg="#f44336", fg="black", font=("Arial", 9, "bold"),
                              relief=tk.RAISED, bd=2, cursor="hand2",
                              activebackground="#da190b", activeforeground="black")
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Ensure dialog is fully displayed before making it modal
        dialog.update()  # Single update is sufficient
        
        # Make modal AFTER everything is created and displayed
        dialog.grab_set()
        
        # Keyboard shortcuts
        dialog.bind('<Return>', lambda e: confirm())
        dialog.bind('<Escape>', lambda e: cancel())
        
        # Focus pallet number entry initially for easy editing
        pallet_number_entry.focus_set()
        
        # Load saved panel type preference asynchronously (non-blocking)
        # This happens after dialog is shown, so it doesn't delay display
        def load_saved_preference():
            try:
                saved_type = self._load_last_panel_type()
                if saved_type:
                    panel_type_var.set(saved_type)
            except Exception:
                pass  # Silently fail - use default
        
        # Schedule async load (non-blocking)
        self.root.after(10, load_saved_preference)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result[0]
    
    def _undo_scan_entry(self):
        """Undo the last edit in the scan entry field"""
        if self.scan_entry:
            try:
                # Check if undo is available (Tkinter tracks this internally)
                # edit_undo() will do nothing if there's nothing to undo
                self.scan_entry.edit_undo()
            except tk.TclError:
                # No undo available - silently ignore
                pass
        return "break"  # Prevent event propagation
    
    def on_barcode_scanned(self, event):
        """Handle barcode scan event (Enter key pressed)"""
        # Input validation and bounds checking
        try:
            # Validate input before processing
            if not hasattr(self, 'scan_entry') or not self.scan_entry:
                return
            
            serial = self.scan_entry.get().strip()

            # Normalize serial early (convert to uppercase for case-insensitive processing)
            from app.serial_database import normalize_serial
            serial = normalize_serial(serial)

            # Input validation: check length and dangerous characters
            if not serial:
                return
            
            if len(serial) > 100:
                self.status_label.config(text="Invalid serial number format (too long)", fg="red")
                self.scan_entry.delete(0, tk.END)
                self.scan_entry.focus()
                return
            
            # Check for null bytes or other dangerous characters
            if '\x00' in serial:
                self.status_label.config(text="Invalid serial number format", fg="red")
                self.scan_entry.delete(0, tk.END)
                self.scan_entry.focus()
                return
            
            # Check if panel type is selected
            # Panel type is selected during export, not before scanning
            
            # Validate SerialNo - use database if available, otherwise workbook
            is_valid = False
            try:
                if self.use_database and self.serial_db:
                    # Use simple database (preferred method) - cached for performance
                    is_valid = self.serial_db.validate_serial(serial)
                elif self.workbook_path:
                    # Use workbook DATA sheet (fallback - may not exist)
                    # validate_serial now returns False if DATA sheet doesn't exist (no error)
                    is_valid = validate_serial(serial, self.workbook_path)
                else:
                    messagebox.showerror(
                        "No Data Source - ERROR CODE: DS001",
                        "No database or workbook available for barcode validation.\n\n"
                        "TROUBLESHOOTING:\n"
                        "1. Check if SerialDatabase is initialized (file: data/PALLETS/serial_database.xlsx)\n"
                        "2. Check if workbook exists (file: data/EXCEL/CURRENT.xlsx)\n"
                        "3. Use 'Import Data' button to import simulator data\n"
                        "4. Verify file permissions on PALLETS and EXCEL folders\n\n"
                        "If issue persists, check console for detailed error messages.",
                        parent=self.root
                    )
                    return
                
                if not is_valid:
                    # Data truly not found – give operator a choice to proceed with
                    # general theoretical values instead of hard-blocking the scan.
                    use_fallback = messagebox.askyesno(
                        "Data Not Found",
                        (
                            "Sun simulator data was not found for this panel.\n\n"
                            f"Serial number: '{serial}'\n\n"
                            "Select 'Yes' to continue and use general theoretical "
                            "values for this panel.\n"
                            "Select 'No' to cancel and rescan or update the data."
                        ),
                        parent=self.root
                    )

                    if not use_fallback:
                        # User chose not to proceed with synthetic data
                        self.scan_entry.delete(0, tk.END)
                        self.scan_entry.focus()
                        if self.status_label:
                            self.status_label.config(text=f"Error: {serial} not found", fg="red")
                        return

                    # Optional: track that this serial used fallback, for potential
                    # logging or display elsewhere.
                    if not hasattr(self, "_fallback_serials"):
                        self._fallback_serials = set()
                    self._fallback_serials.add(serial)
            except FileNotFoundError as e:
                messagebox.showerror(
                    "Workbook Error - ERROR CODE: WB001",
                    f"Workbook file not found.\n\n"
                    f"TROUBLESHOOTING:\n"
                    f"1. Expected location: data/EXCEL/CURRENT.xlsx\n"
                    f"2. Check if EXCEL folder exists in project root\n"
                    f"3. Verify file permissions\n"
                    f"4. Try using 'Import Data' to ensure workbook is created\n\n"
                    f"Error details: {str(e)}\n"
                    f"Expected path: {self.workbook_path if self.workbook_path else 'Not set'}",
                    parent=self.root
                )
                return
            except PermissionError as e:
                messagebox.showerror(
                    "Workbook Locked - ERROR CODE: WB002",
                    f"Excel workbook is open or locked.\n\n"
                    f"TROUBLESHOOTING:\n"
                    f"1. Close all Excel windows that have the workbook open\n"
                    f"2. Check if another instance of Pallet Manager is running\n"
                    f"3. Verify file permissions on: {self.workbook_path if self.workbook_path else 'workbook file'}\n"
                    f"4. On Windows: Check Task Manager for Excel processes\n"
                    f"5. On macOS: Check Activity Monitor for Excel processes\n\n"
                    f"Error details: {str(e)}",
                    parent=self.root
                )
                return
            except Exception as e:
                # Handle any other errors gracefully
                error_msg = str(e)
                if "DATA sheet" in error_msg:
                    # DATA sheet is optional - just show a warning
                    messagebox.showwarning(
                        "Workbook Note",
                        "Workbook does not have a DATA sheet.\n\n"
                        "Using SerialDatabase for validation instead.\n\n"
                        "This is normal if you're using the SerialDatabase feature.",
                        parent=self.root
                    )
                    # Try database validation instead
                    if self.use_database and self.serial_db:
                        is_valid = self.serial_db.validate_serial(serial)
                        if not is_valid:
                            messagebox.showerror(
                                "Invalid Barcode",
                                f"Serial number '{serial}' not found in database.\n\n"
                                "Please check the barcode and try again.\n\n"
                                "If this is a new panel, import the simulator data first.",
                                parent=self.root
                            )
                            self.scan_entry.delete(0, tk.END)
                            self.scan_entry.focus()
                            if self.status_label:
                                self.status_label.config(text=f"Error: {serial} not found", fg="red")
                            return
                    else:
                        messagebox.showerror(
                            "No Data Source",
                            "No database available and workbook has no DATA sheet.\n\n"
                            "Please import simulator data first using 'Import Data' button.",
                            parent=self.root
                        )
                        return
                else:
                    messagebox.showerror(
                        "Validation Error",
                        f"Error validating barcode: {e}",
                        parent=self.root
                    )
                    self.scan_entry.delete(0, tk.END)
                    self.scan_entry.focus()
                    return
            
            # Check for duplicate on current pallet
            if self.current_pallet and serial in self.current_pallet.get('serial_numbers', []):
                self._show_modal_error_dialog(
                    "Duplicate Barcode",
                    f"Serial number '{serial}' is already on this pallet.\n\n"
                    "Please scan a different barcode.",
                    error_type="warning"
                )
                self.scan_entry.delete(0, tk.END)
                self.scan_entry.focus()
                if self.status_label:
                    self.status_label.config(text=f"Duplicate: {serial}", fg="orange")
                return
            
            # Check if serial has been used on any pallet (current or completed)
            # Defer this check to avoid blocking UI (check current pallet first, then others)
            existing_pallet = None
            if self.pallet_manager:
                # Fast check: current pallet first (in-memory, instant)
                if self.current_pallet and serial in self.current_pallet.get('serial_numbers', []):
                    # Already handled above, but check anyway
                    pass
                else:
                    # Defer expensive check to after UI update
                    existing_pallet = self.pallet_manager.is_serial_on_any_pallet(serial, self.current_pallet)
            
            if existing_pallet:
                    pallet_num = existing_pallet.get('pallet_number')
                    completed = existing_pallet.get('completed_at')
                    is_current = existing_pallet.get('is_current', False)
                    
                    if is_current:
                        # This should have been caught by the first check, but handle it anyway
                        message = (
                            f"This barcode has already been added to this pallet.\n\n"
                            f"Pallet #{pallet_num}\n\n"
                            "Please scan a different barcode."
                        )
                    elif completed:
                        message = (
                            f"This barcode has already been added to a pallet.\n\n"
                            f"Pallet #{pallet_num} (completed {completed})\n\n"
                            "Please scan a different barcode."
                        )
                    else:
                        message = (
                            f"This barcode has already been added to a pallet.\n\n"
                            f"Pallet #{pallet_num}\n\n"
                            "Please scan a different barcode."
                        )
                    self._show_modal_error_dialog(
                        "Duplicate Barcode",
                        message,
                        error_type="warning"
                    )
                    self.scan_entry.delete(0, tk.END)
                    self.scan_entry.focus()
                    if self.status_label:
                        self.status_label.config(text=f"Already on Pallet #{pallet_num}", fg="orange")
                    return
            
            # Check if pallet is already full before adding
            if self.current_pallet:
                current_count = len(self.current_pallet.get('serial_numbers', []))
                if current_count >= self.max_panels:
                    # Pallet is already full - show message and prevent adding
                    messagebox.showwarning(
                        "Pallet is Full",
                        f"Pallet #{self.current_pallet['pallet_number']} is already full ({self.max_panels} panels).\n\n"
                        "Please click 'Export Pallet' to export this pallet before scanning more barcodes.",
                        parent=self.root
                    )
                    # Clear entry and refocus for next scan
                    self.scan_entry.delete(0, tk.END)
                    self.scan_entry.focus()
                    if self.status_label:
                        self.status_label.config(
                            text=f"Pallet is full ({self.max_panels} panels)! Click 'Export Pallet' to export.", 
                            fg="orange"
                        )
                    return
            
            # Add valid SerialNo to pallet
            if not self.current_pallet:
                self.start_new_pallet()
            
            if self.pallet_manager:
                is_full = self.pallet_manager.add_serial(self.current_pallet, serial, self.max_panels)
            
            # Immediately enable export button (at least one panel now)
            # Do this BEFORE deferring UI update to ensure button is enabled right away
            count = len(self.current_pallet.get('serial_numbers', []))
            if self.export_button and count > 0:
                try:
                    self.export_button.config(state=tk.NORMAL, bg="#2E7D32", fg="black")
                    # Force immediate GUI update for button state
                    self.root.update_idletasks()
                except Exception as e:
                    # Log error but don't crash - button state update failed
                    print(f"Warning: Could not enable export button: {e}")
            
            # Defer UI update to next event loop (non-blocking)
            self.root.after_idle(self.update_slot_display)
            
            # Check if pallet is now full - show status message
            if is_full:
                self.show_action_buttons()
                # Don't auto-prompt - user must click Export Pallet button
                if self.status_label:
                    self.status_label.config(
                        text="Pallet is full! Click 'Export Pallet' to export.", 
                        fg="green"
                    )
            
            # Clear entry and refocus for next scan
            self.scan_entry.delete(0, tk.END)
            self.scan_entry.focus()
            
            # Update status
            if self.status_label:
                count = len(self.current_pallet.get('serial_numbers', []))
                self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black")
        except Exception as e:
            # Log error but keep app running
            print(f"ERROR in on_barcode_scanned: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Scan Error",
                    f"An error occurred while processing barcode:\n{e}\n\n"
                    "The application will continue running.\n"
                    "Please try scanning again.",
                    parent=self.root
                )
            except Exception:
                # If messagebox fails, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def update_slot_display(self, force_update=False):
        """
        Update the slot display widgets.
        Optimized for older hardware - batches GUI updates.
        Clears all existing widgets and rebuilds the display.
        
        Args:
            force_update: If True, force immediate GUI update (slower)
        """
        # Defer heavy widget operations to avoid blocking UI during barcode scanning
        if not force_update:
            # Use after_idle for non-blocking updates (defer to next event loop)
            self.root.after_idle(lambda: self._update_slot_display_impl())
            return
        
        # Force update - do it immediately
        self._update_slot_display_impl()
    
    def _update_slot_display_impl(self):
        """Internal implementation of slot display update (actual work happens here)"""
        # Preserve scroll position before clearing widgets
        scroll_position = None
        if self.slots_canvas:
            try:
                # Get current scroll position (yview returns tuple like (0.0, 1.0))
                scroll_position = self.slots_canvas.yview()
            except Exception:
                pass  # If we can't get scroll position, continue without preserving it

        # Clear existing slot widgets completely
        for widget in self.slot_widgets:
            try:
                widget.destroy()
            except Exception:
                pass  # Widget may already be destroyed
        self.slot_widgets = []

        # Clear the scrollable frame completely
        if self.slots_scrollable:
            for widget in self.slots_scrollable.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass
        
        if not self.slots_scrollable:
            # Update scroll region even if empty
            if self.slots_canvas:
                self.slots_canvas.configure(scrollregion=self.slots_canvas.bbox("all"))
            return
        
        # Get serials from current pallet, or empty list if no pallet
        serials = self.current_pallet.get('serial_numbers', []) if self.current_pallet else []
        count = len(serials)
        
        # Optimize: Only create widgets up to max panels (already limited)
        # Create slot widget for each position (1 to max_panels)
        for slot_num in range(1, self.max_panels + 1):
            slot_frame = tk.Frame(self.slots_scrollable, relief=tk.RIDGE, borderwidth=1)
            slot_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Slot number label
            slot_label = tk.Label(slot_frame, text=f"[{slot_num}]", 
                                 width=5, font=("Arial", 10, "bold"))
            slot_label.pack(side=tk.LEFT, padx=5)
            
            # Serial number or empty indicator
            if slot_num <= len(serials):
                serial = serials[slot_num - 1]
                serial_label = tk.Label(slot_frame, text=serial, 
                                       width=25, anchor='w', font=("Arial", 10))
                serial_label.pack(side=tk.LEFT, padx=5)
                
                # Remove button - use serial number instead of index to avoid index shift issues
                # This ensures the correct item is removed even if list changes
                remove_btn = tk.Button(slot_frame, text="Remove", width=8,
                                     command=lambda s=serial: self.remove_serial_by_value(s),
                                     font=("Arial", 9))
                remove_btn.pack(side=tk.RIGHT, padx=5)
            else:
                # Empty slot
                empty_label = tk.Label(slot_frame, text="(empty)", 
                                      width=25, anchor='w', 
                                      font=("Arial", 10), fg="gray")
                empty_label.pack(side=tk.LEFT, padx=5)
            
            self.slot_widgets.append(slot_frame)
        
        # Update canvas scroll region and restore scroll position immediately
        if self.slots_canvas:
            try:
                # Update scroll region first
                self.slots_canvas.configure(scrollregion=self.slots_canvas.bbox("all"))

                # Restore scroll position if we saved it, otherwise scroll to top
                if scroll_position is not None:
                    try:
                        # Try to restore the previous scroll position
                        self.slots_canvas.yview_moveto(scroll_position[0])
                    except Exception:
                        # If restoring fails, scroll to top as fallback
                        self.slots_canvas.yview_moveto(0)
                else:
                    # No saved position, scroll to top
                    self.slots_canvas.yview_moveto(0)
            except Exception:
                # Ignore errors during scroll update - scroll to top as final fallback
                try:
                    self.slots_canvas.yview_moveto(0)
                except Exception:
                    pass  # Ignore all scroll errors
        
        # Update slot count status and export button state
        if self.status_label:
            self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black")
        
        # Enable/disable export button based on pallet content
        if self.export_button:
            try:
                if count > 0:
                    self.export_button.config(state=tk.NORMAL, bg="#2E7D32", fg="black")
                    # GUI will update naturally on next event loop
                else:
                    self.export_button.config(state=tk.DISABLED, bg="#757575", fg="black")
            except Exception as e:
                # Log error but don't crash - button state update failed
                print(f"Warning: Could not update export button state: {e}")
                import traceback
                traceback.print_exc()
    
    def remove_serial(self, slot_index: int):
        """Remove serial from specific slot by index (legacy method)"""
        if not self.current_pallet or not self.pallet_manager:
            return
        
        if self.pallet_manager.remove_serial(self.current_pallet, slot_index):
            self.update_slot_display()
            
            # Update export button state
            count = len(self.current_pallet.get('serial_numbers', []))
            if self.export_button:
                if count == 0:
                    self.export_button.config(state=tk.DISABLED)
                else:
                    self.export_button.config(state=tk.NORMAL)
            
            # Hide action buttons if pallet is no longer full
            if count < self.max_panels:
                self.hide_action_buttons()
            
            # Refocus scan entry
            if self.scan_entry:
                self.scan_entry.focus()
    
    def remove_serial_by_value(self, serial: str):
        """Remove serial by value (more reliable than index-based removal)"""
        try:
            if not self.current_pallet or not self.pallet_manager:
                return
            
            serials = self.current_pallet.get('serial_numbers', [])
            if serial not in serials:
                return  # Serial not found
            
            # Find and remove by value
            serials.remove(serial)
            self.pallet_manager.save_history()
            self.update_slot_display()
            
            # Update export button state
            count = len(serials)
            if self.export_button:
                if count == 0:
                    self.export_button.config(state=tk.DISABLED)
                else:
                    self.export_button.config(state=tk.NORMAL)
            
            # Hide action buttons if pallet is no longer full
            if count < self.max_panels:
                self.hide_action_buttons()
            
            # Refocus scan entry
            if self.scan_entry:
                self.scan_entry.focus()
        except Exception as e:
            # Log error but keep app running
            print(f"ERROR in remove_serial_by_value: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Remove Error",
                    f"An error occurred while removing serial:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                # If messagebox fails, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")
        except ValueError:
            # Serial not in list (shouldn't happen, but handle gracefully)
            pass
    
    def _prompt_export_on_full(self):
        """Show status when pallet is full (no longer auto-prompts)"""
        # This method is kept for compatibility but no longer shows a dialog
        # User must manually click Export Pallet button
        pass
    
    def show_action_buttons(self):
        """Show action buttons when pallet is full"""
        # Clear existing buttons
        for widget in self.action_frame.winfo_children():
            widget.destroy()
        
        # Full pallet message
        msg_label = tk.Label(self.action_frame, text="Pallet is full!", 
                           font=("Arial", 12, "bold"), fg="orange")
        msg_label.pack(pady=5)
        
        # Update status
        if self.status_label:
            self.status_label.config(text="Pallet is full! Click Export Pallet button above.", 
                                   fg="orange", font=("Arial", 10, "bold"))
    
    def hide_action_buttons(self):
        """Hide action buttons"""
        for widget in self.action_frame.winfo_children():
            widget.destroy()
        
        # Update status back to normal
        if self.current_pallet and self.status_label:
            count = len(self.current_pallet.get('serial_numbers', []))
            self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black", 
                                   font=("Arial", 10))
    
    def export_pallet(self):
        """Export pallet to Excel and save to history"""
        # Removed DEBUG prints for performance
        
        # Check for required components with specific error messages
        if not self.current_pallet:
            messagebox.showerror("Error", "No pallet to export.\n\nPlease scan some barcodes first.", 
                               parent=self.root)
            return
        
        if not self.pallet_exporter:
            # Try to find workbook if not already found
            if not self.workbook_path:
                try:
                    project_root = get_base_dir()
                    excel_dir = project_root / "EXCEL"
                    current_workbook = excel_dir / "CURRENT.xlsx"
                    
                    # Try to find workbook
                    self.workbook_path = find_pallet_workbook(excel_dir, current_workbook)
                    
                    # If still not found, try BUILD files
                    if not self.workbook_path:
                        build_files = list(excel_dir.glob("BUILD*.xlsx"))
                        if build_files:
                            self.workbook_path = max(build_files, key=lambda p: p.stat().st_mtime)
                except Exception as e:
                    print(f"Error finding workbook: {e}")
            
            # Try to initialize pallet_exporter if workbook is available
            if self.workbook_path and self.workbook_path.exists():
                try:
                    # Get project root from workbook path or use current directory
                    project_root = self.workbook_path.parent.parent if self.workbook_path.parent.name == "EXCEL" else get_base_dir()
                    export_dir = project_root / "PALLETS"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    self.pallet_exporter = PalletExporter(self.workbook_path, export_dir, self.serial_db)
                except Exception as e:
                    messagebox.showerror("Error", 
                                       f"Cannot export: Failed to initialize exporter.\n\n"
                                       f"Error: {e}\n\n"
                                       "Please check that the workbook in EXCEL folder is valid.",
                                       parent=self.root)
                    return
            else:
                # Provide helpful error message with what we looked for
                project_root = get_base_dir()
                excel_dir = project_root / "EXCEL"
                current_workbook = excel_dir / "CURRENT.xlsx"
                build_files = list(excel_dir.glob("BUILD*.xlsx")) if excel_dir.exists() else []
                
                error_msg = "Cannot export: Workbook not found.\n\n"
                error_msg += f"Looked in: {excel_dir}\n\n"
                if not excel_dir.exists():
                    error_msg += "EXCEL folder does not exist.\n"
                elif not current_workbook.exists() and not build_files:
                    error_msg += "No workbook files found.\n"
                    error_msg += "Expected: CURRENT.xlsx or BUILD*.xlsx files\n"
                else:
                    error_msg += f"Found {len(build_files)} BUILD file(s) but couldn't access them.\n"
                
                error_msg += "\nPlease ensure there is a workbook in the EXCEL folder."
                messagebox.showerror("Error", error_msg, parent=self.root)
                return
        
        if not self.pallet_manager:
            messagebox.showerror("Error", "Cannot export: Internal error (pallet manager not initialized).", 
                               parent=self.root)
            return
        
        # Check if pallet has any serial numbers
        count = len(self.current_pallet.get('serial_numbers', []))
        if count == 0:
            messagebox.showerror(
                "Empty Pallet",
                "Cannot export an empty pallet.\n\n"
                "Please add at least one panel before exporting.",
                parent=self.root
            )
            return
        
        # Show panel type selection dialog
        dialog_result = self._select_panel_type_dialog(
            self.current_pallet.get('pallet_number') if self.current_pallet else None
        )
        if not dialog_result:
            # User cancelled panel type selection
            return
        
        panel_type, pallet_number, customer_display_name = dialog_result
        
        # Update pallet number if user changed it
        if self.current_pallet and self.current_pallet.get('pallet_number') != pallet_number:
            self.current_pallet['pallet_number'] = pallet_number
            # Update display
            if self.pallet_label:
                self.pallet_label.config(text=f"#{pallet_number}")
        
        # Get customer object
        customer = self.customer_manager.get_customer_by_name(customer_display_name)
        if not customer:
            messagebox.showerror(
                "Customer Not Found - ERROR CODE: CU001",
                f"Customer '{customer_display_name}' not found in customer database.\n\n"
                "TROUBLESHOOTING:\n"
                "1. Verify customer exists in: data/CUSTOMERS/customers.xlsx\n"
                "2. Check if customer was recently deleted\n"
                "3. Use Customer Management button to add a new customer\n"
                "4. Try refreshing the customer list in Customer Management\n\n"
                f"Searched for: '{customer_display_name}'\n"
                f"Customer file: data/CUSTOMERS/customers.xlsx",
                parent=self.root
            )
            return
        
        # Determine template workbook based on current capacity (25/26/30/35)
        template_workbook = self._get_template_workbook_for_capacity()

        # Update active customer display (do this AFTER export to avoid blocking)
        self.active_customer_display = customer_display_name
        result = messagebox.askyesnocancel(
            "Export Pallet",
            f"Export Pallet #{pallet_number}?\n\n"
            f"Panel Type: {panel_type}\n"
            f"Customer: {customer_display_name}\n"
            f"Serial Numbers: {count}/{self.max_panels}\n\n"
            "Yes = Export pallet\n"
            "No = Cancel export\n"
            "Cancel = Close dialog",
            parent=self.root
        )
        
        # Handle cancellation
        if result is None:  # Cancel button clicked
            return
        if result is False:  # No button clicked
            return
        
        # User confirmed export (result is True)
        try:
            # Disable export button during export to prevent double-clicks
            if self.export_button:
                self.export_button.config(state=tk.DISABLED)
            
            # Update status to show export in progress
            if self.status_label:
                self.status_label.config(text="Exporting pallet...", fg="blue")
            # GUI will update naturally, no need to force
            
            # Create and show progress bar dialog
            progress_window = self._create_progress_dialog()
            # Force the progress window to be visible (only once)
            progress_window.update()
            
            try:
                # Export pallet to Excel file (pass selected panel type, customer, progress callback, and template)
                export_result = self.pallet_exporter.export_pallet(
                    self.current_pallet,
                    panel_type,
                    customer=customer,
                    progress_callback=lambda stage, percent: self._update_progress(
                        progress_window, stage, percent
                    ),
                    template_workbook=template_workbook,
                )
                # Unpack export path and datetime
                export_path, export_datetime = export_result
            finally:
                # Always close progress window
                try:
                    progress_window.destroy()
                except Exception:
                    pass
            
            # Store customer information in pallet before saving to history
            if customer:
                self.current_pallet['customer'] = {
                    'name': customer['name'],
                    'business': customer['business'],
                    'display_name': customer_display_name
                }
            
            # Save to history - pass export_datetime for consistency
            success = self.pallet_manager.complete_pallet(self.current_pallet, export_path, export_datetime)
            
            if not success:
                messagebox.showerror(
                    "Save Error",
                    "Pallet exported but failed to save to history.\n\n"
                    f"Export file: {export_path.name}",
                    parent=self.root
                )
                return
            
            # Clear the pallet BEFORE showing message box (prevents UI lag)
            pallet_num = self.current_pallet['pallet_number']
            file_name = export_path.name
            self.current_pallet = None
            
            # Update UI immediately (don't wait for message box)
            self.hide_action_buttons()
            self.update_slot_display(force_update=False)  # Don't force - let it update async
            
            if self.status_label:
                self.status_label.config(text="Pallet exported. Ready for next pallet.", fg="green")
            if self.export_button:
                self.export_button.config(state=tk.DISABLED)
            if self.pallet_label:
                self.pallet_label.config(text="#--")
            
            # Force UI update before showing message box
            self.root.update_idletasks()
            
            # Show success message first (non-blocking)
            messagebox.showinfo(
                "Pallet Exported",
                f"Pallet #{pallet_num} exported successfully!\n\n"
                f"File: {file_name}",
                parent=self.root
            )
            
            # Update customer menu asynchronously (after message box is dismissed)
            # This prevents UI freezing
            def update_customer_menu_async():
                if self.active_customer_var and self.active_customer_display:
                    try:
                        # Just set the customer directly - don't validate menu
                        if self.active_customer_var.get() != self.active_customer_display:
                            self.active_customer_var.set(self.active_customer_display)
                    except Exception as e:
                        print(f"Warning: Could not update customer menu: {e}")
            
            # Schedule menu update for after message box closes (50ms delay)
            self.root.after(50, update_customer_menu_async)
            
        except FileNotFoundError as e:
            messagebox.showerror(
                "Export Error",
                f"Workbook not found:\n{e}\n\n"
                "Please check that the reference workbook exists in the EXCEL folder.",
                parent=self.root
            )
        except PermissionError as e:
            messagebox.showerror(
                "Export Error",
                f"Workbook is locked or open:\n{e}\n\n"
                "Please close Excel and try again.",
                parent=self.root
            )
        except ValueError as e:
            messagebox.showerror(
                "Export Error",
                f"Invalid pallet data:\n{e}\n\n"
                "Please ensure the pallet has at least one serial number.",
                parent=self.root
            )
        except KeyError as e:
            messagebox.showerror(
                "Export Error",
                f"Required sheet or column not found in workbook:\n{e}\n\n"
                "Please ensure the 'PALLET SHEET' and 'DATA' sheets exist and have expected headers.",
                parent=self.root
            )
        except RuntimeError as e:
            messagebox.showerror(
                "Export Error",
                f"Export operation failed:\n{e}\n\n"
                "Please check the error message and try again.",
                parent=self.root
            )
        except Exception as e:
            # Log full error details for debugging
            print(f"ERROR in export_pallet: {e}")
            import traceback
            traceback.print_exc()
            
            messagebox.showerror(
                "Export Error",
                f"An unexpected error occurred during export:\n{e}\n\n"
                "Please check the console output for more details.\n"
                "The application will continue running.",
                parent=self.root
            )
        finally:
            # Restore status and enable button (only if pallet has content)
            try:
                self.update_status()
                if self.export_button and self.current_pallet:
                    count = len(self.current_pallet.get('serial_numbers', []))
                    if count > 0:
                        self.export_button.config(state=tk.NORMAL)
                    else:
                        self.export_button.config(state=tk.DISABLED)
            except Exception:
                pass  # Ignore errors during cleanup
    
    def open_export_folder(self):
        """Open the export folder in file explorer"""
        if not self.pallet_exporter:
            return
        
        # Get current date-based export directory
        export_dir = self.pallet_exporter._get_export_dir()
        
        try:
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['explorer', str(export_dir.absolute())], check=False)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(export_dir.absolute())], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', str(export_dir.absolute())], check=False)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not open export folder:\n{e}",
                parent=self.root
            )
    
    def restart_application(self):
        """Restart the entire application"""
        result = messagebox.askyesno(
            "Restart Application",
            "Are you sure you want to restart the application?\n\n"
            "All unsaved data will be lost.\n"
            "Current pallet will be cleared.",
            parent=self.root
        )
        
        if result:
            try:
                # Get the script path
                script_path = Path(__file__).absolute()
                
                # Restart the application
                if platform.system() == 'Windows':
                    # Windows
                    os.execv(sys.executable, [sys.executable, str(script_path)])
                else:
                    # macOS/Linux
                    os.execv(sys.executable, [sys.executable, str(script_path)])
            except Exception as e:
                messagebox.showerror(
                    "Restart Error",
                    f"Failed to restart application:\n{e}\n\n"
                    "Please close and reopen the application manually.",
                    parent=self.root
                )
    
    def refresh_application(self):
        """Refresh the application display and reload data"""
        try:
            # Update slot display
            self.update_slot_display(force_update=True)
            
            # Refresh status
            if self.current_pallet:
                count = len(self.current_pallet.get('serial_numbers', []))
                if self.status_label:
                    self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black")
                
                # Update export button state
                if self.export_button:
                    if count > 0:
                        self.export_button.config(state=tk.NORMAL, bg="#2E7D32", fg="black")
                    else:
                        self.export_button.config(state=tk.DISABLED, bg="#757575", fg="black")
            else:
                if self.status_label:
                    self.status_label.config(text="Ready to scan", fg="black")
            
            # Refresh database count
            if self.serial_db:
                db_count = self.serial_db.get_serial_count()
                if self.status_label:
                    current_text = self.status_label.cget("text")
                    if "Database:" not in current_text:
                        self.status_label.config(
                            text=f"{current_text} | Database: {db_count} SerialNos",
                            fg="black"
                        )
            
            # Refresh pallet number display
            if self.current_pallet and self.pallet_label:
                self.pallet_label.config(text=f"#{self.current_pallet['pallet_number']}")
            
            # Force GUI update
            self.root.update_idletasks()
            
            messagebox.showinfo(
                "Refresh Complete",
                "Application display has been refreshed.",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Refresh Error",
                f"Failed to refresh application:\n{e}",
                parent=self.root
            )
    
    def start_new_pallet(self):
        """Start a new empty pallet - maintains panel type from previous pallet"""
        try:
            if not self.pallet_manager:
                messagebox.showerror(
                    "Error",
                    "PalletManager not initialized. Cannot create new pallet.",
                    parent=self.root
                )
                return
            
            try:
                # Create new pallet
                self.current_pallet = self.pallet_manager.create_new_pallet()
            except Exception as e:
                print(f"ERROR in start_new_pallet (create): {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror(
                    "Error",
                    f"Failed to create new pallet:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
                return
            
            # Update pallet number display
            if self.pallet_label:
                self.pallet_label.config(text=f"#{self.current_pallet['pallet_number']}")
            
            # Clear slot display
            self.update_slot_display()
            
            # Reset status message
            if self.status_label:
                self.status_label.config(text="Ready to scan", fg="black", font=("Arial", 10))
            
            # Disable export button (empty pallet)
            if self.export_button:
                self.export_button.config(state=tk.DISABLED)
            
            # Hide action buttons
            self.hide_action_buttons()
            
            # Refocus scan entry for next scan
            if self.scan_entry:
                self.scan_entry.focus()
        except Exception as e:
            # Log error but keep app running
            print(f"ERROR in start_new_pallet: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Error",
                    f"An error occurred while starting new pallet:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                # If messagebox fails, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def _confirm_new_pallet(self):
        """Confirm before starting a new pallet if current has data"""
        if not self.current_pallet:
            # No current pallet, just start new one (with confirmation)
            result = messagebox.askyesnocancel(
                "Start New Pallet",
                "Start a new pallet?\n\n"
                "Yes = Start new pallet\n"
                "No = Cancel\n"
                "Cancel = Close dialog",
                parent=self.root
            )
            if result is True:
                self.start_new_pallet()
            return
        
        count = len(self.current_pallet.get('serial_numbers', []))
        if count == 0:
            # Empty pallet - still ask for confirmation
            result = messagebox.askyesnocancel(
                "Start New Pallet",
                "Current pallet is empty.\n\n"
                "Start a new pallet?\n\n"
                "Yes = Start new pallet\n"
                "No = Cancel\n"
                "Cancel = Close dialog",
                parent=self.root
            )
            if result is True:
                self.start_new_pallet()
            return
        
        # Pallet has barcodes - offer options
        if count < self.max_panels:
            # Not full - offer to export or discard
            result = messagebox.askyesnocancel(
                "Pallet Not Full",
                f"Current pallet has {count} serial numbers (not full).\n\n"
                "What would you like to do?\n\n"
                "Yes = Export current pallet, then start new\n"
                "No = Discard current pallet, start new\n"
                "Cancel = Keep current pallet (close dialog)",
                parent=self.root
            )
            
            if result is True:
                # Export first, then start new
                if self.pallet_exporter and self.pallet_manager:
                    # Show panel type selection dialog
                    dialog_result = self._select_panel_type_dialog(self.current_pallet.get('pallet_number') if self.current_pallet else None)
                    if not dialog_result:
                        # User cancelled panel type selection
                        return
                    
                    panel_type, pallet_number, customer_display_name = dialog_result
                    
                    # Update pallet number if user changed it
                    if self.current_pallet and self.current_pallet.get('pallet_number') != pallet_number:
                        self.current_pallet['pallet_number'] = pallet_number
                        # Update display
                        if self.pallet_label:
                            self.pallet_label.config(text=f"#{pallet_number}")
                    
                    # Get customer object
                    customer = self.customer_manager.get_customer_by_name(customer_display_name)
                    if not customer:
                        messagebox.showerror(
                            "Customer Not Found",
                            f"Customer '{customer_display_name}' not found.\n\n"
                            "Please select a valid customer or add one in Customer Management.",
                            parent=self.root
                        )
                        return
                    
                    # Determine template workbook based on current capacity (25/26/30/35)
                    template_workbook = self._get_template_workbook_for_capacity()
                    
                    try:
                        export_result = self.pallet_exporter.export_pallet(
                            self.current_pallet,
                            panel_type,
                            customer=customer,
                            template_workbook=template_workbook,
                        )
                        export_path, export_datetime = export_result

                        # Store customer information in pallet before saving to history
                        if customer:
                            self.current_pallet['customer'] = {
                                'name': customer['name'],
                                'business': customer['business'],
                                'display_name': customer_display_name
                            }

                        success = self.pallet_manager.complete_pallet(self.current_pallet, export_path, export_datetime)
                        if success:
                            messagebox.showinfo(
                                "Pallet Exported",
                                f"Pallet #{self.current_pallet['pallet_number']} exported successfully!\n\n"
                                f"File: {export_path.name}",
                                parent=self.root
                            )
                            self.start_new_pallet()
                        else:
                            messagebox.showerror(
                                "Export Failed",
                                "Failed to save pallet to history.",
                                parent=self.root
                            )
                    except Exception as e:
                        messagebox.showerror(
                            "Export Error",
                            f"Failed to export pallet:\n{e}",
                            parent=self.root
                        )
                else:
                    messagebox.showerror(
                        "Cannot Export",
                        "Export functionality not available.\n\n"
                        "Workbook not found or exporter not initialized.",
                        parent=self.root
                    )
            elif result is False:
                # Discard and start new
                self.start_new_pallet()
            # If result is None (Cancel), do nothing
        else:
            # Pallet is full - should use export button instead, but allow if they insist
            result = messagebox.askyesno(
                "Pallet is Full",
                f"Current pallet is full ({self.max_panels} serial numbers).\n\n"
                "You should use 'Export & Save Pallet' button instead.\n\n"
                "Start new pallet anyway (current pallet will be lost)?",
                parent=self.root
            )
            if result:
                self.start_new_pallet()
    
    def import_data(self, event=None):
        """Import simulator data into the database"""
        try:
            if not self.serial_db:
                messagebox.showerror("Error", "SerialDatabase not initialized", 
                                   parent=self.root)
                return
            
            # Update status to show we're responding
            if self.status_label:
                self.status_label.config(text="Opening file dialog...", fg="blue")
                self.root.update_idletasks()
            
            # Open file dialog asynchronously to avoid blocking UI (reduced delay)
            self.root.after(10, self._open_import_dialog)
        except Exception as e:
            print(f"ERROR in import_data: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Import Error",
                    f"An error occurred:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def _open_import_dialog(self):
        """Open file dialog for import (called asynchronously)"""
        try:
            # Always open file selector - start in SUN SIMULATOR DATA if it exists, otherwise user's home
            project_root = get_base_dir()
            sun_sim_dir = project_root / "SUN SIMULATOR DATA"
            
            # Determine initial directory
            if sun_sim_dir.exists() and sun_sim_dir.is_dir():
                initial_dir = str(sun_sim_dir.absolute())
            else:
                # Use user's home directory as fallback
                initial_dir = str(Path.home())
            
            # Allow multiple file selection
            file_paths = filedialog.askopenfilenames(
                title="Select Simulator Export Files (CSV or Excel) - Hold Ctrl/Cmd to select multiple",
                filetypes=[
                    ("All Excel files", "*.xlsx;*.xlsm;*.xls;*.xlsb"),
                    ("All compatible files", "*.xlsx;*.xlsm;*.xls;*.xlsb;*.csv"),
                    ("Excel Workbook", "*.xlsx"),
                    ("Excel Macro-Enabled", "*.xlsm"),
                    ("Excel 97-2003", "*.xls"),
                    ("Excel Binary", "*.xlsb"),
                    ("CSV files", "*.csv"),
                    ("All files", "*.*")
                ],
                initialdir=initial_dir,
                parent=self.root
            )
            
            if not file_paths:
                return
            
            # Process files asynchronously to prevent UI blocking
            self.root.after(50, self._process_import_files, file_paths)
        except Exception as e:
            print(f"ERROR in _open_import_dialog: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Import Error",
                    f"An error occurred while opening file dialog:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def _process_import_files(self, file_paths):
        """Process import files (called asynchronously)"""
        try:
            # Process multiple files
            total_imported = 0
            total_updated = 0
            all_errors = []
            successful_files = []
            failed_files = []
            
            # Show progress if multiple files
            if len(file_paths) > 1:
                if self.status_label:
                    self.status_label.config(text=f"Importing {len(file_paths)} files...", fg="blue")
                # GUI will update naturally
            
            # Process each file
            for idx, file_path in enumerate(file_paths, 1):
                import_file = Path(file_path)
                
                if not import_file.exists():
                    failed_files.append((import_file.name, "File not found"))
                    continue
                
                # Update status for each file
                if len(file_paths) > 1 and self.status_label:
                    self.status_label.config(
                        text=f"Importing file {idx}/{len(file_paths)}: {import_file.name}...", 
                        fg="blue"
                    )
                    # Update UI every 3 files instead of every file (reduce CPU)
                    if idx % 3 == 0:
                        self.root.update_idletasks()
                
                # Ensure database is initialized before importing
                if hasattr(self.serial_db, '_init_deferred') and self.serial_db._init_deferred:
                    try:
                        self.serial_db._ensure_database()
                        self.serial_db._ensure_master_data_sheet()
                        self.serial_db._init_deferred = False
                    except Exception as e:
                        messagebox.showerror(
                            "Database Error",
                            f"Could not initialize serial database:\n{e}\n\n"
                            f"Expected location: data/PALLETS/serial_database.xlsx\n\n"
                            "Please ensure the PALLETS folder exists and is writable.",
                            parent=self.root
                        )
                        return
                
                # Import the file with validation (same as command-line tool)
                try:
                    # First parse and validate records like the command-line tool does
                    if import_sunsim:
                        # Set up logging paths (same as tool_runner.py)
                        from app.path_utils import get_base_dir, resolve_project_path
                        base_dir = get_base_dir()
                        import_sunsim.SCRIPT_DIR = base_dir
                        import_sunsim.EXCEL_DIR = resolve_project_path("data/EXCEL")
                        import_sunsim.LOGS_DIR = resolve_project_path("data/LOGS")
                        import_sunsim.ARCHIVE_DIR = resolve_project_path("data/ARCHIVE/processed_files")

                        # Create logger for validation
                        gui_logger = import_sunsim.setup_logging()

                        if import_file.suffix.lower() == '.csv':
                            records = import_sunsim.parse_csv_file(import_file, gui_logger)
                        else:
                            records = import_sunsim.parse_xlsx_file(import_file, gui_logger)

                        if not records:
                            failed_files.append((import_file.name, "No records parsed from file"))
                            continue

                        # Validate records (same as command-line tool)
                        valid_records = []
                        for record_idx, record in enumerate(records, 1):
                            is_valid, warnings = import_sunsim.validate_record(
                                record, gui_logger, row_num=record_idx, verbose=False, exclude_out_of_range=False
                            )
                            if is_valid:
                                valid_records.append(record)

                        if not valid_records:
                            failed_files.append((import_file.name, "No valid records found after validation"))
                            continue

                        # Deduplicate records
                        file_mtime = import_file.stat().st_mtime
                        deduplicated = import_sunsim.deduplicate_records(valid_records, file_mtime, gui_logger)

                        # Import the validated, deduplicated records
                        imported, updated, errors = self.serial_db.import_simulator_file_validated(deduplicated, import_file)
                    else:
                        # Fallback to original method if import_sunsim not available
                        imported, updated, errors = self.serial_db.import_simulator_file(import_file)

                    total_imported += imported
                    total_updated += updated
                    all_errors.extend(errors)
                    successful_files.append((import_file.name, imported, updated))

                    # Lightweight UI update every 3 files (reduce CPU usage by ~67%)
                    if idx % 3 == 0:
                        self.root.update_idletasks()
                except FileNotFoundError as e:
                    failed_files.append((import_file.name, f"File not found: {e}"))
                except PermissionError as e:
                    failed_files.append((import_file.name, f"File is locked or permission denied: {e}"))
                except Exception as e:
                    failed_files.append((import_file.name, str(e)))
                    all_errors.append(f"{import_file.name}: {e}")
            
            # Build summary message
            message = f"Import complete!\n\n"
            
            if len(file_paths) > 1:
                message += f"Files processed: {len(file_paths)}\n"
                message += f"Successful: {len(successful_files)}\n"
                if failed_files:
                    message += f"Failed: {len(failed_files)}\n"
                message += "\n"
            
            message += f"Total imported: {total_imported} new SerialNos\n"
            message += f"Total updated: {total_updated} existing SerialNos\n"
            message += f"Total in database: {self.serial_db.get_serial_count()}\n"
            
            # Show file-by-file results if multiple files
            if len(successful_files) > 1:
                message += "\nFile results:\n"
                for filename, imported, updated in successful_files:
                    message += f"  • {filename}: +{imported} new, {updated} updated\n"
            
            # Show failed files
            if failed_files:
                message += "\nFailed files:\n"
                for filename, error in failed_files:
                    message += f"  • {filename}: {error}\n"
            
            # Show errors
            if all_errors:
                message += f"\nErrors: {len(all_errors)}\n"
                for error in all_errors[:5]:  # Show first 5 errors
                    message += f"  • {error}\n"
                if len(all_errors) > 5:
                    message += f"  ... and {len(all_errors) - 5} more errors"
            
            messagebox.showinfo("Import Complete", message, parent=self.root)
            
            # Force cache refresh to ensure new serials are immediately available
            if self.serial_db:
                self.serial_db.invalidate_cache()
                self.serial_db._refresh_serial_cache()
            
            # Update status
            if self.status_label:
                self.status_label.config(
                    text=f"Database: {self.serial_db.get_serial_count()} SerialNos ready",
                    fg="green"
                )
            
            # Switch to database mode
            self.use_database = True
            
        except Exception as e:
            # Log full error but keep app running
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in import_data: {error_details}")  # Print to console for debugging
            try:
                messagebox.showerror(
                    "Import Error",
                    f"Failed to import file:\n{e}\n\n"
                    "Check console for details.\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                # If messagebox fails, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def restart_application(self):
        """Restart the entire application"""
        result = messagebox.askyesno(
            "Restart Application",
            "Are you sure you want to restart the application?\n\n"
            "All unsaved data will be lost.\n"
            "Current pallet will be cleared.",
            parent=self.root
        )
        
        if result:
            try:
                # Get the script path - handle both direct execution and module execution
                script_path = Path(__file__).absolute()
                
                # Check if we're running as a module (python -m app.pallet_builder_gui)
                # or directly (python app/pallet_builder_gui.py)
                if script_path.name == '__main__.py' or 'pallet_builder_gui.py' in str(script_path):
                    # Try to find the main entry point
                    app_dir = script_path.parent.parent
                    # Look for launcher scripts
                    if platform.system() == 'Windows':
                        launcher = app_dir / "Pallet Manager.bat"
                        if launcher.exists():
                            # Use batch file on Windows
                            subprocess.Popen([str(launcher)], cwd=str(app_dir))
                            self.root.quit()
                            return
                    else:
                        launcher = app_dir / "Pallet Manager.command"
                        if launcher.exists():
                            # Use command file on macOS/Linux
                            subprocess.Popen(['open', str(launcher)] if platform.system() == 'Darwin' 
                                           else [str(launcher)], cwd=str(app_dir))
                            self.root.quit()
                            return
                
                # Fallback: restart using Python module
                # Close current window first
                self.root.quit()
                self.root.destroy()
                
                # Restart the application
                os.execv(sys.executable, [sys.executable, '-m', 'app.pallet_builder_gui'])
            except Exception as e:
                messagebox.showerror(
                    "Restart Error",
                    f"Failed to restart application:\n{e}\n\n"
                    "Please close and reopen the application manually.",
                    parent=self.root
                )
    
    def refresh_application(self):
        """Refresh the application display and reload data"""
        try:
            # Update slot display
            self.update_slot_display(force_update=True)
            
            # Refresh status
            if self.current_pallet:
                count = len(self.current_pallet.get('serial_numbers', []))
                if self.status_label:
                    self.status_label.config(text=f"Slots: {count}/{self.max_panels}", fg="black")
                
                # Update export button state
                if self.export_button:
                    if count > 0:
                        self.export_button.config(state=tk.NORMAL, bg="#2E7D32", fg="black")
                    else:
                        self.export_button.config(state=tk.DISABLED, bg="#757575", fg="black")
            else:
                if self.status_label:
                    self.status_label.config(text="Ready to scan", fg="black")
            
            # Refresh database count
            if self.serial_db:
                db_count = self.serial_db.get_serial_count()
                if self.status_label:
                    current_text = self.status_label.cget("text")
                    if "Database:" not in current_text:
                        self.status_label.config(
                            text=f"{current_text} | Database: {db_count} SerialNos",
                            fg="black"
                        )
            
            # Refresh pallet number display
            if self.current_pallet and self.pallet_label:
                self.pallet_label.config(text=f"#{self.current_pallet['pallet_number']}")
            
            # Force GUI update
            self.root.update_idletasks()
            
            messagebox.showinfo(
                "Refresh Complete",
                "Application display has been refreshed.",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Refresh Error",
                f"Failed to refresh application:\n{e}",
                parent=self.root
            )
    
    def _create_progress_dialog(self):
        """Create a progress bar dialog for export operations"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Exporting Pallet...")
        progress_window.transient(self.root)
        progress_window.resizable(0, 0)  # Use 0 instead of False for Tk compatibility
        progress_window.config(bg="white")
        
        # Center the dialog
        progress_window.geometry("400x120")
        progress_window.update()  # Single update to get window size
        x = (progress_window.winfo_screenwidth() // 2) - (progress_window.winfo_width() // 2)
        y = (progress_window.winfo_screenheight() // 2) - (progress_window.winfo_height() // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        # Make modal AFTER positioning (ensures window is visible)
        progress_window.grab_set()
        
        # Main frame
        main_frame = tk.Frame(progress_window, padx=20, pady=20, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_label = tk.Label(main_frame, text="Preparing export...", 
                               font=("Arial", 10), fg="black", bg="white")
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_bar = ttk.Progressbar(main_frame, mode='determinate', length=350)
        progress_bar.pack()
        
        # Percent label
        percent_label = tk.Label(main_frame, text="0%", 
                               font=("Arial", 9), fg="gray", bg="white")
        percent_label.pack(pady=(5, 0))
        
        # Store references in window for updates
        progress_window.status_label = status_label
        progress_window.progress_bar = progress_bar
        progress_window.percent_label = percent_label
        
        return progress_window
    
    def _update_progress(self, progress_window, stage: str, percent: int):
        """Update progress bar with current stage and percentage"""
        try:
            if progress_window and progress_window.winfo_exists():
                # Update status text
                if hasattr(progress_window, 'status_label'):
                    progress_window.status_label.config(text=stage, fg="black")
                
                # Update progress bar
                if hasattr(progress_window, 'progress_bar'):
                    progress_window.progress_bar['value'] = percent
                
                # Update percent label
                if hasattr(progress_window, 'percent_label'):
                    progress_window.percent_label.config(text=f"{percent}%", fg="gray")
                
                # Only update every 10% to reduce CPU usage significantly
                if percent % 10 == 0 or percent == 100:
                    progress_window.update()  # Full update only at milestones
                # Skip intermediate updates entirely - reduces CPU by 90%
        except Exception:
            # Ignore errors during progress update (window might be closed)
            pass
    
    def show_settings(self):
        """Show customer management window (singleton behavior)"""
        # Check if customer management window already exists
        if self.customer_window:
            try:
                if self.customer_window.winfo_exists():
                    # Window exists, bring it to front
                    self.customer_window.lift()
                    self.customer_window.focus_force()
                    return
            except tk.TclError:
                # Window was destroyed, clear reference
                self.customer_window = None

        self.customer_window = dialog = tk.Toplevel(self.root)
        from app.version import get_version
        version = get_version()
        dialog.title(f"Customer Management - {version}")
        # Don't make it transient - let it be a separate window
        # dialog.transient(self.root)
        dialog.resizable(1, 1)  # Use 1 instead of True for Tk compatibility
        
        # Set window icon
        try:
            parent_icon = self.root.iconbitmap()
            if parent_icon:
                dialog.iconbitmap(parent_icon)
        except:
            pass
        
        # Detect dark mode and set appropriate colors
        is_dark = is_dark_mode()
        
        if is_dark:
            # Dark mode colors
            bg_main = "#2B2B2B"
            bg_section = "#3C3C3C"
            fg_text = "#E0E0E0"
            fg_label = "#B0B0B0"
            entry_bg = "#4A4A4A"
            entry_fg = "#FFFFFF"
            listbox_bg = "#3C3C3C"
            listbox_fg = "#E0E0E0"
            title_fg = "#64B5F6"
        else:
            # Light mode colors
            bg_main = "#F5F5F5"
            bg_section = "#F5F5F5"
            fg_text = "#333333"
            fg_label = "#333333"
            entry_bg = "white"
            entry_fg = "black"
            listbox_bg = "white"
            listbox_fg = "black"
            title_fg = "#1976D2"
        
        dialog.config(bg=bg_main)
        
        # Start with a reasonable size, then maximize
        dialog.geometry("800x700")
        
        # Maximize the window (platform-specific)
        try:
            if platform.system() == 'Windows':
                dialog.state('zoomed')
            elif platform.system() == 'Darwin':  # macOS
                # Manual maximization for macOS (more reliable than zoomed)
                dialog.update_idletasks()
                screen_width = dialog.winfo_screenwidth()
                screen_height = dialog.winfo_screenheight()
                # Leave small margin for dock/menu bar
                dialog.geometry(f"{screen_width-20}x{screen_height-100}+10+50")
            else:  # Linux
                try:
                    dialog.attributes('-zoomed', 1)
                except:
                    pass
        except Exception as e:
            print(f"Could not maximize Customer Management window: {e}")
            # Fallback to large fixed size if maximization fails
            dialog.geometry("1000x800+100+50")
        
        # Main container
        main_frame = tk.Frame(dialog, bg=bg_main)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Title
        title_label = tk.Label(main_frame, text="Customer Management", 
                              font=("Arial", 16, "bold"), bg=bg_main, fg=title_fg)
        title_label.pack(pady=(0, 20))
        
        # List of customers section
        list_section = tk.LabelFrame(main_frame, text=" Existing Customers ", 
                                     font=("Arial", 11, "bold"), bg=bg_section, fg=fg_text,
                                     relief=tk.GROOVE, bd=2)
        list_section.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        list_inner = tk.Frame(list_section, bg=bg_section)
        list_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Listbox with scrollbar and adaptive colors
        listbox_frame = tk.Frame(list_inner, bg=listbox_bg, bd=2, relief=tk.SUNKEN)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        customer_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, 
                                      font=("Arial", 11), height=10, bd=0,
                                      bg=listbox_bg, fg=listbox_fg, selectbackground="#2196F3",
                                      selectforeground="white")
        customer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=customer_listbox.yview)
        
        # Populate listbox
        def refresh_listbox():
            """Refresh customer listbox - does NOT update main menu"""
            try:
                # Force reload customers from Excel file (bypass cache)
                self.customer_manager.refresh_customers(force_reload=True)
                customer_listbox.delete(0, tk.END)
                for customer_name in self.customer_manager.get_customer_names():
                    customer_listbox.insert(tk.END, customer_name)
            except Exception as e:
                # Use the main window as parent to avoid crashes if dialog is closing
                messagebox.showerror("Error", f"Could not load customers:\n{e}", parent=self.root)
        
        # Show "Loading..." message initially
        customer_listbox.insert(0, "Loading customers...")
        customer_listbox.config(fg=fg_label)
        
        # Load customer list asynchronously after window is shown
        def load_async():
            refresh_listbox()
            customer_listbox.config(fg=listbox_fg)  # Restore normal text color
        
        dialog.after(10, load_async)
        
        def open_excel_file():
            """Open Excel file for manual editing"""
            self.customer_manager.open_excel_file()
            messagebox.showinfo(
                "Excel File Opened",
                "The customer Excel file has been opened.\n\n"
                "After making changes, click 'Refresh List' to update the dropdown menu.",
                parent=self.root
            )
        
        # Add/Edit Customer Section
        add_frame = tk.LabelFrame(main_frame, text=" Add / Edit Customer ", 
                                 font=("Arial", 11, "bold"), bg=bg_section, fg=fg_text,
                                 relief=tk.GROOVE, bd=2)
        add_frame.pack(fill=tk.X, pady=(0, 15))
        
        add_inner = tk.Frame(add_frame, bg=bg_section)
        add_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Track currently selected customer for editing (None = adding new)
        editing_customer = {"display_name": None}
        
        # Form fields
        fields = []
        field_labels = ["Name:", "Business:", "Address:", "City:", "State:", "Zip Code:"]
        field_vars = []
        
        for i, label in enumerate(field_labels):
            row = tk.Frame(add_inner, bg=bg_section)
            row.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(row, text=label, width=12, anchor=tk.E, 
                    font=("Arial", 11, "bold"), bg=bg_section, fg=fg_label).pack(side=tk.LEFT, padx=(0, 10))
            
            var = tk.StringVar()
            field_vars.append(var)
            entry = tk.Entry(row, textvariable=var, font=("Arial", 11), 
                           bd=2, relief=tk.SUNKEN, bg=entry_bg, fg=entry_fg)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fields.append(entry)
            
            # Add trace to enable/disable save button
            var.trace('w', lambda *args: check_fields_filled())
        
        # Button frame for save/clear buttons
        button_frame_form = tk.Frame(add_inner, bg=bg_section)
        button_frame_form.pack(pady=(15, 5))
        
        # Save button - initially disabled
        save_btn = tk.Button(button_frame_form, text="💾 Save Customer", 
                            state=tk.DISABLED, width=22,
                            bg="#808080", fg="white", font=("Arial", 11, "bold"),
                            disabledforeground="#CCCCCC", relief=tk.RAISED, bd=3,
                            activebackground="#388E3C", activeforeground="white", cursor="hand2")
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear/New Customer button
        clear_btn = tk.Button(button_frame_form, text="🆕 New Customer", 
                             command=lambda: clear_form(), width=22,
                             bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                             relief=tk.RAISED, bd=3,
                             activebackground="#1565C0", activeforeground="white", cursor="hand2")
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        def check_fields_filled():
            """Check if all fields are filled and enable/disable save button"""
            all_filled = all(var.get().strip() for var in field_vars)
            if all_filled:
                # Update button text based on mode
                if editing_customer["display_name"]:
                    save_btn.config(text="💾 Update Customer", bg="#FF9800")
                else:
                    save_btn.config(text="💾 Save Customer", bg="#4CAF50")
                save_btn.config(state=tk.NORMAL)
            else:
                save_btn.config(state=tk.DISABLED, bg="#808080")
        
        def clear_form():
            """Clear form fields and switch to add mode"""
            for var in field_vars:
                var.set("")
            editing_customer["display_name"] = None
            add_frame.config(text="Add/Edit Customer")
            save_btn.config(state=tk.DISABLED, bg="#808080", text="💾 Save Customer")
            # Deselect in listbox
            customer_listbox.selection_clear(0, tk.END)
        
        def load_customer_for_edit(display_name: str):
            """Load customer data into form fields for editing"""
            customer = self.customer_manager.get_customer_by_name(display_name)
            if not customer:
                messagebox.showerror("Error", f"Customer '{display_name}' not found.", parent=self.root)
                return
            
            # Populate fields
            field_vars[0].set(customer['name'])
            field_vars[1].set(customer['business'])
            field_vars[2].set(customer['address'])
            field_vars[3].set(customer['city'])
            field_vars[4].set(customer['state'])
            field_vars[5].set(customer['zip_code'])
            
            # Set editing mode
            editing_customer["display_name"] = display_name
            add_frame.config(text=f"Edit Customer: {customer['name']}")
            check_fields_filled()  # Enable save button since fields are filled
        
        def on_listbox_select(event):
            """Handle customer selection from listbox"""
            selection = customer_listbox.curselection()
            if selection:
                display_name = customer_listbox.get(selection[0])
                load_customer_for_edit(display_name)
        
        # Bind listbox selection event
        customer_listbox.bind('<<ListboxSelect>>', on_listbox_select)
        
        def save_customer():
            """Save or update customer"""
            name = field_vars[0].get().strip()
            business = field_vars[1].get().strip()
            address = field_vars[2].get().strip()
            city = field_vars[3].get().strip()
            state = field_vars[4].get().strip()
            zip_code = field_vars[5].get().strip()
            
            if not all([name, business, address, city, state, zip_code]):
                messagebox.showerror("Error", "All fields are required.", parent=self.root)
                return
            
            if editing_customer["display_name"]:
                # Update existing customer
                old_display_name = editing_customer["display_name"]
                was_active_customer = (self.active_customer_display == old_display_name)
                
                result = self.customer_manager.update_customer(
                    old_display_name, name, business, address, city, state, zip_code
                )
                if result:
                    # Build new display name
                    new_display_name = f"{name} | {business}"
                    
                    # If this was the active customer, update it to the new display name
                    if was_active_customer:
                        self.active_customer_display = new_display_name
                    
                    messagebox.showinfo("Success", "Customer updated successfully!", parent=self.root)
                    clear_form()
                    refresh_listbox()
                    
                    # Update customer menu on main window (force refresh since customer was updated)
                    if was_active_customer and self.active_customer_var:
                        # Temporarily set the active customer display so menu update uses it
                        self._update_customer_menu(force_refresh=True)
                        # Ensure it's set correctly after menu update
                        customer_names_after = self.customer_manager.get_customer_names()
                        if new_display_name in customer_names_after:
                            if self.active_customer_var.get() != new_display_name:
                                self.active_customer_var.set(new_display_name)
                            self.active_customer_display = new_display_name
                    else:
                        self._update_customer_menu(force_refresh=True)
                else:
                    error_msg = "Failed to update customer.\n\n"
                    error_msg += "If Excel file is open, please close it and try again."
                    messagebox.showerror("Error", error_msg, parent=self.root)
            else:
                # Add new customer
                result = self.customer_manager.add_customer(name, business, address, city, state, zip_code)
                if result:
                    messagebox.showinfo("Success", "Customer added successfully!", parent=self.root)
                    clear_form()
                    refresh_listbox()
                    # Update customer menu on main window (force refresh since customer was updated)
                    self._update_customer_menu(force_refresh=True)
                else:
                    # Check if it's a permission error or duplicate
                    error_msg = "Customer already exists or Excel file is locked.\n\n"
                    error_msg += "If Excel is open, please close it and try again."
                    messagebox.showerror("Error", error_msg, parent=self.root)
        
        # Bind save button to save_customer function
        save_btn.config(command=save_customer)
        
        def remove_customer():
            selection = customer_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a customer to remove.", parent=self.root)
                return
            
            customer_name = customer_listbox.get(selection[0])
            
            # Don't allow removing the last customer
            if len(self.customer_manager.get_customers()) <= 1:
                messagebox.showerror("Error", "Cannot remove the last customer.", parent=self.root)
                return
            
            if messagebox.askyesno("Confirm", f"Remove customer '{customer_name}'?", parent=self.root):
                # Check if the customer being removed is the active customer
                was_active_customer = (self.active_customer_display == customer_name)
                
                result = self.customer_manager.remove_customer(customer_name)
                if result:
                    # If the removed customer was being edited, clear the form
                    if editing_customer["display_name"] == customer_name:
                        clear_form()
                    
                    # If the removed customer was the active customer, reset to default
                    if was_active_customer:
                        self.active_customer_display = None
                        # _update_customer_menu will set it to the first available customer
                    
                    messagebox.showinfo("Success", "Customer removed successfully!", parent=self.root)
                    refresh_listbox()
                    # Update customer menu on main window (force refresh since customer was removed)
                    self._update_customer_menu(force_refresh=True)
                else:
                    error_msg = "Failed to remove customer.\n\n"
                    error_msg += "If Excel file is open, please close it and try again."
                    messagebox.showerror("Error", error_msg, parent=self.root)
        
        # Info label
        info_label = tk.Label(main_frame, 
                             text="💡 Tip: You can edit customers directly in Excel.\n"
                                  "Click 'Open Excel File' to edit, then click '🔄 Refresh List' to update.",
                             font=("Arial", 8), fg="gray", bg=bg_main, justify=tk.LEFT)
        info_label.pack(pady=(0, 10))
        
        # Action Buttons (simplified - single row)
        button_frame = tk.Frame(main_frame, bg=bg_main)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(button_frame, text="📋 Open Excel File", command=open_excel_file, 
                 width=18, bg="#2196F3", fg="white", font=("Arial", 10, "bold"),
                 relief=tk.RAISED, bd=2,
                 activebackground="#1565C0", activeforeground="white", cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🔄 Refresh List", command=refresh_listbox, 
                 width=18, bg="#FF9800", fg="white", font=("Arial", 10, "bold"),
                 relief=tk.RAISED, bd=2,
                 activebackground="#F57C00", activeforeground="white", cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="❌ Delete Selected", 
                 command=remove_customer, width=18,
                 bg="#F44336", fg="white", font=("Arial", 10, "bold"),
                 relief=tk.RAISED, bd=2,
                 activebackground="#C62828", activeforeground="white", cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # Bottom button frame with Close button
        bottom_frame = tk.Frame(main_frame, bg=bg_main)
        bottom_frame.pack(fill=tk.X)
        
        tk.Button(bottom_frame, text="✖ Close", command=dialog.destroy, width=25,
                 bg="#607D8B", fg="white", font=("Arial", 11, "bold"),
                 relief=tk.RAISED, bd=3,
                 activebackground="#455A64", activeforeground="white", cursor="hand2").pack(pady=(5, 0))

        # Bring window to front and focus it
        dialog.lift()
        dialog.focus_force()
        dialog.attributes('-topmost', True)  # Keep on top briefly
        dialog.after(100, lambda: dialog.attributes('-topmost', False))  # Remove topmost after a moment

        # Bind window destruction to clear reference
        dialog.protocol("WM_DELETE_WINDOW", self._on_customer_window_close)
    
    def show_history(self):
        """Show pallet history window (singleton behavior)"""
        try:
            if not self.pallet_manager:
                messagebox.showerror("Error", "PalletManager not initialized",
                                   parent=self.root)
                return

            # Check if history window already exists
            if self.history_window:
                try:
                    if self.history_window.window.winfo_exists():
                        # Window exists, bring it to front
                        self.history_window.window.lift()
                        self.history_window.window.focus_force()
                        return
                except tk.TclError:
                    # Window was destroyed, clear reference
                    self.history_window = None

            # Create new window
            self._create_history_window()
        except Exception as e:
            # Log error but keep app running
            print(f"ERROR in show_history: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "History Error",
                    f"An error occurred while showing history:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                # If messagebox fails, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")
    
    def _create_history_window(self):
        """Create history window (called asynchronously)"""
        try:
            self.history_window = PalletHistoryWindow(self.root, self.pallet_manager, self.customer_manager)
            # Bind window destruction to clear reference
            self.history_window.window.protocol("WM_DELETE_WINDOW", self._on_history_window_close)
            # Window will handle its own lifecycle
        except Exception as e:
            print(f"ERROR in _create_history_window: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "History Error",
                    f"An error occurred while showing history:\n{e}\n\n"
                    "The application will continue running.",
                    parent=self.root
                )
            except Exception:
                print(f"CRITICAL: Could not show error dialog: {e}")

    def _on_history_window_close(self):
        """Handle history window destruction to clear reference and destroy window"""
        if self.history_window and self.history_window.window:
            self.history_window.window.destroy()
        self.history_window = None

    def _on_customer_window_close(self):
        """Handle customer window destruction to clear reference and destroy window"""
        if self.customer_window:
            self.customer_window.destroy()
        self.customer_window = None

    def _load_data_async(self):
        """Load data asynchronously after UI is shown (for faster startup)"""
        try:
            # Initialize SerialDatabase if it was deferred
            if self.serial_db and hasattr(self.serial_db, '_init_deferred') and self.serial_db._init_deferred:
                self.serial_db._ensure_database()
                self.serial_db._ensure_master_data_sheet()
                self.serial_db._init_deferred = False
            
            # Load PalletManager data if it was deferred
            if self.pallet_manager:
                # Ensure directory structure exists
                self.pallet_manager._ensure_directory_structure()
                # Load actual data
                self.pallet_manager.data = self.pallet_manager.load_history()
            
            # Preload cache and run archiving after a short delay
            self.root.after(500, self._preload_cache)
            self.root.after(1000, self._run_archiving)
            
        except Exception as e:
            # Silently fail - this is background initialization
            import traceback
            traceback.print_exc()
            pass
    
    def _preload_cache(self):
        """Pre-load ONLY serial cache (lightweight) - data cache is lazy-loaded"""
        try:
            if self.serial_db:
                # Only refresh serial cache (set of serials - lightweight)
                # Don't pre-load data cache (dict of all data - too heavy, lazy-loaded on demand)
                self.serial_db._refresh_serial_cache()
        except Exception:
            pass  # Silently fail - background operation
    
    def _find_workbook_async(self):
        """Find workbook asynchronously after UI is shown (non-blocking)"""
        try:
            project_root = get_base_dir()
            excel_dir = project_root / "EXCEL"
            current_workbook = excel_dir / "CURRENT.xlsx"
            
            # Try find_pallet_workbook first
            if not self.workbook_path:
                self.workbook_path = find_pallet_workbook(excel_dir, current_workbook)
            
            # If still not found, try BUILD files (expensive operation)
            if not self.workbook_path:
                try:
                    build_files = list(excel_dir.glob("BUILD*.xlsx"))
                    if build_files:
                        self.workbook_path = max(build_files, key=lambda p: p.stat().st_mtime)
                except Exception:
                    pass  # Silently fail - can still scan without workbook
            
            # Initialize PalletExporter if workbook found
            if self.workbook_path and not self.pallet_exporter:
                export_dir = project_root / "PALLETS"
                # Ensure PALLETS directory exists before creating PalletExporter
                try:
                    export_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"WARNING: Could not create PALLETS directory: {export_dir}")
                    print(f"Error: {e}")
                    # Continue anyway - PalletExporter will try to create it later
                self.pallet_exporter = PalletExporter(self.workbook_path, export_dir, self.serial_db)
        except Exception:
            pass  # Silently fail - background operation
    
    def _run_archiving(self):
        """Run archiving operations in background (non-blocking)"""
        try:
            if hasattr(self, 'archive_manager'):
                # Archive old pallets
                archived_pallets = self.archive_manager.archive_old_pallets()
                
                # Archive old history entries if history is too large
                if self.pallet_manager:
                    history_file = self.pallet_manager.history_file
                    archived_entries = self.archive_manager.archive_old_history_entries(history_file, max_entries=1000)
                
                # Clean up old imported files
                cleaned_files = self.archive_manager.cleanup_old_imported_files(max_age_days=180)
        except Exception:
            pass  # Silently fail - background operation
    
    def _scan_for_new_files(self):
        """Lightweight background scan and auto-import of new simulator data files (non-blocking)"""
        try:
            if not self.serial_db:
                return  # Can't import without database
            
            project_root = get_base_dir()
            sun_sim_dir = project_root / "SUN SIMULATOR DATA"
            imported_data_dir = project_root / "IMPORTED DATA"
            
            # Ensure directories exist (create if missing)
            try:
                sun_sim_dir.mkdir(parents=True, exist_ok=True)
                imported_data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create data folders: {e}")
                return
            
            # Skip if directories still don't exist (permission issue)
            if not sun_sim_dir.exists() or not sun_sim_dir.is_dir():
                return
            
            # Get list of files in SUN SIMULATOR DATA (lightweight - just file names)
            sun_sim_files = {}
            for ext in ['.xlsx', '.xlsm', '.xls', '.xlsb', '.csv']:
                for file_path in sun_sim_dir.glob(f'*{ext}'):
                    # Skip temp files
                    if not file_path.name.startswith('~$'):
                        sun_sim_files[file_path.name] = file_path
            
            if not sun_sim_files:
                return  # No files to check
            
            # Get list of files already imported (lightweight - just file names)
            imported_files = set()
            if imported_data_dir.exists():
                for file_path in imported_data_dir.glob('*'):
                    if file_path.is_file():
                        # Remove counter suffix if present (e.g., "file_1.xlsx" -> "file.xlsx")
                        name = file_path.name
                        # Check if it matches pattern with counter
                        import re
                        match = re.match(r'^(.+)_(\d+)(\.[^.]+)$', name)
                        if match:
                            # It's a duplicate with counter, use original name
                            name = match.group(1) + match.group(3)
                        imported_files.add(name)
            
            # Find new files (in SUN SIMULATOR DATA but not in IMPORTED DATA)
            new_file_paths = [
                file_path for name, file_path in sun_sim_files.items()
                if name not in imported_files
            ]
            
            if new_file_paths:
                # Automatically import new files silently in background
                # Use a proper lambda that captures the variable correctly
                self.root.after(100, lambda paths=new_file_paths: self._auto_import_files(paths))
        except Exception:
            # Silently fail - this is a background operation, don't interrupt user
            pass
    
    def _auto_import_files(self, file_paths: list):
        """Automatically import files silently in the background (chunked for responsiveness)"""
        try:
            if not self.serial_db or not file_paths:
                return
            
            # Process files in small chunks to keep UI responsive
            chunk_size = 1  # Process one file at a time
            current_index = [0]  # Use list to allow modification in nested function
            
            def import_next_chunk():
                """Import next chunk of files"""
                if current_index[0] >= len(file_paths):
                    # All files processed - invalidate cache
                    if self.serial_db:
                        self.serial_db.invalidate_cache()
                    return
                
                # Process one file
                file_path = file_paths[current_index[0]]
                try:
                    if file_path.exists():
                        self.serial_db.import_simulator_file(file_path)
                except Exception:
                    pass  # Silently skip files that fail
                
                current_index[0] += 1
                
                # Schedule next chunk (allows UI to process events)
                if current_index[0] < len(file_paths):
                    self.root.after(50, import_next_chunk)
                else:
                    # All done - invalidate cache
                    if self.serial_db:
                        self.serial_db.invalidate_cache()
            
            # Start importing (non-blocking)
            self.root.after(50, import_next_chunk)
                
        except Exception:
            # Silently fail - this is a background operation
            pass
    
    def _on_closing(self):
        """Handle window close event"""
        # Clean up lock file before closing
        _remove_lock_file()
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop"""
        try:
            # Start background operations after UI is fully loaded
            # Delay longer to ensure UI is responsive first
            self.root.after(2000, self._scan_for_new_files)  # Wait 2 seconds after startup
            self.root.mainloop()
        except Exception as e:
            # Prevent app from closing on unexpected errors
            print(f"ERROR: Unexpected error in main loop: {e}")
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror(
                    "Application Error",
                    f"An unexpected error occurred:\n{e}\n\n"
                    "The application will continue running.\n"
                    "Please report this error if it persists.",
                    parent=self.root
                )
            except Exception:
                # If we can't show messagebox, at least log it
                print(f"CRITICAL: Could not show error dialog: {e}")


def _get_lock_file_path() -> Path:
    """Get the path to the lock file for single-instance check"""
    # Use temp directory for lock file
    temp_dir = Path(tempfile.gettempdir())
    lock_file = temp_dir / "pallet_manager.lock"
    return lock_file


def _is_instance_running() -> bool:
    """
    Check if another instance of the application is already running.
    
    Returns:
        True if another instance is running, False otherwise
    """
    lock_file = _get_lock_file_path()
    
    if not lock_file.exists():
        return False
    
    try:
        # Read PID from lock file
        pid = int(lock_file.read_text().strip())
        
        # Check if process is still running
        system = platform.system()
        if system == 'Windows':
            # On Windows, check if process exists
            try:
                # Use tasklist to check if process is running
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                # If PID is found in tasklist output, process is running
                return str(pid) in result.stdout
            except Exception:
                # If we can't check, assume process is dead and remove stale lock
                try:
                    lock_file.unlink()
                except Exception:
                    pass
                return False
        else:
            # On Unix-like systems, check if process exists
            try:
                # Sending signal 0 doesn't kill the process, just checks if it exists
                os.kill(pid, 0)
                return True
            except OSError:
                # Process doesn't exist, remove stale lock file
                try:
                    lock_file.unlink()
                except Exception:
                    pass
                return False
    except (ValueError, FileNotFoundError):
        # Lock file is invalid or doesn't exist
        try:
            lock_file.unlink()
        except Exception:
            pass
        return False


def _create_lock_file():
    """Create a lock file with current process ID"""
    lock_file = _get_lock_file_path()
    try:
        lock_file.write_text(str(os.getpid()))
        # Register cleanup function to remove lock on exit
        atexit.register(_remove_lock_file)
    except Exception as e:
        # If we can't create lock file, log but don't fail
        print(f"Warning: Could not create lock file: {e}")


def _remove_lock_file():
    """Remove the lock file"""
    lock_file = _get_lock_file_path()
    try:
        if lock_file.exists():
            lock_file.unlink()
    except Exception:
        # Ignore errors when removing lock file
        pass


def main():
    """Main entry point for the GUI application"""
    # Check if another instance is already running
    if _is_instance_running():
        # Show message to user
        root = tk.Tk()
        root.withdraw()  # Hide main window
        messagebox.showinfo(
            "Application Already Running",
            "Pallet Manager is already running.\n\n"
            "Please use the existing window instead of opening a new instance.",
            parent=None
        )
        root.destroy()
        sys.exit(0)
    
    # Create lock file to prevent other instances
    _create_lock_file()
    
    try:
        app = PalletBuilderGUI()
        app.run()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
    except Exception as e:
        # Show error if initialization fails
        root = tk.Tk()
        root.withdraw()  # Hide main window
        messagebox.showerror(
            "Fatal Error",
            f"Failed to start Pallet Manager:\n{e}\n\n"
            "Please check the logs and ensure all dependencies are installed."
        )
        root.destroy()
    finally:
        # Clean up lock file on exit
        _remove_lock_file()


if __name__ == "__main__":
    main()
