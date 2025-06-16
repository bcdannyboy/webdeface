#!/usr/bin/env python3
"""Quick validation of fixes before full test suite."""

import sys
from unittest.mock import MagicMock, patch


def test_api_tokens_fix():
    """Test that api_tokens field was added correctly."""
    print("🔍 Testing api_tokens fix...")

    try:
        from webdeface.config.settings import AppSettings

        # Test default settings
        settings = AppSettings()
        print(f"✅ AppSettings has api_tokens: {hasattr(settings, 'api_tokens')}")
        print(f"✅ Default api_tokens: {settings.api_tokens}")

        # Test with custom tokens
        settings_with_tokens = AppSettings(
            api_tokens=["test-token-123", "another-token"]
        )
        print(f"✅ Custom api_tokens: {settings_with_tokens.api_tokens}")

        return True

    except Exception as e:
        print(f"❌ api_tokens test failed: {e}")
        return False


def test_auth_verification_fix():
    """Test that auth verification works with proper mocking."""
    print("\n🔍 Testing auth verification fix...")

    try:
        # Create mock settings with test token
        mock_settings = MagicMock()
        mock_settings.api_tokens = ["test-token-123"]

        # Patch the get_settings function used by verify_api_token
        with patch("webdeface.api.auth.get_settings", return_value=mock_settings):
            from webdeface.api.auth import verify_api_token

            result_valid = verify_api_token("test-token-123")
            result_invalid = verify_api_token("invalid-token")

            print(f"✅ Valid token result: {result_valid} (should be True)")
            print(f"✅ Invalid token result: {result_invalid} (should be False)")

            return result_valid is True and result_invalid is False

    except Exception as e:
        print(f"❌ Auth verification test failed: {e}")
        return False


def test_simple_non_fastapi_test():
    """Test that basic pytest functionality works without FastAPI."""
    print("\n🔍 Testing simple test execution...")

    import subprocess
    import time

    # Create a minimal test file
    minimal_test = '''
import pytest

def test_simple():
    """Simple test that should pass quickly."""
    assert 1 + 1 == 2

def test_import_config():
    """Test that config can be imported."""
    from webdeface.config.settings import AppSettings
    settings = AppSettings()
    assert hasattr(settings, 'api_tokens')
'''

    try:
        with open("test_minimal.py", "w") as f:
            f.write(minimal_test)

        start_time = time.time()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_minimal.py", "-v"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        elapsed = time.time() - start_time
        print(f"✅ Minimal test completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")

        # Clean up
        import os

        os.remove("test_minimal.py")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Minimal test timed out")
        return False
    except Exception as e:
        print(f"❌ Minimal test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Quick validation of fixes...")
    print("=" * 50)

    # Test our fixes
    api_tokens_ok = test_api_tokens_fix()
    auth_ok = test_auth_verification_fix()
    minimal_ok = test_simple_non_fastapi_test()

    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY:")
    print(f"API tokens fix: {'✅ PASS' if api_tokens_ok else '❌ FAIL'}")
    print(f"Auth verification fix: {'✅ PASS' if auth_ok else '❌ FAIL'}")
    print(f"Basic test execution: {'✅ PASS' if minimal_ok else '❌ FAIL'}")

    if api_tokens_ok and auth_ok and minimal_ok:
        print("\n🎯 All fixes validated! Ready for full test suite analysis.")
        sys.exit(0)
    else:
        print("\n❌ Some fixes failed. Need to investigate further.")
        sys.exit(1)
