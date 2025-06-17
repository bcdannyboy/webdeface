"""Dependency registry to resolve circular imports at runtime."""

from typing import Any, Callable, Dict, Optional, TypeVar

from .interfaces import (
    HealthMonitorInterface,
    NotificationDeliveryProtocol,
    SchedulingOrchestratorInterface,
)

T = TypeVar('T')


class DependencyRegistry:
    """Registry for managing dependencies and avoiding circular imports."""
    
    def __init__(self):
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._instances: Dict[str, Any] = {}
    
    def register_factory(self, key: str, factory: Callable[[], Any]) -> None:
        """Register a factory function for a dependency."""
        self._factories[key] = factory
    
    def register_instance(self, key: str, instance: Any) -> None:
        """Register a singleton instance."""
        self._instances[key] = instance
    
    async def get(self, key: str) -> Any:
        """Get an instance, creating it if necessary."""
        # Return cached instance if available
        if key in self._instances:
            return self._instances[key]
        
        # Create instance using factory
        if key in self._factories:
            instance = await self._factories[key]()
            self._instances[key] = instance
            return instance
        
        raise KeyError(f"No factory or instance registered for key: {key}")
    
    def get_sync(self, key: str) -> Any:
        """Get a synchronously available instance."""
        if key in self._instances:
            return self._instances[key]
        raise KeyError(f"No instance available for key: {key}")
    
    def clear(self, key: Optional[str] = None) -> None:
        """Clear cached instances."""
        if key:
            self._instances.pop(key, None)
        else:
            self._instances.clear()


# Global registry instance
_dependency_registry = DependencyRegistry()


def get_dependency_registry() -> DependencyRegistry:
    """Get the global dependency registry."""
    return _dependency_registry


# Convenience functions for specific dependencies
async def get_notification_delivery() -> NotificationDeliveryProtocol:
    """Get notification delivery instance via registry."""
    return await _dependency_registry.get("notification_delivery")


async def get_health_monitor() -> HealthMonitorInterface:
    """Get health monitor instance via registry."""
    return await _dependency_registry.get("health_monitor")


async def get_scheduling_orchestrator() -> SchedulingOrchestratorInterface:
    """Get scheduling orchestrator instance via registry."""
    return await _dependency_registry.get("scheduling_orchestrator")


def setup_scheduler_dependencies():
    """Setup scheduler dependency factories."""
    # These will be registered by the actual implementations
    # This function serves as a placeholder for dependency setup
    pass