#!/usr/bin/env python3
"""
Archive Manager - Automatic archiving of old data

Automatically archives old pallet files and history data to maintain
performance and reduce file size.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import shutil
import json


class ArchiveManager:
    """Manages automatic archiving of old data"""
    
    def __init__(self, project_root: Path, archive_age_days: int = 90):
        """
        Initialize ArchiveManager.
        
        Args:
            project_root: Root directory of the project
            archive_age_days: Number of days before data is archived (default: 90)
        """
        self.project_root = project_root
        self.archive_age_days = archive_age_days
        self.pallets_dir = project_root / "PALLETS"
        self.archive_dir = project_root / "ARCHIVE" / "old_pallets"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def archive_old_pallets(self) -> int:
        """
        Archive pallet files older than archive_age_days.
        
        Returns:
            Number of files archived
        """
        archived_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.archive_age_days)
        
        try:
            # Find all date-based subdirectories in PALLETS
            for date_dir in self.pallets_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                # Try to parse date from directory name (e.g., "6-Jan-26")
                try:
                    dir_date = self._parse_date_dir_name(date_dir.name)
                    if dir_date and dir_date < cutoff_date:
                        # Archive entire directory
                        archive_path = self.archive_dir / date_dir.name
                        if not archive_path.exists():
                            shutil.move(str(date_dir), str(archive_path))
                            archived_count += 1
                except Exception:
                    # Skip directories that don't match date format
                    continue
            
            return archived_count
        except Exception:
            return archived_count
    
    def archive_old_history_entries(self, history_file: Path, max_entries: int = 1000) -> int:
        """
        Archive old entries from pallet history JSON if it gets too large.
        
        Args:
            history_file: Path to pallet_history.json
            max_entries: Maximum number of entries to keep (default: 1000)
            
        Returns:
            Number of entries archived
        """
        if not history_file.exists():
            return 0
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            pallets = data.get('pallets', [])
            if len(pallets) <= max_entries:
                return 0
            
            # Sort by pallet_number (oldest first)
            pallets.sort(key=lambda x: x.get('pallet_number', 0))
            
            # Archive old entries
            entries_to_archive = pallets[:-max_entries]
            archived_count = len(entries_to_archive)
            
            # Keep only recent entries
            data['pallets'] = pallets[-max_entries:]
            
            # Save archived entries
            archive_file = self.archive_dir / f"pallet_history_archive_{datetime.now().strftime('%Y%m%d')}.json"
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump({'pallets': entries_to_archive}, f, indent=2, ensure_ascii=False)
            
            # Update main history file
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return archived_count
        except Exception:
            return 0
    
    def _parse_date_dir_name(self, dir_name: str) -> Optional[datetime]:
        """Parse date from directory name like '6-Jan-26'"""
        try:
            # Format: d-Mmm-yy (e.g., "6-Jan-26")
            return datetime.strptime(dir_name, "%d-%b-%y")
        except Exception:
            return None
    
    def cleanup_old_imported_files(self, max_age_days: int = 180) -> int:
        """
        Clean up very old imported files from IMPORTED DATA directory.
        
        This now prefers the IMPORTED DATA/RAW_IMPORTS/ subdirectory (new structure),
        but will fall back to scanning the root IMPORTED DATA folder for backward
        compatibility with older installs.
        
        Args:
            max_age_days: Maximum age in days before cleanup (default: 180)
            
        Returns:
            Number of files cleaned up
        """
        imported_root = self.project_root / "IMPORTED DATA"
        if not imported_root.exists():
            return 0

        # Prefer new RAW_IMPORTS layout if present; otherwise, use root folder
        imported_dir = imported_root / "RAW_IMPORTS"
        if not imported_dir.exists():
            imported_dir = imported_root
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        try:
            for file_path in imported_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                # Skip master data file when scanning legacy root layout
                if file_path.name == 'sun_simulator_data.xlsx':
                    continue
                
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    # Move to archive
                    archive_path = self.archive_dir / "old_imports" / file_path.name
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(archive_path))
                    cleaned_count += 1
            
            return cleaned_count
        except Exception:
            return cleaned_count





