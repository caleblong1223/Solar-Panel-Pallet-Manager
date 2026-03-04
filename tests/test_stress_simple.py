#!/usr/bin/env python3
"""
Simplified Stress Tests for Pallet Manager - Non-GUI Database Tests Only

Runs database and customer management tests without GUI overhead.
"""

import time
import sys
from pathlib import Path
from typing import List, Dict

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.customer_manager import CustomerManager
from app.serial_database import SerialDatabase
from app.path_utils import get_base_dir


class SimpleStressTestSuite:
    """Simplified stress tests focusing on database operations"""
    
    def __init__(self):
        self.test_results: List[Dict] = []
    
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
    
    def test_customer_operations(self, count: int = 20):
        """Test customer management operations performance"""
        print(f"\n{'='*60}")
        print(f"TEST 1: Customer Operations ({count} operations)")
        print(f"{'='*60}")
        
        start_time = time.time()
        try:
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
            
            duration = time.time() - start_time
            
            self.log_test(
                f"Customer Operations ({count} operations)",
                passed,
                duration,
                None if passed else f"Add: {add_duration/count:.3f}s, Refresh: {refresh_cached_duration/count:.3f}s"
            )
            
            print(f"  - Add operations: {add_duration:.2f}s ({add_duration/count:.3f}s each)")
            print(f"  - Cached refresh: {refresh_cached_duration:.2f}s ({refresh_cached_duration/count:.3f}s each)")
            print(f"  - Force refresh: {refresh_force_duration:.2f}s ({refresh_force_duration/5:.3f}s each)")
            print(f"  - Get operations: {get_duration:.2f}s ({get_duration/(count*10):.4f}s each)")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Customer Operations", False, duration, str(e))
            import traceback
            traceback.print_exc()
    
    def test_serial_validation_performance(self, count: int = 200):
        """Test serial validation performance with database"""
        print(f"\n{'='*60}")
        print(f"TEST 2: Serial Validation Performance ({count} validations)")
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
            
            duration = time.time() - start_time
            
            self.log_test(
                f"Serial Validation Performance ({count} validations)",
                passed,
                duration,
                None if passed else f"Avg: {avg_time:.4f}s, Max: {max_time:.4f}s"
            )
            
            print(f"  - Valid serials found: {valid_count}/{count}")
            print(f"  - Average validation time: {avg_time:.4f}s")
            print(f"  - Min validation time: {min_time:.4f}s")
            print(f"  - Max validation time: {max_time:.4f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            print(f"  - Throughput: {count/total_duration:.0f} validations/sec")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Serial Validation Performance", False, duration, str(e))
            import traceback
            traceback.print_exc()
    
    def test_batch_serial_lookup(self, batch_size: int = 50):
        """Test batch serial data lookup performance"""
        print(f"\n{'='*60}")
        print(f"TEST 3: Batch Serial Lookup ({batch_size} serials)")
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
            
            duration = time.time() - start_time
            
            self.log_test(
                f"Batch Serial Lookup ({batch_size} serials per batch)",
                passed,
                duration,
                None if passed else f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
            )
            
            print(f"  - Batch size: {batch_size} serials")
            print(f"  - Number of batches: 10")
            print(f"  - Average batch time: {avg_time:.3f}s")
            print(f"  - Max batch time: {max_time:.3f}s")
            print(f"  - Total duration: {total_duration:.2f}s")
            print(f"  - Average per serial: {avg_time/batch_size:.4f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Batch Serial Lookup", False, duration, str(e))
            import traceback
            traceback.print_exc()
    
    def test_database_cache_performance(self):
        """Test database cache effectiveness"""
        print(f"\n{'='*60}")
        print("TEST 4: Database Cache Performance")
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
            
            duration = time.time() - start_time
            
            self.log_test(
                "Database Cache Performance",
                passed,
                duration,
                None if passed else f"Cache speedup: {cache_speedup:.1f}x"
            )
            
            print(f"  - First lookup (cache miss): {first_lookup_time:.4f}s")
            print(f"  - Average cached lookup (100x): {avg_cached_time:.4f}s")
            print(f"  - Cache speedup: {cache_speedup:.1f}x")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Database Cache Performance", False, duration, str(e))
            import traceback
            traceback.print_exc()
    
    def test_database_file_operations(self, count: int = 50):
        """Test database file operations under load"""
        print(f"\n{'='*60}")
        print(f"TEST 5: Database File Operations ({count} operations)")
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
            duration = time.time() - start_time
            self.log_test("Database File Operations", False, duration, str(e))
            import traceback
            traceback.print_exc()
    
    def run_all_tests(self):
        """Run all database stress tests"""
        print("\n" + "="*60)
        print("PALLET MANAGER - DATABASE STRESS TESTS")
        print("="*60)
        
        overall_start = time.time()
        
        # Run all tests
        self.test_customer_operations(20)
        time.sleep(0.5)
        
        self.test_serial_validation_performance(200)
        time.sleep(0.5)
        
        self.test_batch_serial_lookup(50)
        time.sleep(0.5)
        
        self.test_database_cache_performance()
        time.sleep(0.5)
        
        self.test_database_file_operations(50)
        
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
    suite = SimpleStressTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)

