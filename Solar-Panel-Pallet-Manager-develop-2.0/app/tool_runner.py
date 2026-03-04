#!/usr/bin/env python3
"""
SunSim Packout Tool - Operator-Friendly Wrapper

This wrapper provides a simple, one-click interface for operators.
Operators never need to run Python directly or pass command-line flags.
"""

import sys
import os
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import yaml

# Import the core import module
# Add parent directory to path to allow importing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import import_sunsim
except ImportError:
    print("Error: Could not import import_sunsim.py")
    print("Make sure import_sunsim.py is in the app/ directory")
    sys.exit(2)


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        return get_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config if config else get_default_config()
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Return default configuration if config.yaml is missing"""
    return {
        'input_folder': '../CSV_INPUT',
        'excel_folder': '../EXCEL',
        'current_workbook': '../data/EXCEL/CURRENT.xlsx',
        'backup_folder': '../data/EXCEL/backups',
        'log_folder': '../LOGS',
        'archive_folder': '../ARCHIVE/processed_files',
        'extra_files_folder': '../ARCHIVE/unprocessed_extra',
        'status_file': '../STATUS.txt',
        'instructions_file': '../OPERATOR INSTRUCTIONS.txt',
        'workbook_name_must_contain': ['BUILD', 'Q'],
        'ignore_prefixes': ['~$'],
        'ranges': {
            'pm_w': [0, 1000],
            'voc_v': [0, 100],
            'isc_a': [0, 50],
            'ipm_a': [0, 50],
            'vpm_v': [0, 100]
        }
    }


def resolve_path(relative_path: str, base_dir: Path) -> Path:
    """Resolve relative path from config to absolute path"""
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def ensure_folders_exist(config: Dict[str, Any], base_dir: Path) -> None:
    """Ensure all required folders exist"""
    folders = [
        'input_folder',
        'excel_folder',
        'backup_folder',
        'log_folder',
        'archive_folder',
        'extra_files_folder'
    ]
    
    for folder_key in folders:
        if folder_key in config:
            folder_path = resolve_path(config[folder_key], base_dir)
            folder_path.mkdir(parents=True, exist_ok=True)


def find_input_files(input_dir: Path) -> list[Path]:
    """Find all .csv and .xlsx files in input directory"""
    files = []
    if not input_dir.exists():
        return files
    
    for ext in ['.csv', '.xlsx']:
        files.extend(list(input_dir.glob(f'*{ext}')))
        # Also check for files with spaces in names
        files.extend(list(input_dir.glob(f'*{ext.upper()}')))
    
    # Filter out temp files
    files = [f for f in files if not f.name.startswith('~$')]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def check_workbook_locked(workbook_path: Path, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Check if workbook is locked/open.
    Returns (is_locked, error_message)
    """
    if not workbook_path.exists():
        return False, None
    
    # Check for Windows lock file
    if platform.system() == 'Windows':
        lock_file = workbook_path.parent / f"~${workbook_path.name}"
        if lock_file.exists():
            return True, "Excel file is open. Please close it and try again."
    
    # Try to open the file in read-only mode to check if it's locked
    try:
        # On Windows, we can't reliably check without trying to open
        # On macOS/Linux, we can check file permissions
        if platform.system() != 'Windows':
            # Try to open in append mode (will fail if locked)
            with open(workbook_path, 'a'):
                pass
    except PermissionError:
        return True, "Excel file is open or locked. Please close it and try again."
    except Exception:
        # Other errors might not indicate a lock
        pass
    
    return False, None


