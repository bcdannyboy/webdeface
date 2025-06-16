"""User permission and authorization system for Slack integration."""

from enum import Enum
from typing import Optional

from slack_sdk.errors import SlackApiError

from ...config.settings import SlackSettings
from ...utils.logging import get_structured_logger
from .app import get_slack_manager

logger = get_structured_logger(__name__)


class Permission(str, Enum):
    """Available permissions for Slack users."""

    # View permissions
    VIEW_STATUS = "view_status"
    VIEW_ALERTS = "view_alerts"
    VIEW_SITES = "view_sites"
    VIEW_SYSTEM = "view_system"
    VIEW_METRICS = "view_metrics"
    VIEW_LOGS = "view_logs"
    VIEW_MONITORING = "view_monitoring"

    # Alert management permissions
    ACKNOWLEDGE_ALERTS = "acknowledge_alerts"
    RESOLVE_ALERTS = "resolve_alerts"

    # Site management permissions
    ADD_SITES = "add_sites"
    REMOVE_SITES = "remove_sites"
    PAUSE_SITES = "pause_sites"
    EDIT_SITES = "edit_sites"
    MANAGE_SITES = "manage_sites"

    # Monitoring permissions
    START_MONITORING = "start_monitoring"
    STOP_MONITORING = "stop_monitoring"
    PAUSE_MONITORING = "pause_monitoring"
    TRIGGER_CHECKS = "trigger_checks"
    CONTROL_MONITORING = "control_monitoring"

    # System management permissions
    SYSTEM_ADMIN = "system_admin"
    USER_MANAGEMENT = "user_management"


