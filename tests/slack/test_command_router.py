"""Tests for Slack command routing system."""

from unittest.mock import MagicMock, patch

import pytest

from src.webdeface.notification.slack.handlers.monitoring import MonitoringHandler
from src.webdeface.notification.slack.handlers.router import (
    SlackCommandRouter,
    get_command_router,
    route_slack_command,
)
from src.webdeface.notification.slack.handlers.system import SystemHandler
from src.webdeface.notification.slack.handlers.website import WebsiteHandler
from tests.slack.conftest import (
    assert_error_response,
    assert_slack_response_format,
    assert_success_response,
    create_mock_parse_result,
    create_mock_validation_result,
)


class TestSlackCommandRouter:
    """Test command routing functionality."""

    def test_router_initialization(self):
        """Test router initializes with correct handlers."""
        router = SlackCommandRouter()

        assert "website" in router.handlers
        assert "monitoring" in router.handlers
        assert "system" in router.handlers

        assert isinstance(router.handlers["website"], WebsiteHandler)
        assert isinstance(router.handlers["monitoring"], MonitoringHandler)
        assert isinstance(router.handlers["system"], SystemHandler)

    @pytest.mark.asyncio
    async def test_route_empty_command_shows_help(
        self, command_router, mock_slack_response
    ):
        """Test routing empty command shows help."""
        await command_router.route_command(
            text="", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_slack_response_format(response)
        assert response["response_type"] == "ephemeral"

    @pytest.mark.asyncio
    async def test_route_help_command(self, command_router, mock_slack_response):
        """Test routing help command."""
        await command_router.route_command(
            text="help", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_slack_response_format(response)
        assert response["response_type"] == "ephemeral"

    @pytest.mark.asyncio
    async def test_route_help_with_context(self, command_router, mock_slack_response):
        """Test routing help command with context."""
        await command_router.route_command(
            text="help website", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_slack_response_format(response)

    @pytest.mark.asyncio
    async def test_route_to_website_handler(self, command_router, mock_slack_response):
        """Test routing to website handler."""
        with patch.object(
            command_router.handlers["website"], "handle_command"
        ) as mock_handler:
            mock_handler.return_value = None

            await command_router.route_command(
                text="website list",
                user_id="U123456",
                respond=mock_slack_response,
                channel_id="C123456",
            )

            mock_handler.assert_called_once_with(
                "website list", "U123456", mock_slack_response, "C123456"
            )

    @pytest.mark.asyncio
    async def test_route_to_monitoring_handler(
        self, command_router, mock_slack_response
    ):
        """Test routing to monitoring handler."""
        with patch.object(
            command_router.handlers["monitoring"], "handle_command"
        ) as mock_handler:
            mock_handler.return_value = None

            await command_router.route_command(
                text="monitoring start", user_id="U234567", respond=mock_slack_response
            )

            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_to_system_handler(self, command_router, mock_slack_response):
        """Test routing to system handler."""
        with patch.object(
            command_router.handlers["system"], "handle_command"
        ) as mock_handler:
            mock_handler.return_value = None

            await command_router.route_command(
                text="system status", user_id="U123456", respond=mock_slack_response
            )

            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_unknown_command_group(
        self, command_router, mock_slack_response
    ):
        """Test routing unknown command group returns error."""
        await command_router.route_command(
            text="unknown command", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Unknown command")

    @pytest.mark.asyncio
    async def test_route_command_parse_error(self, command_router, mock_slack_response):
        """Test routing handles parse errors."""
        with patch.object(command_router.parser, "parse_command") as mock_parser:
            mock_parser.return_value = create_mock_parse_result(
                success=False, error_message="Invalid command syntax"
            )

            await command_router.route_command(
                text="invalid [ syntax", user_id="U123456", respond=mock_slack_response
            )

            response = mock_slack_response.last_response
            assert_error_response(response, "Invalid command syntax")

    @pytest.mark.asyncio
    async def test_route_command_validation_error(
        self, command_router, mock_slack_response
    ):
        """Test routing handles validation errors."""
        with patch.object(
            command_router.parser, "parse_command"
        ) as mock_parser, patch.object(
            command_router.validator, "validate_command"
        ) as mock_validator:
            mock_parser.return_value = create_mock_parse_result(
                success=True, subcommands=["website", "add"], args={}, flags={}
            )

            mock_validator.return_value = create_mock_validation_result(
                is_valid=False,
                error_message="URL is required",
                suggestions=["Try: /webdeface website add <url>"],
            )

            await command_router.route_command(
                text="website add", user_id="U345678", respond=mock_slack_response
            )

            response = mock_slack_response.last_response
            assert_error_response(response, "URL is required")
            # Should include suggestions in blocks
            assert "blocks" in response

    @pytest.mark.asyncio
    async def test_route_command_exception_handling(
        self, command_router, mock_slack_response
    ):
        """Test routing handles unexpected exceptions."""
        with patch.object(command_router.parser, "parse_command") as mock_parser:
            mock_parser.side_effect = Exception("Unexpected error")

            await command_router.route_command(
                text="website list", user_id="U123456", respond=mock_slack_response
            )

            response = mock_slack_response.last_response
            assert_error_response(response, "Internal error occurred")

    def test_add_handler(self, command_router):
        """Test adding a new command handler."""
        new_handler = MagicMock()
        command_router.add_handler("test", new_handler)

        assert "test" in command_router.handlers
        assert command_router.handlers["test"] == new_handler

    def test_remove_handler(self, command_router):
        """Test removing a command handler."""
        # Remove existing handler
        result = command_router.remove_handler("website")
        assert result is True
        assert "website" not in command_router.handlers

        # Try to remove non-existent handler
        result = command_router.remove_handler("nonexistent")
        assert result is False

    def test_get_registered_commands(self, command_router):
        """Test getting list of registered commands."""
        commands = command_router.get_registered_commands()

        assert "website" in commands
        assert "monitoring" in commands
        assert "system" in commands
        assert len(commands) == 3

    @pytest.mark.asyncio
    async def test_send_parse_error_format(self, command_router, mock_slack_response):
        """Test parse error response format."""
        await command_router._send_parse_error(mock_slack_response, "Test parse error")

        response = mock_slack_response.last_response
        assert_error_response(response, "Test parse error")
        assert "blocks" in response
        assert len(response["blocks"]) == 2  # Error section + context section

    @pytest.mark.asyncio
    async def test_send_validation_error_format(
        self, command_router, mock_slack_response
    ):
        """Test validation error response format."""
        suggestions = ["Try: /webdeface help", "Use: /webdeface website list"]

        await command_router._send_validation_error(
            mock_slack_response, "Test validation error", suggestions
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Test validation error")
        assert "blocks" in response
        assert len(response["blocks"]) == 3  # Error + suggestions + context

    @pytest.mark.asyncio
    async def test_send_unknown_command_error_format(
        self, command_router, mock_slack_response
    ):
        """Test unknown command error response format."""
        await command_router._send_unknown_command_error(mock_slack_response, "unknown")

        response = mock_slack_response.last_response
        assert_error_response(response, "Unknown command: unknown")
        assert "blocks" in response
        # Should list available commands
        response_text = str(response["blocks"])
        assert "website" in response_text
        assert "monitoring" in response_text
        assert "system" in response_text

    @pytest.mark.asyncio
    async def test_send_internal_error_format(
        self, command_router, mock_slack_response
    ):
        """Test internal error response format."""
        await command_router._send_internal_error(
            mock_slack_response, "Test internal error"
        )

        response = mock_slack_response.last_response
        assert_error_response(response)
        assert "💥" in response["text"]
        assert "Internal Error" in str(response["blocks"])

    @pytest.mark.asyncio
    async def test_complex_routing_scenario(self, command_router, mock_slack_response):
        """Test complex routing scenario with multiple components."""
        # Mock all components to succeed
        with patch.object(
            command_router.parser, "parse_command"
        ) as mock_parser, patch.object(
            command_router.validator, "validate_command"
        ) as mock_validator, patch.object(
            command_router.handlers["website"], "handle_command"
        ) as mock_handler:
            mock_parser.return_value = create_mock_parse_result(
                success=True,
                subcommands=["website", "add"],
                args={0: "https://example.com"},
                flags={"name": "Test Site"},
            )

            mock_validator.return_value = create_mock_validation_result(is_valid=True)
            mock_handler.return_value = None

            await command_router.route_command(
                text="website add https://example.com name:TestSite",
                user_id="U345678",
                respond=mock_slack_response,
                channel_id="C123456",
            )

            # Verify all components called correctly
            mock_parser.assert_called_once_with(
                "website add https://example.com name:TestSite"
            )
            mock_validator.assert_called_once()
            mock_handler.assert_called_once()


class TestGlobalCommandRouter:
    """Test global command router functions."""

    def test_get_command_router_singleton(self):
        """Test global command router returns singleton instance."""
        router1 = get_command_router()
        router2 = get_command_router()

        assert router1 is router2
        assert isinstance(router1, SlackCommandRouter)

    @pytest.mark.asyncio
    async def test_route_slack_command_convenience_function(self, mock_slack_response):
        """Test convenience function for routing commands."""
        with patch(
            "src.webdeface.notification.slack.handlers.router.get_command_router"
        ) as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router

            await route_slack_command(
                text="website list",
                user_id="U123456",
                respond=mock_slack_response,
                channel_id="C123456",
            )

            mock_router.route_command.assert_called_once_with(
                "website list", "U123456", mock_slack_response, "C123456"
            )


class TestRouterIntegrationScenarios:
    """Test integration scenarios for command routing."""

    @pytest.mark.asyncio
    async def test_end_to_end_website_command_routing(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end routing of website command."""
        router = SlackCommandRouter()
        storage = patch_get_storage_manager

        # Mock website doesn't exist
        storage.get_website_by_url.return_value = None
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        storage.create_website.return_value = mock_website

        await router.route_command(
            text="website add https://example.com name:TestSite",
            user_id="U345678",  # Admin user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website added successfully")

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_command_routing(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end routing of monitoring command."""
        router = SlackCommandRouter()
        storage = patch_get_storage_manager

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        await router.route_command(
            text="monitoring start website123",
            user_id="U234567",  # Operator user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Started monitoring")

    @pytest.mark.asyncio
    async def test_end_to_end_system_command_routing(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end routing of system command."""
        router = SlackCommandRouter()
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock system data
        storage.list_websites.return_value = [MagicMock(is_active=True)]
        storage.get_open_alerts.return_value = []
        orchestrator.get_status.return_value = {"status": "running"}

        await router.route_command(
            text="system status",
            user_id="U123456",  # Viewer user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "System status retrieved")

    @pytest.mark.asyncio
    async def test_permission_error_routing(
        self, mock_slack_response, patch_get_permission_manager
    ):
        """Test routing handles permission errors correctly."""
        router = SlackCommandRouter()

        await router.route_command(
            text="website add https://example.com",
            user_id="U123456",  # Viewer user (insufficient permissions)
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_command_validation_error_routing(
        self, mock_slack_response, patch_get_permission_manager
    ):
        """Test routing handles command validation errors."""
        router = SlackCommandRouter()

        await router.route_command(
            text="website add",  # Missing URL
            user_id="U345678",  # Admin user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response)

    @pytest.mark.asyncio
    async def test_handler_exception_routing(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test routing handles handler exceptions."""
        router = SlackCommandRouter()
        storage = patch_get_storage_manager

        # Make storage throw exception
        storage.list_websites.side_effect = Exception("Database error")

        await router.route_command(
            text="website list", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Internal error occurred")

    @pytest.mark.asyncio
    async def test_router_logging_integration(
        self, mock_slack_response, patch_get_permission_manager
    ):
        """Test router logs commands appropriately."""
        router = SlackCommandRouter()

        with patch(
            "src.webdeface.notification.slack.handlers.router.logger"
        ) as mock_logger:
            await router.route_command(
                text="website list",
                user_id="U123456",
                respond=mock_slack_response,
                channel_id="C123456",
            )

            # Should log command routing
            mock_logger.info.assert_called()
            log_calls = [call.args for call in mock_logger.info.call_args_list]
            assert any("Routing Slack command" in str(call) for call in log_calls)

    @pytest.mark.asyncio
    async def test_router_with_complex_flags(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test router handles commands with complex flag combinations."""
        router = SlackCommandRouter()
        storage = patch_get_storage_manager

        storage.get_website_by_url.return_value = None
        mock_website = MagicMock()
        mock_website.id = "website123"
        storage.create_website.return_value = mock_website

        await router.route_command(
            text='website add https://example.com name:"Complex Site Name" interval:300 max-depth:3',
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website added successfully")

    @pytest.mark.asyncio
    async def test_router_channel_context_handling(
        self,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test router passes channel context to handlers."""
        router = SlackCommandRouter()

        with patch.object(router.handlers["website"], "handle_command") as mock_handler:
            await router.route_command(
                text="website list",
                user_id="U123456",
                respond=mock_slack_response,
                channel_id="C123456",
            )

            # Verify channel_id is passed to handler
            args, kwargs = mock_handler.call_args
            assert args[3] == "C123456"  # channel_id parameter
