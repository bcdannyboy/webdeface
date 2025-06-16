"""Test fixtures and utilities for Slack command tests."""

from datetime import datetime
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from slack_bolt.async_app import AsyncApp, AsyncRespond

from src.webdeface.cli.types import CLIContext, CommandResult
from src.webdeface.notification.slack.handlers.monitoring import MonitoringHandler
from src.webdeface.notification.slack.handlers.router import SlackCommandRouter
from src.webdeface.notification.slack.handlers.system import SystemHandler
from src.webdeface.notification.slack.handlers.website import WebsiteHandler
from src.webdeface.notification.slack.permissions import (
    Permission,
    Role,
    SlackPermissionManager,
    SlackUser,
)
from src.webdeface.notification.slack.utils.formatters import SlackResponseFormatter
from src.webdeface.notification.slack.utils.parsers import SlackCommandParser
from src.webdeface.notification.slack.utils.validators import CommandValidator


@pytest.fixture
def mock_app():
    """Create a mock Slack Bolt app."""
    app = MagicMock(spec=AsyncApp)
    app.client = MagicMock()
    return app


@pytest.fixture
def mock_respond():
    """Create a mock Slack respond function."""
    respond = AsyncMock(spec=AsyncRespond)
    return respond


@pytest.fixture
def slack_user_viewer():
    """Create a test Slack user with viewer role."""
    return SlackUser(
        user_id="U123456",
        username="test_viewer",
        real_name="Test Viewer",
        email="viewer@example.com",
        role=Role.VIEWER,
    )


@pytest.fixture
def slack_user_operator():
    """Create a test Slack user with operator role."""
    return SlackUser(
        user_id="U234567",
        username="test_operator",
        real_name="Test Operator",
        email="operator@example.com",
        role=Role.OPERATOR,
    )


@pytest.fixture
def slack_user_admin():
    """Create a test Slack user with admin role."""
    return SlackUser(
        user_id="U345678",
        username="test_admin",
        real_name="Test Admin",
        email="admin@example.com",
        role=Role.ADMIN,
    )


@pytest.fixture
def mock_permission_manager(slack_user_viewer, slack_user_operator, slack_user_admin):
    """Create a mock permission manager with test users."""
    manager = MagicMock(spec=SlackPermissionManager)

    # Mock users database
    users = {
        slack_user_viewer.user_id: slack_user_viewer,
        slack_user_operator.user_id: slack_user_operator,
        slack_user_admin.user_id: slack_user_admin,
    }

    async def mock_check_permission(user_id: str, permission: Permission) -> bool:
        user = users.get(user_id)
        return user.has_permission(permission) if user else False

    async def mock_get_user(user_id: str) -> Optional[SlackUser]:
        return users.get(user_id)

    manager.check_permission = mock_check_permission
    manager.get_user = mock_get_user

    return manager


@pytest.fixture
def mock_storage():
    """Create a mock storage manager."""
    storage = MagicMock()

    # Mock website data
    mock_website = MagicMock()
    mock_website.id = "website123"
    mock_website.name = "Test Website"
    mock_website.url = "https://example.com"
    mock_website.is_active = True
    mock_website.created_at = datetime.utcnow()
    mock_website.last_checked_at = datetime.utcnow()
    mock_website.check_interval_seconds = 900

    storage.get_website.return_value = mock_website
    storage.get_website_by_url.return_value = None
    storage.create_website.return_value = mock_website
    storage.list_websites.return_value = [mock_website]
    storage.update_website.return_value = True
    storage.delete_website.return_value = True
    storage.health_check.return_value = True
    storage.get_website_snapshots.return_value = []
    storage.get_website_alerts.return_value = []
    storage.get_open_alerts.return_value = []

    return storage


@pytest.fixture
def mock_orchestrator():
    """Create a mock scheduling orchestrator."""
    orchestrator = MagicMock()

    orchestrator.schedule_website_monitoring.return_value = "exec123"
    orchestrator.unschedule_website_monitoring.return_value = True
    orchestrator.pause_website_monitoring.return_value = True
    orchestrator.resume_website_monitoring.return_value = True
    orchestrator.trigger_immediate_check.return_value = "exec456"
    orchestrator.get_status.return_value = {
        "status": "running",
        "active_jobs": 5,
        "pending_jobs": 2,
        "uptime_seconds": 3600,
    }

    return orchestrator


@pytest.fixture
def command_parser():
    """Create a command parser instance."""
    return SlackCommandParser()


@pytest.fixture
def command_validator():
    """Create a command validator instance."""
    return CommandValidator()


@pytest.fixture
def response_formatter():
    """Create a response formatter instance."""
    return SlackResponseFormatter()


@pytest.fixture
def website_handler():
    """Create a website handler instance."""
    return WebsiteHandler()


@pytest.fixture
def monitoring_handler():
    """Create a monitoring handler instance."""
    return MonitoringHandler()


@pytest.fixture
def system_handler():
    """Create a system handler instance."""
    return SystemHandler()