class Role(str, Enum):
    """User roles with predefined permission sets."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.VIEWER: {
        Permission.VIEW_STATUS,
        Permission.VIEW_ALERTS,
        Permission.VIEW_SITES,
        Permission.VIEW_SYSTEM,
        Permission.VIEW_METRICS,
        Permission.VIEW_LOGS,
    },
    Role.OPERATOR: {
        Permission.VIEW_STATUS,
        Permission.VIEW_ALERTS,
        Permission.VIEW_SITES,
        Permission.VIEW_SYSTEM,
        Permission.VIEW_METRICS,
        Permission.VIEW_LOGS,
        Permission.VIEW_MONITORING,
        Permission.ACKNOWLEDGE_ALERTS,
        Permission.RESOLVE_ALERTS,
        Permission.PAUSE_SITES,
        Permission.PAUSE_MONITORING,
        Permission.TRIGGER_CHECKS,
    },
    Role.ADMIN: {
        Permission.VIEW_STATUS,
        Permission.VIEW_ALERTS,
        Permission.VIEW_SITES,
        Permission.VIEW_SYSTEM,
        Permission.VIEW_METRICS,
        Permission.VIEW_LOGS,
        Permission.VIEW_MONITORING,
        Permission.ACKNOWLEDGE_ALERTS,
        Permission.RESOLVE_ALERTS,
        Permission.ADD_SITES,
        Permission.REMOVE_SITES,
        Permission.PAUSE_SITES,
        Permission.EDIT_SITES,
        Permission.MANAGE_SITES,
        Permission.START_MONITORING,
        Permission.STOP_MONITORING,
        Permission.PAUSE_MONITORING,
        Permission.TRIGGER_CHECKS,
        Permission.CONTROL_MONITORING,
    },
    Role.SUPER_ADMIN: set(Permission),  # All permissions
}


class SlackUser:
    """Represents a Slack user with permissions."""

    def __init__(
        self,
        user_id: str,
        username: str,
        real_name: Optional[str] = None,
        email: Optional[str] = None,
        role: Role = Role.VIEWER,
        custom_permissions: Optional[set[Permission]] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.real_name = real_name
        self.email = email
        self.role = role
        self.custom_permissions = custom_permissions or set()
        self._effective_permissions: Optional[set[Permission]] = None

    @property
    def effective_permissions(self) -> set[Permission]:
        """Get effective permissions (role + custom permissions)."""
        if self._effective_permissions is None:
            role_perms = ROLE_PERMISSIONS.get(self.role, set())
            self._effective_permissions = role_perms | self.custom_permissions
        return self._effective_permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.effective_permissions

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.effective_permissions for perm in permissions)

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(perm in self.effective_permissions for perm in permissions)

    def add_permission(self, permission: Permission) -> None:
        """Add a custom permission to the user."""
        self.custom_permissions.add(permission)
        self._effective_permissions = None  # Reset cache

    def remove_permission(self, permission: Permission) -> None:
        """Remove a custom permission from the user."""
        self.custom_permissions.discard(permission)
        self._effective_permissions = None  # Reset cache

    def set_role(self, role: Role) -> None:
        """Set user role."""
        self.role = role
        self._effective_permissions = None  # Reset cache

    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "real_name": self.real_name,
            "email": self.email,
            "role": self.role.value,
            "custom_permissions": [perm.value for perm in self.custom_permissions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> "SlackUser":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            real_name=data.get("real_name"),
            email=data.get("email"),
            role=Role(data.get("role", Role.VIEWER.value)),
            custom_permissions={
                Permission(perm) for perm in data.get("custom_permissions", [])
            },
        )


class SlackPermissionManager:
    """Manages user permissions and authorization for Slack integration."""

    def __init__(self, settings: SlackSettings):
        self.settings = settings
        self._users: dict[str, SlackUser] = {}
        self._user_cache_ttl = 300  # 5 minutes
        self._user_cache_timestamp = 0
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the permission manager."""
        if self._initialized:
            return

        logger.info("Initializing Slack permission manager")

        # Load initial users from settings if configured
        if self.settings.allowed_users:
            for user_id in self.settings.allowed_users:
                await self._load_or_create_user(user_id)

        self._initialized = True
        logger.info("Slack permission manager initialized")

    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        user = await self.get_user(user_id)
        if not user:
            logger.warning("Permission check for unknown user", user_id=user_id)
            return False

        has_perm = user.has_permission(permission)

        if not has_perm:
            logger.info(
                "Permission denied",
                user_id=user_id,
                username=user.username,
                permission=permission.value,
            )

        return has_perm

    async def check_channel_access(self, user_id: str, channel_id: str) -> bool:
        """Check if a user has access to a specific channel."""
        try:
            slack_manager = await get_slack_manager()
            app = slack_manager.get_app()

            # Check if user is member of the channel
            response = await app.client.conversations_members(channel=channel_id)

            if response["ok"]:
                return user_id in response["members"]

            return False
        except SlackApiError as e:
            if e.response["error"] == "channel_not_found":
                logger.warning("Channel not found", channel_id=channel_id)
                return False
            logger.error(
                "Failed to check channel access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "Error checking channel access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e),
            )
            return False

    async def get_user(self, user_id: str) -> Optional[SlackUser]:
        """Get user information."""
        if user_id in self._users:
            return self._users[user_id]

        # Try to load user from Slack API
        return await self._load_or_create_user(user_id)

    async def add_user(
        self,
        user_id: str,
        role: Role = Role.VIEWER,
        custom_permissions: Optional[set[Permission]] = None,
    ) -> SlackUser:
        """Add a new user with specified role and permissions."""
        user = await self._load_or_create_user(user_id)
        if user:
            user.set_role(role)
            if custom_permissions:
                user.custom_permissions = custom_permissions

            logger.info(
                "User added/updated",
                user_id=user_id,
                username=user.username,
                role=role.value,
            )

        return user

    async def remove_user(self, user_id: str) -> bool:
        """Remove a user from the system."""
        if user_id in self._users:
            user = self._users[user_id]
            del self._users[user_id]

            logger.info("User removed", user_id=user_id, username=user.username)
            return True

        return False

    async def update_user_role(self, user_id: str, role: Role) -> bool:
        """Update user role."""
        user = await self.get_user(user_id)
        if user:
            old_role = user.role
            user.set_role(role)

            logger.info(
                "User role updated",
                user_id=user_id,
                username=user.username,
                old_role=old_role.value,
                new_role=role.value,
            )
            return True

        return False

    async def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant a custom permission to a user."""
        user = await self.get_user(user_id)
        if user:
            user.add_permission(permission)

            logger.info(
                "Permission granted",
                user_id=user_id,
                username=user.username,
                permission=permission.value,
            )
            return True

        return False

    async def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke a custom permission from a user."""
        user = await self.get_user(user_id)
        if user:
            user.remove_permission(permission)

            logger.info(
                "Permission revoked",
                user_id=user_id,
                username=user.username,
                permission=permission.value,
            )
            return True

        return False

    async def list_users(self) -> list[SlackUser]:
        """List all users in the system."""
        return list(self._users.values())

    async def get_users_with_permission(
        self, permission: Permission
    ) -> list[SlackUser]:
        """Get all users with a specific permission."""
        return [
            user for user in self._users.values() if user.has_permission(permission)
        ]

    async def get_admins(self) -> list[SlackUser]:
        """Get all admin users."""
        return [
            user
            for user in self._users.values()
            if user.role in [Role.ADMIN, Role.SUPER_ADMIN]
        ]

    async def _load_or_create_user(self, user_id: str) -> Optional[SlackUser]:
        """Load user from Slack API or create a basic user record."""
        try:
            slack_manager = await get_slack_manager()
            app = slack_manager.get_app()

            # Get user info from Slack
            response = await app.client.users_info(user=user_id)

            if response["ok"]:
                user_data = response["user"]

                # Determine default role based on allowed users list
                default_role = (
                    Role.OPERATOR
                    if user_id in self.settings.allowed_users
                    else Role.VIEWER
                )

                user = SlackUser(
                    user_id=user_id,
                    username=user_data.get("name", "unknown"),
                    real_name=user_data.get("real_name"),
                    email=user_data.get("profile", {}).get("email"),
                    role=default_role,
                )

                self._users[user_id] = user

                logger.debug(
                    "User loaded from Slack", user_id=user_id, username=user.username
                )

                return user
            else:
                logger.warning(
                    "Failed to load user from Slack",
                    user_id=user_id,
                    error=response.get("error"),
                )

        except Exception as e:
            logger.error("Error loading user from Slack", user_id=user_id, error=str(e))

        # Create minimal user record if Slack API fails
        user = SlackUser(user_id=user_id, username=f"user_{user_id}", role=Role.VIEWER)

        self._users[user_id] = user
        return user

    def is_user_allowed(self, user_id: str) -> bool:
        """Check if user is in the allowed users list."""
        if not self.settings.allowed_users:
            return True  # If no restrictions, allow all users

        return user_id in self.settings.allowed_users


