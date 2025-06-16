"""FastAPI dependency providers for API components."""

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    from ..scheduler.orchestrator import SchedulingOrchestrator
    from ..storage.interface import StorageManager


async def get_storage_manager(request: Request) -> "StorageManager":
    """Dependency to get storage manager from app state."""
    if not hasattr(request.app.state, "storage") or request.app.state.storage is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )
    return request.app.state.storage


async def get_orchestrator(request: Request) -> "SchedulingOrchestrator":
    """Dependency to get scheduling orchestrator from app state."""
    if (
        not hasattr(request.app.state, "orchestrator")
        or request.app.state.orchestrator is None
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Orchestrator not initialized",
        )
    return request.app.state.orchestrator


async def get_settings(request: Request):
    """Dependency to get settings from app state."""
    if not hasattr(request.app.state, "settings") or request.app.state.settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Settings not initialized",
        )
    return request.app.state.settings
