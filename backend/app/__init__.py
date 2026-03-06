from __future__ import annotations

from pathlib import Path

__all__ = []

_root_app_path = Path(__file__).resolve().parents[1].parent / "app"
path_str = str(_root_app_path)
if path_str not in __path__:
    __path__.append(path_str)
