# Test Suite

This directory contains all test files for the Pallet Manager application.

## Test Files

- `test_bugs.py` - Bug detection and validation tests
- `test_long_term_stability.py` - Long-term stability and memory leak tests
- `test_stress.py` - Full stress test suite (includes GUI tests)
- `test_stress_simple.py` - Database-only stress tests (no GUI)
- `verify_dependencies.py` - Dependency verification script

## Running Tests

### Run all tests
```bash
python3 -m pytest tests/ -v
```

### Run specific test
```bash
python3 tests/test_stress_simple.py
```

### Run stability tests
```bash
python3 tests/test_long_term_stability.py
```

## Test Requirements

Some tests require additional dependencies:
- `psutil` - For memory monitoring (optional)
- `pytest` - For test framework (optional)

Tests will skip features that require unavailable dependencies.









