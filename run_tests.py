#!/usr/bin/env python3
"""
Test runner for Research Trend Analyzer Light Agent.
Run basic unit tests to verify the workflow functionality.
"""

import unittest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run all unit tests."""
    print("Running Research Trend Analyzer Light Agent tests...")
    print("=" * 60)
    
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)