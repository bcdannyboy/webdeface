"""Notification module for web defacement alerts and system notifications."""

from .slack import (
    NotificationPriority,
    # Routing
    NotificationRouter,
    NotificationTemplate,
    # Permissions
    Permission,
    Role,
    # App management
    SlackBoltManager,
    # Formatting
    SlackMessageFormatter,
    # Message delivery
    SlackNotificationDelivery,
    SlackPermissionManager,
    SlackUser,
    check_user_permission,
    cleanup_slack_manager,
    get_notification_delivery,
    get_notification_router,
    get_permission_manager,
    get_slack_manager,
    permission_required,
    # Commands and handlers
    register_slack_commands,
    register_slack_handlers,
    require_permission,
    route_defacement_notification,
    route_site_down_notification,
    send_defacement_notification,
    send_site_down_notification,
    send_system_status_notification,
    slack_health_check,
)
from .types import (
    AlertContext,
    AlertType,
    DefacementAlert,
    MessageResult,
    NotificationError,
    SiteDownAlert,
    SlackMessage,
)

__all__ = [
    # Types
    "AlertType",
    "AlertContext",
    "DefacementAlert",
    "MessageResult",
    "NotificationError",
    "SiteDownAlert",
    "SlackMessage",
    # Slack integration
    "SlackBoltManager",
    "get_slack_manager",
    "cleanup_slack_manager",
    "slack_health_check",
    "register_slack_commands",
    "register_slack_handlers",
    "SlackNotificationDelivery",
    "get_notification_delivery",
    "send_defacement_notification",
    "send_site_down_notification",
    "send_system_status_notification",
    "SlackMessageFormatter",
    "Permission",
    "Role",
    "SlackUser",
    "SlackPermissionManager",
    "get_permission_manager",
    "check_user_permission",
    "require_permission",
    "permission_required",
    "NotificationRouter",
    "NotificationTemplate",
    "NotificationPriority",
    "get_notification_router",
    "route_defacement_notification",
    "route_site_down_notification",
]
