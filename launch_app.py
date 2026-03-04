#!/usr/bin/env python3
"""Launcher script for Pallet Manager."""

from pathlib import Path
import sys
import traceback


def _show_startup_error(message: str) -> None:
    """Show startup failures in GUI-safe way for windowed EXE builds."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Pallet Manager - Startup Error", message)
        root.destroy()
        return
    except Exception:
        pass

    # Final fallback: write startup error to a local log file.
    try:
        Path("startup_error.log").write_text(message + "\n", encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    project_root = Path(__file__).parent.resolve()
    sys.path.insert(0, str(project_root))

    try:
        from app.pallet_builder_gui import main as gui_main
        gui_main()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        _show_startup_error(f"{exc}\n\n{details}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