# Global permission manager instance
_permission_manager: Optional[SlackPermissionManager] = None


async def get_permission_manager(
    settings: Optional[SlackSettings] = None,
) -> SlackPermissionManager:
    """Get or create the global permission manager."""
    global _permission_manager

    if _permission_manager is None:
        if settings is None:
            from ...config import get_settings

            app_settings = get_settings()
            settings = app_settings.slack

        _permission_manager = SlackPermissionManager(settings)
        await _permission_manager.initialize()

    return _permission_manager


async def check_user_permission(user_id: str, permission: Permission) -> bool:
    """Convenience function to check user permission."""
    manager = await get_permission_manager()
    return await manager.check_permission(user_id, permission)


async def require_permission(user_id: str, permission: Permission) -> None:
    """Raise exception if user doesn't have permission."""
    if not await check_user_permission(user_id, permission):
        user = await (await get_permission_manager()).get_user(user_id)
        username = user.username if user else user_id
        raise PermissionError(
            f"User {username} lacks required permission: {permission.value}"
        )


def permission_required(permission: Permission):
    """Decorator to require specific permission for function execution."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from function arguments or kwargs
            user_id = kwargs.get("user_id") or (args[0] if args else None)
            if not user_id:
                raise ValueError("user_id required for permission check")

            await require_permission(user_id, permission)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Compatibility aliases
PermissionManager = SlackPermissionManager
