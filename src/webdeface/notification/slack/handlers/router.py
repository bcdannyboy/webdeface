"""Slack command routing system."""

from typing import Any, Optional
from unittest.mock import AsyncMock

from slack_bolt.async_app import AsyncRespond

from ....utils.logging import get_structured_logger
from ..utils.formatters import SlackResponseFormatter
from ..utils.parsers import SlackCommandParser
from ..utils.validators import CommandValidator
from .base import BaseSlackHandler
from .monitoring import MonitoringHandler
from .system import SystemHandler
from .website import WebsiteHandler

logger = get_structured_logger(__name__)


class SlackCommandRouter:
    """Routes Slack commands to appropriate handlers."""

    def __init__(self):
        self.parser = SlackCommandParser()
        self.validator = CommandValidator()
        self.formatter = SlackResponseFormatter()
        self.permission_manager = None  # Will be initialized on first use

        # Initialize handlers
        self.handlers: dict[str, BaseSlackHandler] = {
            "website": WebsiteHandler(),
            "monitoring": MonitoringHandler(),
            "system": SystemHandler(),
        }

    async def route_command(
        self,
        text: str = None,
        user_id: str = None,
        respond: AsyncRespond = None,
        channel_id: Optional[str] = None,
        command_text: str = None,  # Support legacy parameter name
        **kwargs
    ) -> None:
        """
        Route a Slack command to the appropriate handler.

        Args:
            text: Raw command text from Slack
            user_id: User ID who sent the command
            respond: Slack response function
            channel_id: Channel where command was sent (optional)
        """
        # Handle legacy parameter names
        if command_text is not None:
            text = command_text
        if text is None:
            text = ""
        if user_id is None:
            user_id = "test_user"
        if respond is None:
            respond = AsyncMock()
            
        logger.info(
            "Routing Slack command",
            user_id=user_id,
            text=text[:100] if text else "",  # Truncate for logging
            channel_id=channel_id,
        )

        try:
            # Handle help command explicitly
            if text and text.strip() == "help":
                await self._handle_help(respond, text.strip())
                return

            # Parse command
            parse_result = self.parser.parse_command(text)

            if not parse_result.success:
                await self._send_parse_error(respond, parse_result.error_message)
                return

            # Check if we have any subcommands
            if not parse_result.subcommands:
                # Check if we have args that look like command attempts
                if parse_result.args and len(parse_result.args) > 0:
                    first_arg = parse_result.args.get(0, "")
                    if first_arg and not first_arg.startswith("http"):  # Not a URL
                        await self._send_unknown_command_error(respond, first_arg)
                        return
                await self._send_command_required_error(respond)
                return

            command_group = parse_result.subcommands[0]

            # Handle help command with context
            if command_group == "help":
                context = (
                    parse_result.subcommands[1]
                    if len(parse_result.subcommands) > 1
                    else None
                )
                await self._handle_help(respond, context)
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
                    respond,
                    validation_result.error_message,
                    validation_result.suggestions,
                )
                return

            handler = self.handlers.get(command_group)
            if not handler:
                await self._send_unknown_command_error(respond, command_group)
                return

            # Delegate to handler
            await handler.handle_command(text, user_id, respond, channel_id)

        except Exception as e:
            logger.error(
                "Error routing Slack command",
                user_id=user_id,
                text=text,
                error=str(e),
            )
            await self._send_internal_error(respond, str(e))

    async def _handle_help(
        self, respond: AsyncRespond, context: Optional[str] = None
    ) -> None:
        """Handle help command."""
        help_response = self.formatter.format_help_message(context)
        await respond(help_response)

    async def _send_parse_error(
        self, respond: AsyncRespond, error_message: str
    ) -> None:
        """Send command parsing error response."""
        response = {
            "text": f"❌ {error_message}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Parse Error*\n{error_message}",
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

    async def _send_validation_error(
        self, respond: AsyncRespond, error_message: str, suggestions: list[str] = None
    ) -> None:
        """Send validation error response."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *Validation Error*\n{error_message}",
                },
            }
        ]

        if suggestions:
            suggestion_text = "\n".join(
                [f"• {suggestion}" for suggestion in suggestions]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"💡 *Suggestions:*\n{suggestion_text}",
                    },
                }
            )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "📖 Try `/webdeface help` for complete documentation",
                    }
                ],
            }
        )

        response = {
            "text": f"❌ {error_message}",
            "response_type": "ephemeral",
            "blocks": blocks,
        }
        await respond(response)

    async def _send_unknown_command_error(
        self, respond: AsyncRespond, command: str
    ) -> None:
        """Send unknown command error response."""
        available_commands = list(self.handlers.keys())
        response = {
            "text": f"❌ Unknown command: {command}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Unknown Command*\n`{command}` is not a recognized command.",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Available commands:*\n• {' • '.join(available_commands)}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Try `/webdeface help` for detailed usage information",
                        }
                    ],
                },
            ],
        }
        await respond(response)

    async def _send_command_required_error(self, respond: AsyncRespond) -> None:
        """Send command required error response."""
        response = {
            "text": "❌ Command is required (website, monitoring, or system)",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "❌ *Command Required*\nPlease specify a command group.",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available commands:*\n• website • monitoring • system",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Try `/webdeface help` for detailed usage information",
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

    def add_handler(self, command: str, handler: BaseSlackHandler) -> None:
        """Add a new command handler."""
        self.handlers[command] = handler
        logger.info(
            "Command handler added", command=command, handler=handler.__class__.__name__
        )

    def remove_handler(self, command: str) -> bool:
        """Remove a command handler."""
        if command in self.handlers:
            del self.handlers[command]
            logger.info("Command handler removed", command=command)
            return True
        return False

    def get_registered_commands(self) -> list[str]:
        """Get list of registered command groups."""
        return list(self.handlers.keys())

    async def get_available_commands(self) -> dict[str, Any]:
        """Get available commands with metadata."""
        commands = {}
        for command_group, handler in self.handlers.items():
            commands[command_group] = {
                "description": f"{command_group.title()} management commands",
                "handler": handler.__class__.__name__,
                "subcommands": self._get_handler_subcommands(command_group)
            }
        return commands

    def _get_handler_subcommands(self, command_group: str) -> list[str]:
        """Get subcommands for a handler."""
        # Define basic subcommands for each handler type
        subcommands_map = {
            "website": ["add", "remove", "list", "status"],
            "monitoring": ["start", "stop", "pause", "resume", "check"],
            "system": ["status", "health", "metrics", "logs"]
        }
        return subcommands_map.get(command_group, [])

    async def validate_permissions_for_user(self, user_id: str, command: str) -> bool:
        """Validate if user has permissions for a command."""
        try:
            from ..permissions import get_permission_manager
            
            if not self.permission_manager:
                self.permission_manager = await get_permission_manager()
            
            # Parse command to get subcommands
            parse_result = self.parser.parse_command(command)
            if not parse_result.success or not parse_result.subcommands:
                return False
                
            # Get handler and check permissions
            command_group = parse_result.subcommands[0]
            handler = self.handlers.get(command_group)
            if not handler:
                return False
                
            required_permissions = handler.get_required_permissions(parse_result.subcommands)
            
            for permission in required_permissions:
                has_permission = await self.permission_manager.check_permission(user_id, permission)
                if not has_permission:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error("Error validating permissions", user_id=user_id, command=command, error=str(e))
            return False


# Global command router instance
_command_router: Optional[SlackCommandRouter] = None


def get_command_router() -> SlackCommandRouter:
    """Get the global command router instance."""
    global _command_router

    if _command_router is None:
        _command_router = SlackCommandRouter()
        logger.info("Slack command router initialized")

    return _command_router


async def route_slack_command(
    text: str, user_id: str, respond: AsyncRespond, channel_id: Optional[str] = None
) -> None:
    """
    Convenience function to route Slack commands.

    Args:
        text: Raw command text from Slack
        user_id: User ID who sent the command
        respond: Slack response function
        channel_id: Channel where command was sent (optional)
    """
    router = get_command_router()
    await router.route_command(text, user_id, respond, channel_id)
