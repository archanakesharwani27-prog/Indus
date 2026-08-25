# tests/run_all_tests.py
"""
Master Test Runner for INDUS Production Test Suite
Executes all unit, integration, recovery, and closed-loop E2E test suites.
"""

import sys
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def run_all():
    print("=" * 70)
    print("  INDUS (INDUS) — MASTER PRODUCTION VERIFICATION RUNNER")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover and add all tests in tests/ directory
    # All test files — every suite must be included here
    test_files = [
        "test_agent_loop.py",
        "test_vision_engine.py",
        "test_vision_system_phase7.py",
        "test_wake_word.py",
        "test_cancellation.py",
        "test_action_verifier.py",
        "test_daily_use_scenarios.py",
        "test_security_hardening.py",
        "test_avatar_system.py",
        "test_ui_end_to_end.py",
        "test_reliability_fixes.py",
    ]


    tests_dir = BASE_DIR / "tests"

    for tf in test_files:
        test_path = tests_dir / tf
        if test_path.exists():
            discovered = loader.discover(start_dir=str(tests_dir), pattern=tf)
            suite.addTests(discovered)

    runner = unittest.TextTestRunner(verbosity=2)
    start_t = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start_t

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    print("\n" + "=" * 70)
    print(f"  TOTAL TESTS RUN : {total}")
    print(f"  PASSED          : {passed} / {total} ({(passed/total)*100:.1f}%)")
    print(f"  FAILURES        : {failures}")
    print(f"  ERRORS          : {errors}")
    print(f"  ELAPSED TIME    : {elapsed:.2f}s")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
