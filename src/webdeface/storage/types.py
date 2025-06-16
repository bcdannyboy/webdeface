"""Type definitions for storage components."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class SiteStatus(str, Enum):
    """Status of a monitored site."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class SiteRecord:
    """Record for a monitored site."""

    id: Optional[int]
    url: str
    name: Optional[str]
    interval: str  # Cron expression
    max_depth: int
    status: SiteStatus
    last_scan: Optional[datetime] = None
    last_change: Optional[datetime] = None
    error_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ScanRecord:
    """Record for a site scan."""

    id: Optional[int]
    site_id: int
    status: str  # 'success', 'failed', 'no_change'
    pages_scanned: int
    changes_detected: int
    structure_hash: str
    chunk_hashes: list[str]
    classification_label: Optional[str] = None
    classification_explanation: Optional[str] = None
    error_message: Optional[str] = None
    scan_duration: Optional[float] = None
    scanned_at: Optional[datetime] = None
