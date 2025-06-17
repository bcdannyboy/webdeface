"""Slack notification integration module."""

from .app import (
    SlackBoltManager,
    cleanup_slack_manager,
    get_slack_manager,
    slack_health_check,
)
from .delivery import (
    SlackNotificationDelivery,
    get_notification_delivery,
    send_defacement_notification,
    send_site_down_notification,
    send_system_status_notification,
)
from .formatting import SlackMessageFormatter
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

# Lazy imports to avoid circular dependencies
def get_command_handler():
    """Get command handler with lazy import."""
    from .commands import get_command_handler as _get_command_handler
    return _get_command_handler()

def register_slack_commands():
    """Register Slack commands with lazy import."""
    from .commands import register_slack_commands as _register_slack_commands
    return _register_slack_commands()

def get_command_router():
    """Get command router with lazy import."""
    from .handlers.router import get_command_router as _get_command_router
    return _get_command_router()

def register_slack_handlers():
    """Register Slack handlers with lazy import."""
    from .handlers import register_slack_handlers as _register_slack_handlers
    return _register_slack_handlers()

__all__ = [
    # App management
    "SlackBoltManager",
    "get_slack_manager",
    "cleanup_slack_manager",
    "slack_health_check",
    # Commands (lazy loaded)
    "get_command_handler",
    "register_slack_commands",
    "register_slack_handlers",
    # CLI Integration
    "SlackCLIIntegration",
    "get_cli_integration",
    "register_cli_integration",
    "handle_cli_command_from_slack",
    # Command routing (lazy loaded)
    "get_command_router",
    # Message delivery
    "SlackNotificationDelivery",
    "get_notification_delivery",
    "send_defacement_notification",
    "send_site_down_notification",
    "send_system_status_notification",
    # Message formatting
    "SlackMessageFormatter",
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
