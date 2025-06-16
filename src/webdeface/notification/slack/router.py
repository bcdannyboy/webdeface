"""Enhanced notification templates and routing system with CLI integration."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ...storage.sqlite.models import DefacementAlert, Website, WebsiteSnapshot
from ...utils.logging import get_structured_logger
from ..types import AlertType
from .delivery import get_notification_delivery
from .formatting import SlackMessageFormatter

logger = get_structured_logger(__name__)


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    SLACK = "slack"
    EMAIL = "email"  # Future implementation
    WEBHOOK = "webhook"  # Future implementation


class NotificationTemplate:
    """Represents a notification template with routing rules."""

    def __init__(
        self,
        template_id: str,
        alert_type: AlertType,
        priority: NotificationPriority,
        channels: list[str],
        users: list[str],
        conditions: Optional[dict[str, Any]] = None,
        throttle_minutes: int = 0,
        escalation_minutes: int = 0,
    ):
        self.template_id = template_id
        self.alert_type = alert_type
        self.priority = priority
        self.channels = channels
        self.users = users
        self.conditions = conditions or {}
        self.throttle_minutes = throttle_minutes
        self.escalation_minutes = escalation_minutes


class NotificationRouter:
    """Routes notifications based on templates and rules."""

    def __init__(self):
        self.formatter = SlackMessageFormatter()
        self.delivery = get_notification_delivery()
        self.templates: dict[str, NotificationTemplate] = {}
        self.notification_history: dict[str, datetime] = {}
        self.escalation_tracking: dict[str, datetime] = {}

        # Initialize default templates
        self._setup_default_templates()

    def _setup_default_templates(self) -> None:
        """Setup default notification templates."""

        # Critical defacement alerts
        self.add_template(
            NotificationTemplate(
                template_id="critical_defacement",
                alert_type=AlertType.DEFACEMENT,
                priority=NotificationPriority.CRITICAL,
                channels=["#security-alerts", "#incidents"],
                users=["@security-team"],
                conditions={"severity": "critical"},
                throttle_minutes=5,
                escalation_minutes=15,
            )
        )

        # High severity defacement alerts
        self.add_template(
            NotificationTemplate(
                template_id="high_defacement",
                alert_type=AlertType.DEFACEMENT,
                priority=NotificationPriority.HIGH,
                channels=["#security-alerts"],
                users=["@on-call"],
                conditions={"severity": "high"},
                throttle_minutes=10,
                escalation_minutes=30,
            )
        )

        # Medium/Low defacement alerts
        self.add_template(
            NotificationTemplate(
                template_id="standard_defacement",
                alert_type=AlertType.DEFACEMENT,
                priority=NotificationPriority.MEDIUM,
                channels=["#monitoring"],
                users=[],
                conditions={"severity": ["medium", "low"]},
                throttle_minutes=15,
            )
        )

        # Site down alerts
        self.add_template(
            NotificationTemplate(
                template_id="site_down_critical",
                alert_type=AlertType.SITE_DOWN,
                priority=NotificationPriority.HIGH,
                channels=["#infrastructure", "#monitoring"],
                users=["@sre-team"],
                throttle_minutes=5,
                escalation_minutes=20,
            )
        )

        # System error alerts
        self.add_template(
            NotificationTemplate(
                template_id="system_error",
                alert_type=AlertType.SYSTEM_ERROR,
                priority=NotificationPriority.MEDIUM,
                channels=["#monitoring"],
                users=["@admin"],
                throttle_minutes=30,
            )
        )

        # Benign change notifications
        self.add_template(
            NotificationTemplate(
                template_id="benign_change",
                alert_type=AlertType.BENIGN_CHANGE,
                priority=NotificationPriority.LOW,
                channels=["#monitoring"],
                users=[],
                throttle_minutes=60,
            )
        )

        logger.info(
            "Default notification templates initialized",
            template_count=len(self.templates),
        )

    def add_template(self, template: NotificationTemplate) -> None:
        """Add a notification template."""
        self.templates[template.template_id] = template
        logger.debug("Notification template added", template_id=template.template_id)

    def remove_template(self, template_id: str) -> bool:
        """Remove a notification template."""
        if template_id in self.templates:
            del self.templates[template_id]
            logger.debug("Notification template removed", template_id=template_id)
            return True
        return False

    async def route_defacement_alert(
        self,
        alert: DefacementAlert,
        website: Website,
        snapshot: Optional[WebsiteSnapshot] = None,
        custom_channels: Optional[list[str]] = None,
        custom_users: Optional[list[str]] = None,
    ) -> list[str]:
        """Route a defacement alert through the notification system."""

        logger.info(
            "Routing defacement alert",
            alert_id=alert.id,
            website_id=website.id,
            severity=alert.severity,
        )

        # Find matching templates
        matching_templates = self._find_matching_templates(
            AlertType.DEFACEMENT,
            {"severity": alert.severity, "confidence": alert.confidence_score},
        )

        if not matching_templates:
            logger.warning(
                "No matching templates for defacement alert",
                alert_id=alert.id,
                severity=alert.severity,
            )
            # Use fallback template
            matching_templates = [self.templates.get("standard_defacement")]

        # Collect all channels and users
        all_channels = set(custom_channels or [])
        all_users = set(custom_users or [])

        for template in matching_templates:
            if template and self._should_send_notification(template, alert.id):
                all_channels.update(template.channels)
                all_users.update(template.users)

        # Send notifications
        results = await self.delivery.send_defacement_alert(
            alert=alert,
            website=website,
            snapshot=snapshot,
            channels=list(all_channels),
            users=list(all_users),
        )

        # Track notification for throttling
        self._track_notification(alert.id)

        # Schedule escalation if needed
        await self._schedule_escalation(alert, matching_templates)

        successful_deliveries = [
            r.channel or r.message_id for r in results if r.success
        ]

        logger.info(
            "Defacement alert routing complete",
            alert_id=alert.id,
            delivered_to=len(successful_deliveries),
            channels=list(all_channels),
            users=list(all_users),
        )

        return successful_deliveries

    async def route_site_down_alert(
        self,
        website: Website,
        error_message: str,
        retry_count: int = 0,
        last_successful: Optional[datetime] = None,
        custom_channels: Optional[list[str]] = None,
        custom_users: Optional[list[str]] = None,
    ) -> list[str]:
        """Route a site down alert through the notification system."""

        logger.info(
            "Routing site down alert", website_id=website.id, error=error_message[:50]
        )

        # Find matching templates
        matching_templates = self._find_matching_templates(
            AlertType.SITE_DOWN, {"retry_count": retry_count}
        )

        if not matching_templates:
            matching_templates = [self.templates.get("site_down_critical")]

        # Collect channels and users
        all_channels = set(custom_channels or [])
        all_users = set(custom_users or [])

        for template in matching_templates:
            if template and self._should_send_notification(
                template, f"site_down_{website.id}"
            ):
                all_channels.update(template.channels)
                all_users.update(template.users)

        # Send notifications
        results = await self.delivery.send_site_down_alert(
            website=website,
            error_message=error_message,
            retry_count=retry_count,
            last_successful=last_successful,
            channels=list(all_channels),
            users=list(all_users),
        )

        # Track notification
        self._track_notification(f"site_down_{website.id}")

        successful_deliveries = [
            r.channel or r.message_id for r in results if r.success
        ]

        logger.info(
            "Site down alert routing complete",
            website_id=website.id,
            delivered_to=len(successful_deliveries),
        )

        return successful_deliveries

    async def route_system_status_update(
        self,
        health_status: dict[str, bool],
        storage_stats: dict[str, Any],
        active_alerts: int,
        monitored_sites: int,
        channels: Optional[list[str]] = None,
    ) -> list[str]:
        """Route system status updates."""

        logger.info(
            "Routing system status update",
            active_alerts=active_alerts,
            monitored_sites=monitored_sites,
        )

        # Use provided channels or default monitoring channels
        target_channels = channels or ["#monitoring"]

        results = await self.delivery.send_system_status(
            storage_health=health_status,
            storage_stats=storage_stats,
            active_alerts=active_alerts,
            monitored_sites=monitored_sites,
            channels=target_channels,
        )

        successful_deliveries = [
            r.channel or r.message_id for r in results if r.success
        ]

        logger.info(
            "System status update routing complete",
            delivered_to=len(successful_deliveries),
        )

        return successful_deliveries

    async def route_batch_alerts_summary(
        self,
        alerts: list[DefacementAlert],
        channels: Optional[list[str]] = None,
        summary_type: str = "daily",
    ) -> list[str]:
        """Route batch alert summaries."""

        logger.info(
            "Routing batch alerts summary",
            alert_count=len(alerts),
            summary_type=summary_type,
        )

        # Default to monitoring channels for summaries
        target_channels = channels or ["#monitoring", "#security-summary"]

        results = await self.delivery.send_alert_summary(
            alerts=alerts, channels=target_channels
        )

        successful_deliveries = [
            r.channel or r.message_id for r in results if r.success
        ]

        logger.info(
            "Batch alerts summary routing complete",
            delivered_to=len(successful_deliveries),
        )

        return successful_deliveries

    def _find_matching_templates(
        self, alert_type: AlertType, context: dict[str, Any]
    ) -> list[NotificationTemplate]:
        """Find templates that match the given alert type and conditions."""

        matching = []

        for template in self.templates.values():
            if template.alert_type != alert_type:
                continue

            # Check if template conditions match the context
            if self._template_matches_context(template, context):
                matching.append(template)

        # Sort by priority (critical first)
        priority_order = {
            NotificationPriority.CRITICAL: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.LOW: 3,
        }

        matching.sort(key=lambda t: priority_order.get(t.priority, 9))

        return matching

    def _template_matches_context(
        self, template: NotificationTemplate, context: dict[str, Any]
    ) -> bool:
        """Check if template conditions match the given context."""

        for condition_key, condition_value in template.conditions.items():
            context_value = context.get(condition_key)

            if context_value is None:
                continue

            # Handle list conditions (e.g., severity in ["medium", "low"])
            if isinstance(condition_value, list):
                if context_value not in condition_value:
                    return False
            # Handle exact match conditions
            elif context_value != condition_value:
                return False

        return True

    def _should_send_notification(
        self, template: NotificationTemplate, notification_key: str
    ) -> bool:
        """Check if notification should be sent based on throttling rules."""

        if template.throttle_minutes <= 0:
            return True

        last_sent = self.notification_history.get(
            f"{template.template_id}:{notification_key}"
        )

        if last_sent is None:
            return True

        time_since_last = datetime.utcnow() - last_sent
        throttle_threshold = timedelta(minutes=template.throttle_minutes)

        should_send = time_since_last >= throttle_threshold

        if not should_send:
            logger.debug(
                "Notification throttled",
                template_id=template.template_id,
                notification_key=notification_key,
                time_since_last=time_since_last.total_seconds(),
            )

        return should_send

    def _track_notification(self, notification_key: str) -> None:
        """Track when a notification was sent for throttling purposes."""
        timestamp = datetime.utcnow()

        # Clean up old entries to prevent memory growth
        cutoff = timestamp - timedelta(hours=24)
        self.notification_history = {
            k: v for k, v in self.notification_history.items() if v > cutoff
        }

        # Track this notification
        for template_id in self.templates.keys():
            key = f"{template_id}:{notification_key}"
            self.notification_history[key] = timestamp

    async def _schedule_escalation(
        self, alert: DefacementAlert, templates: list[NotificationTemplate]
    ) -> None:
        """Schedule escalation for unresolved alerts."""

        escalation_templates = [t for t in templates if t.escalation_minutes > 0]

        if not escalation_templates:
            return

        # For now, just log the escalation schedule
        # In a full implementation, this would use a task scheduler
        for template in escalation_templates:
            escalation_time = datetime.utcnow() + timedelta(
                minutes=template.escalation_minutes
            )

            logger.info(
                "Escalation scheduled",
                alert_id=alert.id,
                template_id=template.template_id,
                escalation_time=escalation_time.isoformat(),
            )

    def get_template_stats(self) -> dict[str, Any]:
        """Get statistics about notification templates and usage."""

        template_stats = {}

        for template_id, template in self.templates.items():
            # Count recent notifications for this template
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_count = sum(
                1
                for key, timestamp in self.notification_history.items()
                if key.startswith(f"{template_id}:") and timestamp > cutoff
            )

            template_stats[template_id] = {
                "alert_type": template.alert_type.value,
                "priority": template.priority.value,
                "channels": len(template.channels),
                "users": len(template.users),
                "recent_notifications_24h": recent_count,
                "throttle_minutes": template.throttle_minutes,
                "escalation_minutes": template.escalation_minutes,
            }

        return template_stats

    def cleanup_old_tracking_data(self, hours: int = 48) -> None:
        """Clean up old tracking data to prevent memory growth."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Clean notification history
        old_count = len(self.notification_history)
        self.notification_history = {
            k: v for k, v in self.notification_history.items() if v > cutoff
        }

        # Clean escalation tracking
        self.escalation_tracking = {
            k: v for k, v in self.escalation_tracking.items() if v > cutoff
        }

        cleaned_count = old_count - len(self.notification_history)
        if cleaned_count > 0:
            logger.debug(
                "Cleaned old tracking data",
                removed_entries=cleaned_count,
                remaining_entries=len(self.notification_history),
            )


# Global notification router instance
_notification_router: Optional[NotificationRouter] = None


def get_notification_router() -> NotificationRouter:
    """Get the global notification router instance."""
    global _notification_router

    if _notification_router is None:
        _notification_router = NotificationRouter()

    return _notification_router


async def route_defacement_notification(
    alert: DefacementAlert,
    website: Website,
    snapshot: Optional[WebsiteSnapshot] = None,
    custom_channels: Optional[list[str]] = None,
    custom_users: Optional[list[str]] = None,
) -> list[str]:
    """Convenience function to route defacement notifications."""
    router = get_notification_router()
    return await router.route_defacement_alert(
        alert, website, snapshot, custom_channels, custom_users
    )


async def route_site_down_notification(
    website: Website,
    error_message: str,
    retry_count: int = 0,
    last_successful: Optional[datetime] = None,
    custom_channels: Optional[list[str]] = None,
    custom_users: Optional[list[str]] = None,
) -> list[str]:
    """Convenience function to route site down notifications."""
    router = get_notification_router()
    return await router.route_site_down_alert(
        website,
        error_message,
        retry_count,
        last_successful,
        custom_channels,
        custom_users,
    )
