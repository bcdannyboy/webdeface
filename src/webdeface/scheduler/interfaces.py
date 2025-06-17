"""Shared interfaces for scheduler components to avoid circular imports."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol

from .types import MonitoringReport


class NotificationDeliveryProtocol(Protocol):
    """Protocol for notification delivery to avoid circular imports."""
    
    async def send_health_alert(self, message: str, **kwargs: Any) -> bool:
        """Send a health alert notification."""
        ...

    async def send_system_status(self, status: dict[str, Any], **kwargs: Any) -> bool:
        """Send system status notification."""
        ...


class HealthMonitorInterface(ABC):
    """Abstract interface for health monitoring to avoid circular imports."""

    @abstractmethod
    async def generate_monitoring_report(self) -> MonitoringReport:
        """Generate a comprehensive monitoring report."""
        ...

    @abstractmethod
    def get_latest_report(self) -> Optional[MonitoringReport]:
        """Get the latest monitoring report."""
        ...

    @abstractmethod
    async def setup(self) -> None:
        """Initialize the health monitor."""
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up the health monitor."""
        ...


class SchedulingOrchestratorInterface(ABC):
    """Abstract interface for scheduling orchestrator to avoid circular imports."""

    @abstractmethod
    async def schedule_website_monitoring(
        self, 
        website_id: str, 
        interval: Optional[str] = None, 
        priority: Any = None
    ) -> str:
        """Schedule monitoring for a specific website."""
        ...

    @abstractmethod
    async def unschedule_website_monitoring(self, website_id: str) -> bool:
        """Remove monitoring for a specific website."""
        ...

    @abstractmethod
    async def pause_website_monitoring(self, website_id: str, duration: int) -> None:
        """Pause monitoring for a website for specified duration."""
        ...

    @abstractmethod
    async def resume_website_monitoring(self, website_id: str) -> None:
        """Resume monitoring for a website."""
        ...

    @abstractmethod
    async def trigger_immediate_check(self, website_id: str) -> str:
        """Trigger immediate check for a website."""
        ...

    @abstractmethod
    async def get_orchestrator_status(self) -> dict[str, Any]:
        """Get comprehensive orchestrator status."""
        ...