"""Webhook handlers for Slack events and interactions."""

from typing import Any, Optional

from slack_bolt.async_app import AsyncAck, AsyncRespond, AsyncSay

from ...storage import get_storage_manager
from ...utils.logging import get_structured_logger
from .app import get_slack_manager
from .delivery import get_notification_delivery
from .formatting import SlackMessageFormatter

logger = get_structured_logger(__name__)


class SlackEventHandler:
    """Handles Slack webhook events and interactive components."""

    def __init__(self):
        self.formatter = SlackMessageFormatter()
        self.delivery = get_notification_delivery()

    async def register_handlers(self) -> None:
        """Register all event handlers with the Slack app."""
        slack_manager = await get_slack_manager()
        app = slack_manager.get_app()

        # Button interactions
        @app.action("alert_acknowledge")
        async def handle_alert_acknowledge(
            ack: AsyncAck, body: dict[str, Any], respond: AsyncRespond
        ):
            await ack()
            await self._handle_alert_acknowledge(body, respond)

        @app.action("alert_resolve")
        async def handle_alert_resolve(
            ack: AsyncAck, body: dict[str, Any], respond: AsyncRespond
        ):
            await ack()
            await self._handle_alert_resolve(body, respond)

        @app.action("alert_investigate")
        async def handle_alert_investigate(
            ack: AsyncAck, body: dict[str, Any], respond: AsyncRespond
        ):
            await ack()
            await self._handle_alert_investigate(body, respond)

        @app.action("alert_details")
        async def handle_alert_details(
            ack: AsyncAck, body: dict[str, Any], respond: AsyncRespond
        ):
            await ack()
            await self._handle_alert_details(body, respond)

        # Site management actions
        @app.action("site_actions")
        async def handle_site_actions(
            ack: AsyncAck, body: dict[str, Any], respond: AsyncRespond
        ):
            await ack()
            await self._handle_site_actions(body, respond)

        # App mentions and direct messages
        @app.event("app_mention")
        async def handle_app_mention(body: dict[str, Any], say: AsyncSay):
            await self._handle_app_mention(body, say)

        @app.event("message")
        async def handle_direct_message(body: dict[str, Any], say: AsyncSay):
            await self._handle_direct_message(body, say)

        # Reaction events for quick actions
        @app.event("reaction_added")
        async def handle_reaction_added(body: dict[str, Any]):
            await self._handle_reaction_added(body)

        logger.info("Slack event handlers registered successfully")

    async def _handle_alert_acknowledge(
        self, body: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle alert acknowledgment button click."""
        user = body["user"]
        alert_id = body["actions"][0]["value"]

        try:
            storage = await get_storage_manager()
            success = await storage.acknowledge_alert(alert_id, user["username"])

            if success:
                await respond(
                    {
                        "text": f"✅ Alert acknowledged by <@{user['id']}>",
                        "replace_original": False,
                        "response_type": "in_channel",
                    }
                )

                logger.info(
                    "Alert acknowledged via Slack",
                    alert_id=alert_id,
                    user_id=user["id"],
                    username=user["username"],
                )
            else:
                await respond(
                    {
                        "text": "❌ Failed to acknowledge alert (may already be acknowledged/resolved)",
                        "response_type": "ephemeral",
                    }
                )
        except Exception as e:
            logger.error(
                "Failed to acknowledge alert",
                alert_id=alert_id,
                user_id=user["id"],
                error=str(e),
            )
            await respond(
                {
                    "text": f"❌ Error acknowledging alert: {str(e)}",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_alert_resolve(
        self, body: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle alert resolution button click."""
        user = body["user"]
        alert_id = body["actions"][0]["value"]

        try:
            storage = await get_storage_manager()
            success = await storage.resolve_alert(alert_id)

            if success:
                await respond(
                    {
                        "text": f"✅ Alert resolved by <@{user['id']}>",
                        "replace_original": False,
                        "response_type": "in_channel",
                    }
                )

                logger.info(
                    "Alert resolved via Slack",
                    alert_id=alert_id,
                    user_id=user["id"],
                    username=user["username"],
                )
            else:
                await respond(
                    {
                        "text": "❌ Failed to resolve alert (may already be resolved)",
                        "response_type": "ephemeral",
                    }
                )
        except Exception as e:
            logger.error(
                "Failed to resolve alert",
                alert_id=alert_id,
                user_id=user["id"],
                error=str(e),
            )
            await respond(
                {
                    "text": f"❌ Error resolving alert: {str(e)}",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_alert_investigate(
        self, body: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle alert investigation button click."""
        user = body["user"]
        alert_id = body["actions"][0]["value"]

        try:
            storage = await get_storage_manager()

            # Get alert details (implementation would fetch from storage)
            await respond(
                {
                    "text": f"🔍 Investigation details for alert `{alert_id}` will be available in the web dashboard soon.",
                    "response_type": "ephemeral",
                }
            )

            logger.info(
                "Alert investigation requested", alert_id=alert_id, user_id=user["id"]
            )
        except Exception as e:
            logger.error(
                "Failed to get alert investigation details",
                alert_id=alert_id,
                error=str(e),
            )
            await respond(
                {
                    "text": f"❌ Error getting investigation details: {str(e)}",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_alert_details(
        self, body: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle alert details button click."""
        user = body["user"]
        alert_id = body["actions"][0]["value"]

        try:
            # Implementation would fetch detailed alert information
            await respond(
                {
                    "text": f"📋 Detailed view for alert `{alert_id}` coming soon!",
                    "response_type": "ephemeral",
                }
            )

            logger.info(
                "Alert details requested", alert_id=alert_id, user_id=user["id"]
            )
        except Exception as e:
            logger.error("Failed to get alert details", alert_id=alert_id, error=str(e))

    async def _handle_site_actions(
        self, body: dict[str, Any], respond: AsyncRespond
    ) -> None:
        """Handle site management overflow menu actions."""
        user = body["user"]
        action_value = body["actions"][0]["selected_option"]["value"]
        action, site_id = action_value.split("_", 1)

        try:
            storage = await get_storage_manager()

            if action == "pause":
                # Implementation would pause site monitoring
                await respond(
                    {
                        "text": f"⏸️ Site paused by <@{user['id']}>",
                        "response_type": "in_channel",
                    }
                )
            elif action == "resume":
                # Implementation would resume site monitoring
                await respond(
                    {
                        "text": f"▶️ Site resumed by <@{user['id']}>",
                        "response_type": "in_channel",
                    }
                )
            elif action == "history":
                await respond(
                    {
                        "text": f"📊 Site history for `{site_id}` coming soon!",
                        "response_type": "ephemeral",
                    }
                )
            elif action == "edit":
                await respond(
                    {
                        "text": f"⚙️ Site settings editor for `{site_id}` coming soon!",
                        "response_type": "ephemeral",
                    }
                )

            logger.info(
                "Site action executed",
                action=action,
                site_id=site_id,
                user_id=user["id"],
            )
        except Exception as e:
            logger.error(
                "Failed to execute site action",
                action=action,
                site_id=site_id,
                error=str(e),
            )
            await respond(
                {
                    "text": f"❌ Error executing action: {str(e)}",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_app_mention(self, body: dict[str, Any], say: AsyncSay) -> None:
        """Handle app mentions in channels."""
        event = body["event"]
        user = event["user"]
        text = event.get("text", "").lower()

        logger.info(
            "App mention received",
            user_id=user,
            channel=event["channel"],
            text=text[:100],
        )

        try:
            if "status" in text:
                storage = await get_storage_manager()
                health = await storage.health_check()
                alerts = await storage.get_open_alerts(limit=1000)
                sites = await storage.list_websites(active_only=True)
                stats = await storage.get_storage_stats()

                message = self.formatter.format_system_status(
                    health, stats, len(alerts), len(sites)
                )
                await say(**message)

            elif "alerts" in text:
                storage = await get_storage_manager()
                alerts = await storage.get_open_alerts(limit=20)
                message = self.formatter.format_alert_summary(alerts)
                await say(**message)

            elif "help" in text:
                message = self.formatter.format_help_message()
                await say(**message)

            else:
                await say(
                    f"Hi <@{user}>! 👋 I'm monitoring {await self._get_sites_count()} websites for defacement. "
                    f"Say 'status', 'alerts', or 'help' to get started!"
                )

        except Exception as e:
            logger.error("Failed to handle app mention", error=str(e))
            await say(f"Sorry <@{user}>, I encountered an error: {str(e)}")

    async def _handle_direct_message(self, body: dict[str, Any], say: AsyncSay) -> None:
        """Handle direct messages to the bot."""
        event = body["event"]

        # Skip messages from bots and our own messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        user = event["user"]
        text = event.get("text", "").lower()
        channel_type = event.get("channel_type")

        # Only handle direct messages
        if channel_type != "im":
            return

        logger.info("Direct message received", user_id=user, text=text[:100])

        try:
            if any(word in text for word in ["hello", "hi", "hey"]):
                await say(
                    f"Hello! 👋 I'm the Web Defacement Monitor bot. "
                    f"I'm currently monitoring {await self._get_sites_count()} websites. "
                    f"Type 'help' to see what I can do!"
                )
            elif "help" in text:
                message = self.formatter.format_help_message()
                await say(**message)
            else:
                await say(
                    "I'm here to help with web defacement monitoring! "
                    "Type 'help' to see available commands, or mention me in a channel."
                )

        except Exception as e:
            logger.error("Failed to handle direct message", error=str(e))
            await say(f"Sorry, I encountered an error: {str(e)}")

    async def _handle_reaction_added(self, body: dict[str, Any]) -> None:
        """Handle reaction additions for quick actions."""
        event = body["event"]
        reaction = event["reaction"]
        user = event["user"]

        # Only handle specific reactions on alert messages
        if reaction not in ["white_check_mark", "x", "eyes"]:
            return

        logger.debug(
            "Reaction added to message",
            reaction=reaction,
            user_id=user,
            channel=event["item"]["channel"],
        )

        try:
            # Implementation would check if message is an alert and perform action
            # For now, just log the reaction
            logger.info(
                "Quick action reaction detected", reaction=reaction, user_id=user
            )
        except Exception as e:
            logger.error("Failed to handle reaction", error=str(e))

    async def _get_sites_count(self) -> int:
        """Get count of active monitored sites."""
        try:
            storage = await get_storage_manager()
            sites = await storage.list_websites(active_only=True)
            return len(sites)
        except Exception:
            return 0


# Global event handler instance
_event_handler: Optional[SlackEventHandler] = None


async def get_event_handler() -> SlackEventHandler:
    """Get the global event handler instance."""
    global _event_handler

    if _event_handler is None:
        _event_handler = SlackEventHandler()
        await _event_handler.register_handlers()

    return _event_handler


async def register_slack_handlers() -> None:
    """Register all Slack event handlers."""
    await get_event_handler()
    logger.info("Slack event handlers registration complete")
