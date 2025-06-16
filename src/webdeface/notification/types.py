"""Type definitions for the notification module."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from ..classifier.types import Classification


class NotificationError(Exception):
    """Base exception for notification-related errors."""

    pass


class AlertType(str, Enum):
    """Types of alerts that can be sent."""

    SITE_DOWN = "site_down"
    BENIGN_CHANGE = "benign_change"
    DEFACEMENT = "defacement"
    SYSTEM_ERROR = "system_error"


@dataclass
class AlertContext:
    """Context information for alerts."""

    site_id: int
    site_url: str
    site_name: Optional[str] = None
    scan_id: Optional[int] = None
    error_message: Optional[str] = None
    additional_data: Optional[dict[str, Any]] = None


@dataclass
class MessageResult:
    """Result of sending a message."""

    success: bool
    message_id: Optional[str] = None
    channel: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

    def __post_init__(self):
        if self.sent_at is None:
            self.sent_at = datetime.utcnow()


@dataclass
class SlackMessage:
    """Slack message structure."""

    text: str
    blocks: Optional[list[dict[str, Any]]] = None
    attachments: Optional[list[dict[str, Any]]] = None
    channel: Optional[str] = None
    thread_ts: Optional[str] = None


@dataclass
class DefacementAlert:
    """Alert data for defacement detection."""

    site_url: str
    classification: Classification
    explanation: str
    confidence: Optional[float] = None
    changed_content: list[str] = None
    scan_id: Optional[int] = None
    detected_at: Optional[datetime] = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
        if self.changed_content is None:
            self.changed_content = []


@dataclass
class SiteDownAlert:
    """Alert data for site down detection."""

    site_url: str
    error_message: str
    retry_count: int = 0
    last_successful_scan: Optional[datetime] = None
    detected_at: Optional[datetime] = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()


# Type alias for alert targets
AlertTarget = list[str]  # List of channels (#channel) or users (@user)
