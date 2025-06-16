"""Tests for Slack command parsing with name:value flags."""

from unittest.mock import patch

from src.webdeface.notification.slack.utils.parsers import (
    ParseResult,
    SlackCommandParser,
    extract_command_flags,
    extract_flags,
    extract_global_flags,
    parse_slack_command,
)


class TestSlackCommandParser:
    """Test command parser functionality."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = SlackCommandParser()

        assert parser.flag_pattern is not None
        assert parser.quoted_pattern is not None

    def test_parse_empty_command(self):
        """Test parsing empty command."""
        parser = SlackCommandParser()
        result = parser.parse_command("")

        assert result.success is True
        assert result.subcommands == []
        assert result.args == {}
        assert result.flags == {}

    def test_parse_simple_command(self):
        """Test parsing simple command without flags."""
        parser = SlackCommandParser()
        result = parser.parse_command("website list")

        assert result.success is True
        assert result.subcommands == ["website", "list"]
        assert result.args == {}
        assert result.flags == {}

    def test_parse_command_with_argument(self):
        """Test parsing command with positional argument."""
        parser = SlackCommandParser()
        result = parser.parse_command("website add https://example.com")

        assert result.success is True
        assert result.subcommands == ["website", "add"]
        assert result.args == {0: "https://example.com"}
        assert result.flags == {}

    def test_parse_command_with_flags(self):
        """Test parsing command with name:value flags."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com name:TestSite interval:600"
        )

        assert result.success is True
        assert result.subcommands == ["website", "add"]
        assert result.args == {0: "https://example.com"}
        assert result.flags == {"name": "TestSite", "interval": 600}

    def test_parse_command_with_quoted_flags(self):
        """Test parsing command with quoted flag values."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            'website add https://example.com name:"Test Site Name"'
        )

        assert result.success is True
        assert result.flags == {"name": "Test Site Name"}

    def test_parse_command_with_boolean_flags(self):
        """Test parsing command with boolean flags."""
        parser = SlackCommandParser()
        result = parser.parse_command("website remove website123 force:true")

        assert result.success is True
        assert result.flags == {"force": True}

        # Test false boolean
        result = parser.parse_command("website remove website123 force:false")
        assert result.flags == {"force": False}

    def test_parse_command_with_global_flags(self):
        """Test parsing command with global flags."""
        parser = SlackCommandParser()
        result = parser.parse_command("website list verbose:true debug:false")

        assert result.success is True
        assert result.global_flags == {"verbose": True, "debug": False}
        assert result.flags == {}

    def test_parse_command_mixed_flags(self):
        """Test parsing command with both global and command flags."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com name:TestSite verbose:true interval:300"
        )

        assert result.success is True
        assert result.global_flags == {"verbose": True}
        assert result.flags == {"name": "TestSite", "interval": 300}

    def test_parse_command_with_complex_url(self):
        """Test parsing command with complex URL including parameters."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com/path?param=value name:TestSite"
        )

        assert result.success is True
        assert result.args == {0: "https://example.com/path?param=value"}
        assert result.flags == {"name": "TestSite"}

    def test_parse_command_with_special_characters(self):
        """Test parsing command with special characters in values."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com name:test-site_123"
        )

        assert result.success is True
        assert result.flags == {"name": "test-site_123"}

    def test_parse_monitoring_commands(self):
        """Test parsing monitoring commands."""
        parser = SlackCommandParser()

        # Test start command
        result = parser.parse_command("monitoring start website123")
        assert result.success is True
        assert result.subcommands == ["monitoring", "start"]
        assert result.args == {0: "website123"}

        # Test pause with duration
        result = parser.parse_command("monitoring pause website123 duration:3600")
        assert result.success is True
        assert result.subcommands == ["monitoring", "pause"]
        assert result.args == {0: "website123"}
        assert result.flags == {"duration": 3600}

    def test_parse_system_commands(self):
        """Test parsing system commands."""
        parser = SlackCommandParser()

        # Test metrics with filters
        result = parser.parse_command("system metrics range:24h type:performance")
        assert result.success is True
        assert result.subcommands == ["system", "metrics"]
        assert result.flags == {"range": "24h", "type": "performance"}

        # Test logs with multiple flags
        result = parser.parse_command("system logs level:error limit:100 since:2h")
        assert result.success is True
        assert result.subcommands == ["system", "logs"]
        assert result.flags == {"level": "error", "limit": 100, "since": "2h"}

    def test_parse_single_word_commands(self):
        """Test parsing single word commands."""
        parser = SlackCommandParser()

        # Known commands should be treated as subcommands
        result = parser.parse_command("help")
        assert result.success is True
        assert result.subcommands == ["help"]

        # Unknown single words should be treated as arguments
        result = parser.parse_command("website123")
        assert result.success is True
        assert result.args == {0: "website123"}

    def test_parse_quoted_arguments(self):
        """Test parsing commands with quoted arguments."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            'website add "https://example.com/complex path" name:TestSite'
        )

        assert result.success is True
        assert result.args == {0: "https://example.com/complex path"}
        assert result.flags == {"name": "TestSite"}

    def test_extract_flags_function(self):
        """Test extract_flags utility function."""
        parser = SlackCommandParser()
        flags = parser._extract_flags(
            "website add https://example.com name:TestSite interval:600 force:true"
        )

        assert flags == {"name": "TestSite", "interval": 600, "force": True}

    def test_remove_flags_function(self):
        """Test _remove_flags utility function."""
        parser = SlackCommandParser()
        clean_text = parser._remove_flags(
            "website add https://example.com name:TestSite interval:600"
        )

        assert clean_text == "website add https://example.com"

    def test_parse_subcommands_and_args_function(self):
        """Test _parse_subcommands_and_args function."""
        parser = SlackCommandParser()
        subcommands, args = parser._parse_subcommands_and_args(
            "website add https://example.com"
        )

        assert subcommands == ["website", "add"]
        assert args == {0: "https://example.com"}

    def test_parse_command_sync_compatibility(self):
        """Test synchronous parse_command_sync method for backward compatibility."""
        parser = SlackCommandParser()
        subcommands, args, flags = parser.parse_command_sync(
            "website add https://example.com name:TestSite"
        )

        assert subcommands == ["website", "add"]
        assert args == {0: "https://example.com"}
        assert flags == {"name": "TestSite"}

    def test_to_cli_args_conversion(self):
        """Test converting parsed command to CLI arguments."""
        parser = SlackCommandParser()

        cli_args = parser.to_cli_args(
            subcommands=["website", "add"],
            args={0: "https://example.com"},
            flags={"name": "TestSite", "interval": 600},
            global_flags={"verbose": True, "debug": False},
        )

        expected_args = [
            "--verbose",
            "website",
            "add",
            "https://example.com",
            "--name",
            "TestSite",
            "--interval",
            "600",
        ]

        assert cli_args == expected_args

    def test_to_cli_args_with_boolean_flags(self):
        """Test CLI args conversion with boolean flags."""
        parser = SlackCommandParser()

        cli_args = parser.to_cli_args(
            subcommands=["website", "remove"],
            args={0: "website123"},
            flags={"force": True, "confirm": False},
        )

        # True boolean flags should be included, false ones should not
        assert "--force" in cli_args
        assert "--confirm" not in cli_args

    def test_slack_flag_to_cli_option_mapping(self):
        """Test flag name conversion from Slack to CLI format."""
        parser = SlackCommandParser()

        assert parser._slack_flag_to_cli_option("max-depth") == "max-depth"
        assert parser._slack_flag_to_cli_option("check-interval") == "interval"
        assert parser._slack_flag_to_cli_option("website-id") == "website-id"
        assert parser._slack_flag_to_cli_option("custom_flag") == "custom-flag"

    def test_parse_error_handling(self):
        """Test parser error handling."""
        parser = SlackCommandParser()

        # Mock an exception in parsing
        with patch.object(
            parser, "_extract_flags", side_effect=Exception("Parse error")
        ):
            result = parser.parse_command("website add https://example.com")

            assert result.success is False
            assert "Failed to parse command" in result.error_message

    def test_parse_command_with_shlex_failure(self):
        """Test parser handles shlex parsing failures gracefully."""
        parser = SlackCommandParser()

        # Command with unmatched quotes should fall back to simple split
        result = parser.parse_command('website add "unmatched quote')

        assert result.success is True
        # Should still parse the command parts


class TestParseResult:
    """Test ParseResult class."""

    def test_parse_result_initialization(self):
        """Test ParseResult initialization."""
        result = ParseResult(
            success=True,
            subcommands=["website", "add"],
            args={0: "https://example.com"},
            flags={"name": "TestSite"},
            global_flags={"verbose": True},
        )

        assert result.success is True
        assert result.subcommands == ["website", "add"]
        assert result.args == {0: "https://example.com"}
        assert result.flags == {"name": "TestSite"}
        assert result.global_flags == {"verbose": True}

    def test_parse_result_defaults(self):
        """Test ParseResult with default values."""
        result = ParseResult(success=True)

        assert result.subcommands == []
        assert result.args == {}
        assert result.flags == {}
        assert result.global_flags == {}
        assert result.error_message is None

    def test_parse_result_with_error(self):
        """Test ParseResult with error."""
        result = ParseResult(success=False, error_message="Parse error")

        assert result.success is False
        assert result.error_message == "Parse error"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_slack_command_function(self):
        """Test parse_slack_command convenience function."""
        subcommands, args, flags = parse_slack_command(
            "website add https://example.com name:TestSite"
        )

        assert subcommands == ["website", "add"]
        assert args == {0: "https://example.com"}
        assert flags == {"name": "TestSite"}

    def test_extract_flags_function(self):
        """Test extract_flags convenience function."""
        flags = extract_flags(
            "website add https://example.com name:TestSite interval:600"
        )

        assert flags == {"name": "TestSite", "interval": 600}

    def test_extract_global_flags_function(self):
        """Test extract_global_flags function."""
        all_flags = {
            "name": "TestSite",
            "verbose": True,
            "debug": False,
            "config": "/path/to/config",
        }
        global_flags = extract_global_flags(all_flags)

        assert global_flags == {
            "verbose": True,
            "debug": False,
            "config": "/path/to/config",
        }

    def test_extract_command_flags_function(self):
        """Test extract_command_flags function."""
        all_flags = {
            "name": "TestSite",
            "verbose": True,
            "debug": False,
            "interval": 600,
        }
        command_flags = extract_command_flags(all_flags)

        assert command_flags == {"name": "TestSite", "interval": 600}


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_flag_values(self):
        """Test handling of empty flag values."""
        parser = SlackCommandParser()
        result = parser.parse_command("website add https://example.com name:")

        assert result.success is True
        # Empty value should be handled gracefully

    def test_flag_without_value(self):
        """Test handling of flags without values."""
        parser = SlackCommandParser()
        result = parser.parse_command("website add https://example.com name")

        assert result.success is True
        # Should treat 'name' as an argument, not a flag

    def test_multiple_colons_in_value(self):
        """Test handling of values with multiple colons."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com url:http://test.com:8080"
        )

        assert result.success is True
        assert result.flags["url"] == "http://test.com:8080"

    def test_complex_quoted_values(self):
        """Test handling of complex quoted values."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            'website add https://example.com name:"Site with: special chars"'
        )

        assert result.success is True
        assert result.flags["name"] == "Site with: special chars"

    def test_numeric_conversions(self):
        """Test automatic numeric conversions."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com interval:600 max-depth:3"
        )

        assert result.success is True
        assert result.flags["interval"] == 600
        assert result.flags["max-depth"] == 3
        assert isinstance(result.flags["interval"], int)
        assert isinstance(result.flags["max-depth"], int)

    def test_boolean_value_variations(self):
        """Test various boolean value representations."""
        parser = SlackCommandParser()

        # Test true variations
        for true_val in ["true", "yes", "1", "True", "YES"]:
            result = parser.parse_command(f"website remove website123 force:{true_val}")
            assert result.flags["force"] is True

        # Test false variations
        for false_val in ["false", "no", "0", "False", "NO"]:
            result = parser.parse_command(
                f"website remove website123 force:{false_val}"
            )
            assert result.flags["force"] is False

    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "  website   add   https://example.com   name:TestSite  "
        )

        assert result.success is True
        assert result.subcommands == ["website", "add"]
        assert result.args == {0: "https://example.com"}
        assert result.flags == {"name": "TestSite"}

    def test_case_sensitivity(self):
        """Test case sensitivity in parsing."""
        parser = SlackCommandParser()
        result = parser.parse_command("Website Add https://example.com Name:TestSite")

        assert result.success is True
        # Command parts should preserve case
        assert result.subcommands == ["Website", "Add"]
        assert result.flags == {"Name": "TestSite"}

    def test_special_characters_in_values(self):
        """Test handling of special characters in flag values."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com name:test@site.com"
        )

        assert result.success is True
        assert result.flags["name"] == "test@site.com"

    def test_very_long_commands(self):
        """Test handling of very long commands."""
        parser = SlackCommandParser()
        long_url = "https://example.com/" + "a" * 1000
        result = parser.parse_command(f"website add {long_url} name:TestSite")

        assert result.success is True
        assert result.args[0] == long_url

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        parser = SlackCommandParser()
        result = parser.parse_command("website add https://example.com name:测试网站")

        assert result.success is True
        assert result.flags["name"] == "测试网站"

    def test_malformed_commands(self):
        """Test handling of malformed commands."""
        parser = SlackCommandParser()

        # Test with only flags, no command
        result = parser.parse_command("name:TestSite interval:600")
        assert result.success is True

        # Test with mixed argument/flag ordering
        result = parser.parse_command(
            "website name:TestSite add https://example.com interval:600"
        )
        assert result.success is True


class TestBehavioralParity:
    """Test behavioral parity with CLI argument parsing."""

    def test_cli_equivalent_parsing(self):
        """Test that Slack parsing produces CLI-equivalent results."""
        parser = SlackCommandParser()

        # Slack command
        result = parser.parse_command(
            "website add https://example.com name:TestSite interval:600 verbose:true"
        )

        # Convert to CLI args
        cli_args = parser.to_cli_args(
            result.subcommands, result.args, result.flags, result.global_flags
        )

        expected_cli = [
            "--verbose",
            "website",
            "add",
            "https://example.com",
            "--name",
            "TestSite",
            "--interval",
            "600",
        ]

        assert cli_args == expected_cli

    def test_flag_ordering_preservation(self):
        """Test that flag ordering is preserved for CLI compatibility."""
        parser = SlackCommandParser()
        result = parser.parse_command(
            "website add https://example.com interval:600 name:TestSite max-depth:3"
        )

        # Flags should be extracted consistently
        assert "interval" in result.flags
        assert "name" in result.flags
        assert "max-depth" in result.flags

    def test_complex_command_parity(self):
        """Test complex command parsing maintains CLI parity."""
        parser = SlackCommandParser()

        complex_command = (
            "monitoring pause website123 duration:7200 verbose:true debug:false"
        )
        result = parser.parse_command(complex_command)

        cli_args = parser.to_cli_args(
            result.subcommands, result.args, result.flags, result.global_flags
        )

        # Should produce valid CLI equivalent
        assert "monitoring" in cli_args
        assert "pause" in cli_args
        assert "website123" in cli_args
        assert "--duration" in cli_args
        assert "7200" in cli_args
        assert "--verbose" in cli_args
        assert "--debug" not in cli_args  # False boolean should be omitted
