"""Message formatting utilities for Slack notifications."""

from datetime import datetime
from typing import Any, Optional

from ...storage.sqlite.models import DefacementAlert, Website, WebsiteSnapshot
from ...utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class SlackMessageFormatter:
    """Formats various types of messages for Slack delivery."""

    @staticmethod
    def format_defacement_alert(
        alert: DefacementAlert,
        website: Website,
        snapshot: Optional[WebsiteSnapshot] = None,
    ) -> dict[str, Any]:
        """Format a defacement alert for Slack."""

        # Determine severity emoji and color
        severity_config = {
            "low": {"emoji": "🟡", "color": "#FFA500"},
            "medium": {"emoji": "🟠", "color": "#FF6B35"},
            "high": {"emoji": "🔴", "color": "#FF0000"},
            "critical": {"emoji": "🚨", "color": "#8B0000"},
        }

        config = severity_config.get(alert.severity, severity_config["medium"])

        # Build main message text
        main_text = (
            f"{config['emoji']} *DEFACEMENT DETECTED* {config['emoji']}\n"
            f"Website: {website.name} ({website.url})\n"
            f"Severity: {alert.severity.upper()}\n"
            f"Detected: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        # Build blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{config['emoji']} Defacement Alert - {alert.severity.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Website:*\n{website.name}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*URL:*\n<{website.url}|{website.url}>",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert.severity.upper()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Detected:*\n{alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{alert.description}",
                },
            },
        ]

        # Add classification details if available
        if alert.classification_label or alert.confidence_score:
            classification_text = []
            if alert.classification_label:
                classification_text.append(
                    f"*Classification:* {alert.classification_label}"
                )
            if alert.confidence_score:
                classification_text.append(
                    f"*Confidence:* {alert.confidence_score:.2%}"
                )
            if alert.similarity_score:
                classification_text.append(
                    f"*Similarity:* {alert.similarity_score:.2%}"
                )

            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(classification_text)},
                }
            )

        # Add snapshot details if available
        if snapshot:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Status Code:*\n{snapshot.status_code}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Response Time:*\n{snapshot.response_time_ms:.0f}ms",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Content Hash:*\n`{snapshot.content_hash[:16]}...`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Captured:*\n{snapshot.captured_at.strftime('%H:%M:%S UTC')}",
                        },
                    ],
                }
            )

        # Add action buttons
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 Investigate"},
                        "style": "primary",
                        "action_id": "alert_investigate",
                        "value": alert.id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Acknowledge"},
                        "action_id": "alert_acknowledge",
                        "value": alert.id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✔️ Resolve"},
                        "style": "danger",
                        "action_id": "alert_resolve",
                        "value": alert.id,
                    },
                ],
            }
        )

        return {
            "text": main_text,
            "blocks": blocks,
            "attachments": [
                {
                    "color": config["color"],
                    "fields": [
                        {"title": "Alert ID", "value": alert.id, "short": True},
                        {"title": "Website ID", "value": website.id, "short": True},
                    ],
                }
            ],
        }

    @staticmethod
    def format_site_down_alert(
        website: Website,
        error_message: str,
        retry_count: int = 0,
        last_successful: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Format a site down alert for Slack."""

        main_text = (
            f"🔴 *SITE DOWN ALERT*\n"
            f"Website: {website.name} ({website.url})\n"
            f"Error: {error_message}\n"
            f"Detected: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔴 Site Down Alert"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Website:*\n{website.name}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*URL:*\n<{website.url}|{website.url}>",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Error:*\n```{error_message}```"},
            },
        ]

        # Add retry information if applicable
        if retry_count > 0:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Retry Attempts:* {retry_count}",
                    },
                }
            )

        # Add last successful check if available
        if last_successful:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Last Successful Check:* {last_successful.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                }
            )

        return {
            "text": main_text,
            "blocks": blocks,
            "attachments": [
                {
                    "color": "#FF0000",
                    "fields": [
                        {"title": "Website ID", "value": website.id, "short": True},
                        {"title": "Status", "value": "DOWN", "short": True},
                    ],
                }
            ],
        }

    @staticmethod
    def format_system_status(
        storage_health: dict[str, bool],
        storage_stats: dict[str, Any],
        active_alerts: int,
        monitored_sites: int,
    ) -> dict[str, Any]:
        """Format system status message for Slack."""

        # Determine overall health
        all_healthy = all(storage_health.values()) if storage_health else False
        status_emoji = "✅" if all_healthy else "⚠️"

        main_text = (
            f"{status_emoji} *Web Defacement Monitor Status*\n"
            f"Overall Health: {'Healthy' if all_healthy else 'Issues Detected'}\n"
            f"Active Alerts: {active_alerts}\n"
            f"Monitored Sites: {monitored_sites}"
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} System Status Report",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Overall Status:*\n{'✅ Healthy' if all_healthy else '⚠️ Issues'}",
                    },
                    {"type": "mrkdwn", "text": f"*Active Alerts:*\n{active_alerts}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Monitored Sites:*\n{monitored_sites}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Last Updated:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
        ]

        # Add storage health details
        if storage_health:
            health_text = []
            for component, healthy in storage_health.items():
                emoji = "✅" if healthy else "❌"
                health_text.append(f"{emoji} {component.replace('_', ' ').title()}")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Storage Health:*\n" + "\n".join(health_text),
                    },
                }
            )

        # Add storage statistics
        if storage_stats:
            stats_text = []
            for component, stats in storage_stats.items():
                if isinstance(stats, dict):
                    if component == "database":
                        total_records = sum(
                            info.get("row_count", 0)
                            for info in stats.values()
                            if isinstance(info, dict)
                        )
                        stats_text.append(f"Database: {total_records} total records")
                    elif component == "vector_database":
                        vectors_count = stats.get("vectors_count", 0)
                        stats_text.append(f"Vector DB: {vectors_count} vectors")

            if stats_text:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Storage Stats:*\n" + "\n".join(stats_text),
                        },
                    }
                )

        return {"text": main_text, "blocks": blocks}

    @staticmethod
    def format_alert_summary(alerts: list[DefacementAlert]) -> dict[str, Any]:
        """Format a summary of multiple alerts."""

        if not alerts:
            return {
                "text": "✅ No active alerts",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "✅ *No Active Alerts*\nAll monitored websites are secure.",
                        },
                    }
                ],
            }

        # Count alerts by severity
        severity_counts = {}
        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        main_text = f"🚨 *Alert Summary* - {len(alerts)} active alerts"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Alert Summary ({len(alerts)} active)",
                },
            }
        ]

        # Add severity breakdown
        severity_text = []
        for severity in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = {"critical": "🚨", "high": "🔴", "medium": "🟠", "low": "🟡"}[
                    severity
                ]
                severity_text.append(f"{emoji} {severity.title()}: {count}")

        if severity_text:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*By Severity:*\n" + "\n".join(severity_text),
                    },
                }
            )

        # Add recent alerts (up to 5)
        recent_alerts = sorted(alerts, key=lambda a: a.created_at, reverse=True)[:5]
        if recent_alerts:
            alert_list = []
            for alert in recent_alerts:
                time_str = alert.created_at.strftime("%H:%M")
                alert_list.append(f"• {time_str} - {alert.title} ({alert.severity})")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Recent Alerts:*\n" + "\n".join(alert_list),
                    },
                }
            )

        return {"text": main_text, "blocks": blocks}

    @staticmethod
    def format_simple_message(
        text: str, emoji: str = "ℹ️", color: Optional[str] = None
    ) -> dict[str, Any]:
        """Format a simple text message."""

        message = {
            "text": f"{emoji} {text}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{emoji} {text}"},
                }
            ],
        }

        if color:
            message["attachments"] = [{"color": color}]

        return message

    @staticmethod
    def format_help_message() -> dict[str, Any]:
        """Format help message with available commands."""

        return {
            "text": "📖 Web Defacement Monitor Help",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📖 Web Defacement Monitor Help",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Available Commands:*"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "• `/webdeface status` - Show system status\n"
                            "• `/webdeface alerts` - List active alerts\n"
                            "• `/webdeface sites` - List monitored sites\n"
                            "• `/webdeface help` - Show this help message"
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Interactive Features:*"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "• Click buttons on alerts to acknowledge or resolve\n"
                            "• Mention the bot for quick status updates\n"
                            "• Use reactions on alert messages for quick actions"
                        ),
                    },
                },
            ],
        }
