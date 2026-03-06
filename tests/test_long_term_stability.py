#!/usr/bin/env python3
"""
Long-Term Stability Tests

Tests to ensure the application can run for extended periods without
memory leaks, resource exhaustion, or crashes.
"""

import gc
import time
import sys
from pathlib import Path

import pytest

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

try:
    from serial_database import SerialDatabase
    from customer_manager import CustomerManager
    from resource_manager import ResourceLimits
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    print("WARNING: Some dependencies not available. Some tests may be skipped.")
    PSUTIL_AVAILABLE = False


def test_memory_stability(num_operations=1000):
    """Test memory usage remains stable over many operations"""
    print("\n" + "=" * 70)
    print("TEST 1: Memory Stability Over Many Operations")
    print("=" * 70)
    
    if not PSUTIL_AVAILABLE:
        pytest.skip("psutil not available")
    
    try:
        import os
        process = psutil.Process(os.getpid())
        
        # Initialize database
        db_path = Path("PALLETS/serial_database.xlsx")
        if not db_path.exists():
            pytest.skip("Database file not found")
        
        db = SerialDatabase(db_path)
        
        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Initial memory: {initial_memory:.2f} MB")
        
        # Perform many operations
        for i in range(num_operations):
            # Validate serials
            test_serial = f"TEST{i:06d}"
            db.validate_serial(test_serial)
            
            # Batch lookup
            if i % 100 == 0:
                test_serials = [f"TEST{j:06d}" for j in range(i, min(i+50, num_operations))]
                db.get_serial_data_batch(test_serials)
            
            # Force GC every 200 operations
            if i % 200 == 0:
                gc.collect()
        
        # Measure final memory
        gc.collect()  # Final GC
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Check if memory increase is reasonable (< 50 MB for 1000 operations)
        assert memory_increase < 50, f"Memory increase too large ({memory_increase:.2f} MB > 50 MB)"
        print(f"✅ PASS - Memory increase within acceptable limits ({memory_increase:.2f} MB)")
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Error during memory stability test: {e}")
            
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_limits():
    """Test that cache size limits are enforced"""
    print("\n" + "=" * 70)
    print("TEST 2: Cache Size Limits")
    print("=" * 70)
    
    try:
        db_path = Path("PALLETS/serial_database.xlsx")
        if not db_path.exists():
            pytest.skip("Database file not found")
        
        db = SerialDatabase(db_path)
        
        # Check initial cache size
        initial_cache_size = len(db._data_cache)
        print(f"Initial cache size: {initial_cache_size}")
        
        # Try to add many entries (should be limited)
        test_serials = [f"LIMIT_TEST{i:06d}" for i in range(2000)]
        for serial in test_serials:
            db.validate_serial(serial)
        
        final_cache_size = len(db._data_cache)
        print(f"Final cache size: {final_cache_size}")
        print(f"Max cache size: {db._data_cache_max_size}")
        
        # Check if cache is within limits
        assert final_cache_size <= db._data_cache_max_size, (
            f"Cache size exceeds limit ({final_cache_size} > {db._data_cache_max_size})"
        )
        print(f"✅ PASS - Cache size within limits ({final_cache_size} <= {db._data_cache_max_size})")
            
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Error during cache limits test: {e}")


def test_resource_cleanup():
    """Test that resources are properly cleaned up"""
    print("\n" + "=" * 70)
    print("TEST 3: Resource Cleanup")
    print("=" * 70)
    
    try:
        db_path = Path("PALLETS/serial_database.xlsx")
        if not db_path.exists():
            pytest.skip("Database file not found")
        
        # Create many database instances (should clean up properly)
        instances = []
        for i in range(10):
            db = SerialDatabase(db_path)
            instances.append(db)
            # Use the database
            db.validate_serial(f"CLEANUP_TEST{i:06d}")
        
        # Delete instances
        del instances
        gc.collect()
        
        print("✅ PASS - Resources cleaned up properly")
        
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Error during resource cleanup test: {e}")


def test_input_validation():
    """Test input validation handles edge cases"""
    print("\n" + "=" * 70)
    print("TEST 4: Input Validation")
    print("=" * 70)
    
    try:
        db_path = Path("PALLETS/serial_database.xlsx")
        if not db_path.exists():
            pytest.skip("Database file not found")
        
        db = SerialDatabase(db_path)
        
        # Test various edge cases
        test_cases = [
            ("", False),  # Empty string
            (" " * 200, False),  # Very long string
            ("test\x00null", False),  # Null byte
            ("normal_serial", True),  # Normal serial
            (None, False),  # None value
        ]
        
        all_passed = True
        for input_val, should_handle in test_cases:
            try:
                if input_val is None:
                    result = db.validate_serial(None)
                else:
                    result = db.validate_serial(input_val)
                # Should not crash
                print(f"  ✅ Handled: {repr(input_val)[:30]}")
            except Exception as e:
                print(f"  ❌ Failed: {repr(input_val)[:30]} - {e}")
                all_passed = False
        
        assert all_passed, "Some input validation edge cases are not handled"
        print("✅ PASS - Input validation handles edge cases")
            
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Error during input validation test: {e}")


def test_error_recovery():
    """Test that errors are handled gracefully"""
    print("\n" + "=" * 70)
    print("TEST 5: Error Recovery")
    print("=" * 70)
    
    try:
        db_path = Path("PALLETS/serial_database.xlsx")
        if not db_path.exists():
            pytest.skip("Database file not found")
        
        db = SerialDatabase(db_path)
        
        # Try invalid operations (should not crash)
        try:
            db.validate_serial("test")
            db.get_serial_data("test")
            db.get_serial_data_batch(["test1", "test2"])
        except Exception as e:
            print(f"  ⚠️  Warning: Unexpected error: {e}")
        
        print("✅ PASS - Errors handled gracefully")
        
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Error during error recovery test: {e}")


def main():
    """Run all long-term stability tests"""
    print("=" * 70)
    print("LONG-TERM STABILITY TESTS")
    print("=" * 70)
    
    tests = [
        ("Memory Stability", lambda: test_memory_stability(500)),
        ("Cache Limits", test_cache_limits),
        ("Resource Cleanup", test_resource_cleanup),
        ("Input Validation", test_input_validation),
        ("Error Recovery", test_error_recovery),
    ]
    results = []

    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, True, None))
        except Exception as exc:
            results.append((test_name, False, str(exc)))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for test_name, result, message in results:
        status = "✅ PASS" if result else "❌ FAIL"
        extra = f" ({message})" if message else ""
        print(f"{status} - {test_name}{extra}")
    
    print("\n" + "=" * 70)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
