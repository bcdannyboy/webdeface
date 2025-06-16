"""Structured logging setup using structlog."""

import logging
import logging.config
import sys
from typing import Any, Optional

import structlog
from structlog.types import FilteringBoundLogger


def setup_logging(
    log_level: str = "INFO", json_logs: bool = False, include_caller_info: bool = False
) -> None:
    """Configure structured logging with appropriate processors."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Build processor chain
    processors = [
        # Add contextvars (like request IDs)
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.processors.add_log_level,
        # Add logger name (safe for WriteLogger)
        _safe_add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Add caller info if requested
    if include_caller_info:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            )
        )

    # Add stack info and exception formatting
    processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.format_exc_info,
        ]
    )

    # Choose final renderer based on format preference
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=sys.stderr.isatty(),
                exception_formatter=structlog.dev.better_traceback,
            )
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _safe_add_logger_name(logger, method_name: str, event_dict):
    """Safely add logger name, handling WriteLogger and other logger types."""
    try:
        # Try to get name from logger
        if hasattr(logger, "name"):
            event_dict["logger"] = logger.name
        elif hasattr(logger, "_logger") and hasattr(logger._logger, "name"):
            event_dict["logger"] = logger._logger.name
        else:
            # Fallback for WriteLogger or other types - use the module name from event_dict or a default
            event_dict["logger"] = event_dict.get("logger", "unknown")
    except Exception:
        # Ultimate fallback
        event_dict["logger"] = "unknown"
    return event_dict


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)


def configure_component_logging(
    component_levels: Optional[dict[str, str]] = None
) -> None:
    """Configure logging levels for specific components."""
    if not component_levels:
        return

    for component, level in component_levels.items():
        logger = logging.getLogger(component)
        logger.setLevel(getattr(logging, level.upper()))


def setup_request_logging() -> None:
    """Setup request-scoped logging context."""
    import uuid

    # Generate request ID
    request_id = str(uuid.uuid4())[:8]

    # Bind to context
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_logging() -> None:
    """Clear request-scoped logging context."""
    structlog.contextvars.clear_contextvars()


class LoggingContextManager:
    """Context manager for request-scoped logging."""

    def __init__(self, **context: Any):
        self.context = context
        self.original_context: dict[str, Any] = {}

    def __enter__(self):
        # Save current context
        self.original_context = structlog.contextvars._CONTEXT.copy()

        # Bind new context
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.original_context)


def with_logging_context(**context: Any):
    """Decorator to add logging context to function calls."""

    def decorator(func):
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            # Async function
            async def async_wrapper(*args, **kwargs):
                with LoggingContextManager(**context):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:
            # Sync function
            def sync_wrapper(*args, **kwargs):
                with LoggingContextManager(**context):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


class StructuredLogger:
    """Wrapper for structured logging with convenience methods."""

    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.name = name

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with structured data."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with structured data."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with structured data."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with structured data."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with structured data."""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Create a new logger with bound context."""
        bound_logger = StructuredLogger(self.name)
        bound_logger.logger = self.logger.bind(**kwargs)
        return bound_logger


# Convenience function for getting structured loggers
def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# Pre-configured loggers for common components
def get_app_logger() -> StructuredLogger:
    """Get application logger."""
    return get_structured_logger("webdeface.app")


def get_scraper_logger() -> StructuredLogger:
    """Get scraper logger."""
    return get_structured_logger("webdeface.scraper")


def get_classifier_logger() -> StructuredLogger:
    """Get classifier logger."""
    return get_structured_logger("webdeface.classifier")


def get_storage_logger() -> StructuredLogger:
    """Get storage logger."""
    return get_structured_logger("webdeface.storage")


def get_scheduler_logger() -> StructuredLogger:
    """Get scheduler logger."""
    return get_structured_logger("webdeface.scheduler")


def get_notification_logger() -> StructuredLogger:
    """Get notification logger."""
    return get_structured_logger("webdeface.notification")
