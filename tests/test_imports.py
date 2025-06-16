"""Test basic package imports to validate structure."""

import pytest


def test_main_package_imports():
    """Test that main package components can be imported."""
    from src.webdeface import __version__, get_settings, main

    assert __version__ == "0.1.0"
    assert callable(main)
    assert callable(get_settings)


def test_config_imports():
    """Test configuration module imports."""
    from src.webdeface.config import (
        AppSettings,
        ConfigError,
        ConfigLoader,
        get_settings,
    )

    assert AppSettings is not None
    assert callable(get_settings)
    assert ConfigLoader is not None
    assert issubclass(ConfigError, Exception)


def test_utils_imports():
    """Test utility module imports."""
    from src.webdeface.utils import (
        UtilityError,
        get_logger,
        run_with_timeout,
        setup_logging,
    )

    assert callable(setup_logging)
    assert callable(get_logger)
    assert callable(run_with_timeout)
    assert issubclass(UtilityError, Exception)


def test_scraper_imports():
    """Test scraper module imports."""
    from src.webdeface.scraper import CrawlResult, PageResult, ScrapingError

    assert PageResult is not None
    assert CrawlResult is not None
    assert issubclass(ScrapingError, Exception)


def test_classifier_imports():
    """Test classifier module imports."""
    from src.webdeface.classifier import (
        Classification,
        ClassificationError,
        ClassificationResult,
    )

    assert Classification is not None
    assert ClassificationResult is not None
    assert issubclass(ClassificationError, Exception)


def test_storage_imports():
    """Test storage module imports."""
    from src.webdeface.storage import ScanRecord, SiteRecord, StorageError

    assert issubclass(StorageError, Exception)
    assert ScanRecord is not None
    assert SiteRecord is not None


def test_scheduler_imports():
    """Test scheduler module imports."""
    from src.webdeface.scheduler import JobStatus, SchedulerError

    assert JobStatus is not None
    assert issubclass(SchedulerError, Exception)


def test_notification_imports():
    """Test notification module imports."""
    from src.webdeface.notification import AlertType, MessageResult, NotificationError

    assert issubclass(NotificationError, Exception)
    assert AlertType is not None
    assert MessageResult is not None


def test_api_imports():
    """Test API module imports."""
    from src.webdeface.api import APIError, HealthStatus

    assert issubclass(APIError, Exception)
    assert HealthStatus is not None


def test_cli_imports():
    """Test CLI module imports."""
    from src.webdeface.cli import CLIError, CommandResult

    assert issubclass(CLIError, Exception)
    assert CommandResult is not None


@pytest.mark.asyncio
async def test_async_utils():
    """Test async utility functions."""
    import asyncio

    from src.webdeface.utils.async_utils import run_with_timeout

    async def simple_task():
        await asyncio.sleep(0.1)
        return "completed"

    result = await run_with_timeout(simple_task(), timeout=1.0)
    assert result == "completed"


def test_logging_setup():
    """Test logging setup functionality."""
    from src.webdeface.utils.logging import get_logger, setup_logging

    # Setup logging
    setup_logging(log_level="INFO", json_logs=False)

    # Get a logger
    logger = get_logger(__name__)
    assert logger is not None

    # Test logging (should not raise exceptions)
    logger.info("Test message", test_key="test_value")
