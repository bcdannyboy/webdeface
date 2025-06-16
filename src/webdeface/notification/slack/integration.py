"""Integration module for CLI command handlers with existing Slack infrastructure."""

from typing import Any, Optional

from slack_bolt.async_app import AsyncAck, AsyncRespond

from ...utils.logging import get_structured_logger
from .app import get_slack_manager
from .handlers.router import SlackCommandRouter

logger = get_structured_logger(__name__)


class SlackCLIIntegration:
    """Integrates CLI command handlers with Slack Bolt app."""

    def __init__(self):
        self.command_router = SlackCommandRouter()
        self._registered = False

    async def register_cli_commands(self) -> None:
        """Register CLI command handlers with the Slack app."""
        if self._registered:
            return

        slack_manager = await get_slack_manager()
        app = slack_manager.get_app()

        # Override the existing /webdeface command with our CLI router
        @app.command("/webdeface")
        async def handle_webdeface_cli_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ) -> None:
            """Handle /webdeface commands through CLI router."""
            await ack()

            # Extract command details
            command_text = command.get("text", "").strip()
            user_id = command.get("user_id")
            channel_id = command.get("channel_id")
            team_id = command.get("team_id")
            response_url = command.get("response_url")

            logger.info(
                "Processing CLI command via Slack",
                command_text=command_text,
                user_id=user_id,
                channel_id=channel_id,
            )

            try:
                # Route through our CLI command router
                response = await self.command_router.route_command(
                    command_text=command_text,
                    user_id=user_id,
                    channel_id=channel_id,
                    team_id=team_id,
                    response_url=response_url,
                )

                # Send the formatted response
                await respond(response)

            except Exception as e:
                logger.error(
                    "CLI command processing failed",
                    command_text=command_text,
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )

                # Send error response
                await respond(
                    {
                        "text": f"❌ An error occurred while processing your command: {str(e)}",
                        "response_type": "ephemeral",
                    }
                )

        # Add support for legacy standalone commands by routing them through CLI
        @app.command("/status")
        async def handle_legacy_status_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ) -> None:
            """Handle legacy /status command by routing to CLI."""
            await ack()
            await self._handle_legacy_command("system status", command, respond)

        @app.command("/alerts")
        async def handle_legacy_alerts_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ) -> None:
            """Handle legacy /alerts command by routing to CLI."""
            await ack()
            limit = command.get("text", "20").strip() or "20"
            await self._handle_legacy_command(
                f"system logs limit:{limit}", command, respond
            )

        @app.command("/sites")
        async def handle_legacy_sites_command(
            ack: AsyncAck, respond: AsyncRespond, command: dict[str, Any]
        ) -> None:
            """Handle legacy /sites command by routing to CLI."""
            await ack()
            status_filter = command.get("text", "").strip()
            if status_filter:
                await self._handle_legacy_command(
                    f"website list status:{status_filter}", command, respond
                )
            else:
                await self._handle_legacy_command("website list", command, respond)

        self._registered = True
        logger.info("CLI command integration registered successfully")

    async def _handle_legacy_command(
        self, cli_command: str, command: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle legacy commands by routing through CLI."""
        try:
            response = await self.command_router.route_command(
                command_text=cli_command,
                user_id=command.get("user_id"),
                channel_id=command.get("channel_id"),
                team_id=command.get("team_id"),
                response_url=command.get("response_url"),
            )

            await respond(response)

        except Exception as e:
            logger.error(
                "Legacy command routing failed", cli_command=cli_command, error=str(e)
            )

            await respond(
                {"text": f"❌ Command failed: {str(e)}", "response_type": "ephemeral"}
            )

    async def get_available_commands(self) -> dict[str, Any]:
        """Get information about available CLI commands."""
        return {
            "commands": await self.command_router.get_available_commands(),
            "cli_syntax": "Use /webdeface <command> <subcommand> [args] [flags]",
            "examples": [
                "/webdeface website add https://example.com name:MyWebsite",
                "/webdeface monitoring start",
                "/webdeface system health",
                "/webdeface help",
            ],
        }

    async def validate_user_permissions(
        self, user_id: str, team_id: str
    ) -> dict[str, Any]:
        """Validate user permissions for CLI commands."""
        return await self.command_router.validate_permissions_for_user(user_id, team_id)


# Global CLI integration instance
_cli_integration: Optional[SlackCLIIntegration] = None


async def get_cli_integration() -> SlackCLIIntegration:
    """Get the global CLI integration instance."""
    global _cli_integration

    if _cli_integration is None:
        _cli_integration = SlackCLIIntegration()
        await _cli_integration.register_cli_commands()

    return _cli_integration


async def register_cli_integration() -> None:
    """Register CLI command integration with Slack."""
    await get_cli_integration()
    logger.info("Slack CLI integration registration complete")


async def handle_cli_command_from_slack(
    command_text: str,
    user_id: str,
    channel_id: str,
    team_id: str,
    response_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Handle a CLI command from Slack interface.

    This is a convenience function for external integrations.
    """
    integration = await get_cli_integration()
    return await integration.command_router.route_command(
        command_text=command_text,
        user_id=user_id,
        channel_id=channel_id,
        team_id=team_id,
        response_url=response_url,
    )
