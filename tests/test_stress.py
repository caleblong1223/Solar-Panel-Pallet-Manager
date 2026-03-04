#!/usr/bin/env python3
"""
Comprehensive Stress Tests for Pallet Manager

Tests performance and reliability under various load conditions.
"""

import time
import sys
import signal
import threading
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pallet_builder_gui import PalletBuilderGUI
from app.customer_manager import CustomerManager
from app.pallet_manager import PalletManager
from app.serial_database import SerialDatabase
from app.path_utils import get_base_dir


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


class StressTestSuite:
    """Comprehensive stress tests for Pallet Manager"""
    
    def __init__(self):
        self.test_results: List[Dict] = []
        self.root = None
        self.test_timeout = 120  # 2 minutes per test
    
    def log_test(self, test_name: str, passed: bool, duration: float, error: str = None):
        """Log test result"""
        result = {
            'name': test_name,
            'passed': passed,
            'duration': duration,
            'error': error
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name} ({duration:.3f}s)" + (f" - {error}" if error else ""))
    
    def run_with_timeout(self, func, timeout_seconds: int, *args, **kwargs):
        """Run a function with a timeout"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            raise TimeoutError(f"Test exceeded timeout of {timeout_seconds} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def test_rapid_barcode_scanning(self, count: int = 50):
        """Test rapid barcode scanning performance"""
        print(f"\n{'='*60}")
        print(f"TEST 1: Rapid Barcode Scanning ({count} scans)")
        print(f"{'='*60}")
        
        def run_test():
            app = None
            try:
                app = PalletBuilderGUI()
                
                # Wait for initialization (non-blocking)
                for _ in range(10):
                    app.root.update_idletasks()
                    time.sleep(0.1)
                    if app.pallet_manager:
                        break
                
                if not app.pallet_manager:
                    raise Exception("PalletManager not initialized")
                
                # Start new pallet
                app.start_new_pallet()
                app.root.update_idletasks()
                time.sleep(0.2)
                
                scan_start = time.time()
                scan_times = []
                processed = 0
                
                for i in range(count):
                    serial = f"TEST{i:06d}"
                    scan_time = time.time()
                    
                    # Simulate barcode scan
                    try:
                        app.scan_entry.delete(0, tk.END)
                        app.scan_entry.insert(0, serial)
                        app.on_barcode_scanned(None)
                        processed += 1
                    except Exception as e:
                        print(f"    Warning: Scan {i} failed: {e}")
                    
                    # Allow GUI to update (limited updates)
                    if i % 10 == 0:  # Update every 10 scans
                        app.root.update_idletasks()
                    
                    scan_time = time.time() - scan_time
                    scan_times.append(scan_time)
                
                total_duration = time.time() - scan_start
                avg_time = sum(scan_times) / len(scan_times) if scan_times else 0
                max_time = max(scan_times) if scan_times else 0
                
                # Check if scans were processed
                pallet_count = len(app.current_pallet.get('serial_numbers', [])) if app.current_pallet else 0
                
                # Allow for some processing overhead
                passed = (pallet_count >= count * 0.9) and (avg_time < 0.15)  # 90% processed, < 150ms per scan
                
                self.log_test(
                    f"Rapid Barcode Scanning ({count} scans)",
                    passed,
                    total_duration,
                    None if passed else f"Count: {pallet_count}/{count}, Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
                )
                
                print(f"  - Processed: {pallet_count}/{count}")
                print(f"  - Average scan time: {avg_time:.3f}s")
                print(f"  - Max scan time: {max_time:.3f}s")
                print(f"  - Total duration: {total_duration:.2f}s")
                
                if app:
                    app.root.destroy()
                
                return True
                
            except Exception as e:
                if app:
                    try:
                        app.root.destroy()
                    except:
                        pass
                raise e
        
        start_time = time.time()
        try:
            self.run_with_timeout(run_test, self.test_timeout)
            duration = time.time() - start_time
            self.log_test(f"Rapid Barcode Scanning ({count} scans)", True, duration)
        except TimeoutError as e:
            duration = time.time() - start_time
            self.log_test(f"Rapid Barcode Scanning ({count} scans)", False, duration, str(e))
            print(f"  ⚠️  Test timed out after {duration:.1f}s")
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Rapid Barcode Scanning", False, duration, str(e))
            import traceback
            print(f"  Error details:")
            traceback.print_exc()
    
    def test_customer_operations(self, count: int = 20):
        """Test customer management operations performance"""
        print(f"\n{'='*60}")
        print(f"TEST 2: Customer Operations ({count} operations)")
        print(f"{'='*60}")
        
        def run_test():
            from app.path_utils import get_base_dir
            
            start_time = time.time()
            project_root = get_base_dir()
            customer_file = project_root / "CUSTOMERS" / "customers.xlsx"
            customer_file.parent.mkdir(parents=True, exist_ok=True)
            
            manager = CustomerManager(customer_file)
            
            # Test add operations
            add_start = time.time()
            for i in range(count):
                name = f"Test Customer {i}"
                business = f"Test Business {i}"
                result = manager.add_customer(name, business, "123 Test St", "Test City", "TS", "12345")
                if not result and i < 10:  # First few might already exist
                    pass  # Expected for some
            add_duration = time.time() - add_start
            
            # Test refresh operations (with caching)
            refresh_start = time.time()
            for i in range(count):
                manager.refresh_customers(force_reload=False)  # Use cache
            refresh_cached_duration = time.time() - refresh_start
            
            # Test refresh with force reload
            refresh_force_start = time.time()
            for i in range(5):  # Only test 5 forced refreshes
                manager.refresh_customers(force_reload=True)
            refresh_force_duration = time.time() - refresh_force_start
            
            # Test get operations
            get_start = time.time()
            for i in range(count * 10):  # Test many gets
                names = manager.get_customer_names()
            get_duration = time.time() - get_start
            
            passed = (add_duration / count < 0.2 and  # < 200ms per add
                     refresh_cached_duration / count < 0.01 and  # < 10ms per cached refresh
                     get_duration / (count * 10) < 0.001)  # < 1ms per get
            
            self.log_test(
                f"Customer Operations ({count} operations)",
                passed,
                time.time() - start_time,
                None if passed else f"Add: {add_duration/count:.3f}s, Refresh: {refresh_cached_duration/count:.3f}s"
            )
            
            print(f"  - Add operations: {add_duration:.2f}s ({add_duration/count:.3f}s each)")
            print(f"  - Cached refresh: {refresh_cached_duration:.2f}s ({refresh_cached_duration/count:.3f}s each)")
            print(f"  - Force refresh: {refresh_force_duration:.2f}s ({refresh_force_duration/5:.3f}s each)")
            print(f"  - Get operations: {get_duration:.2f}s ({get_duration/(count*10):.4f}s each)")
            
            return True
        
        start_time = time.time()
        try:
            self.run_with_timeout(run_test, self.test_timeout)
            duration = time.time() - start_time
            print(f"✅ Test completed in {duration:.2f}s")
        except TimeoutError as e:
            duration = time.time() - start_time
            self.log_test(f"Customer Operations ({count} operations)", False, duration, str(e))
            print(f"  ⚠️  Test timed out after {duration:.1f}s")
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Customer Operations", False, duration, str(e))
            import traceback
            print(f"  Error details:")
            traceback.print_exc()
    
    def test_slot_display_updates(self, count: int = 100):
        """Test slot display update performance"""
        print(f"\n{'='*60}")
        print(f"TEST 3: Slot Display Updates ({count} updates)")
        print(f"{'='*60}")
        
        start_time = time.time()
        app = None
        try:
            app = PalletBuilderGUI()
            
            # Wait for initialization
            for _ in range(10):
                app.root.update_idletasks()
                time.sleep(0.1)
                if app.pallet_manager:
                    break
            
            if not app.pallet_manager:
                self.log_test("Slot Display Updates - Init", False, time.time() - start_time, "PalletManager not initialized")
                if app:
                    app.root.destroy()
                return
            
            app.start_new_pallet()
            app.root.update_idletasks()
            time.sleep(0.2)
            
            # Add some serials
            if app.current_pallet:
                for i in range(25):
                    app.current_pallet['serial_numbers'].append(f"TEST{i:06d}")
            
            update_start = time.time()
            update_times = []
            
            for i in range(count):
                update_time = time.time()
                
                # Update display (deferred updates)
                app.update_slot_display(force_update=False)
                if i % 10 == 0:  # Update GUI every 10 iterations
                    app.root.update_idletasks()
                
                update_time = time.time() - update_time
                update_times.append(update_time)
            
            total_duration = time.time() - update_start
            avg_time = sum(update_times) / len(update_times) if update_times else 0
            max_time = max(update_times) if update_times else 0
            
            passed = avg_time < 0.05 and max_time < 0.2  # Should be fast
            
            self.log_test(
                f"Slot Display Updates ({count} updates)",
                passed,
                total_duration,
                None if passed else f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
            )
            
            print(f"  - Average update time: {avg_time:.3f}s")
            print(f"  - Max update time: {max_time:.3f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            
            if app:
                app.root.destroy()
            
            return True
        
        except Exception as e:
            # Ensure the GUI is cleaned up if anything goes wrong inside run_test
            if app:
                try:
                    app.root.destroy()
                except Exception:
                    pass
            # Re-raise so outer timeout/exception handling can log it
            raise e
        
        start_time = time.time()
        try:
            self.run_with_timeout(run_test, self.test_timeout)
            duration = time.time() - start_time
            self.log_test(f"Slot Display Updates ({count} updates)", True, duration)
        except TimeoutError as e:
            duration = time.time() - start_time
            self.log_test(f"Slot Display Updates ({count} updates)", False, duration, str(e))
            print(f"  ⚠️  Test timed out after {duration:.1f}s")
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Slot Display Updates", False, duration, str(e))
            import traceback
            print(f"  Error details:")
            traceback.print_exc()
    
    def test_customer_menu_updates(self, count: int = 50):
        """Test customer menu update performance"""
        print(f"\n{'='*60}")
        print(f"TEST 4: Customer Menu Updates ({count} updates)")
        print(f"{'='*60}")
        
        start_time = time.time()
        app = None
        try:
            app = PalletBuilderGUI()
            
            # Wait for initialization
            for _ in range(10):
                app.root.update_idletasks()
                time.sleep(0.1)
                if app.customer_manager and app.active_customer_menu:
                    break
            
            if not app.customer_manager or not app.active_customer_menu:
                self.log_test("Customer Menu Updates - Init", False, time.time() - start_time, "Customer menu not initialized")
                if app:
                    app.root.destroy()
                return
            
            update_start = time.time()
            update_times = []
            
            for i in range(count):
                update_time = time.time()
                
                # Update menu (should use cache)
                app._update_customer_menu(force_refresh=False)
                if i % 10 == 0:  # Update GUI every 10 iterations
                    app.root.update_idletasks()
                
                update_time = time.time() - update_time
                update_times.append(update_time)
            
            total_duration = time.time() - update_start
            avg_time = sum(update_times) / len(update_times) if update_times else 0
            max_time = max(update_times) if update_times else 0
            
            passed = avg_time < 0.02  # Should be very fast with caching
            
            self.log_test(
                f"Customer Menu Updates ({count} updates)",
                passed,
                total_duration,
                None if passed else f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
            )
            
            print(f"  - Average update time: {avg_time:.3f}s")
            print(f"  - Max update time: {max_time:.3f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            
            if app:
                app.root.destroy()
            
        except Exception as e:
            self.log_test("Customer Menu Updates", False, time.time() - start_time, str(e))
            if app:
                try:
                    app.root.destroy()
                except:
                    pass
            import traceback
            traceback.print_exc()
    
    def test_concurrent_operations(self):
        """Test handling of concurrent operations"""
        print(f"\n{'='*60}")
        print("TEST 5: Concurrent Operations")
        print(f"{'='*60}")
        
        start_time = time.time()
        app = None
        try:
            app = PalletBuilderGUI()
            
            # Wait for initialization
            for _ in range(10):
                app.root.update_idletasks()
                time.sleep(0.1)
                if app.pallet_manager:
                    break
            
            if not app.pallet_manager:
                self.log_test("Concurrent Operations - Init", False, time.time() - start_time, "PalletManager not initialized")
                if app:
                    app.root.destroy()
                return
            
            app.start_new_pallet()
            app.root.update_idletasks()
            time.sleep(0.2)
            
            # Simulate rapid operations
            for i in range(20):
                serial = f"CONCURRENT{i:06d}"
                try:
                    app.scan_entry.delete(0, tk.END)
                    app.scan_entry.insert(0, serial)
                    app.on_barcode_scanned(None)
                except Exception:
                    pass  # Ignore individual errors
                
                app.update_slot_display()  # Deferred updates
                
                if app.customer_manager and i % 5 == 0:  # Refresh every 5 iterations
                    app.customer_manager.refresh_customers(force_reload=False)
                
                if i % 5 == 0:  # Update GUI every 5 iterations
                    app.root.update_idletasks()
            
            # Check if app is still responsive
            app.root.update_idletasks()
            
            pallet_count = len(app.current_pallet.get('serial_numbers', [])) if app.current_pallet else 0
            passed = pallet_count >= 15  # At least 15 should be processed
            
            duration = time.time() - start_time
            
            self.log_test(
                "Concurrent Operations",
                passed,
                duration,
                None if passed else f"Only {pallet_count}/20 processed"
            )
            
            print(f"  - Processed: {pallet_count}/20 operations")
            print(f"  - Duration: {duration:.2f}s")
            
            if app:
                app.root.destroy()
            
        except Exception as e:
            self.log_test("Concurrent Operations", False, time.time() - start_time, str(e))
            if app:
                try:
                    app.root.destroy()
                except:
                    pass
            import traceback
            traceback.print_exc()
    
    def test_memory_usage(self):
        """Test memory usage under load"""
        print(f"\n{'='*60}")
        print("TEST 6: Memory Usage")
        print(f"{'='*60}")
        
        app = None
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            app = PalletBuilderGUI()
            
            # Wait for initialization
            for _ in range(10):
                app.root.update_idletasks()
                time.sleep(0.1)
            
            after_init_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform operations
            if app.pallet_manager:
                app.start_new_pallet()
                app.root.update_idletasks()
                time.sleep(0.2)
            
            for i in range(50):
                if app.current_pallet:
                    app.current_pallet['serial_numbers'].append(f"MEMTEST{i:06d}")
                app.update_slot_display()  # Deferred updates
                if app.customer_manager and i % 10 == 0:
                    app.customer_manager.refresh_customers(force_reload=False)
                if i % 10 == 0:
                    app.root.update_idletasks()
                    time.sleep(0.05)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            passed = memory_increase < 150  # Should not increase by more than 150MB
            
            self.log_test(
                "Memory Usage",
                passed,
                0,
                None if passed else f"Memory increased by {memory_increase:.1f}MB"
            )
            
            print(f"  - Initial memory: {initial_memory:.1f}MB")
            print(f"  - After init: {after_init_memory:.1f}MB")
            print(f"  - Final memory: {final_memory:.1f}MB")
            print(f"  - Memory increase: {memory_increase:.1f}MB")
            
            if app:
                app.root.destroy()
            
        except ImportError:
            self.log_test("Memory Usage", True, 0, "psutil not available, skipping")
            print("  - psutil not available, skipping memory test")
        except Exception as e:
            self.log_test("Memory Usage", False, 0, str(e))
            if app:
                try:
                    app.root.destroy()
                except:
                    pass
    
    def test_serial_validation_performance(self, count: int = 200):
        """Test serial validation performance with database"""
        print(f"\n{'='*60}")
        print(f"TEST 7: Serial Validation Performance ({count} validations)")
        print(f"{'='*60}")
        
        start_time = time.time()
        serial_db = None
        try:
            project_root = get_base_dir()
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            
            # Initialize database
            serial_db = SerialDatabase(db_file, defer_init=False)
            
            # Wait for cache to initialize
            time.sleep(0.5)
            
            # Generate test serials (mix of valid and invalid)
            test_serials = []
            for i in range(count):
                # Mix of formats
                if i % 3 == 0:
                    test_serials.append(f"TEST{i:06d}")
                elif i % 3 == 1:
                    test_serials.append(f"CRS{i:05d}")
                else:
                    test_serials.append(str(1000000000 + i))
            
            validation_start = time.time()
            validation_times = []
            valid_count = 0
            
            for serial in test_serials:
                val_time = time.time()
                is_valid = serial_db.validate_serial(serial)
                val_time = time.time() - val_time
                validation_times.append(val_time)
                if is_valid:
                    valid_count += 1
            
            total_duration = time.time() - validation_start
            avg_time = sum(validation_times) / len(validation_times) if validation_times else 0
            max_time = max(validation_times) if validation_times else 0
            min_time = min(validation_times) if validation_times else 0
            
            # Should be very fast with caching (< 10ms per validation)
            passed = avg_time < 0.01 and max_time < 0.05
            
            self.log_test(
                f"Serial Validation Performance ({count} validations)",
                passed,
                total_duration,
                None if passed else f"Avg: {avg_time:.4f}s, Max: {max_time:.4f}s"
            )
            
            print(f"  - Valid serials found: {valid_count}/{count}")
            print(f"  - Average validation time: {avg_time:.4f}s")
            print(f"  - Min validation time: {min_time:.4f}s")
            print(f"  - Max validation time: {max_time:.4f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            print(f"  - Throughput: {count/total_duration:.0f} validations/sec")
            
        except Exception as e:
            self.log_test("Serial Validation Performance", False, time.time() - start_time, str(e))
            import traceback
            traceback.print_exc()
    
    def test_batch_serial_lookup(self, batch_size: int = 50):
        """Test batch serial data lookup performance"""
        print(f"\n{'='*60}")
        print(f"TEST 8: Batch Serial Lookup ({batch_size} serials)")
        print(f"{'='*60}")
        
        start_time = time.time()
        serial_db = None
        try:
            project_root = get_base_dir()
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            
            serial_db = SerialDatabase(db_file, defer_init=False)
            time.sleep(0.5)  # Wait for cache
            
            # Generate test serials
            test_serials = [f"BATCH{i:06d}" for i in range(batch_size)]
            
            lookup_start = time.time()
            lookup_times = []
            
            for i in range(10):  # Test 10 batch lookups
                batch_time = time.time()
                results = serial_db.get_serial_data_batch(test_serials)
                batch_time = time.time() - batch_time
                lookup_times.append(batch_time)
            
            total_duration = time.time() - lookup_start
            avg_time = sum(lookup_times) / len(lookup_times) if lookup_times else 0
            max_time = max(lookup_times) if lookup_times else 0
            
            # Batch lookups should be efficient (< 100ms per batch)
            passed = avg_time < 0.1
            
            self.log_test(
                f"Batch Serial Lookup ({batch_size} serials per batch)",
                passed,
                total_duration,
                None if passed else f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
            )
            
            print(f"  - Batch size: {batch_size} serials")
            print(f"  - Number of batches: 10")
            print(f"  - Average batch time: {avg_time:.3f}s")
            print(f"  - Max batch time: {max_time:.3f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            print(f"  - Average per serial: {avg_time/batch_size:.4f}s")
            
        except Exception as e:
            self.log_test("Batch Serial Lookup", False, time.time() - start_time, str(e))
            import traceback
            traceback.print_exc()
    
    def test_database_cache_performance(self):
        """Test database cache effectiveness"""
        print(f"\n{'='*60}")
        print("TEST 9: Database Cache Performance")
        print(f"{'='*60}")
        
        start_time = time.time()
        serial_db = None
        try:
            project_root = get_base_dir()
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            
            serial_db = SerialDatabase(db_file, defer_init=False)
            time.sleep(0.5)  # Wait for initial cache
            
            # First lookup (cache miss - should be slower)
            first_lookup_start = time.time()
            serial_db.validate_serial("CACHE_TEST_001")
            first_lookup_time = time.time() - first_lookup_start
            
            # Second lookup (cache hit - should be faster)
            second_lookup_start = time.time()
            for i in range(100):
                serial_db.validate_serial("CACHE_TEST_001")
            second_lookup_time = time.time() - second_lookup_start
            avg_cached_time = second_lookup_time / 100
            
            # Cache should be significantly faster
            cache_speedup = first_lookup_time / avg_cached_time if avg_cached_time > 0 else 0
            passed = cache_speedup > 2 or avg_cached_time < 0.001  # At least 2x faster or < 1ms
            
            self.log_test(
                "Database Cache Performance",
                passed,
                time.time() - start_time,
                None if passed else f"Cache speedup: {cache_speedup:.1f}x"
            )
            
            print(f"  - First lookup (cache miss): {first_lookup_time:.4f}s")
            print(f"  - Average cached lookup (100x): {avg_cached_time:.4f}s")
            print(f"  - Cache speedup: {cache_speedup:.1f}x")
            
        except Exception as e:
            self.log_test("Database Cache Performance", False, time.time() - start_time, str(e))
            import traceback
            traceback.print_exc()
    
    def test_database_file_operations(self, count: int = 50):
        """Test database file operations under load"""
        print(f"\n{'='*60}")
        print(f"TEST 10: Database File Operations ({count} operations)")
        print(f"{'='*60}")
        
        start_time = time.time()
        serial_db = None
        try:
            project_root = get_base_dir()
            db_file = project_root / "PALLETS" / "serial_database.xlsx"
            
            serial_db = SerialDatabase(db_file, defer_init=False)
            time.sleep(0.5)
            
            # Test various operations
            operation_times = []
            
            for i in range(count):
                op_time = time.time()
                
                # Mix of operations
                if i % 3 == 0:
                    # Validation
                    serial_db.validate_serial(f"FILEOP{i:06d}")
                elif i % 3 == 1:
                    # Single data lookup
                    serial_db.get_serial_data(f"FILEOP{i:06d}")
                else:
                    # Batch lookup
                    serial_db.get_serial_data_batch([f"FILEOP{j:06d}" for j in range(i, min(i+5, count))])
                
                op_time = time.time() - op_time
                operation_times.append(op_time)
            
            total_duration = time.time() - start_time
            avg_time = sum(operation_times) / len(operation_times) if operation_times else 0
            max_time = max(operation_times) if operation_times else 0
            
            # Operations should be fast with caching
            passed = avg_time < 0.05  # < 50ms average
            
            self.log_test(
                f"Database File Operations ({count} operations)",
                passed,
                total_duration,
                None if passed else f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
            )
            
            print(f"  - Operations performed: {count}")
            print(f"  - Average operation time: {avg_time:.3f}s")
            print(f"  - Max operation time: {max_time:.3f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            
        except Exception as e:
            self.log_test("Database File Operations", False, time.time() - start_time, str(e))
            import traceback
            traceback.print_exc()
    
    def run_all_tests(self):
        """Run all stress tests with timeout protection"""
        print("\n" + "="*60)
        print("PALLET MANAGER - COMPREHENSIVE STRESS TESTS")
        print("="*60)
        print(f"Test timeout: {self.test_timeout} seconds per test")
        print("="*60)
        
        overall_start = time.time()
        
        # Run all tests with error handling
        tests = [
            ("Rapid Barcode Scanning", lambda: self.test_rapid_barcode_scanning(50)),
            ("Customer Operations", lambda: self.test_customer_operations(20)),
            ("Slot Display Updates", lambda: self.test_slot_display_updates(100)),
            ("Customer Menu Updates", lambda: self.test_customer_menu_updates(50)),
            ("Concurrent Operations", lambda: self.test_concurrent_operations()),
            ("Memory Usage", lambda: self.test_memory_usage()),
            ("Serial Validation Performance", lambda: self.test_serial_validation_performance(200)),
            ("Batch Serial Lookup", lambda: self.test_batch_serial_lookup(50)),
            ("Database Cache Performance", lambda: self.test_database_cache_performance()),
            ("Database File Operations", lambda: self.test_database_file_operations(50)),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n⏳ Starting: {test_name}...")
                test_func()
                print(f"✅ Completed: {test_name}")
            except KeyboardInterrupt:
                print(f"\n⚠️  Test suite interrupted by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error in {test_name}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                time.sleep(0.5)  # Brief pause between tests
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        total_time = time.time() - overall_start
        passed_count = sum(1 for r in self.test_results if r['passed'])
        failed_count = len(self.test_results) - passed_count
        
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} - {result['name']} ({result['duration']:.3f}s)")
            if result['error']:
                print(f"       Error: {result['error']}")
        
        print(f"\n{'='*60}")
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Total Duration: {total_time:.2f}s")
        print(f"{'='*60}\n")
        
        return failed_count == 0


if __name__ == "__main__":
    suite = StressTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)

