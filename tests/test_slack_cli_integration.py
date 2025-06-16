"""Tests for Slack CLI integration functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from webdeface.cli.types import CommandResult
from webdeface.notification.slack.handlers.monitoring import MonitoringHandler
from webdeface.notification.slack.handlers.router import SlackCommandRouter
from webdeface.notification.slack.handlers.system import SystemHandler
from webdeface.notification.slack.handlers.website import WebsiteHandler
from webdeface.notification.slack.integration import SlackCLIIntegration
from webdeface.notification.slack.utils.formatters import SlackFormatter
from webdeface.notification.slack.utils.parsers import SlackCommandParser


class TestSlackCommandParser:
    """Test the Slack command parser."""

    @pytest.fixture
    def parser(self):
        return SlackCommandParser()

    @pytest.mark.asyncio
    async def test_parse_simple_command(self, parser):
        """Test parsing a simple command."""
        result = await parser.parse_command("website list")

        assert result.success
        assert result.subcommands == ["website", "list"]
        assert result.args == []
        assert result.flags == {}

    @pytest.mark.asyncio
    async def test_parse_command_with_args(self, parser):
        """Test parsing command with arguments."""
        result = await parser.parse_command("website add https://example.com")

        assert result.success
        assert result.subcommands == ["website", "add"]
        assert result.args == ["https://example.com"]

    @pytest.mark.asyncio
    async def test_parse_command_with_flags(self, parser):
        """Test parsing command with flags."""
        result = await parser.parse_command(
            "website add https://example.com name:MyWebsite interval:300"
        )

        assert result.success
        assert result.subcommands == ["website", "add"]
        assert result.args == ["https://example.com"]
        assert result.flags["name"] == "MyWebsite"
        assert result.flags["interval"] == "300"

    @pytest.mark.asyncio
    async def test_parse_empty_command(self, parser):
        """Test parsing empty command."""
        result = await parser.parse_command("")

        assert result.success
        assert result.subcommands == []

    @pytest.mark.asyncio
    async def test_parse_help_command(self, parser):
        """Test parsing help command."""
        result = await parser.parse_command("help website")

        assert result.success
        assert result.subcommands == ["help", "website"]


class TestSlackFormatter:
    """Test the Slack response formatter."""

    @pytest.fixture
    def formatter(self):
        return SlackFormatter()

    def test_format_success_response(self, formatter):
        """Test formatting successful command response."""
        result = CommandResult(
            success=True,
            message="Website added successfully",
            data={"website_id": "test-123"},
        )

        response = formatter.format_command_response(result, user_id="U123")

        assert "text" in response
        assert "blocks" in response
        assert "✅" in response["text"]
        assert "Website added successfully" in response["text"]

    def test_format_error_response(self, formatter):
        """Test formatting error response."""
        response = formatter.format_error_response("Command failed")

        assert "text" in response
        assert "❌" in response["text"]
        assert "Command failed" in response["text"]
        assert response["response_type"] == "ephemeral"

    def test_format_help_response(self, formatter):
        """Test formatting help response."""
        help_content = {
            "title": "Test Help",
            "description": "Test description",
            "commands": [],
        }

        response = formatter.format_help_response(help_content)

        assert "text" in response
        assert "blocks" in response
        assert "Test Help" in response["text"]


class TestWebsiteHandler:
    """Test the website command handler."""

    @pytest.fixture
    def handler(self):
        return WebsiteHandler()

    @pytest.fixture
    def mock_storage(self):
        with patch(
            "webdeface.notification.slack.handlers.website.get_storage_manager"
        ) as mock:
            storage = AsyncMock()
            mock.return_value = storage
            yield storage

    @pytest.fixture
    def mock_orchestrator(self):
        with patch(
            "webdeface.notification.slack.handlers.website.get_scheduling_orchestrator"
        ) as mock:
            orchestrator = AsyncMock()
            mock.return_value = orchestrator
            yield orchestrator

    @pytest.mark.asyncio
    async def test_website_add_command(self, handler, mock_storage, mock_orchestrator):
        """Test website add command."""
        # Setup mocks
        mock_storage.get_website_by_url.return_value = None
        mock_website = MagicMock()
        mock_website.id = "test-123"
        mock_website.name = "Test Site"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = datetime.utcnow()
        mock_storage.create_website.return_value = mock_website
        mock_orchestrator.schedule_website_monitoring.return_value = "exec-456"

        # Execute command
        result = await handler.handle_command(
            subcommands=["website", "add"],
            args=["https://example.com"],
            flags={"name": "Test Site"},
            global_flags={},
            user_id="U123",
        )

        # Verify result
        assert result.success
        assert "Website added successfully" in result.message
        assert result.data["website_id"] == "test-123"

        # Verify storage calls
        mock_storage.get_website_by_url.assert_called_once_with("https://example.com")
        mock_storage.create_website.assert_called_once()
        mock_orchestrator.schedule_website_monitoring.assert_called_once_with(
            "test-123"
        )

    @pytest.mark.asyncio
    async def test_website_list_command(self, handler, mock_storage):
        """Test website list command."""
        # Setup mock
        mock_websites = [
            MagicMock(
                id="site-1",
                name="Site 1",
                url="https://site1.com",
                is_active=True,
                last_checked_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                check_interval_seconds=900,
            ),
            MagicMock(
                id="site-2",
                name="Site 2",
                url="https://site2.com",
                is_active=False,
                last_checked_at=None,
                created_at=datetime.utcnow(),
                check_interval_seconds=600,
            ),
        ]
        mock_storage.list_websites.return_value = mock_websites

        # Execute command
        result = await handler.handle_command(
            subcommands=["website", "list"],
            args=[],
            flags={},
            global_flags={},
            user_id="U123",
        )

        # Verify result
        assert result.success
        assert "Found 2 websites" in result.message
        assert len(result.data["websites"]) == 2
        assert result.data["total"] == 2

    @pytest.mark.asyncio
    async def test_website_invalid_subcommand(self, handler):
        """Test invalid website subcommand."""
        result = await handler.handle_command(
            subcommands=["website", "invalid"],
            args=[],
            flags={},
            global_flags={},
            user_id="U123",
        )

        assert not result.success
        assert "Unknown website command" in result.message


class TestMonitoringHandler:
    """Test the monitoring command handler."""

    @pytest.fixture
    def handler(self):
        return MonitoringHandler()

    @pytest.fixture
    def mock_storage(self):
        with patch(
            "webdeface.notification.slack.handlers.monitoring.get_storage_manager"
        ) as mock:
            storage = AsyncMock()
            mock.return_value = storage
            yield storage

    @pytest.fixture
    def mock_orchestrator(self):
        with patch(
            "webdeface.notification.slack.handlers.monitoring.get_scheduling_orchestrator"
        ) as mock:
            orchestrator = AsyncMock()
            mock.return_value = orchestrator
            yield orchestrator

    @pytest.mark.asyncio
    async def test_monitoring_start_command(
        self, handler, mock_storage, mock_orchestrator
    ):
        """Test monitoring start command."""
        # Setup mock
        mock_website = MagicMock()
        mock_website.id = "site-123"
        mock_website.name = "Test Site"
        mock_website.is_active = False
        mock_storage.get_website.return_value = mock_website
        mock_orchestrator.schedule_website_monitoring.return_value = "exec-456"

        # Execute command
        result = await handler.handle_command(
            subcommands=["monitoring", "start"],
            args=["site-123"],
            flags={},
            global_flags={},
            user_id="U123",
        )

        # Verify result
        assert result.success
        assert "Started monitoring for" in result.message
        assert result.data["website_id"] == "site-123"

        # Verify calls
        mock_storage.update_website.assert_called_once_with(
            "site-123", {"is_active": True}
        )
        mock_orchestrator.schedule_website_monitoring.assert_called_once_with(
            "site-123"
        )

    @pytest.mark.asyncio
    async def test_monitoring_check_command(
        self, handler, mock_storage, mock_orchestrator
    ):
        """Test monitoring check command."""
        # Setup mock
        mock_website = MagicMock()
        mock_website.id = "site-123"
        mock_website.name = "Test Site"
        mock_storage.get_website.return_value = mock_website
        mock_orchestrator.trigger_immediate_check.return_value = "exec-789"

        # Execute command
        result = await handler.handle_command(
            subcommands=["monitoring", "check"],
            args=["site-123"],
            flags={},
            global_flags={},
            user_id="U123",
        )

        # Verify result
        assert result.success
        assert "Triggered immediate check" in result.message
        assert result.data["execution_id"] == "exec-789"


class TestSystemHandler:
    """Test the system command handler."""

    @pytest.fixture
    def handler(self):
        return SystemHandler()

    @pytest.fixture
    def mock_storage(self):
        with patch(
            "webdeface.notification.slack.handlers.system.get_storage_manager"
        ) as mock:
            storage = AsyncMock()
            mock.return_value = storage
            yield storage

    @pytest.fixture
    def mock_orchestrator(self):
        with patch(
            "webdeface.notification.slack.handlers.system.get_scheduling_orchestrator"
        ) as mock:
            orchestrator = AsyncMock()
            mock.return_value = orchestrator
            yield orchestrator

    @pytest.mark.asyncio
    async def test_system_status_command(
        self, handler, mock_storage, mock_orchestrator
    ):
        """Test system status command."""
        # Setup mocks
        mock_websites = [MagicMock(is_active=True), MagicMock(is_active=False)]
        mock_storage.list_websites.return_value = mock_websites
        mock_storage.get_snapshots_since.return_value = []
        mock_storage.get_alerts_since.return_value = []
        mock_storage.get_total_snapshot_count.return_value = 100
        mock_storage.get_total_alert_count.return_value = 10
        mock_orchestrator.get_status.return_value = {
            "status": "running",
            "active_jobs": 5,
            "pending_jobs": 2,
            "uptime_seconds": 3600,
        }

        # Execute command
        result = await handler.handle_command(
            subcommands=["system", "status"],
            args=[],
            flags={},
            global_flags={},
            user_id="U123",
        )

        # Verify result
        assert result.success
        assert "System status retrieved successfully" in result.message
        assert result.data["websites"]["total"] == 2
        assert result.data["websites"]["active"] == 1
        assert result.data["scheduler"]["status"] == "running"


class TestSlackCommandRouter:
    """Test the main command router."""

    @pytest.fixture
    def router(self):
        return SlackCommandRouter()

    @pytest.mark.asyncio
    async def test_route_website_command(self, router):
        """Test routing website command."""
        with patch.object(router.handlers["website"], "handle_command") as mock_handler:
            mock_handler.return_value = CommandResult(success=True, message="Success")

            with patch.object(
                router.permission_manager, "check_permissions"
            ) as mock_perms:
                mock_perms.return_value = True

                with patch.object(
                    router.validator, "validate_command"
                ) as mock_validator:
                    mock_validator.return_value = MagicMock(is_valid=True)

                    response = await router.route_command(
                        command_text="website list",
                        user_id="U123",
                        channel_id="C123",
                        team_id="T123",
                    )

                    assert "text" in response
                    assert "blocks" in response
                    mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_help_command(self, router):
        """Test routing help command."""
        response = await router.route_command(
            command_text="help", user_id="U123", channel_id="C123", team_id="T123"
        )

        assert "text" in response
        assert "blocks" in response
        assert "WebDeface Slack Commands" in response["text"]

    @pytest.mark.asyncio
    async def test_route_invalid_command(self, router):
        """Test routing invalid command."""
        response = await router.route_command(
            command_text="invalid_command",
            user_id="U123",
            channel_id="C123",
            team_id="T123",
        )

        assert "text" in response
        assert "❌" in response["text"]
        assert "Unknown command" in response["text"]

    @pytest.mark.asyncio
    async def test_route_permission_denied(self, router):
        """Test routing with insufficient permissions."""
        with patch.object(router.permission_manager, "check_permissions") as mock_perms:
            mock_perms.return_value = False

            response = await router.route_command(
                command_text="website add https://example.com",
                user_id="U123",
                channel_id="C123",
                team_id="T123",
            )

            assert "text" in response
            assert "❌" in response["text"]
            assert "Insufficient permissions" in response["text"]


class TestSlackCLIIntegration:
    """Test the Slack CLI integration."""

    @pytest.fixture
    def integration(self):
        return SlackCLIIntegration()

    @pytest.mark.asyncio
    async def test_get_available_commands(self, integration):
        """Test getting available commands."""
        commands_info = await integration.get_available_commands()

        assert "commands" in commands_info
        assert "cli_syntax" in commands_info
        assert "examples" in commands_info
        assert isinstance(commands_info["commands"], list)
        assert len(commands_info["examples"]) > 0

    @pytest.mark.asyncio
    async def test_validate_user_permissions(self, integration):
        """Test validating user permissions."""
        with patch.object(
            integration.command_router, "validate_permissions_for_user"
        ) as mock_validate:
            mock_validate.return_value = {"permissions": ["VIEW_SITES"]}

            permissions = await integration.validate_user_permissions("U123", "T123")

            assert "permissions" in permissions
            mock_validate.assert_called_once_with("U123", "T123")


@pytest.mark.asyncio
async def test_full_integration_flow():
    """Test full integration flow from Slack command to response."""
    # This would test the complete flow but requires more extensive mocking
    # For now, we'll test that the integration can be instantiated
    integration = SlackCLIIntegration()
    router = integration.command_router

    assert router is not None
    assert hasattr(router, "route_command")
    assert len(router.handlers) > 0


if __name__ == "__main__":
    # Run basic validation when executed directly
    import asyncio

    async def main():
        print("🧪 Running basic CLI integration validation...")

        # Test parser
        parser = SlackCommandParser()
        result = await parser.parse_command("website add https://example.com name:Test")
        print(f"✅ Parser test: {result.success}")

        # Test formatter
        formatter = SlackFormatter()
        cmd_result = CommandResult(success=True, message="Test success")
        response = formatter.format_command_response(cmd_result, user_id="U123")
        print(f"✅ Formatter test: {'text' in response}")

        # Test router instantiation
        router = SlackCommandRouter()
        print(f"✅ Router test: {len(router.handlers)} handlers registered")

        print("🎉 Basic validation complete!")

    asyncio.run(main())
