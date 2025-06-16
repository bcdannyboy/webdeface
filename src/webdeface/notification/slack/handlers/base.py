"""Base handler class for Slack command handlers."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional

from slack_bolt.async_app import AsyncRespond

from ....cli.types import CLIContext, CommandResult
from ....utils.logging import get_structured_logger
from ..permissions import Permission, get_permission_manager
from ..utils.formatters import SlackResponseFormatter, format_cli_result_for_slack
from ..utils.parsers import (
    SlackCommandParser,
)
from ..utils.validators import SlackCommandValidator

logger = get_structured_logger(__name__)


class BaseSlackHandler(ABC):
    """Base class for Slack command handlers with common functionality."""

    def __init__(self):
        self.parser = SlackCommandParser()
        self.validator = SlackCommandValidator()
        self.formatter = SlackResponseFormatter()

    async def handle_command(
        self,
        text: str,
        user_id: str,
        respond: AsyncRespond,
        channel_id: Optional[str] = None,
    ) -> None:
        """
        Main entry point for handling Slack commands.

        Args:
            text: Raw command text from Slack
            user_id: User ID who sent the command
            respond: Slack response function
            channel_id: Channel where command was sent (optional)
        """
        logger.info(
            "Processing Slack command",
            user_id=user_id,
            text=text[:100],  # Truncate for logging
            channel_id=channel_id,
        )

        try:
            # Parse command
            parse_result = self.parser.parse_command(text)

            if not parse_result.success:
                await self._send_validation_error(respond, parse_result.error_message)
                return

            # Validate command structure
            validation_result = await self.validator.validate_command(
                parse_result.subcommands,
                parse_result.args,
                parse_result.flags,
                parse_result.global_flags,
            )

            if not validation_result.is_valid:
                await self._send_validation_error(
                    respond, validation_result.error_message
                )
                return

            # Check permissions
            permission_granted, permission_error = await self._check_permissions(
                user_id, parse_result.subcommands
            )

            if not permission_granted:
                await self._send_permission_error(respond, permission_error)
                return

            # Execute command
            result = await self._execute_command(
                parse_result.subcommands,
                parse_result.args,
                parse_result.flags,
                parse_result.global_flags,
                user_id,
            )

            # Format and send response
            await self._send_formatted_response(
                respond, result, parse_result.global_flags
            )

        except Exception as e:
            logger.error(
                "Error handling Slack command",
                user_id=user_id,
                text=text,
                error=str(e),
            )
            await self._send_internal_error(respond, str(e))

    @abstractmethod
    async def _execute_command(
        self,
        subcommands: list[str],
        args: dict[str, Any],
        flags: dict[str, Any],
        global_flags: dict[str, Any],
        user_id: str,
    ) -> CommandResult:
        """
        Execute the specific command logic.

        This method should be implemented by each handler to execute
        the actual CLI business logic and return a CommandResult.

        Args:
            subcommands: List of command parts (e.g., ["website", "add"])
            args: Positional arguments
            flags: Command-specific flags
            global_flags: Global flags (verbose, debug, config)
            user_id: User executing the command

        Returns:
            CommandResult object with execution results
        """
        pass

    @abstractmethod
    def get_required_permissions(self, subcommands: list[str]) -> list[Permission]:
        """
        Get required permissions for the given command.

        Args:
            subcommands: List of command parts

        Returns:
            List of required permissions
        """
        pass

    async def _check_permissions(
        self, user_id: str, subcommands: list[str]
    ) -> tuple[bool, Optional[str]]:
        """Check if user has required permissions for command."""
        try:
            required_permissions = self.get_required_permissions(subcommands)

            if not required_permissions:
                return True, None  # No permissions required

            permission_manager = await get_permission_manager()

            # Check each required permission
            for permission in required_permissions:
                has_permission = await permission_manager.check_permission(
                    user_id, permission
                )
                if not has_permission:
                    return (
                        False,
                        f"Insufficient permissions. Required: {permission.value}",
                    )

            return True, None

        except Exception as e:
            logger.error("Error checking permissions", user_id=user_id, error=str(e))
            return False, f"Permission check failed: {str(e)}"

    async def _send_validation_error(
        self, respond: AsyncRespond, error_message: str
    ) -> None:
        """Send validation error response."""
        response = {
            "text": f"❌ {error_message}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Validation Error*\n{error_message}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Try `/webdeface help` for usage examples",
                        }
                    ],
                },
            ],
        }
        await respond(response)

    async def _send_permission_error(
        self, respond: AsyncRespond, error_message: str
    ) -> None:
        """Send permission error response."""
        response = {
            "text": f"🔒 {error_message}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔒 *Access Denied*\n{error_message}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Contact your administrator to request access",
                        }
                    ],
                },
            ],
        }
        await respond(response)

    async def _send_internal_error(
        self, respond: AsyncRespond, error_message: str
    ) -> None:
        """Send internal error response."""
        response = {
            "text": "💥 Internal error occurred",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "💥 *Internal Error*\nSomething went wrong processing your command.",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Error details: {error_message[:100]}...",
                        }
                    ],
                },
            ],
        }
        await respond(response)

    async def _send_formatted_response(
        self, respond: AsyncRespond, result: CommandResult, global_flags: dict[str, Any]
    ) -> None:
        """Format and send the command result as a Slack response."""
        try:
            # Determine output preferences from global flags
            verbose = global_flags.get("verbose", False)
            output_format = global_flags.get("format", "table")

            # Format the result
            slack_response = format_cli_result_for_slack(
                result, verbose=verbose, output_format=output_format
            )

            await respond(slack_response)

        except Exception as e:
            logger.error("Error formatting response", error=str(e))
            await self._send_internal_error(respond, "Response formatting failed")

    def create_cli_context(
        self, global_flags: dict[str, Any], user_id: str
    ) -> CLIContext:
        """
        Create a CLI context object from global flags.

        Args:
            global_flags: Global flags from Slack command
            user_id: User executing the command

        Returns:
            CLIContext object for CLI compatibility
        """
        return CLIContext(
            verbose=global_flags.get("verbose", False),
            debug=global_flags.get("debug", False),
        )

    async def run_cli_operation(
        self, operation_func, cli_context: CLIContext, *args, **kwargs
    ) -> CommandResult:
        """
        Run a CLI operation with proper error handling and result formatting.

        Args:
            operation_func: The CLI function to execute
            cli_context: CLI context object
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            CommandResult object
        """
        try:
            # Execute the operation
            result = await operation_func(cli_context, *args, **kwargs)

            if isinstance(result, CommandResult):
                return result
            else:
                # Convert other return types to CommandResult
                return CommandResult(
                    success=True,
                    message="Operation completed successfully",
                    data=result if isinstance(result, dict) else {"result": result},
                )

        except Exception as e:
            logger.error(
                "CLI operation failed", operation=operation_func.__name__, error=str(e)
            )
            return CommandResult(
                success=False, message=f"Operation failed: {str(e)}", exit_code=1
            )

    async def handle_help(
        self, respond: AsyncRespond, command_context: Optional[str] = None
    ) -> None:
        """Handle help command for this handler."""
        help_response = self.formatter.format_help_message(command_context)
        await respond(help_response)


class AsyncCommandMixin:
    """Mixin to provide async command execution capabilities."""

    async def execute_with_timeout(
        self, operation, timeout_seconds: int = 30, *args, **kwargs
    ) -> Any:
        """
        Execute an operation with a timeout.

        Args:
            operation: Async operation to execute
            timeout_seconds: Timeout in seconds
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        try:
            return await asyncio.wait_for(
                operation(*args, **kwargs), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Operation timed out",
                operation=operation.__name__
                if hasattr(operation, "__name__")
                else str(operation),
                timeout=timeout_seconds,
            )
            raise