def write_status(status: str, details: Dict[str, Any], status_file_path: Path) -> None:
    """Write STATUS.txt with human-readable result"""
    try:
        with open(status_file_path, 'w', encoding='utf-8') as f:
            f.write(f"STATUS: {status}\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            if status == "SUCCESS":
                f.write(f"Imported file:\n{details.get('imported_file', 'N/A')}\n\n")
                f.write(f"Workbook updated:\n{details.get('workbook', 'N/A')}\n\n")
                f.write(f"Updated: {details.get('updated', 0)}\n")
                f.write(f"Added: {details.get('added', 0)}\n")
                f.write(f"Skipped: {details.get('skipped', 0)}\n\n")
                f.write("Next step:\n")
                f.write("Open Excel, scan barcodes, print pallet.\n")
            else:
                f.write(f"Reason:\n{details.get('reason', 'Unknown error')}\n\n")
                f.write(f"Fix:\n{details.get('fix', 'Check logs for details')}\n")
    except Exception as e:
        # If we can't write status, at least try to log it
        print(f"Warning: Could not write STATUS.txt: {e}")


def open_file_cross_platform(file_path: Path) -> bool:
    """Open file using platform-appropriate method"""
    try:
        system = platform.system()
        if system == 'Windows':
            os.startfile(str(file_path))
        elif system == 'Darwin':  # macOS
            subprocess.run(['open', str(file_path)], check=False)
        else:  # Linux
            subprocess.run(['xdg-open', str(file_path)], check=False)
        return True
    except Exception as e:
        print(f"Warning: Could not open {file_path}: {e}")
        return False


def move_extra_files(extra_files: list[Path], extra_dir: Path) -> None:
    """Move extra files to unprocessed_extra folder"""
    extra_dir.mkdir(parents=True, exist_ok=True)
    
    for file_path in extra_files:
        try:
            # Add timestamp to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            dest_path = extra_dir / new_name
            file_path.rename(dest_path)
        except Exception as e:
            print(f"Warning: Could not move {file_path.name} to extra folder: {e}")


def main():
    """Main wrapper entry point"""
    # Get base directory (where tool_runner.py is located)
    base_dir = Path(__file__).parent.absolute()
    
    # Load configuration
    config = load_config()
    
    # Resolve all paths relative to base_dir
    input_dir = resolve_path(config['input_folder'], base_dir)
    excel_dir = resolve_path(config['excel_folder'], base_dir)
    status_file_path = resolve_path(config['status_file'], base_dir)
    extra_files_dir = resolve_path(config['extra_files_folder'], base_dir)
    
    # Ensure folders exist
    ensure_folders_exist(config, base_dir)
    
    # Set paths in import_sunsim module first (needed for find_pallet_workbook)
    import_sunsim.SCRIPT_DIR = base_dir.parent.absolute()
    import_sunsim.CSV_INPUT_DIR = input_dir
    import_sunsim.EXCEL_DIR = excel_dir
    import_sunsim.BACKUPS_DIR = resolve_path(config['backup_folder'], base_dir)
    import_sunsim.LOGS_DIR = resolve_path(config['log_folder'], base_dir)
    import_sunsim.ARCHIVE_DIR = resolve_path(config['archive_folder'], base_dir)
    
    # Setup logging early (needed for find_pallet_workbook)
    logger = import_sunsim.setup_logging()
    
    # Find input files
    input_files = find_input_files(input_dir)
    
    # Handle no files case
    if not input_files:
        write_status("FAILED", {
            'reason': 'No simulator export files found in CSV_INPUT folder.',
            'fix': 'Copy simulator export file (.xlsx or .csv) into CSV_INPUT folder, then run again.'
        }, status_file_path)
        open_file_cross_platform(status_file_path)
        return 1
    
    # Handle multiple files case
    input_file = input_files[0]  # Process newest
    extra_files = input_files[1:]  # Move others
    
    if extra_files:
        move_extra_files(extra_files, extra_files_dir)
        # Note: We'll add a warning to STATUS about extra files
    
    # Find workbook using the existing function
    workbook_path = None
    current_workbook_path = resolve_path(config['current_workbook'], base_dir)
    if current_workbook_path.exists():
        workbook_path = current_workbook_path
    else:
        # Use the existing find_pallet_workbook function
        workbook_path = import_sunsim.find_pallet_workbook(None, logger)
    
    if not workbook_path or not workbook_path.exists():
        write_status("FAILED", {
            'reason': 'Could not find pallet workbook.',
            'fix': 'Ensure EXCEL/CURRENT.xlsx exists or place a BUILD YYYY Q-X.xlsx file in EXCEL folder.'
        }, status_file_path)
        open_file_cross_platform(status_file_path)
        return 1
    
    # Check if workbook is locked
    is_locked, lock_error = check_workbook_locked(workbook_path, config)
    if is_locked:
        write_status("FAILED", {
            'reason': lock_error or 'Excel file is locked.',
            'fix': 'Close Excel and run again.'
        }, status_file_path)
        open_file_cross_platform(status_file_path)
        return 1
    
    logger.info("=" * 60)
    logger.info("SunSim Packout Tool - Starting")
    logger.info("=" * 60)
    
    try:
        # Parse input file
        if input_file.suffix.lower() == '.csv':
            records = import_sunsim.parse_csv_file(input_file, logger)
        else:
            records = import_sunsim.parse_xlsx_file(input_file, logger)
        
        if not records:
            write_status("FAILED", {
                'reason': 'No records found in input file.',
                'fix': 'Check that the simulator export file contains valid data with SerialNo and electrical values.'
            }, status_file_path)
            open_file_cross_platform(status_file_path)
            return 1
        
        # Validate records
        valid_records = []
        skipped_records = []
        skipped_count = 0
        
        for idx, record in enumerate(records, 1):
            is_valid, warnings = import_sunsim.validate_record(
                record, logger, row_num=idx, verbose=False, exclude_out_of_range=False
            )
            if is_valid:
                valid_records.append(record)
            else:
                skipped_count += 1
                serial_no = record.get('SerialNo', 'N/A')
                skip_reason = warnings[0] if warnings else "Validation failed"
                skipped_records.append({
                    'SerialNo': serial_no,
                    'reason': skip_reason,
                    'row': idx,
                    'record': record
                })
        
        if not valid_records:
            write_status("FAILED", {
                'reason': 'No valid records found after validation.',
                'fix': 'Check that records have valid SerialNo and all required electrical values (Pm, Isc, Voc, Ipm, Vpm).'
            }, status_file_path)
            open_file_cross_platform(status_file_path)
            return 1
        
        # Deduplicate
        file_mtime = input_file.stat().st_mtime
        deduplicated = import_sunsim.deduplicate_records(valid_records, file_mtime, logger)
        
        # Validate workbook structure
        is_valid, structure_warnings = import_sunsim.validate_workbook_structure(workbook_path, logger)
        if not is_valid:
            write_status("FAILED", {
                'reason': 'Workbook structure validation failed.',
                'fix': 'Check that workbook has DATA sheet with required columns (B, H, I, J, K, L). See logs for details.'
            }, status_file_path)
            open_file_cross_platform(status_file_path)
            return 1
        
        # Create backup
        backup_path = import_sunsim.create_backup(workbook_path, logger)
        if not backup_path:
            logger.warning("Backup creation failed, but continuing...")
        
        # Update workbook
        try:
            updated_count, added_count, change_details = import_sunsim.update_excel_workbook(
                workbook_path, deduplicated, logger, dry_run=False, show_progress=False
            )
        except PermissionError:
            write_status("FAILED", {
                'reason': 'Cannot update workbook - file may be open in Excel.',
                'fix': 'Close Excel and run again.'
            }, status_file_path)
            open_file_cross_platform(status_file_path)
            return 1
        except Exception as e:
            logger.error(f"Error updating workbook: {e}")
            write_status("FAILED", {
                'reason': f'Error updating workbook: {str(e)[:100]}',
                'fix': 'Check logs for details. Restore from backup if needed.'
            }, status_file_path)
            open_file_cross_platform(status_file_path)
            return 2
        
        # Generate summary report
        report_path = import_sunsim.generate_summary_report(
            change_details, skipped_records, logger,
            input_file.name, workbook_path.name
        )
        
        # Archive input file
        if updated_count + added_count > 0:
            import_sunsim.archive_file(input_file, logger)
        
        # Write success status
        status_details = {
            'imported_file': input_file.name,
            'workbook': workbook_path.name,
            'updated': updated_count,
            'added': added_count,
            'skipped': skipped_count
        }
        
        write_status("SUCCESS", status_details, status_file_path)
        
        # Add note about extra files if any
        if extra_files:
            logger.info(f"Note: {len(extra_files)} other file(s) were moved to ARCHIVE/unprocessed_extra/")
            try:
                with open(status_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"\nNote: {len(extra_files)} other file(s) moved to ARCHIVE/unprocessed_extra/\n")
            except Exception:
                pass
        
        # Open Excel and STATUS.txt
        open_file_cross_platform(workbook_path)
        open_file_cross_platform(status_file_path)
        
        logger.info("=" * 60)
        logger.info("Import complete - SUCCESS")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        write_status("FAILED", {
            'reason': f'Unexpected error occurred: {str(e)[:100]}',
            'fix': 'Check logs for details. Contact support if problem persists.'
        }, status_file_path)
        open_file_cross_platform(status_file_path)
        return 2


if __name__ == "__main__":
    sys.exit(main())

