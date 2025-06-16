"""Slack notification integration module."""

from .app import (
    SlackBoltManager,
    cleanup_slack_manager,
    get_slack_manager,
    slack_health_check,
)
from .commands import SlackCommandHandler, get_command_handler, register_slack_commands
from .delivery import (
    SlackNotificationDelivery,
    get_notification_delivery,
    send_defacement_notification,
    send_site_down_notification,
    send_system_status_notification,
)
from .formatting import SlackMessageFormatter

# from .handlers import SlackEventHandler, get_event_handler, register_slack_handlers
from .handlers.router import SlackCommandRouter
from .integration import (
    SlackCLIIntegration,
    get_cli_integration,
    handle_cli_command_from_slack,
    register_cli_integration,
)
from .permissions import (
    Permission,
    Role,
    SlackPermissionManager,
    SlackUser,
    check_user_permission,
    get_permission_manager,
    permission_required,
    require_permission,
)
from .router import (
    NotificationPriority,
    NotificationRouter,
    NotificationTemplate,
    get_notification_router,
    route_defacement_notification,
    route_site_down_notification,
)

__all__ = [
    # App management
    "SlackBoltManager",
    "get_slack_manager",
    "cleanup_slack_manager",
    "slack_health_check",
    # Commands
    "SlackCommandHandler",
    "get_command_handler",
    "register_slack_commands",
    # CLI Integration
    "SlackCommandRouter",
    "SlackCLIIntegration",
    "get_cli_integration",
    "register_cli_integration",
    "handle_cli_command_from_slack",
    # Message delivery
    "SlackNotificationDelivery",
    "get_notification_delivery",
    "send_defacement_notification",
    "send_site_down_notification",
    "send_system_status_notification",
    # Message formatting
    "SlackMessageFormatter",
    # Event handlers
    # "SlackEventHandler",
    # "get_event_handler",
    # "register_slack_handlers",
    # Permissions
    "Permission",
    "Role",
    "SlackUser",
    "SlackPermissionManager",
    "get_permission_manager",
    "check_user_permission",
    "require_permission",
    "permission_required",
    # Routing
    "NotificationRouter",
    "NotificationTemplate",
    "NotificationPriority",
    "get_notification_router",
    "route_defacement_notification",
    "route_site_down_notification",
]
