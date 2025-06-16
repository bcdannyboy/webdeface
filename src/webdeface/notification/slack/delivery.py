"""Notification delivery system with retry logic and error handling."""

import asyncio
from datetime import datetime
from typing import Any, Optional

from slack_sdk.errors import SlackApiError

from ...storage.sqlite.models import DefacementAlert, Website, WebsiteSnapshot
from ...utils.async_utils import retry_async
from ...utils.logging import get_structured_logger
from ..types import MessageResult
from .app import get_slack_manager
from .formatting import SlackMessageFormatter

logger = get_structured_logger(__name__)


class SlackNotificationDelivery:
    """Handles Slack notification delivery with retry logic and error handling."""

    def __init__(self):
        self.formatter = SlackMessageFormatter()
        self.delivery_stats = {
            "sent": 0,
            "failed": 0,
            "retried": 0,
        }

    async def send_defacement_alert(
        self,
        alert: DefacementAlert,
        website: Website,
        snapshot: Optional[WebsiteSnapshot] = None,
        channels: Optional[list[str]] = None,
        users: Optional[list[str]] = None,
    ) -> list[MessageResult]:
        """Send defacement alert to specified channels and users."""

        logger.info(
            "Sending defacement alert",
            alert_id=alert.id,
            website_id=website.id,
            channels=channels,
            users=users,
        )

        # Format message
        message_data = self.formatter.format_defacement_alert(alert, website, snapshot)

        # Send to channels and users
        results = []

        if channels:
            for channel in channels:
                result = await self._send_message_with_retry(
                    channel=channel,
                    message_data=message_data,
                    message_type="defacement_alert",
                )
                results.append(result)

        if users:
            for user in users:
                # Convert username to DM channel
                dm_channel = await self._get_dm_channel(user)
                if dm_channel:
                    result = await self._send_message_with_retry(
                        channel=dm_channel,
                        message_data=message_data,
                        message_type="defacement_alert",
                    )
                    results.append(result)

        # Update alert notification tracking
        successful_sends = sum(1 for r in results if r.success)
        if successful_sends > 0:
            await self._update_alert_notification_tracking(alert.id)

        logger.info(
            "Defacement alert delivery complete",
            alert_id=alert.id,
            total_attempts=len(results),
            successful=successful_sends,
        )

        return results

    async def send_site_down_alert(
        self,
        website: Website,
        error_message: str,
        retry_count: int = 0,
        last_successful: Optional[datetime] = None,
        channels: Optional[list[str]] = None,
        users: Optional[list[str]] = None,
    ) -> list[MessageResult]:
        """Send site down alert to specified channels and users."""

        logger.info(
            "Sending site down alert",
            website_id=website.id,
            error=error_message,
            channels=channels,
            users=users,
        )

        # Format message
        message_data = self.formatter.format_site_down_alert(
            website, error_message, retry_count, last_successful
        )

        # Send to channels and users
        results = []

        if channels:
            for channel in channels:
                result = await self._send_message_with_retry(
                    channel=channel,
                    message_data=message_data,
                    message_type="site_down_alert",
                )
                results.append(result)

        if users:
            for user in users:
                dm_channel = await self._get_dm_channel(user)
                if dm_channel:
                    result = await self._send_message_with_retry(
                        channel=dm_channel,
                        message_data=message_data,
                        message_type="site_down_alert",
                    )
                    results.append(result)

        successful_sends = sum(1 for r in results if r.success)
        logger.info(
            "Site down alert delivery complete",
            website_id=website.id,
            total_attempts=len(results),
            successful=successful_sends,
        )

        return results

    async def send_system_status(
        self,
        storage_health: dict[str, bool],
        storage_stats: dict[str, Any],
        active_alerts: int,
        monitored_sites: int,
        channels: Optional[list[str]] = None,
    ) -> list[MessageResult]:
        """Send system status update to specified channels."""

        logger.info(
            "Sending system status update",
            channels=channels,
            active_alerts=active_alerts,
            monitored_sites=monitored_sites,
        )

        # Format message
        message_data = self.formatter.format_system_status(
            storage_health, storage_stats, active_alerts, monitored_sites
        )

        # Send to channels
        results = []
        if channels:
            for channel in channels:
                result = await self._send_message_with_retry(
                    channel=channel,
                    message_data=message_data,
                    message_type="system_status",
                )
                results.append(result)

        successful_sends = sum(1 for r in results if r.success)
        logger.info(
            "System status update delivery complete",
            total_attempts=len(results),
            successful=successful_sends,
        )

        return results

    async def send_alert_summary(
        self, alerts: list[DefacementAlert], channels: Optional[list[str]] = None
    ) -> list[MessageResult]:
        """Send alert summary to specified channels."""

        logger.info("Sending alert summary", channels=channels, alert_count=len(alerts))

        # Format message
        message_data = self.formatter.format_alert_summary(alerts)

        # Send to channels
        results = []
        if channels:
            for channel in channels:
                result = await self._send_message_with_retry(
                    channel=channel,
                    message_data=message_data,
                    message_type="alert_summary",
                )
                results.append(result)

        successful_sends = sum(1 for r in results if r.success)
        logger.info(
            "Alert summary delivery complete",
            total_attempts=len(results),
            successful=successful_sends,
        )

        return results

    async def send_simple_message(
        self,
        text: str,
        channels: Optional[list[str]] = None,
        users: Optional[list[str]] = None,
        emoji: str = "ℹ️",
        color: Optional[str] = None,
    ) -> list[MessageResult]:
        """Send a simple text message."""

        logger.debug(
            "Sending simple message",
            text=text[:50] + "..." if len(text) > 50 else text,
            channels=channels,
            users=users,
        )

        # Format message
        message_data = self.formatter.format_simple_message(text, emoji, color)

        # Send to channels and users
        results = []

        if channels:
            for channel in channels:
                result = await self._send_message_with_retry(
                    channel=channel,
                    message_data=message_data,
                    message_type="simple_message",
                )
                results.append(result)

        if users:
            for user in users:
                dm_channel = await self._get_dm_channel(user)
                if dm_channel:
                    result = await self._send_message_with_retry(
                        channel=dm_channel,
                        message_data=message_data,
                        message_type="simple_message",
                    )
                    results.append(result)

        return results

    async def _send_message_with_retry(
        self,
        channel: str,
        message_data: dict[str, Any],
        message_type: str,
        max_retries: int = 3,
    ) -> MessageResult:
        """Send a message with retry logic."""

        async def send_attempt():
            slack_manager = await get_slack_manager()
            app = slack_manager.get_app()

            # Send message
            response = await app.client.chat_postMessage(
                channel=channel, **message_data
            )

            return MessageResult(
                success=True,
                message_id=response["ts"],
                channel=channel,
                sent_at=datetime.utcnow(),
            )

        try:
            result = await retry_async(
                send_attempt(),
                max_retries=max_retries,
                delay=1.0,
                backoff_factor=2.0,
                exceptions=(SlackApiError, Exception),
            )

            self.delivery_stats["sent"] += 1
            logger.debug(
                "Message sent successfully",
                channel=channel,
                message_type=message_type,
                message_id=result.message_id,
            )

            return result

        except Exception as e:
            self.delivery_stats["failed"] += 1
            error_msg = str(e)

            logger.error(
                "Failed to send message after retries",
                channel=channel,
                message_type=message_type,
                error=error_msg,
            )

            return MessageResult(
                success=False,
                channel=channel,
                error_message=error_msg,
                sent_at=datetime.utcnow(),
            )

    async def _get_dm_channel(self, user: str) -> Optional[str]:
        """Get or create a direct message channel with a user."""
        try:
            slack_manager = await get_slack_manager()
            app = slack_manager.get_app()

            # Open DM channel
            response = await app.client.conversations_open(users=[user])

            if response["ok"]:
                return response["channel"]["id"]

            logger.warning("Failed to open DM channel", user=user)
            return None

        except Exception as e:
            logger.error("Error opening DM channel", user=user, error=str(e))
            return None

    async def _update_alert_notification_tracking(self, alert_id: str) -> None:
        """Update notification tracking for an alert."""
        try:
            from ...storage import get_storage_manager

            storage = await get_storage_manager()

            # This would update the alert's notification tracking
            # For now, just log the notification
            logger.debug("Alert notification sent", alert_id=alert_id)

        except Exception as e:
            logger.error(
                "Failed to update alert notification tracking",
                alert_id=alert_id,
                error=str(e),
            )

    async def batch_send_notifications(
        self,
        notifications: list[tuple[str, dict[str, Any], list[str]]],
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
    ) -> list[MessageResult]:
        """Send multiple notifications in batches to avoid rate limits."""

        logger.info(
            "Starting batch notification delivery",
            total_notifications=len(notifications),
            batch_size=batch_size,
        )

        all_results = []

        for i in range(0, len(notifications), batch_size):
            batch = notifications[i : i + batch_size]

            # Send batch concurrently
            batch_tasks = []
            for message_type, message_data, channels in batch:
                for channel in channels:
                    task = self._send_message_with_retry(
                        channel=channel,
                        message_data=message_data,
                        message_type=message_type,
                    )
                    batch_tasks.append(task)

            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, MessageResult):
                    all_results.append(result)
                elif isinstance(result, Exception):
                    logger.error("Batch notification failed", error=str(result))
                    all_results.append(
                        MessageResult(
                            success=False,
                            error_message=str(result),
                            sent_at=datetime.utcnow(),
                        )
                    )

            # Delay between batches
            if i + batch_size < len(notifications):
                await asyncio.sleep(delay_between_batches)

        successful_sends = sum(1 for r in all_results if r.success)
        logger.info(
            "Batch notification delivery complete",
            total_sent=len(all_results),
            successful=successful_sends,
        )

        return all_results

    def get_delivery_stats(self) -> dict[str, int]:
        """Get delivery statistics."""
        return self.delivery_stats.copy()

    def reset_delivery_stats(self) -> None:
        """Reset delivery statistics."""
        self.delivery_stats = {"sent": 0, "failed": 0, "retried": 0}


