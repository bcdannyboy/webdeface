"""Type definitions for utility modules."""

from typing import Any, Protocol, TypeVar


class UtilityError(Exception):
    """Base exception for utility-related errors."""

    pass


class AsyncTimeoutError(UtilityError):
    """Exception raised when async operations timeout."""

    pass


T = TypeVar("T")


class LoggerProtocol(Protocol):
    """Protocol for logger objects."""

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        ...


class AsyncCallable(Protocol[T]):
    """Protocol for async callable objects."""

    async def __call__(self, *args: Any, **kwargs: Any) -> T:
        """Call the async function."""
        ...


class HealthCheck(Protocol):
    """Protocol for health check implementations."""

    async def check(self) -> bool:
        """Perform health check and return status."""
        ...

    @property
    def name(self) -> str:
        """Name of the health check."""
        ...
