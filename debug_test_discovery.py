#!/usr/bin/env python3
"""Diagnostic test to isolate test discovery hanging issue."""

import subprocess
import sys
import time


def test_single_file_collection():
    """Test collecting tests from a single file."""
    print("🔍 Testing single file test collection...")

    start_time = time.time()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_api_interface.py",
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        elapsed = time.time() - start_time
        print(f"✅ Collection completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Found tests: {result.stdout.count('::')}")

        if result.stderr:
            print(f"Warnings/Errors: {result.stderr[:200]}...")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"❌ Collection timed out after {elapsed:.2f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Collection failed after {elapsed:.2f}s: {e}")
        return False


def test_all_files_collection():
    """Test collecting tests from all files."""
    print("\n🔍 Testing all files test collection...")

    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        elapsed = time.time() - start_time
        print(f"✅ Collection completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Found tests: {result.stdout.count('::')}")

        if result.stderr:
            print(f"Warnings/Errors: {result.stderr[:300]}...")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"❌ Collection timed out after {elapsed:.2f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Collection failed after {elapsed:.2f}s: {e}")
        return False


def test_specific_hanging_test():
    """Test running just the problematic test."""
    print("\n🔍 Testing the specific failing test...")

    start_time = time.time()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_api_interface.py::TestAuthenticationAPI::test_token_verification",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        elapsed = time.time() - start_time
        print(f"✅ Test completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")

        if "PASSED" in result.stdout:
            print("✅ Test PASSED")
        elif "FAILED" in result.stdout:
            print("❌ Test FAILED")

        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}...")

        return True

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"❌ Test timed out after {elapsed:.2f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Test failed after {elapsed:.2f}s: {e}")
        return False


def check_api_tokens_issue():
    """Check the api_tokens configuration issue."""
    print("\n🔍 Checking api_tokens configuration...")

    try:
        from webdeface.config.settings import AppSettings

        settings = AppSettings()

        print(f"Settings has api_tokens attr: {hasattr(settings, 'api_tokens')}")

        # Check what getattr returns
        api_tokens = getattr(settings, "api_tokens", ["dev-token-12345"])
        print(f"Default api_tokens: {api_tokens}")

        # Test the exact token verification logic
        test_token = "test-token-123"
        default_token = "dev-token-12345"

        print(f"'{test_token}' in {api_tokens}: {test_token in api_tokens}")
        print(f"'{default_token}' in {api_tokens}: {default_token in api_tokens}")

        return True

    except Exception as e:
        print(f"❌ Config check failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Diagnosing WebDeface test discovery and hanging...")
    print("=" * 60)

    # Test api_tokens issue first
    config_ok = check_api_tokens_issue()

    # Test single file collection
    single_ok = test_single_file_collection()

    # Test all files collection
    all_ok = test_all_files_collection()

    # Test specific test
    specific_ok = test_specific_hanging_test()

    print("\n" + "=" * 60)
    print("📊 DIAGNOSIS SUMMARY:")
    print(f"Config check: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Single file collection: {'✅ PASS' if single_ok else '❌ FAIL'}")
    print(f"All files collection: {'✅ PASS' if all_ok else '❌ FAIL'}")
    print(f"Specific test: {'✅ PASS' if specific_ok else '❌ FAIL'}")

    if not all_ok and single_ok:
        print("\n🎯 CONFIRMED: Issue is with collecting from all test files")
    elif not specific_ok:
        print("\n🎯 CONFIRMED: Issue is with the specific test execution")
    else:
        print("\n🤔 INCONCLUSIVE: All tests completed without hanging")
