"""Type definitions for the CLI module."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CLIError(Exception):
    """Base exception for CLI-related errors."""

    pass


class CommandResult:
    """Result of a CLI command execution."""

    def __init__(
        self,
        success: bool,
        message: str = "",
        data: Optional[dict[str, Any]] = None,
        exit_code: int = 0,
    ):
        self.success = success
        self.message = message
        self.data = data or {}
        self.exit_code = exit_code
        self.timestamp = datetime.utcnow()

    def __bool__(self) -> bool:
        return self.success


class CLIContext:
    """Context object for CLI commands."""

    def __init__(self, verbose: bool = False, debug: bool = False):
        self.verbose = verbose
        self.debug = debug
        self.start_time = datetime.utcnow()
        self.timestamp = datetime.utcnow()

    def log(self, message: str, level: str = "info") -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose or level == "error":
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level.upper()}: {message}")


@dataclass
class ScanCommand:
    """Configuration for scan command."""

    url: str
    depth: int = 2
    output_format: str = "text"  # text, json
    save_results: bool = False


@dataclass
class InitCommand:
    """Configuration for init command."""

    config_path: str = "config.yaml"
    env_path: str = ".env"
    force: bool = False


# Command type definitions
class OutputFormat(str, Enum):
    """Output format options for CLI commands."""

    TEXT = "text"
    JSON = "json"
    TABLE = "table"
