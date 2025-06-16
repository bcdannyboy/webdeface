#!/usr/bin/env python3
"""Diagnostic test to isolate the settings loading issue."""

import sys
import time
from unittest.mock import MagicMock, patch


def test_settings_loading_speed():
    """Test how long settings take to load."""
    print("Testing settings loading...")

    start_time = time.time()

    try:
        # Try to import and call get_settings
        from webdeface.config import get_settings

        settings = get_settings()

        load_time = time.time() - start_time
        print(f"✅ Settings loaded successfully in {load_time:.2f} seconds")
        print(f"Settings debug mode: {settings.debug}")
        print(f"API tokens available: {hasattr(settings, 'api_tokens')}")

    except Exception as e:
        load_time = time.time() - start_time
        print(f"❌ Settings loading failed after {load_time:.2f} seconds: {e}")
        return False

    return True


def test_auth_with_mock():
    """Test auth function with proper mocking."""
    print("\nTesting auth with correct mock...")

    # Mock settings with api_tokens
    mock_settings = MagicMock()
    mock_settings.api_tokens = ["test-token-123"]

    # Patch the correct function
    with patch("webdeface.config.settings.get_settings", return_value=mock_settings):
        try:
            from webdeface.api.auth import verify_api_token

            result = verify_api_token("test-token-123")
            print(f"✅ Mock auth test: {result} (should be True)")
            return result
        except Exception as e:
            print(f"❌ Mock auth test failed: {e}")
            return False


def test_auth_without_mock():
    """Test auth function without mocking to see real behavior."""
    print("\nTesting auth without mock...")

    start_time = time.time()
    try:
        from webdeface.api.auth import verify_api_token

        result = verify_api_token("test-token-123")
        load_time = time.time() - start_time
        print(f"Result: {result} (took {load_time:.2f} seconds)")
        return True
    except Exception as e:
        load_time = time.time() - start_time
        print(f"❌ Auth test failed after {load_time:.2f} seconds: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Diagnosing WebDeface test hanging issue...")
    print("=" * 50)

    # Test 1: Raw settings loading
    settings_ok = test_settings_loading_speed()

    # Test 2: Auth with proper mock
    mock_auth_ok = test_auth_with_mock()

    # Test 3: Auth without mock (this may hang)
    print("\n⚠️  Testing without mock (may hang - will timeout in 5 seconds)...")
    try:
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Function call timed out")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout

        unmocked_auth_ok = test_auth_without_mock()
        signal.alarm(0)  # Cancel alarm

    except TimeoutError:
        print("❌ Auth without mock timed out after 5 seconds (confirms hanging)")
        unmocked_auth_ok = False
    except Exception as e:
        print(f"❌ Auth without mock failed: {e}")
        unmocked_auth_ok = False

    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY:")
    print(f"Settings loading: {'✅ PASS' if settings_ok else '❌ FAIL'}")
    print(f"Auth with mock: {'✅ PASS' if mock_auth_ok else '❌ FAIL'}")
    print(f"Auth without mock: {'✅ PASS' if unmocked_auth_ok else '❌ FAIL/HANG'}")

    if settings_ok and mock_auth_ok and not unmocked_auth_ok:
        print(
            "\n🎯 CONFIRMED: Issue is unmocked settings loading blocking the auth function"
        )
        sys.exit(0)
    else:
        print("\n🤔 INCONCLUSIVE: Need to investigate further")
        sys.exit(1)
