"""Middleware components for the API."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        cutoff_time = current_time - self.period
        self.clients = {
            ip: times
            for ip, times in self.clients.items()
            if any(t > cutoff_time for t in times)
        }

        # Get client request times
        client_times = self.clients.get(client_ip, [])
        client_times = [t for t in client_times if t > cutoff_time]

        # Check rate limit
        if len(client_times) >= self.calls:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(self.period)},
            )

        # Record this request
        client_times.append(current_time)
        self.clients[client_ip] = client_times

        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers[
            "Strict-Transport-Security"
        ] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


def setup_middleware(app, settings) -> None:
    """Setup middleware for the FastAPI application."""

    # Add rate limiting middleware
    if not settings.development:
        app.add_middleware(RateLimitMiddleware, calls=100, period=60)

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("API middleware configured")
