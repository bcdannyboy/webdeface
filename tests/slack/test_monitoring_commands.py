"""Tests for Slack monitoring control commands."""

from unittest.mock import MagicMock

import pytest

from src.webdeface.notification.slack.permissions import Permission
from tests.slack.conftest import (
    assert_error_response,
    assert_success_response,
)


class TestMonitoringHandler:
    """Test monitoring command handler."""

    @pytest.mark.asyncio
    async def test_monitoring_start_specific_website(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test starting monitoring for a specific website."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring start website123",
            user_id="U234567",  # Operator user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Started monitoring for")

        # Verify calls
        storage.get_website.assert_called_once_with("website123")
        storage.update_website.assert_called_once_with(
            "website123", {"is_active": True}
        )
        orchestrator.schedule_website_monitoring.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_monitoring_start_already_active(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test starting monitoring for already active website."""
        storage = patch_get_storage_manager

        # Mock active website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = True
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring start website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Monitoring already active")

    @pytest.mark.asyncio
    async def test_monitoring_start_all_websites(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test starting monitoring for all inactive websites."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock inactive websites
        inactive_websites = [
            MagicMock(id="web1", name="Site 1", is_active=False),
            MagicMock(id="web2", name="Site 2", is_active=False),
        ]
        storage.list_websites.return_value = inactive_websites

        await monitoring_handler.handle_command(
            text="monitoring start", user_id="U234567", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Started monitoring for 2 websites")

        # Verify calls for each website
        assert storage.update_website.call_count == 2
        assert orchestrator.schedule_website_monitoring.call_count == 2

    @pytest.mark.asyncio
    async def test_monitoring_start_no_inactive_websites(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test starting monitoring when all websites are already active."""
        storage = patch_get_storage_manager

        # Mock active websites
        active_websites = [
            MagicMock(id="web1", name="Site 1", is_active=True),
            MagicMock(id="web2", name="Site 2", is_active=True),
        ]
        storage.list_websites.return_value = active_websites

        await monitoring_handler.handle_command(
            text="monitoring start", user_id="U234567", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "All websites are already being monitored")

    @pytest.mark.asyncio
    async def test_monitoring_stop_specific_website(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test stopping monitoring for a specific website."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock active website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = True
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring stop website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Stopped monitoring for")

        # Verify calls
        storage.update_website.assert_called_once_with(
            "website123", {"is_active": False}
        )
        orchestrator.unschedule_website_monitoring.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_monitoring_stop_already_inactive(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test stopping monitoring for already inactive website."""
        storage = patch_get_storage_manager

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring stop website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Monitoring already stopped")

    @pytest.mark.asyncio
    async def test_monitoring_stop_all_websites(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test stopping monitoring for all active websites."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock active websites
        active_websites = [
            MagicMock(id="web1", name="Site 1", is_active=True),
            MagicMock(id="web2", name="Site 2", is_active=True),
        ]
        storage.list_websites.return_value = active_websites

        await monitoring_handler.handle_command(
            text="monitoring stop", user_id="U234567", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Stopped monitoring for 2 websites")

    @pytest.mark.asyncio
    async def test_monitoring_pause_success(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test pausing monitoring for a website."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock active website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = True
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring pause website123 duration:7200",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Paused monitoring for")

        orchestrator.pause_website_monitoring.assert_called_once_with(
            "website123", 7200
        )

    @pytest.mark.asyncio
    async def test_monitoring_pause_inactive_website(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test pausing monitoring for inactive website."""
        storage = patch_get_storage_manager

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring pause website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Monitoring not active")

    @pytest.mark.asyncio
    async def test_monitoring_pause_default_duration(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test pausing monitoring with default duration."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = True
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring pause website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        # Should use default duration of 3600 seconds (1 hour)
        orchestrator.pause_website_monitoring.assert_called_once_with(
            "website123", 3600
        )

    @pytest.mark.asyncio
    async def test_monitoring_resume_success(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test resuming monitoring for a website."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring resume website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Resumed monitoring for")

        orchestrator.resume_website_monitoring.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_monitoring_check_success(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test triggering immediate check for a website."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        storage.get_website.return_value = mock_website

        await monitoring_handler.handle_command(
            text="monitoring check website123",
            user_id="U123456",  # Viewer can trigger checks
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Triggered immediate check")

        orchestrator.trigger_immediate_check.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_monitoring_check_website_not_found(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test check command with non-existent website."""
        storage = patch_get_storage_manager
        storage.get_website.return_value = None

        await monitoring_handler.handle_command(
            text="monitoring check nonexistent",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Website not found")

    @pytest.mark.asyncio
    async def test_monitoring_permission_denied(
        self, monitoring_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test monitoring commands with insufficient permissions."""
        await monitoring_handler.handle_command(
            text="monitoring start website123",
            user_id="U123456",  # Viewer user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_get_required_permissions(self, monitoring_handler):
        """Test permission requirements for monitoring commands."""
        # Test control commands need CONTROL_MONITORING
        for cmd in ["start", "stop", "pause", "resume"]:
            perms = monitoring_handler.get_required_permissions(["monitoring", cmd])
            assert Permission.CONTROL_MONITORING in perms

        # Test check command needs VIEW_MONITORING
        check_perms = monitoring_handler.get_required_permissions(
            ["monitoring", "check"]
        )
        assert Permission.VIEW_MONITORING in check_perms

    @pytest.mark.asyncio
    async def test_monitoring_commands_missing_website_id(
        self, monitoring_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test monitoring commands that require website ID without providing it."""
        for cmd in ["pause", "resume", "check"]:
            mock_slack_response.clear()
            await monitoring_handler.handle_command(
                text=f"monitoring {cmd}", user_id="U234567", respond=mock_slack_response
            )

            response = mock_slack_response.last_response
            assert_error_response(response, "Website ID is required")

    @pytest.mark.asyncio
    async def test_unknown_monitoring_command(
        self, monitoring_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test handling of unknown monitoring subcommand."""
        await monitoring_handler.handle_command(
            text="monitoring unknown", user_id="U234567", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Unknown monitoring command")

    @pytest.mark.asyncio
    async def test_monitoring_exception_handling(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test exception handling in monitoring commands."""
        storage = patch_get_storage_manager
        storage.get_website.side_effect = Exception("Database error")

        await monitoring_handler.handle_command(
            text="monitoring check website123",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Command failed")

    @pytest.mark.asyncio
    async def test_monitoring_start_with_partial_failures(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test starting monitoring with some websites failing."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock websites with one that will fail
        inactive_websites = [
            MagicMock(id="web1", name="Site 1", is_active=False),
            MagicMock(id="web2", name="Site 2", is_active=False),
        ]
        storage.list_websites.return_value = inactive_websites

        # Make second website scheduling fail
        def mock_schedule_side_effect(website_id):
            if website_id == "web2":
                raise Exception("Scheduling failed")
            return "exec123"

        orchestrator.schedule_website_monitoring.side_effect = mock_schedule_side_effect

        await monitoring_handler.handle_command(
            text="monitoring start", user_id="U234567", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Started monitoring for 1 websites")

    @pytest.mark.asyncio
    async def test_behavioral_parity_with_cli(
        self,
        monitoring_handler,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test that Slack commands produce same results as CLI equivalents."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        # Execute monitoring start via handler's _execute_command (simulates CLI path)
        result = await monitoring_handler._execute_command(
            subcommands=["monitoring", "start"],
            args={0: "website123"},
            flags={},
            global_flags={},
            user_id="U234567",
        )

        # Verify result matches expected CLI behavior
        assert result.success is True
        assert "Started monitoring for" in result.message
        assert result.data["website_id"] == "website123"
        assert result.data["website_name"] == "Test Website"
        assert "execution_id" in result.data

    @pytest.mark.asyncio
    async def test_monitoring_commands_timeout_handling(
        self,
        monitoring_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test monitoring commands handle timeouts gracefully."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        # Test with AsyncCommandMixin timeout functionality
        import asyncio

        orchestrator.schedule_website_monitoring.side_effect = asyncio.TimeoutError()

        await monitoring_handler.handle_command(
            text="monitoring start website123",
            user_id="U234567",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Command failed")
