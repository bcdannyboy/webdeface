"""Response formatting utilities for converting CLI output to Slack format."""

import json
from datetime import datetime
from typing import Any, Optional

from ....cli.types import CommandResult
from ....utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class SlackResponseFormatter:
    """Converts CLI CommandResult objects to Slack-compatible response format."""

    def __init__(self):
        self.emoji_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "website": "🌐",
            "monitoring": "🔄",
            "system": "🖥️",
            "health": "💚",
            "metrics": "📊",
            "logs": "📋",
        }

    def format_command_response(
        self, result: CommandResult, user_id: str = None, verbose: bool = False, output_format: str = "table"
    ) -> dict[str, Any]:
        """
        Format CLI CommandResult for Slack response.
        
        Args:
            result: CLI CommandResult object
            user_id: Slack user ID (optional, for context)
            verbose: Whether to include verbose details
            output_format: Format preference (table, json)
            
        Returns:
            Slack response dict with text and blocks
        """
        return self.format_result(result, verbose, output_format)
    
    def format_result(
        self, result: CommandResult, verbose: bool = False, output_format: str = "table"
    ) -> dict[str, Any]:
        """
        Convert CommandResult to Slack response format.

        Args:
            result: CLI CommandResult object
            verbose: Whether to include verbose details
            output_format: Format preference (table, json)

        Returns:
            Slack response dict with text and blocks
        """
        try:
            if result.success:
                return self._format_success_result(result, verbose, output_format)
            else:
                return self._format_error_result(result, verbose)
        except Exception as e:
            logger.error("Error formatting Slack response", error=str(e))
            return self._format_fallback_error(str(e))
    
    def format_success(self, message: str, data: dict = None) -> dict[str, Any]:
        """Format a success response."""
        from ....cli.types import CommandResult
        result = CommandResult(success=True, message=message, data=data or {})
        return self.format_result(result)
    
    def format_error(self, message: str, data: dict = None) -> dict[str, Any]:
        """Format an error response."""
        from ....cli.types import CommandResult
        result = CommandResult(success=False, message=message, data=data or {})
        return self.format_result(result)
        
    def format_help(self, command_context: str = None) -> dict[str, Any]:
        """Format a help response."""
        return self.format_help_message(command_context)

    def format_error_response(self, error_message: str, error_type: str = "error") -> dict[str, Any]:
        """Format an error response with proper styling."""
        emoji = self.emoji_map.get(error_type, "❌")
        return {
            "text": f"{emoji} {error_message}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *Error:* {error_message}",
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

    def format_help_response(self, command_context: str = None) -> dict[str, Any]:
        """Format a help response."""
        return self.format_help_message(command_context)

    def _format_success_result(
        self, result: CommandResult, verbose: bool, output_format: str
    ) -> dict[str, Any]:
        """Format successful command result."""
        emoji = self.emoji_map["success"]

        # Base response structure
        response = {
            "text": f"{emoji} {result.message}"
            if result.message
            else f"{emoji} Command completed successfully",
            "response_type": "in_channel",
        }

        blocks = []

        # Add main message block
        if result.message:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{emoji} *{result.message}*"},
                }
            )

        # Add data blocks if present
        if result.data:
            data_blocks = self._format_data_blocks(result.data, output_format, verbose)
            blocks.extend(data_blocks)

        # Add timestamp for verbose mode
        if verbose:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏰ Executed at {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        }
                    ],
                }
            )

        if blocks:
            response["blocks"] = blocks

        return response

    def _format_error_result(
        self, result: CommandResult, verbose: bool
    ) -> dict[str, Any]:
        """Format error command result."""
        emoji = self.emoji_map["error"]

        response = {
            "text": f"{emoji} {result.message}"
            if result.message
            else f"{emoji} Command failed",
            "response_type": "ephemeral",  # Errors are private by default
        }

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Error:* {result.message}",
                },
            }
        ]

        # Add error details if available and verbose mode is on
        if verbose and result.data:
            if isinstance(result.data, dict) and result.data.get("error_details"):
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Details:* ```{json.dumps(result.data['error_details'], indent=2)}```",
                        },
                    }
                )

        # Add help suggestion
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 Try `/webdeface help` for available commands and usage examples",
                    }
                ],
            }
        )

        response["blocks"] = blocks
        return response

    def _format_data_blocks(
        self, data: dict[str, Any], output_format: str, verbose: bool
    ) -> list[dict[str, Any]]:
        """Format data into appropriate Slack blocks."""
        blocks = []

        if output_format == "json":
            # Format as JSON code block
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```json\n{json.dumps(data, indent=2, default=str)}\n```",
                    },
                }
            )
        else:
            # Format as structured blocks (table-like)
            blocks.extend(self._format_table_blocks(data, verbose))

        return blocks

    def _format_table_blocks(
        self, data: dict[str, Any], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format data as table-like Slack blocks."""
        blocks = []

        # Handle different data structures
        if "websites" in data:
            blocks.extend(self._format_websites_table(data["websites"], verbose))
        elif "alerts" in data:
            blocks.extend(self._format_alerts_table(data["alerts"], verbose))
        elif "status" in data or "health" in data:
            blocks.extend(self._format_status_table(data, verbose))
        elif "metrics" in data:
            blocks.extend(self._format_metrics_table(data["metrics"], verbose))
        else:
            # Generic key-value formatting
            blocks.extend(self._format_generic_table(data, verbose))

        return blocks

    def _format_websites_table(
        self, websites: list[dict], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format websites list as Slack blocks."""
        blocks = []

        if not websites:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "📝 No websites found"},
                }
            )
            return blocks

        # Header
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🌐 Websites ({len(websites)})",
                },
            }
        )

        # Website entries
        for website in websites[:10]:  # Limit to prevent message size issues
            status_emoji = "✅" if website.get("is_active", True) else "⏸️"
            last_checked = website.get("last_checked_at", "Never")
            if last_checked != "Never" and isinstance(last_checked, str):
                try:
                    dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
                    last_checked = dt.strftime("%m/%d %H:%M")
                except:
                    pass

            website_text = (
                f"{status_emoji} *{website.get('name', 'Unknown')}*\n"
                f"URL: <{website.get('url', '')}|{website.get('url', '')}>\n"
                f"Last Check: {last_checked}"
            )

            if verbose:
                website_text += (
                    f"\nInterval: {website.get('check_interval_seconds', 900)}s"
                )
                website_text += f"\nID: `{website.get('id', '')}`"

            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": website_text}}
            )

        if len(websites) > 10:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"... and {len(websites) - 10} more websites",
                        }
                    ],
                }
            )

        return blocks

    def _format_alerts_table(
        self, alerts: list[dict], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format alerts list as Slack blocks."""
        blocks = []

        if not alerts:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "📝 No alerts found"},
                }
            )
            return blocks

        # Header
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Alerts ({len(alerts)})",
                },
            }
        )

        # Alert entries
        for alert in alerts[:10]:  # Limit to prevent message size issues
            severity = alert.get("severity", "unknown").upper()
            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
                "INFO": "🔵"
            }.get(severity, "⚪")
            
            created_at = alert.get("created_at", "Unknown")
            if created_at != "Unknown" and isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_at = dt.strftime("%m/%d %H:%M")
                except:
                    pass

            alert_text = (
                f"{severity_emoji} *{alert.get('title', 'Unknown Alert')}*\n"
                f"Type: {alert.get('alert_type', 'Unknown')}\n"
                f"Severity: {severity}\n"
                f"Created: {created_at}"
            )

            if verbose:
                alert_text += f"\nWebsite: {alert.get('website_name', 'Unknown')}"
                alert_text += f"\nStatus: {alert.get('status', 'open')}"
                if alert.get('description'):
                    alert_text += f"\nDescription: {alert.get('description')}"

            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": alert_text}}
            )

        if len(alerts) > 10:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"... and {len(alerts) - 10} more alerts",
                        }
                    ],
                }
            )

        return blocks

    def _format_metrics_table(
        self, metrics: dict[str, Any], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format metrics data as Slack blocks."""
        blocks = []

        # Header
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 System Metrics",
                },
            }
        )

        # Format metrics by category
        if "performance" in metrics:
            perf = metrics["performance"]
            fields = []
            if "cpu_usage" in perf:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*CPU Usage:*\n{perf['cpu_usage']:.1f}%"
                })
            if "memory_usage" in perf:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Memory Usage:*\n{perf['memory_usage']:.1f}%"
                })
            if "disk_usage" in perf:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Disk Usage:*\n{perf['disk_usage']:.1f}%"
                })
            
            if fields:
                blocks.append({"type": "section", "fields": fields})

        # Add monitoring metrics if present
        if "monitoring" in metrics:
            mon = metrics["monitoring"]
            mon_text = "*Monitoring Activity:*\n"
            if "checks_performed" in mon:
                mon_text += f"Checks Performed: {mon['checks_performed']}\n"
            if "alerts_generated" in mon:
                mon_text += f"Alerts Generated: {mon['alerts_generated']}\n"
            if "average_response_time" in mon:
                mon_text += f"Avg Response Time: {mon['average_response_time']:.2f}ms\n"
                
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": mon_text}
            })

        return blocks

    def _format_status_table(
        self, data: dict[str, Any], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format system status as Slack blocks."""
        blocks = []

        # Main status
        overall_status = data.get("status", "unknown")
        status_emoji = "✅" if overall_status == "running" else "⚠️"

        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{status_emoji} System Status"},
            }
        )

        # Key metrics
        fields = []
        if "uptime_seconds" in data:
            uptime_hours = data["uptime_seconds"] / 3600
            fields.append(
                {"type": "mrkdwn", "text": f"*Uptime:*\n{uptime_hours:.1f} hours"}
            )

        if "active_websites" in data:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Active Sites:*\n{data['active_websites']}",
                }
            )

        if "total_jobs_scheduled" in data:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Scheduled Jobs:*\n{data['total_jobs_scheduled']}",
                }
            )

        if "total_workflows_executed" in data:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Workflows Executed:*\n{data['total_workflows_executed']}",
                }
            )

        if fields:
            blocks.append({"type": "section", "fields": fields})

        # Component status if verbose
        if verbose and "components" in data:
            component_text = "*Component Status:*\n"
            for component, status in data["components"].items():
                emoji = "✅" if status else "❌"
                component_text += f"{emoji} {component.replace('_', ' ').title()}\n"

            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": component_text}}
            )

        return blocks

    def _format_generic_table(
        self, data: dict[str, Any], verbose: bool
    ) -> list[dict[str, Any]]:
        """Format generic data as key-value pairs."""
        blocks = []

        # Convert dict to fields
        fields = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                continue  # Skip complex objects for now

            # Format key nicely
            display_key = key.replace("_", " ").title()

            fields.append({"type": "mrkdwn", "text": f"*{display_key}:*\n{str(value)}"})

        # Group fields into sections (max 10 fields per section)
        for i in range(0, len(fields), 10):
            section_fields = fields[i : i + 10]
            blocks.append({"type": "section", "fields": section_fields})

        return blocks

    def _format_fallback_error(self, error_message: str) -> dict[str, Any]:
        """Format a fallback error message when formatting fails."""
        return {
            "text": f"❌ Command failed: {error_message}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Internal Error*\n{error_message}",
                    },
                }
            ],
        }

    def format_help_message(
        self, command_context: Optional[str] = None
    ) -> dict[str, Any]:
        """Format help message for Slack."""
        if command_context == "website":
            return self._format_website_help()
        elif command_context == "monitoring":
            return self._format_monitoring_help()
        elif command_context == "system":
            return self._format_system_help()
        else:
            return self._format_general_help()

    def _format_general_help(self) -> dict[str, Any]:
        """Format general help message."""
        return {
            "text": "📖 WebDeface Monitor Help",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📖 WebDeface Monitor Commands",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Website Management:*\n• `/webdeface website add <url>` - Add website\n• `/webdeface website list` - List websites\n• `/webdeface website status <id>` - Show website status\n• `/webdeface website remove <id>` - Remove website",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Monitoring Control:*\n• `/webdeface monitoring start` - Start monitoring\n• `/webdeface monitoring stop` - Stop monitoring\n• `/webdeface monitoring pause <id>` - Pause monitoring\n• `/webdeface monitoring resume <id>` - Resume monitoring\n• `/webdeface monitoring check <id>` - Run immediate check",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*System Information:*\n• `/webdeface system status` - System status\n• `/webdeface system health` - Health check\n• `/webdeface system metrics` - System metrics\n• `/webdeface system logs` - View system logs",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": '*Command Syntax:*\nUse `key:value` for flags: `name:MyWebsite interval:600`\nUse quotes for values with spaces: `name:"My Website"`',
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": '*Examples:*\n• `/webdeface website add https://example.com name:"My Website" interval:600`\n• `/webdeface monitoring start`\n• `/webdeface system logs level:error limit:20`\n• `/webdeface website list status:active`',
                    },
                },
            ],
        }

    def _format_website_help(self) -> dict[str, Any]:
        """Format website-specific help message."""
        return {
            "text": "🌐 Website Management Help",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🌐 Website Management Commands",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `add <url>` - Add a new website for monitoring\n• `remove <id>` - Remove a website from monitoring\n• `list` - List all monitored websites\n• `status <id>` - Show detailed status for a website",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": '*Add Command Flags:*\n• `name:"Website Name"` - Custom display name\n• `interval:600` - Check interval in seconds (default: 900)\n• `max-depth:3` - Maximum crawl depth (default: 2)',
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*List Command Flags:*\n• `status:active` - Show only active websites\n• `status:inactive` - Show only inactive websites\n• `status:all` - Show all websites (default)\n• `format:json` - Output in JSON format",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": '*Examples:*\n• `/webdeface website add https://example.com`\n• `/webdeface website add https://example.com name:"My Site" interval:300`\n• `/webdeface website list status:active`\n• `/webdeface website status abc123`',
                    },
                },
            ],
        }

    def _format_monitoring_help(self) -> dict[str, Any]:
        """Format monitoring-specific help message."""
        return {
            "text": "🔄 Monitoring Control Help",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔄 Monitoring Control Commands",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `start [<id>]` - Start monitoring (all sites or specific site)\n• `stop [<id>]` - Stop monitoring (all sites or specific site)\n• `pause <id>` - Pause monitoring for a specific site\n• `resume <id>` - Resume monitoring for a specific site\n• `check <id>` - Run immediate check for a specific site",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Pause Command Flags:*\n• `duration:3600` - Pause duration in seconds (default: 3600)",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Examples:*\n• `/webdeface monitoring start` - Start all monitoring\n• `/webdeface monitoring stop abc123` - Stop monitoring for specific site\n• `/webdeface monitoring pause abc123 duration:1800` - Pause for 30 minutes\n• `/webdeface monitoring check abc123` - Run immediate check",
                    },
                },
            ],
        }

    def _format_system_help(self) -> dict[str, Any]:
        """Format system-specific help message."""
        return {
            "text": "🖥️ System Information Help",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🖥️ System Information Commands",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `status` - Show overall system status\n• `health` - Show detailed health information\n• `metrics` - Show system metrics and statistics\n• `logs` - View recent system logs",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Metrics Command Flags:*\n• `range:24h` - Time range (1h, 24h, 7d, 30d)\n• `type:performance` - Metric type (performance, monitoring, alerts, system, all)",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Logs Command Flags:*\n• `level:error` - Log level (debug, info, warning, error)\n• `component:scheduler` - Filter by component\n• `limit:50` - Number of entries to show (default: 50)\n• `since:2h` - Show logs since (e.g., 2h, 1d, 2024-01-01)",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Examples:*\n• `/webdeface system status`\n• `/webdeface system metrics range:7d type:performance`\n• `/webdeface system logs level:error limit:20`\n• `/webdeface system logs component:scheduler since:1h`",
                    },
                },
            ],
        }


def format_cli_result_for_slack(
    result: CommandResult, verbose: bool = False, output_format: str = "table"
) -> dict[str, Any]:
    """
    Convenience function to format CLI result for Slack.

    Args:
        result: CLI CommandResult object
        verbose: Whether to include verbose details
        output_format: Format preference (table, json)

    Returns:
        Slack-compatible response dict
    """
    formatter = SlackResponseFormatter()
    return formatter.format_result(result, verbose, output_format)


# Alias for backward compatibility and cleaner imports
SlackFormatter = SlackResponseFormatter
