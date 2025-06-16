"""Type definitions for configuration system."""

from typing import Any, Optional, Protocol


class ConfigError(Exception):
    """Base exception for configuration-related errors."""

    pass


class ConfigValidationError(ConfigError):
    """Exception raised when configuration validation fails."""

    pass


class ConfigLoadError(ConfigError):
    """Exception raised when configuration loading fails."""

    pass


class ConfigSource(Protocol):
    """Protocol for configuration sources."""

    def load(self) -> dict[str, Any]:
        """Load configuration data."""
        ...

    def save(self, data: dict[str, Any]) -> None:
        """Save configuration data."""
        ...

    @property
    def source_name(self) -> str:
        """Name of the configuration source."""
        ...


class AlertTarget:
    """Configuration for alert targets."""

    def __init__(
        self, channels: Optional[list[str]] = None, users: Optional[list[str]] = None
    ):
        self.channels = channels or []
        self.users = users or []

    def __bool__(self) -> bool:
        """Return True if there are any targets configured."""
        return bool(self.channels or self.users)

    def __repr__(self) -> str:
        return f"AlertTarget(channels={self.channels}, users={self.users})"


class GlobalAlertSettings:
    """Global alert configuration."""

    def __init__(
        self,
        site_down: Optional[AlertTarget] = None,
        benign_change: Optional[AlertTarget] = None,
        defacement: Optional[AlertTarget] = None,
    ):
        self.site_down = site_down or AlertTarget()
        self.benign_change = benign_change or AlertTarget()
        self.defacement = defacement or AlertTarget()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlobalAlertSettings":
        """Create from dictionary configuration."""

        def parse_target(target_data):
            if isinstance(target_data, list):
                # Legacy format: just a list of channels
                channels = [t for t in target_data if t.startswith("#")]
                users = [t for t in target_data if t.startswith("@")]
                return AlertTarget(channels=channels, users=users)
            elif isinstance(target_data, dict):
                return AlertTarget(
                    channels=target_data.get("channels", []),
                    users=target_data.get("users", []),
                )
            else:
                return AlertTarget()

        return cls(
            site_down=parse_target(data.get("site_down", [])),
            benign_change=parse_target(data.get("benign_change", [])),
            defacement=parse_target(data.get("defacement", [])),
        )


class SiteConfiguration:
    """Configuration for a monitored site."""

    def __init__(
        self,
        url: str,
        interval: str = "*/15 * * * *",
        depth: int = 2,
        enabled: bool = True,
        name: Optional[str] = None,
    ):
        self.url = url
        self.interval = interval
        self.depth = depth
        self.enabled = enabled
        self.name = name or url

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteConfiguration":
        """Create from dictionary configuration."""
        return cls(
            url=data["url"],
            interval=data.get("interval", "*/15 * * * *"),
            depth=data.get("depth", 2),
            enabled=data.get("enabled", True),
            name=data.get("name"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "interval": self.interval,
            "depth": self.depth,
            "enabled": self.enabled,
            "name": self.name,
        }


class GlobalConfiguration:
    """Global application configuration."""

    def __init__(
        self,
        default_interval: str = "*/15 * * * *",
        keep_scans: int = 20,
        alert: Optional[GlobalAlertSettings] = None,
    ):
        self.default_interval = default_interval
        self.keep_scans = keep_scans
        self.alert = alert or GlobalAlertSettings()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlobalConfiguration":
        """Create from dictionary configuration."""
        return cls(
            default_interval=data.get("default_interval", "*/15 * * * *"),
            keep_scans=data.get("keep_scans", 20),
            alert=GlobalAlertSettings.from_dict(data.get("alert", {})),
        )
