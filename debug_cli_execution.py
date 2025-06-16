#!/usr/bin/env python3
"""Targeted debug for CLI command execution issues."""

import traceback
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner


def test_actual_command_execution():
    """Test actual command execution with mocks."""
    print("=== Testing Actual Command Execution ===")
    try:
        from src.webdeface.cli.main import cli

        # Set up mocks exactly like the tests
        mock_storage = AsyncMock()
        mock_website = MagicMock()
        mock_website.id = "test-website-123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = "2024-01-01T00:00:00Z"
        mock_website.last_checked_at = None

        mock_storage.create_website.return_value = mock_website
        mock_storage.get_website_by_url.return_value = None

        mock_orchestrator = AsyncMock()
        mock_orchestrator.schedule_website_monitoring.return_value = "execution-123"

        runner = CliRunner()

        with patch(
            "src.webdeface.cli.main.get_storage_manager", return_value=mock_storage
        ), patch(
            "src.webdeface.cli.main.get_scheduling_orchestrator",
            return_value=mock_orchestrator,
        ):
            result = runner.invoke(
                cli, ["website", "add", "https://example.com", "--name", "Test Website"]
            )

            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")

            if result.exception:
                print("Exception traceback:")
                traceback.print_exception(
                    type(result.exception),
                    result.exception,
                    result.exception.__traceback__,
                )

            # Try a simple help command to see the difference
            help_result = runner.invoke(cli, ["website", "--help"])
            print(f"\nHelp exit code: {help_result.exit_code}")
            print(f"Help output length: {len(help_result.output)}")

            return result.exit_code == 0

    except Exception as e:
        print(f"❌ Command execution test failed: {e}")
        traceback.print_exc()
        return False


def test_decorator_preservation():
    """Test if async_command decorator preserves function metadata."""
    print("\n=== Testing Decorator Function Preservation ===")
    try:
        import inspect

        from src.webdeface.cli.main import async_command

        # Test function with Click decorators
        async def test_func(ctx, arg1: str, arg2: int = 5):
            """Test function docstring."""
            return f"result: {arg1}, {arg2}"

        # Apply the async_command decorator
        wrapped = async_command(test_func)

        print(f"Original function name: {test_func.__name__}")
        print(f"Wrapped function name: {wrapped.__name__}")
        print(f"Original signature: {inspect.signature(test_func)}")
        print(f"Wrapped signature: {inspect.signature(wrapped)}")
        print(f"Original docstring: {test_func.__doc__}")
        print(f"Wrapped docstring: {wrapped.__doc__}")

        # Check if wrapped function has Click-required attributes
        for attr in ["__click_params__", "__name__", "__doc__"]:
            orig_val = getattr(test_func, attr, "NOT_FOUND")
            wrap_val = getattr(wrapped, attr, "NOT_FOUND")
            print(f"{attr}: orig={orig_val}, wrapped={wrap_val}")

        return True

    except Exception as e:
        print(f"❌ Decorator preservation test failed: {e}")
        traceback.print_exc()
        return False


def test_click_command_inspection():
    """Inspect actual Click commands."""
    print("\n=== Inspecting Click Commands ===")
    try:
        import inspect

        from src.webdeface.cli.main import cli

        # Check the website group
        website_group = cli.commands["website"]
        print(f"Website group type: {type(website_group)}")
        print(f"Website commands: {list(website_group.commands.keys())}")

        # Check a specific command
        for cmd_name, cmd in website_group.commands.items():
            print(f"\nCommand '{cmd_name}':")
            print(f"  Type: {type(cmd)}")
            print(f"  Callback: {cmd.callback}")
            if hasattr(cmd.callback, "__name__"):
                print(f"  Callback name: {cmd.callback.__name__}")
            if hasattr(cmd, "params"):
                print(f"  Parameters: {[p.name for p in cmd.params]}")

            # Try to get signature
            try:
                sig = inspect.signature(cmd.callback)
                print(f"  Signature: {sig}")
            except Exception as e:
                print(f"  Signature error: {e}")

        return True

    except Exception as e:
        print(f"❌ Click command inspection failed: {e}")
        traceback.print_exc()
        return False


def test_entry_point_mismatch():
    """Test the entry point mismatch issue."""
    print("\n=== Testing Entry Point Mismatch ===")
    try:
        # The pyproject.toml has: webdeface-monitor = "webdeface.main:main_cli"
        # But the actual module is at: src.webdeface.main:main_cli

        # Test what happens when Click tries to resolve the entry point
        try:
            import webdeface.main

            print("❌ CRITICAL: Can import webdeface.main - this is wrong!")
            print(
                "This means there's a duplicate module or incorrect import resolution"
            )

            # Check what's in this module
            main_cli = getattr(webdeface.main, "main_cli", None)
            if main_cli:
                print("Found main_cli in webdeface.main")
            else:
                print("No main_cli in webdeface.main")

        except ImportError:
            print("✅ Cannot import webdeface.main (expected)")

        # Test the correct import
        try:
            import src.webdeface.main

            print("✅ Can import src.webdeface.main")
            main_cli = getattr(src.webdeface.main, "main_cli", None)
            if main_cli:
                print("✅ Found main_cli in src.webdeface.main")
            else:
                print("❌ No main_cli in src.webdeface.main")
        except ImportError as e:
            print(f"❌ Cannot import src.webdeface.main: {e}")

        return True

    except Exception as e:
        print(f"❌ Entry point test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run targeted diagnostic tests."""
    print("🪲 CLI Command Execution Diagnostics")
    print("=" * 50)

    tests = [
        test_entry_point_mismatch,
        test_decorator_preservation,
        test_click_command_inspection,
        test_actual_command_execution,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("🔍 ROOT CAUSE ANALYSIS")
    print("=" * 50)


if __name__ == "__main__":
    main()
