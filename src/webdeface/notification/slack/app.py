"""Slack Bolt app initialization and configuration."""

from typing import Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.request import BoltRequest

from ...config.settings import SlackSettings
from ...utils.async_utils import AsyncContextManager
from ...utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class SlackBoltManager(AsyncContextManager):
    """Manages Slack Bolt app initialization and lifecycle."""

    def __init__(self, settings: SlackSettings):
        self.settings = settings
        self.app: Optional[AsyncApp] = None
        self._initialized = False

    async def setup(self) -> None:
        """Initialize Slack Bolt app with configuration."""
        if self._initialized:
            return

        logger.info("Initializing Slack Bolt app")

        # Initialize Slack app
        self.app = AsyncApp(
            token=self.settings.bot_token.get_secret_value(),
            signing_secret=self.settings.signing_secret.get_secret_value(),
            # Enable socket mode for interactive features
            app_token=self.settings.app_token.get_secret_value(),
            # Process before ack for better responsiveness
            process_before_response=True,
        )

        # Register event handlers
        await self._register_handlers()

        # Register middleware
        await self._register_middleware()

        self._initialized = True
        logger.info("Slack Bolt app initialization complete")

    async def cleanup(self) -> None:
        """Clean up Slack app resources."""
        if self.app:
            logger.info("Cleaning up Slack Bolt app")
            # Stop the app if it's running
            if hasattr(self.app, "_client"):
                await self.app.client.rtm_disconnect()
            self.app = None
            self._initialized = False

    async def _register_handlers(self) -> None:
        """Register Slack event and command handlers."""
        if not self.app:
            return

        # Register message handlers
        @self.app.message("hello")
        async def handle_hello_message(message, say):
            await say(f"Hello <@{message['user']}>! 👋")

        # Register app mention handlers
        @self.app.event("app_mention")
        async def handle_app_mention(body, say):
            user = body["event"]["user"]
            await say(
                f"Hi <@{user}>! How can I help you with web defacement monitoring?"
            )

        # Register slash command handlers (will be expanded in SLK-04)
        @self.app.command("/webdeface")
        async def handle_webdeface_command(ack, respond, command):
            await ack()
            await respond("Web Defacement Monitor is active! 🚨")

        # Register button interaction handlers (will be expanded in SLK-05)
        @self.app.action("alert_acknowledge")
        async def handle_alert_acknowledge(ack, body, respond):
            await ack()
            user = body["user"]["username"]
            await respond(f"Alert acknowledged by {user} ✅")

        @self.app.action("alert_resolve")
        async def handle_alert_resolve(ack, body, respond):
            await ack()
            user = body["user"]["username"]
            await respond(f"Alert resolved by {user} ✅")

        logger.info("Slack event handlers registered")

    async def _register_middleware(self) -> None:
        """Register Slack middleware for authorization and logging."""
        if not self.app:
            return

        # Authorization middleware
        @self.app.middleware
        async def authorize_user(req: BoltRequest, resp, next):
            """Check if user is authorized to use the app."""
            user_id = None

            # Extract user ID from different event types
            if req.body.get("event"):
                user_id = req.body["event"].get("user")
            elif req.body.get("user"):
                user_id = req.body["user"].get("id")
            elif req.body.get("user_id"):
                user_id = req.body.get("user_id")

            # Check authorization if allowed users are configured
            if self.settings.allowed_users and user_id:
                if user_id not in self.settings.allowed_users:
                    logger.warning(
                        "Unauthorized user attempted access", user_id=user_id
                    )
                    return

            await next()

        # Logging middleware
        @self.app.middleware
        async def log_requests(req: BoltRequest, resp, next):
            """Log incoming Slack requests."""
            event_type = req.body.get("type", "unknown")
            user_id = None

            if req.body.get("event"):
                user_id = req.body["event"].get("user")
            elif req.body.get("user"):
                user_id = req.body["user"].get("id")

            logger.debug(
                "Slack request received", event_type=event_type, user_id=user_id
            )

            await next()

        logger.info("Slack middleware registered")

    async def start_socket_mode(self) -> None:
        """Start the Slack app in socket mode."""
        if not self.app:
            raise RuntimeError("Slack app not initialized")

        logger.info("Starting Slack app in socket mode")
        await self.app.async_start()

    async def stop_socket_mode(self) -> None:
        """Stop the Slack app socket mode."""
        if self.app:
            logger.info("Stopping Slack app socket mode")
            await self.app.async_stop()

    def get_app(self) -> AsyncApp:
        """Get the Slack Bolt app instance."""
        if not self.app:
            raise RuntimeError("Slack app not initialized")
        return self.app

    async def health_check(self) -> bool:
        """Perform Slack app health check."""
        try:
            if not self.app:
                return False

            # Test API connection
            response = await self.app.client.auth_test()
            return response.get("ok", False)
        except Exception as e:
            logger.error("Slack health check failed", error=str(e))
            return False

    async def get_bot_info(self) -> dict:
        """Get information about the bot."""
        if not self.app:
            return {}

        try:
            response = await self.app.client.auth_test()
            if response.get("ok"):
                return {
                    "bot_id": response.get("bot_id"),
                    "user_id": response.get("user_id"),
                    "team": response.get("team"),
                    "url": response.get("url"),
                }
            return {}
        except Exception as e:
            logger.error("Failed to get bot info", error=str(e))
            return {}


# Global Slack Bolt manager instance
_slack_manager: Optional[SlackBoltManager] = None


async def get_slack_manager(
    settings: Optional[SlackSettings] = None,
) -> SlackBoltManager:
    """Get or create the global Slack manager."""
    global _slack_manager

    if _slack_manager is None:
        if settings is None:
            from ...config import get_settings

            app_settings = get_settings()
            settings = app_settings.slack

        _slack_manager = SlackBoltManager(settings)
        await _slack_manager.setup()

    return _slack_manager


async def cleanup_slack_manager() -> None:
    """Clean up the global Slack manager."""
    global _slack_manager

    if _slack_manager:
        await _slack_manager.cleanup()
        _slack_manager = None


async def slack_health_check() -> bool:
    """Perform Slack health check."""
    try:
        slack_manager = await get_slack_manager()
        return await slack_manager.health_check()
    except Exception as e:
        logger.error("Slack health check failed", error=str(e))
        return False
