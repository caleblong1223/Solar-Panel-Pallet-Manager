#!/usr/bin/env python3
"""
Test script for file monitoring functionality

Tests that the FileMonitor correctly detects external file changes
without impacting performance.
"""

import time
from pathlib import Path
from app.path_utils import FileMonitor, get_base_dir

def test_file_monitoring():
    """Test file monitoring with actual file operations"""
    print("🧪 Testing File Monitoring Implementation\n")
    
    # Get test file path
    base_dir = get_base_dir()
    test_file = base_dir / "data" / "PALLETS" / "serial_database.xlsx"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print("   Creating a test file...")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")
        print(f"✅ Created test file: {test_file}\n")
    
    # Initialize monitor
    print(f"📁 Monitoring file: {test_file}")
    monitor = FileMonitor(test_file, debug=True)
    
    # Test 1: Initial state
    print("\n📋 Test 1: Initial state check")
    has_changed = monitor.has_changed()
    print(f"   Result: has_changed = {has_changed} (expected: False)")
    assert has_changed == False, "Initial check should return False"
    print("   ✅ PASSED")
    
    # Test 2: No change detection
    print("\n📋 Test 2: No change detection")
    time.sleep(0.1)  # Small delay
    has_changed = monitor.has_changed()
    print(f"   Result: has_changed = {has_changed} (expected: False)")
    assert has_changed == False, "No change should return False"
    print("   ✅ PASSED")
    
    # Test 3: File modification detection
    print("\n📋 Test 3: File modification detection")
    print("   Modifying file...")
    time.sleep(0.1)  # Ensure different timestamp
    test_file.touch()  # Update modification time
    time.sleep(0.1)  # Small delay
    
    has_changed = monitor.has_changed()
    print(f"   Result: has_changed = {has_changed} (expected: True)")
    assert has_changed == True, "File change should be detected"
    print("   ✅ PASSED")
    
    # Test 4: Subsequent check (no change)
    print("\n📋 Test 4: Subsequent check after change")
    has_changed = monitor.has_changed()
    print(f"   Result: has_changed = {has_changed} (expected: False)")
    assert has_changed == False, "Subsequent check should return False"
    print("   ✅ PASSED")
    
    # Test 5: Multiple changes
    print("\n📋 Test 5: Multiple file changes")
    initial_count = monitor.get_info()['change_count']
    for i in range(3):
        time.sleep(0.1)
        test_file.touch()
        time.sleep(0.1)
        has_changed = monitor.has_changed()
        print(f"   Change {i+1}: has_changed = {has_changed} (expected: True)")
        assert has_changed == True, f"Change {i+1} should be detected"
    
    info = monitor.get_info()
    new_changes = info['change_count'] - initial_count
    print(f"   New changes detected: {new_changes} (expected: 3)")
    assert new_changes == 3, f"Should detect 3 new changes, got {new_changes}"
    print("   ✅ PASSED")
    
    # Test 6: Performance test
    print("\n📋 Test 6: Performance test")
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        monitor.has_changed()
    
    elapsed = time.time() - start_time
    avg_time = (elapsed / iterations) * 1000  # Convert to milliseconds
    
    print(f"   Iterations: {iterations}")
    print(f"   Total time: {elapsed:.4f} seconds")
    print(f"   Average time per check: {avg_time:.4f} ms")
    print(f"   Checks per second: {iterations / elapsed:.0f}")
    
    # Performance should be very fast (< 1ms per check)
    assert avg_time < 1.0, f"Performance too slow: {avg_time}ms per check"
    print("   ✅ PASSED (Performance acceptable)")
    
    # Test 7: Reset functionality
    print("\n📋 Test 7: Reset functionality")
    monitor.reset()
    info = monitor.get_info()
    assert info['change_count'] == 0, "Reset should clear change count"
    assert info['last_mtime'] is not None, "Reset should preserve mtime"
    print("   ✅ PASSED")
    
    # Test 8: Monitor info
    print("\n📋 Test 8: Monitor info")
    info = monitor.get_info()
    print(f"   File path: {info['file_path']}")
    print(f"   Last mtime: {info['last_mtime']}")
    print(f"   Change count: {info['change_count']}")
    print(f"   File exists: {info['exists']}")
    assert 'file_path' in info and 'last_mtime' in info
    print("   ✅ PASSED")
    
    print("\n" + "="*60)
    print("🎉 All tests PASSED!")
    print("="*60)
    print("\n📊 Summary:")
    print(f"   ✅ File change detection working correctly")
    print(f"   ✅ Performance: {avg_time:.4f}ms per check (excellent)")
    print(f"   ✅ Multiple changes tracked correctly")
    print(f"   ✅ Reset functionality working")
    print("\n💡 The file monitoring system is ready for production use!")
    
    return True

if __name__ == "__main__":
    try:
        test_file_monitoring()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