# Global notification delivery instance
_notification_delivery: Optional[SlackNotificationDelivery] = None


def get_notification_delivery() -> SlackNotificationDelivery:
    """Get the global notification delivery instance."""
    global _notification_delivery

    if _notification_delivery is None:
        _notification_delivery = SlackNotificationDelivery()

    return _notification_delivery


async def send_defacement_notification(
    alert: DefacementAlert,
    website: Website,
    snapshot: Optional[WebsiteSnapshot] = None,
    channels: Optional[list[str]] = None,
    users: Optional[list[str]] = None,
) -> list[MessageResult]:
    """Convenience function to send defacement notification."""
    delivery = get_notification_delivery()
    return await delivery.send_defacement_alert(
        alert, website, snapshot, channels, users
    )


async def send_site_down_notification(
    website: Website,
    error_message: str,
    retry_count: int = 0,
    last_successful: Optional[datetime] = None,
    channels: Optional[list[str]] = None,
    users: Optional[list[str]] = None,
) -> list[MessageResult]:
    """Convenience function to send site down notification."""
    delivery = get_notification_delivery()
    return await delivery.send_site_down_alert(
        website, error_message, retry_count, last_successful, channels, users
    )


async def send_system_status_notification(
    storage_health: dict[str, bool],
    storage_stats: dict[str, Any],
    active_alerts: int,
    monitored_sites: int,
    channels: Optional[list[str]] = None,
) -> list[MessageResult]:
    """Convenience function to send system status notification."""
    delivery = get_notification_delivery()
    return await delivery.send_system_status(
        storage_health, storage_stats, active_alerts, monitored_sites, channels
    )
