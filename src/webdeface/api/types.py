"""Type definitions for the API module."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class APIError(Exception):
    """Base exception for API-related errors."""

    pass


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""

    status: HealthStatus
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: dict[str, bool] = {}
    message: Optional[str] = None


class SiteResponse(BaseModel):
    """Response model for site information."""

    id: int
    url: str
    name: Optional[str]
    status: str
    interval: str
    max_depth: int
    last_scan: Optional[datetime]
    last_change: Optional[datetime]
    error_count: int
    created_at: datetime
    updated_at: datetime


class ScanResponse(BaseModel):
    """Response model for scan information."""

    id: int
    site_id: int
    status: str
    pages_scanned: int
    changes_detected: int
    classification_label: Optional[str]
    classification_explanation: Optional[str]
    error_message: Optional[str]
    scan_duration: Optional[float]
    scanned_at: datetime


class MetricsResponse(BaseModel):
    """Response model for metrics."""

    total_sites: int
    active_sites: int
    total_scans_today: int
    defacements_detected_today: int
    average_scan_duration: float
    last_scan_time: Optional[datetime]


class CreateSiteRequest(BaseModel):
    """Request model for creating a new site."""

    url: str
    name: Optional[str] = None
    interval: str = "*/15 * * * *"
    max_depth: int = 2


class UpdateSiteRequest(BaseModel):
    """Request model for updating a site."""

    name: Optional[str] = None
    interval: Optional[str] = None
    max_depth: Optional[int] = None
    status: Optional[str] = None


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get("timestamp") is None:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)
