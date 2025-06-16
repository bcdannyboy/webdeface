"""Enhanced Slack commands with CLI integration."""

from typing import Any, Optional

from slack_bolt.async_app import AsyncAck, AsyncRespond

from ...storage import get_storage_manager
from ...utils.logging import get_structured_logger
from .app import get_slack_manager
from .delivery import get_notification_delivery
from .formatting import SlackMessageFormatter
from .handlers.router import get_command_router, route_slack_command

logger = get_structured_logger(__name__)


class SlackCommandHandler:
    """Enhanced Slack command handler with CLI integration."""

    def __init__(self):
        self.formatter = SlackMessageFormatter()
        self.delivery = get_notification_delivery()
        self.router = get_command_router()

    async def register_commands(self) -> None:
        """Register all command handlers with the Slack app."""
        slack_manager = await get_slack_manager()
        app = slack_manager.get_app()

        # Main webdeface command with enhanced routing
        @app.command("/webdeface")
        async def handle_webdeface_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ):
            await ack()
            await self._handle_main_command(respond, command)

        # Legacy compatibility commands
        @app.command("/status")
        async def handle_status_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ):
            await ack()
            # Route to new system as "system status"
            await route_slack_command(
                "system status",
                command.get("user_id", ""),
                respond,
                command.get("channel_id"),
            )

        @app.command("/alerts")
        async def handle_alerts_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ):
            await ack()
            # Legacy alert handling - could be enhanced later
            await self._handle_legacy_alerts_command(respond, command)

        @app.command("/sites")
        async def handle_sites_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ):
            await ack()
            # Route to new system as "website list"
            text = command.get("text", "").strip()
            cmd_text = f"website list {text}" if text else "website list"
            await route_slack_command(
                cmd_text, command.get("user_id", ""), respond, command.get("channel_id")
            )

        logger.info("Enhanced Slack commands registered successfully")

    async def _handle_main_command(
        self, respond: AsyncRespond, command: dict[str, Any]
    ) -> None:
        """Handle the main /webdeface command using the new router."""
        user_id = command.get("user_id", "")
        text = command.get("text", "").strip()
        channel_id = command.get("channel_id")

        logger.info(
            "Processing enhanced webdeface command",
            user_id=user_id,
            text=text,
            channel=channel_id,
        )

        try:
            # Route to the new command system
            await route_slack_command(text, user_id, respond, channel_id)
        except Exception as e:
            logger.error(
                "Enhanced command execution failed",
                user_id=user_id,
                text=text,
                error=str(e),
            )
            await respond(
                {"text": f"❌ Command failed: {str(e)}", "response_type": "ephemeral"}
            )

    async def _handle_legacy_alerts_command(
        self, respond: AsyncRespond, command: dict[str, Any]
    ) -> None:
        """Handle legacy alerts command for backward compatibility."""
        user_id = command.get("user_id")
        text = command.get("text", "").strip()

        logger.info("Processing legacy alerts command", user_id=user_id, text=text)

        try:
            # Parse arguments
            limit = 20
            args = text.split() if text else []
            if args and args[0].isdigit():
                limit = min(int(args[0]), 100)  # Cap at 100

            # Get active alerts
            storage = await get_storage_manager()
            alerts = await storage.get_open_alerts(limit=limit)

            if not alerts:
                await respond(
                    {"text": "✅ No active alerts found.", "response_type": "ephemeral"}
                )
                return

            # Format alert summary
            message = self.formatter.format_alert_summary(alerts)

            # Add detailed list for smaller numbers of alerts
            if len(alerts) <= 10:
                blocks = message.get("blocks", [])
                blocks.append({"type": "divider"})

                for alert in alerts[:10]:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*{alert.title}*\n"
                                    f"Severity: {alert.severity} | "
                                    f"Created: {alert.created_at.strftime('%m/%d %H:%M')}\n"
                                    f"Description: {alert.description[:100]}..."
                                ),
                            },
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details"},
                                "action_id": "alert_details",
                                "value": alert.id,
                            },
                        }
                    )

                message["blocks"] = blocks

            await respond({**message, "response_type": "in_channel"})

        except Exception as e:
            logger.error("Legacy alerts command failed", user_id=user_id, error=str(e))
            await respond(
                {
                    "text": f"❌ Failed to get alerts: {str(e)}",
                    "response_type": "ephemeral",
                }
            )


# Global command handler instance
_command_handler: Optional[SlackCommandHandler] = None


async def get_command_handler() -> SlackCommandHandler:
    """Get the global command handler instance."""
    global _command_handler

    if _command_handler is None:
        _command_handler = SlackCommandHandler()
        await _command_handler.register_commands()

    return _command_handler


async def register_slack_commands() -> None:
    """Register all Slack commands."""
    await get_command_handler()
    logger.info("Slack commands registration complete")
