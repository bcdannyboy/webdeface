"""FastAPI application with async endpoints."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..scheduler.orchestrator import (
    cleanup_scheduling_orchestrator,
    get_scheduling_orchestrator,
)
from ..storage import get_storage_manager
from ..utils.logging import get_structured_logger
from .auth import setup_auth
from .middleware import setup_middleware
from .routers import (
    alerts_router,
    auth_router,
    metrics_router,
    monitoring_router,
    system_router,
    websites_router,
)
from .types import APIError, ErrorResponse

logger = get_structured_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    logger.info("Starting WebDeface API application")

    try:
        # Initialize core components
        settings = get_settings()

        # Initialize storage
        storage = await get_storage_manager()
        app.state.storage = storage

        # Initialize orchestrator
        orchestrator = await get_scheduling_orchestrator()
        app.state.orchestrator = orchestrator

        # Store settings
        app.state.settings = settings

        logger.info("WebDeface API application started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    finally:
        logger.info("Shutting down WebDeface API application")

        try:
            # Cleanup orchestrator
            await cleanup_scheduling_orchestrator()

            # Cleanup storage
            if hasattr(app.state, "storage"):
                await app.state.storage.cleanup()

        except Exception as e:
            logger.error(f"Error during application shutdown: {str(e)}")

        logger.info("WebDeface API application shutdown complete")


def get_storage_from_state(request) -> "StorageManager":
    """Dependency to get storage manager from app state."""
    if not hasattr(request.app.state, "storage") or request.app.state.storage is None:
        raise RuntimeError("Database not initialized")
    return request.app.state.storage


def get_orchestrator_from_state(request) -> "SchedulingOrchestrator":
    """Dependency to get orchestrator from app state."""
    if (
        not hasattr(request.app.state, "orchestrator")
        or request.app.state.orchestrator is None
    ):
        raise RuntimeError("Orchestrator not initialized")
    return request.app.state.orchestrator


def create_app(settings=None) -> FastAPI:
    """Create and configure FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="WebDeface Monitor API",
        description="REST API for Web Defacement Detection and Monitoring",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Setup middleware
    setup_middleware(app, settings)

    # Setup authentication
    setup_auth(app, settings)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Setup routers
    setup_routers(app)

    logger.info("FastAPI application created and configured")
    return app


def setup_middleware(app: FastAPI, settings) -> None:
    """Setup middleware for the FastAPI application."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware for production
    if not settings.development:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "localhost",
                "127.0.0.1",
                "*.example.com",
            ],  # Configure for production
        )

    # Request/Response logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = asyncio.get_event_loop().time()

        try:
            response = await call_next(request)

            process_time = asyncio.get_event_loop().time() - start_time

            logger.info(
                "HTTP request",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time,
                client_ip=request.client.host if request.client else None,
            )

            return response

        except Exception as e:
            process_time = asyncio.get_event_loop().time() - start_time

            logger.error(
                "HTTP request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=process_time,
                client_ip=request.client.host if request.client else None,
            )

            raise


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with standardized error format."""
        # Fix for authentication: Map 403 "Not authenticated" to 401
        status_code = exc.status_code
        if exc.status_code == 403 and exc.detail == "Not authenticated":
            status_code = 401

        # Standardize error response format to have 'error' key at top level
        content = {"error": exc.detail}

        logger.warning(
            "HTTP exception",
            status_code=status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle API-specific errors."""
        error_response = ErrorResponse(
            error="API_ERROR", message=str(exc), details={"type": type(exc).__name__}
        )

        logger.warning(
            "API error", error=str(exc), path=request.url.path, method=request.method
        )

        return JSONResponse(status_code=400, content=error_response.dict())

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors."""
        error_response = ErrorResponse(
            error="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details={"type": type(exc).__name__},
        )

        logger.error(
            "Unexpected error",
            error=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        return JSONResponse(status_code=500, content=error_response.dict())


def setup_routers(app: FastAPI) -> None:
    """Setup API routers."""

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "0.1.0",
        }

    # API v1 routes
    api_prefix = "/api/v1"

    app.include_router(
        auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"]
    )

    app.include_router(
        websites_router, prefix=f"{api_prefix}/websites", tags=["Website Management"]
    )

    app.include_router(
        monitoring_router,
        prefix=f"{api_prefix}/monitoring",
        tags=["Monitoring Control"],
    )

    app.include_router(
        system_router, prefix=f"{api_prefix}/system", tags=["System Status"]
    )

    app.include_router(
        alerts_router, prefix=f"{api_prefix}/alerts", tags=["Alert Management"]
    )

    app.include_router(
        metrics_router, prefix=f"{api_prefix}/metrics", tags=["Metrics & Analytics"]
    )


def main() -> None:
    """Run the FastAPI application."""
    settings = get_settings()

    # Configure uvicorn based on environment
    config = {
        "app": "src.webdeface.api.app:create_app",
        "factory": True,
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.development,
        "log_level": settings.logging.level.lower(),
        "access_log": True,
    }

    logger.info("Starting WebDeface API server...")
    logger.info(f"Server will be available at http://{config['host']}:{config['port']}")
    logger.info(f"API documentation at http://{config['host']}:{config['port']}/docs")

    uvicorn.run(**config)


if __name__ == "__main__":
    main()
