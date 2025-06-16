"""API routers for different endpoint groups."""

from .alerts import router as alerts_router
from .auth import router as auth_router
from .metrics import router as metrics_router
from .monitoring import router as monitoring_router
from .system import router as system_router
from .websites import router as websites_router

__all__ = [
    "auth_router",
    "websites_router",
    "monitoring_router",
    "system_router",
    "alerts_router",
    "metrics_router",
]
