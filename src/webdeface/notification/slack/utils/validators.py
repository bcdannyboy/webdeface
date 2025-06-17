"""Input validation utilities for Slack commands."""

import re
from typing import Any, Optional
from urllib.parse import urlparse

from ....utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class SlackCommandValidator:
    """Validates Slack command arguments and flags."""

    def __init__(self):
        # URL validation pattern
        self.url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        # Valid log levels
        self.valid_log_levels = {"debug", "info", "warning", "error"}

        # Valid status filters
        self.valid_status_filters = {"active", "inactive", "all"}

        # Valid output formats
        self.valid_output_formats = {"table", "json"}

    def validate_command(
        self, subcommands: list[str], args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate complete command structure.

        Args:
            subcommands: List of command parts
            args: Dict of positional arguments
            flags: Dict of flags

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate command structure
            if not subcommands:
                return False, "Command is required (website, monitoring, or system)"

            if subcommands[0] not in ["website", "monitoring", "system", "help"]:
                return False, f"Unknown command group: {subcommands[0]}"

            # Route to specific validators
            if subcommands[0] == "website":
                return self._validate_website_command(subcommands, args, flags)
            elif subcommands[0] == "monitoring":
                return self._validate_monitoring_command(subcommands, args, flags)
            elif subcommands[0] == "system":
                return self._validate_system_command(subcommands, args, flags)
            elif subcommands[0] == "help":
                return True, None

            return True, None

        except Exception as e:
            logger.error("Error validating command", error=str(e))
            return False, f"Validation error: {str(e)}"

    def _validate_website_command(
        self, subcommands: list[str], args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate website commands."""
        if len(subcommands) < 2:
            # Check if we have an unknown command in args
            if 0 in args:
                unknown_cmd = str(args[0])
                valid_commands = ["add", "remove", "list", "status"]
                if unknown_cmd not in valid_commands:
                    return False, "Unknown website command"
            return False, "Website command is required (add, remove, list, status)"

        website_cmd = subcommands[1]

        if website_cmd == "add":
            return self._validate_website_add(args, flags)
        elif website_cmd == "remove":
            return self._validate_website_remove(args, flags)
        elif website_cmd == "list":
            return self._validate_website_list(args, flags)
        elif website_cmd == "status":
            return self._validate_website_status(args, flags)
        else:
            return False, f"Unknown website command: {website_cmd}"

    def _validate_website_add(
        self, args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate website add command."""
        # URL is required as first argument
        if 0 not in args:
            return False, "URL is required for website add command"

        url = str(args[0])
        is_valid_url, url_error = self.validate_url(url)
        if not is_valid_url:
            return False, f"Invalid URL: {url_error}"

        # Validate optional flags
        if "interval" in flags:
            interval = flags["interval"]
            if not isinstance(interval, int) or interval < 60:
                return False, "Interval must be at least 60 seconds"

        if "max-depth" in flags:
            max_depth = flags["max-depth"]
            if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 10:
                return False, "Max depth must be between 1 and 10"

        return True, None

    def _validate_website_remove(
        self, args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate website remove command."""
        if 0 not in args:
            return False, "Website ID is required for remove command"

        website_id = str(args[0])
        if not website_id.strip():
            return False, "Website ID cannot be empty"

        return True, None

    def _validate_website_list(
        self, args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate website list command."""
        # Validate status filter
        if "status" in flags:
            status = flags["status"]
            if status not in self.valid_status_filters:
                return (
                    False,
                    f"Invalid status filter. Must be one of: {', '.join(self.valid_status_filters)}",
                )

        # Validate format
        if "format" in flags:
            format_val = flags["format"]
            if format_val not in self.valid_output_formats:
                return (
                    False,
                    f"Invalid format. Must be one of: {', '.join(self.valid_output_formats)}",
                )

        return True, None

    def _validate_website_status(
        self, args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate website status command."""
        if 0 not in args:
            return False, "Website ID is required for status command"

        website_id = str(args[0])
        if not website_id.strip():
            return False, "Website ID cannot be empty"

        return True, None

    def _validate_monitoring_command(
        self, subcommands: list[str], args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate monitoring commands."""
        if len(subcommands) < 2:
            # Check if we have an unknown command in args
            if 0 in args:
                unknown_cmd = str(args[0])
                valid_commands = ["start", "stop", "pause", "resume", "check"]
                if unknown_cmd not in valid_commands:
                    return False, "Unknown monitoring command"
            return (
                False,
                "Monitoring command is required (start, stop, pause, resume, check)",
            )

        monitoring_cmd = subcommands[1]
        valid_commands = ["start", "stop", "pause", "resume", "check"]

        if monitoring_cmd not in valid_commands:
            return (
                False,
                f"Unknown monitoring command: {monitoring_cmd}. Valid commands: {', '.join(valid_commands)}",
            )

        # Check command requires website ID
        if monitoring_cmd == "check":
            if 0 not in args:
                return False, "Website ID is required for monitoring check command"

            website_id = str(args[0])
            if not website_id.strip():
                return False, "Website ID cannot be empty"

        # Other commands can optionally specify website-id flag
        if "website-id" in flags:
            website_id = str(flags["website-id"])
            if not website_id.strip():
                return False, "Website ID cannot be empty when specified"

        return True, None

    def _validate_system_command(
        self, subcommands: list[str], args: dict[str, Any], flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate system commands."""
        if len(subcommands) < 2:
            # Check if we have an unknown command in args
            if 0 in args:
                unknown_cmd = str(args[0])
                valid_commands = ["status", "health", "metrics", "logs"]
                if unknown_cmd not in valid_commands:
                    return False, "Unknown system command"
            return False, "System command is required (status, health, metrics, logs)"

        system_cmd = subcommands[1]
        valid_commands = ["status", "health", "metrics", "logs"]

        if system_cmd not in valid_commands:
            return (
                False,
                f"Unknown system command: {system_cmd}. Valid commands: {', '.join(valid_commands)}",
            )

        # Validate logs-specific flags
        if system_cmd == "logs":
            if "level" in flags:
                level = flags["level"]
                if level not in self.valid_log_levels:
                    return (
                        False,
                        f"Invalid log level. Must be one of: {', '.join(self.valid_log_levels)}",
                    )

            if "lines" in flags:
                lines = flags["lines"]
                if not isinstance(lines, int) or lines < 1 or lines > 1000:
                    return False, "Lines must be between 1 and 1000"

        return True, None

    def validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL format.

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"

        url = url.strip()

        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Validate with regex
        if not self.url_pattern.match(url):
            return False, "Invalid URL format"

        # Additional validation with urlparse
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "URL must include a domain"

            # Check for common invalid patterns
            if parsed.netloc.startswith(".") or parsed.netloc.endswith("."):
                return False, "Invalid domain format"

            return True, None

        except Exception:
            return False, "URL parsing failed"

    def validate_website_id(self, website_id: str) -> tuple[bool, Optional[str]]:
        """
        Validate website ID format.

        Args:
            website_id: Website ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not website_id or not website_id.strip():
            return False, "Website ID cannot be empty"

        website_id = website_id.strip()

        # Basic length check
        if len(website_id) < 3:
            return False, "Website ID too short"

        if len(website_id) > 100:
            return False, "Website ID too long"

        # Check for invalid characters (allow alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9_-]+$", website_id):
            return False, "Website ID contains invalid characters"

        return True, None

    def validate_global_flags(
        self, flags: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate global flags (verbose, debug, config).

        Args:
            flags: Dictionary of flags to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Verbose and debug should be boolean
        for flag_name in ["verbose", "debug"]:
            if flag_name in flags:
                value = flags[flag_name]
                if not isinstance(value, bool):
                    return False, f"{flag_name} flag must be true or false"

        # Config should be a valid file path string
        if "config" in flags:
            config_path = flags["config"]
            if not isinstance(config_path, str) or not config_path.strip():
                return False, "Config flag must be a valid file path"

        return True, None


def validate_arguments(
    subcommands: list[str], args: dict[str, Any], flags: dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate command arguments.

    Args:
        subcommands: List of command parts
        args: Dict of positional arguments
        flags: Dict of flags

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = SlackCommandValidator()
    return validator.validate_command(subcommands, args, flags)


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate URL.

    Args:
        url: URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = SlackCommandValidator()
    return validator.validate_url(url)


def validate_website_id(website_id: str) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate website ID.

    Args:
        website_id: Website ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = SlackCommandValidator()
    return validator.validate_website_id(website_id)


class ValidationResult:
    """Result of command validation."""

    def __init__(
        self, is_valid: bool, error_message: str = None, suggestions: list[str] = None
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.suggestions = suggestions or []


class CommandValidator:
    """Async wrapper for SlackCommandValidator."""

    def __init__(self):
        self.validator = SlackCommandValidator()

    async def validate_command(
        self,
        subcommands: list[str],
        args: dict[str, Any],
        flags: dict[str, Any],
        global_flags: dict[str, Any] = None,
    ) -> ValidationResult:
        """
        Validate command asynchronously.

        Args:
            subcommands: List of command parts
            args: Dict of positional arguments
            flags: Dict of command-specific flags
            global_flags: Dict of global flags

        Returns:
            ValidationResult object
        """
        try:
            # Validate global flags first
            if global_flags:
                is_valid, error = self.validator.validate_global_flags(global_flags)
                if not is_valid:
                    return ValidationResult(False, error)

            # Validate command
            is_valid, error = self.validator.validate_command(subcommands, args, flags)

            if not is_valid:
                suggestions = self._get_suggestions(subcommands, error)
                return ValidationResult(False, error, suggestions)

            return ValidationResult(True)

        except Exception as e:
            return ValidationResult(False, f"Validation failed: {str(e)}")

    def _get_suggestions(self, subcommands: list[str], error: str) -> list[str]:
        """Get command suggestions based on error."""
        suggestions = []

        if not subcommands:
            suggestions = [
                "Try: /webdeface help",
                "Available commands: website, monitoring, system",
            ]
        elif len(subcommands) == 1:
            command = subcommands[0]
            if command == "website":
                suggestions = [
                    "Try: /webdeface website add <url>",
                    "Try: /webdeface website list",
                    "Try: /webdeface help website",
                ]
            elif command == "monitoring":
                suggestions = [
                    "Try: /webdeface monitoring start",
                    "Try: /webdeface monitoring check <website_id>",
                    "Try: /webdeface help monitoring",
                ]
            elif command == "system":
                suggestions = [
                    "Try: /webdeface system status",
                    "Try: /webdeface system health",
                    "Try: /webdeface help system",
                ]

        return suggestions


# Aliases for backward compatibility
SlackValidator = SlackCommandValidator
