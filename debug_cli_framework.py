#!/usr/bin/env python3
"""Debug script to investigate CLI framework issues."""

import asyncio
import traceback

from click.testing import CliRunner


def test_basic_import():
    """Test if CLI module can be imported."""
    print("=== Testing CLI Module Import ===")
    try:
        print("✅ CLI module imported successfully")
        return True
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        traceback.print_exc()
        return False


def test_cli_help_command():
    """Test basic CLI help command."""
    print("\n=== Testing CLI Help Command ===")
    try:
        from src.webdeface.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        print(f"Exit code: {result.exit_code}")
        print(f"Output length: {len(result.output)}")
        if result.exit_code != 0:
            print(f"❌ Help command failed with exit code {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
            if result.exception:
                traceback.print_exception(
                    type(result.exception),
                    result.exception,
                    result.exception.__traceback__,
                )
        else:
            print("✅ Help command succeeded")
        return result.exit_code == 0
    except Exception as e:
        print(f"❌ Help command test failed: {e}")
        traceback.print_exc()
        return False


def test_cli_groups():
    """Test CLI subgroups."""
    print("\n=== Testing CLI Subgroups ===")
    try:
        from src.webdeface.cli.main import cli

        runner = CliRunner()

        groups = ["website", "monitoring", "system"]
        for group in groups:
            result = runner.invoke(cli, [group, "--help"])
            print(f"{group} group - Exit code: {result.exit_code}")
            if result.exit_code != 0:
                print(f"❌ {group} group failed")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            else:
                print(f"✅ {group} group succeeded")
        return True
    except Exception as e:
        print(f"❌ CLI groups test failed: {e}")
        traceback.print_exc()
        return False


def test_async_command_decorator():
    """Test the async command decorator."""
    print("\n=== Testing Async Command Decorator ===")
    try:
        from src.webdeface.cli.main import async_command

        @async_command
        async def test_async_func():
            await asyncio.sleep(0.01)
            return "success"

        # Check if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            print(f"❌ Already in event loop: {loop}")
            print("This explains the asyncio.run() conflict!")
            return False
        except RuntimeError:
            print("✅ No running event loop detected")

        # Try to call the decorated function
        result = test_async_func()
        print(f"✅ Async command decorator result: {result}")
        return True

    except Exception as e:
        print(f"❌ Async command decorator test failed: {e}")
        traceback.print_exc()
        return False


def test_entry_point_resolution():
    """Test entry point module resolution."""
    print("\n=== Testing Entry Point Resolution ===")
    try:
        # Test the actual entry point from pyproject.toml
        import importlib

        # Try to import as configured in pyproject.toml
        try:
            module = importlib.import_module("webdeface.main")
            print("❌ Can import 'webdeface.main' - entry point mismatch detected!")
        except ImportError:
            print("✅ Cannot import 'webdeface.main' - as expected with src/ structure")

        # Try to import the actual module
        try:
            module = importlib.import_module("src.webdeface.main")
            print("✅ Can import 'src.webdeface.main' - actual module structure")
            main_cli = getattr(module, "main_cli", None)
            if main_cli:
                print("✅ main_cli function found")
            else:
                print("❌ main_cli function not found")
        except ImportError as e:
            print(f"❌ Cannot import 'src.webdeface.main': {e}")

        return True
    except Exception as e:
        print(f"❌ Entry point resolution test failed: {e}")
        traceback.print_exc()
        return False


def test_click_command_registration():
    """Test Click command registration."""
    print("\n=== Testing Click Command Registration ===")
    try:
        from src.webdeface.cli.main import cli

        # Check if commands are properly registered
        print(f"CLI commands: {list(cli.commands.keys())}")
        print(
            f"CLI groups: {[name for name, cmd in cli.commands.items() if hasattr(cmd, 'commands')]}"
        )

        # Check specific groups
        for group_name in ["website", "monitoring", "system"]:
            if group_name in cli.commands:
                group = cli.commands[group_name]
                if hasattr(group, "commands"):
                    print(f"{group_name} commands: {list(group.commands.keys())}")
                else:
                    print(f"❌ {group_name} is not a proper group")
            else:
                print(f"❌ {group_name} group not found")

        return True
    except Exception as e:
        print(f"❌ Command registration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("🪲 CLI Framework Diagnostic Tests")
    print("=" * 50)

    tests = [
        test_basic_import,
        test_entry_point_resolution,
        test_click_command_registration,
        test_cli_help_command,
        test_cli_groups,
        test_async_command_decorator,
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
    print("🪲 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed < total:
        print("\n🔍 LIKELY ROOT CAUSES:")
        if not results[0]:  # import test failed
            print("1. CLI module import issues - check import paths")
        if not results[1]:  # entry point test failed
            print("2. Entry point mismatch - pyproject.toml vs src/ structure")
        if not results[5]:  # async decorator test failed
            print("3. Async event loop conflicts - asyncio.run() in running loop")
        if not results[2]:  # command registration failed
            print("4. Click command registration failures")


if __name__ == "__main__":
    main()
