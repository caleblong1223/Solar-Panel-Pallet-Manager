#!/usr/bin/env python3
"""
Pallet Manager - JSON-based pallet history management

Manages pallet tracking using lightweight JSON storage.
Handles pallet creation, serial number management, and history tracking.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class PalletManager:
    """Manages pallet history using JSON file storage"""
    
    def __init__(self, history_file: Path, defer_load: bool = False):
        """
        Initialize PalletManager with history file path.
        
        Creates PALLETS directory structure if it doesn't exist:
        - PALLETS/ directory
        - PALLETS/ directory (date subfolders created automatically)
        - PALLETS/pallet_history.json file (if missing)
        
        Args:
            history_file: Path to JSON file storing pallet history
            defer_load: If True, don't load history immediately (for faster startup)
        """
        self.history_file = history_file
        self._ensure_directory_structure()
        if defer_load:
            # Load default structure, actual data loaded later
            self.data = self._get_default_structure()
        else:
            self.data = self.load_history()
        self._history_mtime = self._get_history_mtime()

    def _get_history_mtime(self) -> Optional[float]:
        """Get current history file modification time, if available."""
        try:
            if self.history_file.exists():
                return self.history_file.stat().st_mtime
        except Exception:
            pass
        return None

    def _refresh_from_disk_if_changed(self):
        """
        Refresh in-memory history if the underlying file changed externally.

        This prevents stale duplicate checks when another process or background
        task modifies pallet_history.json.
        """
        current_mtime = self._get_history_mtime()
        if current_mtime is None:
            return

        if self._history_mtime is None:
            self._history_mtime = current_mtime
            return

        if current_mtime > self._history_mtime:
            self.data = self.load_history()
            self._history_mtime = current_mtime
    
    def _ensure_directory_structure(self):
        """Ensure PALLETS directory exists"""
        # Create PALLETS directory if it doesn't exist
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize JSON file with default structure if it doesn't exist
        if not self.history_file.exists():
            default_data = self._get_default_structure()
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # If we can't write, load_history() will handle it
    
    def load_history(self) -> Dict[str, Any]:
        """
        Load pallet history from JSON file.
        
        Handles missing file and JSON corruption gracefully.
        Returns default structure if file is missing or corrupted.
        
        Returns:
            Dict with 'pallets' list and 'next_pallet_number' int
        """
        if not self.history_file.exists():
            return self._get_default_structure()
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict):
                return self._get_default_structure()
            
            if 'pallets' not in data or 'next_pallet_number' not in data:
                return self._get_default_structure()
            
            self._history_mtime = self._get_history_mtime()
            return data
            
        except json.JSONDecodeError:
            # JSON corruption detected - backup corrupted file and start fresh
            backup_path = self.history_file.with_suffix('.json.corrupted')
            try:
                shutil.copy2(self.history_file, backup_path)
            except Exception:
                pass  # If backup fails, continue anyway
            
            self._history_mtime = self._get_history_mtime()
            return self._get_default_structure()
            
        except Exception as e:
            # Any other error (permissions, etc.) - return default
            self._history_mtime = self._get_history_mtime()
            return self._get_default_structure()
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return default empty structure for pallet history"""
        return {
            "pallets": [],
            "next_pallet_number": 1
        }
    
    def save_history(self) -> bool:
        """
        Save pallet history to JSON file using atomic write pattern.
        
        Uses temporary file + rename to prevent corruption on write failure.
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Create temporary file in same directory
            temp_file = self.history_file.with_suffix('.json.tmp')
            
            # Write to temporary file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (works on both Windows and Unix)
            temp_file.replace(self.history_file)
            self._history_mtime = self._get_history_mtime()
            
            return True
            
        except IOError as e:
            # Permission error, disk full, etc.
            return False
        except Exception as e:
            # Any other error
            return False
    
    def create_new_pallet(self) -> Dict[str, Any]:
        """
        Create a new empty pallet with day-based numbering.
        
        Pallet numbers reset to 1 each day. If pallets already exist for today,
        the new pallet will continue from the highest pallet number for today.
        
        Returns:
            Dict representing new pallet with structure:
            {
                'pallet_number': int,
                'serial_numbers': [],
                'completed_at': None,
                'exported_file': None
            }
        """
        # Get today's date string (YYYY-MM-DD format)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Find the highest pallet number for today
        max_pallet_number_today = 0
        for pallet in self.data.get("pallets", []):
            completed_at = pallet.get("completed_at")
            if completed_at:
                # Extract date from completed_at (format: "YYYY-MM-DD HH:MM:SS")
                pallet_date = completed_at.split()[0] if " " in completed_at else completed_at[:10]
                if pallet_date == today:
                    pallet_num = pallet.get("pallet_number", 0)
                    if pallet_num > max_pallet_number_today:
                        max_pallet_number_today = pallet_num
        
        # Next pallet number for today is max + 1 (or 1 if no pallets today)
        next_pallet_number_today = max_pallet_number_today + 1
        
        pallet = {
            "pallet_number": next_pallet_number_today,
            "serial_numbers": [],
            "completed_at": None,
            "exported_file": None
        }
        return pallet
    
    def add_serial(self, pallet: Dict[str, Any], serial: str, max_panels: int = 25) -> bool:
        """
        Add a serial number to a pallet.

        Args:
            pallet: Pallet dict to add serial to
            serial: Serial number string to add
            max_panels: Maximum number of panels per pallet (default 25, can be 26)

        Returns:
            True if pallet is now full (max_panels serials), False otherwise
        """
        if len(pallet["serial_numbers"]) >= max_panels:
            return True  # Already full

        # Normalize serial (convert to uppercase for case-insensitive storage)
        from app.serial_database import normalize_serial
        normalized_serial = normalize_serial(serial)
        pallet["serial_numbers"].append(normalized_serial)
        return len(pallet["serial_numbers"]) == max_panels
    
    def remove_serial(self, pallet: Dict[str, Any], slot_index: int) -> bool:
        """
        Remove a serial number from a specific slot in a pallet.
        
        Args:
            pallet: Pallet dict to remove serial from
            slot_index: Zero-based index of slot to remove
            
        Returns:
            True if removal successful, False if index invalid
        """
        if not 0 <= slot_index < len(pallet["serial_numbers"]):
            return False
        
        pallet["serial_numbers"].pop(slot_index)
        return True
    
    def is_serial_on_any_pallet(self, serial: str, current_pallet: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Check if a serial number has been used on any pallet (current or completed).

        Args:
            serial: Serial number to check
            current_pallet: Optional current pallet dict to check (not yet in history)

        Returns:
            Dict with pallet info if found, None otherwise
            Format: {'pallet_number': int, 'completed_at': str or None, 'is_current': bool}
        """
        # Keep in-memory state aligned with on-disk history to avoid false
        # duplicate hits after background/external file updates.
        self._refresh_from_disk_if_changed()

        # Normalize serial for case-insensitive comparison
        from app.serial_database import normalize_serial
        normalized_serial = normalize_serial(serial)

        # Check current pallet first (if provided and not yet in history)
        if current_pallet and normalized_serial in current_pallet.get('serial_numbers', []):
            return {
                'pallet_number': current_pallet.get('pallet_number'),
                'completed_at': None,
                'is_current': True
            }
        
        # Check all completed pallets in history.
        # Skip reset pallets and stale records whose export file no longer exists.
        for pallet in self.data.get("pallets", []):
            if pallet.get("reset", False):
                continue  # Skip reset pallets - their serials can be reused
            if not self._is_pallet_record_usable_for_duplicate_check(pallet):
                continue
            if normalized_serial in pallet.get("serial_numbers", []):
                return {
                    'pallet_number': pallet.get("pallet_number"),
                    'completed_at': pallet.get("completed_at"),
                    'is_current': False
                }
        
        return None

    def _is_pallet_record_usable_for_duplicate_check(self, pallet: Dict[str, Any]) -> bool:
        """
        Return True if this history record should block duplicate scans.

        Pallets with missing exported files are treated as non-blocking because
        operators cannot verify/open them in History and these stale records can
        cause false "already on pallet" alerts.
        """
        exported_file = pallet.get("exported_file")
        if not exported_file:
            return True

        try:
            file_path = Path(exported_file)
            if file_path.is_absolute():
                return file_path.exists()

            # Match pallet_history_window behavior for relative paths.
            from app.path_utils import get_base_dir
            pallets_dir = get_base_dir() / "PALLETS"

            full_path = pallets_dir / file_path
            if full_path.exists():
                return True

            filename_only = file_path.name
            if (pallets_dir / filename_only).exists():
                return True

            if pallets_dir.exists():
                for date_dir in pallets_dir.iterdir():
                    if date_dir.is_dir() and (date_dir / filename_only).exists():
                        return True
        except Exception:
            # If we can't validate the path, do not hard-block scanning.
            return False

        return False
    
    def complete_pallet(self, pallet: Dict[str, Any], exported_file: Path, export_datetime: Optional[datetime] = None) -> bool:
        """
        Mark a pallet as complete and save to history.

        Args:
            pallet: Pallet dict to complete
            exported_file: Path to exported Excel file
            export_datetime: Optional datetime to use for completion timestamp (for consistency)

        Returns:
            True if save successful, False otherwise
        """
        # Set completion timestamp - use provided export_datetime for consistency, or current time
        completed_datetime = export_datetime if export_datetime else datetime.now()
        pallet["completed_at"] = completed_datetime.strftime("%Y-%m-%d %H:%M:%S")

        # Store exported file path (relative to project root)
        pallet["exported_file"] = str(exported_file)

        # Add to history
        self.data["pallets"].append(pallet)

        # Increment next pallet number
        self.data["next_pallet_number"] = pallet["pallet_number"] + 1

        # Save to file
        return self.save_history()
    
    def delete_pallet(self, pallet_number: int) -> bool:
        """
        Delete a pallet from history by pallet number.
        This removes the pallet entirely, allowing its serials to be reused.
        
        Args:
            pallet_number: Pallet number to delete
            
        Returns:
            True if deletion successful, False if pallet not found
        """
        pallets = self.data.get("pallets", [])
        original_count = len(pallets)
        
        # Remove pallet with matching number
        self.data["pallets"] = [
            p for p in pallets if p.get("pallet_number") != pallet_number
        ]
        
        # Check if pallet was actually removed
        if len(self.data["pallets"]) < original_count:
            # Save updated history
            return self.save_history()
        
        return False

    def reset_pallet(self, pallet_number: int, reason: str = "Manual reset") -> bool:
        """
        Reset a pallet, marking it as reset and allowing its serials to be reused.
        Unlike delete_pallet, this keeps the pallet in history with a reset record.

        Args:
            pallet_number: Pallet number to reset
            reason: Reason for the reset (for audit trail)

        Returns:
            True if reset successful, False if pallet not found
        """
        pallets = self.data.get("pallets", [])

        # Find and update the pallet
        for pallet in pallets:
            if pallet.get("pallet_number") == pallet_number:
                # Mark pallet as reset
                pallet["reset"] = True
                pallet["reset_at"] = datetime.now().isoformat()
                pallet["reset_reason"] = reason

                # Save updated history
                return self.save_history()

        return False

    def get_history(self, filter_exported: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Get pallet history, optionally filtered.
        
        Args:
            filter_exported: If True, return only exported pallets.
                           If False, return only non-exported pallets.
                           If None, return all pallets.
        
        Returns:
            List of pallet dicts, sorted by pallet_number descending (most recent first)
        """
        # Use cached data directly (already loaded, no file I/O)
        pallets = self.data.get("pallets", [])
        
        # Filter by exported status if requested
        if filter_exported is not None:
            pallets = [
                p for p in pallets 
                if (p.get("exported_file") is not None) == filter_exported
            ]
        
        # In-place sort is more memory efficient
        pallets.sort(key=lambda x: x.get("pallet_number", 0), reverse=True)
        
        return pallets
