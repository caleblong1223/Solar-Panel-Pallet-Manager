#!/usr/bin/env python3
"""
Debug logging system for Pallet Manager
Provides detailed logging for troubleshooting and performance monitoring
"""

import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
import platform

class DebugLogger:
    """Centralized logging system with performance monitoring"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize logger
        
        Args:
            log_dir: Directory to save log files (default: LOGS/)
        """
        if log_dir is None:
            log_dir = Path("LOGS")
        
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        
        # Create session log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"debug_{timestamp}.log"
        
        # Performance tracking
        self.timers = {}
        
        # Write system info header
        self._write_system_info()
    
    def _write_system_info(self):
        """Write system information to log"""
        info = [
            "=" * 70,
            f"Pallet Manager Debug Log",
            f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            f"Platform: {platform.system()} {platform.release()}",
            f"Python: {sys.version}",
            f"Frozen: {getattr(sys, 'frozen', False)}",
        ]
        
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                info.append(f"PyInstaller MEIPASS: {sys._MEIPASS}")
            else:
                info.append(f"Executable: {sys.executable}")
        
        info.append("=" * 70)
        info.append("")
        
        self._write("\n".join(info))
    
    def _write(self, message: str):
        """Write message to log file and console"""
        try:
            # Write to file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
            
            # Also print to console
            print(message)
        except Exception as e:
            print(f"Logger error: {e}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp
        
        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:7s}] {message}"
        self._write(formatted)
    
    def info(self, message: str):
        """Log info message"""
        self.log(message, "INFO")
    
    def warning(self, message: str):
        """Log warning message"""
        self.log(message, "WARNING")
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """Log error message with optional exception info
        
        Args:
            message: Error message
            exc_info: Exception object to log traceback
        """
        self.log(message, "ERROR")
        
        if exc_info:
            tb = ''.join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            self._write(f"Traceback:\n{tb}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.log(message, "DEBUG")
    
    def start_timer(self, name: str):
        """Start a performance timer
        
        Args:
            name: Timer name/identifier
        """
        self.timers[name] = time.time()
        self.debug(f"Timer started: {name}")
    
    def end_timer(self, name: str) -> float:
        """End a performance timer and log elapsed time
        
        Args:
            name: Timer name/identifier
            
        Returns:
            Elapsed time in seconds
        """
        if name not in self.timers:
            self.warning(f"Timer '{name}' was never started")
            return 0.0
        
        elapsed = time.time() - self.timers[name]
        del self.timers[name]
        
        self.info(f"Timer '{name}': {elapsed:.3f}s")
        return elapsed
    
    def log_memory_usage(self):
        """Log current memory usage (if psutil available)"""
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            self.debug(f"Memory usage: {mem_mb:.1f} MB")
        except ImportError:
            self.debug("Memory logging unavailable (psutil not installed)")
    
    def section(self, title: str):
        """Create a section header in the log
        
        Args:
            title: Section title
        """
        separator = "-" * 70
        self._write(f"\n{separator}")
        self._write(f"  {title}")
        self._write(separator)

# Global logger instance
_logger: Optional[DebugLogger] = None

def get_logger() -> DebugLogger:
    """Get the global logger instance (creates if doesn't exist)"""
    global _logger
    if _logger is None:
        _logger = DebugLogger()
    return _logger








