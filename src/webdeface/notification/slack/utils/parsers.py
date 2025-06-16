"""CLI argument parsing utilities for Slack commands."""

import re
import shlex
from typing import Any, Optional

from ....utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class ParseResult:
    """Result of parsing a Slack command."""

    def __init__(
        self,
        success: bool,
        subcommands: list[str] = None,
        args: dict[str, Any] = None,
        flags: dict[str, Any] = None,
        global_flags: dict[str, Any] = None,
        error_message: str = None,
    ):
        self.success = success
        self.subcommands = subcommands or []
        self.args = args or {}
        self.flags = flags or {}
        self.global_flags = global_flags or {}
        self.error_message = error_message


class SlackCommandParser:
    """Parses Slack command text into CLI-compatible arguments and flags."""

    def __init__(self):
        # Pattern to match key:value flags in Slack commands
        self.flag_pattern = re.compile(r'(\w+):([\w\-_./:]+|"[^"]*")')
        # Pattern to match quoted arguments
        self.quoted_pattern = re.compile(r'"([^"]*)"')

    def parse_command(self, text: str) -> ParseResult:
        """
        Parse Slack command text into CLI-compatible arguments and flags.

        Args:
            text: Slack command text (e.g., "website add https://example.com name:MyWebsite")

        Returns:
            ParseResult object with parsed components
        """
        try:
            if not text or not text.strip():
                return ParseResult(success=True, subcommands=[], args={}, flags={})

            # Extract flags first (key:value pairs)
            flags = self._extract_flags(text)

            # Separate global flags from command flags
            global_flags = extract_global_flags(flags)
            command_flags = extract_command_flags(flags)

            # Remove flags from text to get remaining arguments
            text_without_flags = self._remove_flags(text)

            # Parse remaining text into subcommands and positional arguments
            subcommands, args = self._parse_subcommands_and_args(text_without_flags)

            logger.debug(
                "Parsed Slack command",
                original_text=text,
                subcommands=subcommands,
                args=args,
                flags=command_flags,
                global_flags=global_flags,
            )

            return ParseResult(
                success=True,
                subcommands=subcommands,
                args=args,
                flags=command_flags,
                global_flags=global_flags,
            )

        except Exception as e:
            logger.error("Failed to parse Slack command", text=text, error=str(e))
            return ParseResult(
                success=False, error_message=f"Failed to parse command: {str(e)}"
            )

    def parse_command_sync(
        self, text: str
    ) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
        """
        Synchronous version of parse_command for backward compatibility.

        Args:
            text: Slack command text (e.g., "website add https://example.com name:MyWebsite")

        Returns:
            Tuple of (subcommands, args, flags)
            - subcommands: List of command parts (e.g., ["website", "add"])
            - args: Dict of positional arguments by position
            - flags: Dict of flag key-value pairs
        """
        if not text or not text.strip():
            return [], {}, {}

        # Extract flags first (key:value pairs)
        flags = self._extract_flags(text)

        # Remove flags from text to get remaining arguments
        text_without_flags = self._remove_flags(text)

        # Parse remaining text into subcommands and positional arguments
        subcommands, args = self._parse_subcommands_and_args(text_without_flags)

        logger.debug(
            "Parsed Slack command",
            original_text=text,
            subcommands=subcommands,
            args=args,
            flags=flags,
        )

        return subcommands, args, flags

    def _extract_flags(self, text: str) -> dict[str, Any]:
        """Extract key:value flags from command text."""
        flags = {}

        for match in self.flag_pattern.finditer(text):
            key = match.group(1)
            value = match.group(2)

            # Remove quotes from value if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            # Convert common boolean flags
            if value.lower() in ("true", "yes", "1"):
                value = True
            elif value.lower() in ("false", "no", "0"):
                value = False
            # Try to convert to int if possible
            elif value.isdigit():
                value = int(value)

            flags[key] = value

        return flags

    def _remove_flags(self, text: str) -> str:
        """Remove flag patterns from text to get clean arguments."""
        # Remove all key:value patterns
        text_without_flags = self.flag_pattern.sub("", text)
        # Clean up extra whitespace
        return " ".join(text_without_flags.split())

    def _parse_subcommands_and_args(
        self, text: str
    ) -> tuple[list[str], dict[str, Any]]:
        """Parse subcommands and positional arguments from cleaned text."""
        if not text.strip():
            return [], {}

        try:
            # Use shlex to properly handle quoted arguments
            parts = shlex.split(text)
        except ValueError:
            # If shlex fails, fall back to simple split
            parts = text.split()

        subcommands = []
        args = {}

        # First parts are typically subcommands (website, add, etc.)
        # Last parts are typically arguments (URLs, IDs, etc.)

        if len(parts) == 1:
            # Could be either a subcommand or an argument
            if parts[0] in [
                "website",
                "monitoring",
                "system",
                "add",
                "remove",
                "list",
                "status",
                "start",
                "stop",
                "pause",
                "resume",
                "check",
                "health",
                "metrics",
                "logs",
            ]:
                subcommands = [parts[0]]
            else:
                args[0] = parts[0]
        elif len(parts) >= 2:
            # Identify subcommands vs arguments
            # Known subcommand patterns
            known_commands = {
                "website": ["add", "remove", "list", "status"],
                "monitoring": ["start", "stop", "pause", "resume", "check"],
                "system": ["status", "health", "metrics", "logs"],
            }

            if parts[0] in known_commands:
                subcommands.append(parts[0])
                if len(parts) > 1 and parts[1] in known_commands[parts[0]]:
                    subcommands.append(parts[1])
                    # Remaining parts are arguments
                    for i, arg in enumerate(parts[2:]):
                        args[i] = arg
                else:
                    # Second part is an argument
                    for i, arg in enumerate(parts[1:]):
                        args[i] = arg
            else:
                # All parts are arguments
                for i, arg in enumerate(parts):
                    args[i] = arg

        return subcommands, args

    def to_cli_args(
        self,
        subcommands: list[str],
        args: dict[str, Any],
        flags: dict[str, Any],
        global_flags: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        """
        Convert parsed Slack command to CLI argument list.

        Args:
            subcommands: List of subcommand parts
            args: Dict of positional arguments
            flags: Dict of command-specific flags
            global_flags: Dict of global flags (verbose, debug, config)

        Returns:
            List of CLI arguments suitable for Click framework
        """
        cli_args = []

        # Add global flags first
        if global_flags:
            if global_flags.get("verbose"):
                cli_args.append("--verbose")
            if global_flags.get("debug"):
                cli_args.append("--debug")
            if global_flags.get("config"):
                cli_args.extend(["--config", str(global_flags["config"])])

        # Add subcommands
        cli_args.extend(subcommands)

        # Add positional arguments in order
        for i in sorted(args.keys()):
            cli_args.append(str(args[i]))

        # Add flags as CLI options
        for key, value in flags.items():
            # Convert Slack flag names to CLI option names
            cli_option = self._slack_flag_to_cli_option(key)

            if isinstance(value, bool) and value:
                cli_args.append(f"--{cli_option}")
            elif not isinstance(value, bool):
                cli_args.extend([f"--{cli_option}", str(value)])

        return cli_args

    def _slack_flag_to_cli_option(self, slack_flag: str) -> str:
        """Convert Slack flag name to CLI option name."""
        # Handle special mappings
        flag_mappings = {
            "website-id": "website-id",
            "max-depth": "max-depth",
            "check-interval": "interval",
        }

        return flag_mappings.get(slack_flag, slack_flag.replace("_", "-"))


def parse_slack_command(text: str) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """
    Convenience function to parse Slack command text.

    Args:
        text: Slack command text

    Returns:
        Tuple of (subcommands, args, flags)
    """
    parser = SlackCommandParser()
    return parser.parse_command(text)


def extract_flags(text: str) -> dict[str, Any]:
    """
    Convenience function to extract only flags from Slack command text.

    Args:
        text: Slack command text

    Returns:
        Dict of flag key-value pairs
    """
    parser = SlackCommandParser()
    _, _, flags = parser.parse_command(text)
    return flags


def extract_global_flags(flags: dict[str, Any]) -> dict[str, Any]:
    """
    Extract global flags (verbose, debug, config) from flag dictionary.

    Args:
        flags: Dictionary of all flags

    Returns:
        Dictionary containing only global flags
    """
    global_flag_names = {"verbose", "debug", "config"}
    return {k: v for k, v in flags.items() if k in global_flag_names}


def extract_command_flags(flags: dict[str, Any]) -> dict[str, Any]:
    """
    Extract command-specific flags (excluding global flags).

    Args:
        flags: Dictionary of all flags

    Returns:
        Dictionary containing only command-specific flags
    """
    global_flag_names = {"verbose", "debug", "config"}
    return {k: v for k, v in flags.items() if k not in global_flag_names}