@pytest.fixture
def command_router():
    """Create a command router instance."""
    return SlackCommandRouter()


@pytest.fixture
def cli_context():
    """Create a CLI context for testing."""
    return CLIContext(verbose=False, debug=False)


@pytest.fixture
def successful_command_result():
    """Create a successful command result."""
    return CommandResult(
        success=True,
        message="Command executed successfully",
        data={"result": "success"},
        exit_code=0,
    )


@pytest.fixture
def failed_command_result():
    """Create a failed command result."""
    return CommandResult(success=False, message="Command failed", data={}, exit_code=1)


class MockSlackResponse:
    """Helper class to capture Slack responses for testing."""

    def __init__(self):
        self.responses = []

    async def __call__(self, response: dict[str, Any]):
        self.responses.append(response)

    @property
    def last_response(self) -> Optional[dict[str, Any]]:
        return self.responses[-1] if self.responses else None

    def clear(self):
        self.responses.clear()


@pytest.fixture
def mock_slack_response():
    """Create a mock Slack response handler."""
    return MockSlackResponse()


@pytest.fixture
def patch_get_storage_manager(mock_storage):
    """Patch the get_storage_manager function."""
    with patch(
        "src.webdeface.notification.slack.handlers.website.get_storage_manager",
        return_value=mock_storage,
    ), patch(
        "src.webdeface.notification.slack.handlers.monitoring.get_storage_manager",
        return_value=mock_storage,
    ), patch(
        "src.webdeface.notification.slack.handlers.system.get_storage_manager",
        return_value=mock_storage,
    ):
        yield mock_storage


@pytest.fixture
def patch_get_scheduling_orchestrator(mock_orchestrator):
    """Patch the get_scheduling_orchestrator function."""
    with patch(
        "src.webdeface.notification.slack.handlers.website.get_scheduling_orchestrator",
        return_value=mock_orchestrator,
    ), patch(
        "src.webdeface.notification.slack.handlers.monitoring.get_scheduling_orchestrator",
        return_value=mock_orchestrator,
    ), patch(
        "src.webdeface.notification.slack.handlers.system.get_scheduling_orchestrator",
        return_value=mock_orchestrator,
    ):
        yield mock_orchestrator


@pytest.fixture
def patch_get_permission_manager(mock_permission_manager):
    """Patch the get_permission_manager function."""
    with patch(
        "src.webdeface.notification.slack.handlers.base.get_permission_manager",
        return_value=mock_permission_manager,
    ):
        yield mock_permission_manager


# Test data fixtures
@pytest.fixture
def sample_website_data():
    """Sample website data for testing."""
    return {
        "url": "https://example.com",
        "name": "Test Website",
        "check_interval_seconds": 900,
        "is_active": True,
    }


@pytest.fixture
def sample_parse_results():
    """Sample parse results for different commands."""
    return {
        "website_add": {
            "success": True,
            "subcommands": ["website", "add"],
            "args": {0: "https://example.com"},
            "flags": {"name": "Test Site", "interval": 600},
            "global_flags": {},
        },
        "website_list": {
            "success": True,
            "subcommands": ["website", "list"],
            "args": {},
            "flags": {"status": "active", "format": "table"},
            "global_flags": {},
        },
        "monitoring_start": {
            "success": True,
            "subcommands": ["monitoring", "start"],
            "args": {0: "website123"},
            "flags": {},
            "global_flags": {},
        },
        "system_status": {
            "success": True,
            "subcommands": ["system", "status"],
            "args": {},
            "flags": {},
            "global_flags": {},
        },
    }


# Helper functions for tests
def assert_slack_response_format(response: dict[str, Any]):
    """Assert that a response follows Slack message format."""
    assert "text" in response
    assert "response_type" in response
    assert response["response_type"] in ["ephemeral", "in_channel"]


def assert_error_response(response: dict[str, Any], error_text: str = None):
    """Assert that a response is an error response."""
    assert_slack_response_format(response)
    assert response["response_type"] == "ephemeral"
    assert "❌" in response["text"] or "🔒" in response["text"] or "💥" in response["text"]
    if error_text:
        assert error_text in response["text"]


def assert_success_response(response: dict[str, Any], success_text: str = None):
    """Assert that a response is a success response."""
    assert_slack_response_format(response)
    if success_text:
        assert success_text in response["text"]


def create_mock_validation_result(
    is_valid: bool, error_message: str = None, suggestions: list = None
):
    """Create a mock validation result."""
    result = MagicMock()
    result.is_valid = is_valid
    result.error_message = error_message
    result.suggestions = suggestions or []
    return result


def create_mock_parse_result(
    success: bool,
    subcommands: list = None,
    args: dict = None,
    flags: dict = None,
    global_flags: dict = None,
    error_message: str = None,
):
    """Create a mock parse result."""
    result = MagicMock()
    result.success = success
    result.subcommands = subcommands or []
    result.args = args or {}
    result.flags = flags or {}
    result.global_flags = global_flags or {}
    result.error_message = error_message
    return result
