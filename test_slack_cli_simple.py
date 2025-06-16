#!/usr/bin/env python3
"""Simple validation script for Slack CLI integration components."""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_basic_components():
    """Test basic Slack CLI components in isolation."""
    print("🧪 Testing Slack CLI Integration Components...")

    # Test 1: Parser
    try:
        from webdeface.notification.slack.utils.parsers import (
            SlackCommandParser,
        )

        parser = SlackCommandParser()
        result = await parser.parse_command("website add https://example.com name:Test")

        assert result.success, "Parser should parse command successfully"
        assert result.subcommands == ["website", "add"], "Should parse subcommands"
        assert result.args == ["https://example.com"], "Should parse args"
        assert result.flags.get("name") == "Test", "Should parse flags"

        print("✅ Parser test passed")
    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        return False

    # Test 2: Formatter
    try:
        from webdeface.cli.types import CommandResult
        from webdeface.notification.slack.utils.formatters import SlackFormatter

        formatter = SlackFormatter()
        cmd_result = CommandResult(
            success=True, message="Test success", data={"test": "data"}
        )
        response = formatter.format_command_response(cmd_result, user_id="U123")

        assert "text" in response, "Response should have text"
        assert "blocks" in response, "Response should have blocks"
        assert "✅" in response["text"], "Success should have checkmark"

        print("✅ Formatter test passed")
    except Exception as e:
        print(f"❌ Formatter test failed: {e}")
        return False

    # Test 3: Validator
    try:
        from webdeface.notification.slack.utils.validators import (
            CommandValidator,
        )

        validator = CommandValidator()
        validation = await validator.validate_command(
            subcommands=["website", "add"],
            args=["https://example.com"],
            flags={"name": "Test"},
        )

        assert validation.is_valid, "Valid command should pass validation"

        print("✅ Validator test passed")
    except Exception as e:
        print(f"❌ Validator test failed: {e}")
        return False

    # Test 4: Command parsing variations
    try:
        parser = SlackCommandParser()

        # Test empty command
        result = await parser.parse_command("")
        assert result.success
        assert result.subcommands == []

        # Test help command
        result = await parser.parse_command("help website")
        assert result.success
        assert result.subcommands == ["help", "website"]

        # Test complex flags
        result = await parser.parse_command(
            "monitoring start site-123 interval:600 notify:true"
        )
        assert result.success
        assert result.subcommands == ["monitoring", "start"]
        assert result.args == ["site-123"]
        assert result.flags["interval"] == "600"
        assert result.flags["notify"] == "true"

        print("✅ Command parsing variations test passed")
    except Exception as e:
        print(f"❌ Command parsing variations test failed: {e}")
        return False

    # Test 5: Response formatting variations
    try:
        formatter = SlackFormatter()

        # Test error response
        error_response = formatter.format_error_response("Test error message")
        assert "❌" in error_response["text"]
        assert error_response["response_type"] == "ephemeral"

        # Test help response
        help_content = {
            "title": "Test Commands",
            "description": "Test description",
            "commands": [{"name": "test", "description": "Test command"}],
        }
        help_response = formatter.format_help_response(help_content)
        assert "Test Commands" in help_response["text"]
        assert "blocks" in help_response

        print("✅ Response formatting variations test passed")
    except Exception as e:
        print(f"❌ Response formatting variations test failed: {e}")
        return False

    return True


async def test_integration_structure():
    """Test that integration components can be imported and instantiated."""
    print("\n🔗 Testing Integration Structure...")

    try:
        from webdeface.notification.slack.integration import SlackCLIIntegration

        # Test instantiation
        integration = SlackCLIIntegration()
        assert hasattr(integration, "command_router"), "Should have command router"

        # Test available commands
        commands_info = await integration.get_available_commands()
        assert "commands" in commands_info, "Should return commands info"
        assert "cli_syntax" in commands_info, "Should return CLI syntax info"
        assert "examples" in commands_info, "Should return examples"

        print("✅ Integration structure test passed")
        return True
    except Exception as e:
        print(f"❌ Integration structure test failed: {e}")
        return False


def test_permissions_enum():
    """Test permissions enum."""
    print("\n🔒 Testing Permissions...")

    try:
        from webdeface.notification.slack.permissions import Permission

        # Test basic permissions exist
        assert hasattr(Permission, "VIEW_SITES")
        assert hasattr(Permission, "MANAGE_SITES")
        assert hasattr(Permission, "VIEW_SYSTEM")
        assert hasattr(Permission, "VIEW_METRICS")

        print("✅ Permissions test passed")
        return True
    except Exception as e:
        print(f"❌ Permissions test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Slack CLI Integration Validation")
    print("=" * 50)

    success = True

    # Test basic components
    if not await test_basic_components():
        success = False

    # Test integration structure
    if not await test_integration_structure():
        success = False

    # Test permissions
    if not test_permissions_enum():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 All Slack CLI Integration tests passed!")
        print("\n📋 Components validated:")
        print("  • Command parser (args, flags, subcommands)")
        print("  • Response formatter (success, error, help)")
        print("  • Input validator (command validation)")
        print("  • Integration structure (router, handlers)")
        print("  • Permissions system")
        print("\n✅ Ready for Slack Bolt app integration!")
    else:
        print("❌ Some tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
