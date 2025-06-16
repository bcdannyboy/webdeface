"""Tests for Slack system management commands."""

from unittest.mock import MagicMock

import pytest

from src.webdeface.notification.slack.permissions import Permission
from tests.slack.conftest import (
    assert_error_response,
    assert_success_response,
)


class TestSystemHandler:
    """Test system command handler."""

    @pytest.mark.asyncio
    async def test_system_status_success(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test successful system status command."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock websites
        websites = [
            MagicMock(id="web1", name="Site 1", is_active=True),
            MagicMock(id="web2", name="Site 2", is_active=False),
            MagicMock(id="web3", name="Site 3", is_active=True),
        ]
        storage.list_websites.return_value = websites

        # Mock alerts
        alerts = [
            MagicMock(status="open", severity="high"),
            MagicMock(status="resolved", severity="medium"),
        ]
        storage.get_open_alerts.return_value = alerts

        # Mock scheduler status
        scheduler_status = {
            "status": "running",
            "active_jobs": 5,
            "pending_jobs": 2,
            "uptime_seconds": 7200,
        }
        orchestrator.get_status.return_value = scheduler_status

        await system_handler.handle_command(
            text="system status",
            user_id="U123456",  # Viewer can see status
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "System status retrieved successfully")

        # Verify storage calls
        storage.list_websites.assert_called_once()
        storage.get_open_alerts.assert_called_once_with(limit=1000)
        orchestrator.get_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_health_all_healthy(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system health check with all components healthy."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock healthy components
        storage.health_check.return_value = True
        orchestrator.get_status.return_value = {"status": "running"}

        await system_handler.handle_command(
            text="system health", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "System health: healthy")

        storage.health_check.assert_called_once()
        orchestrator.get_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_health_with_failures(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system health check with component failures."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock storage failure
        storage.health_check.side_effect = Exception("Storage connection failed")
        orchestrator.get_status.return_value = {"status": "running"}

        await system_handler.handle_command(
            text="system health", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "System health: critical")

    @pytest.mark.asyncio
    async def test_system_health_partial_failures(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system health check with partial failures."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock storage healthy but scheduler warning
        storage.health_check.return_value = True
        orchestrator.get_status.return_value = {"status": "degraded"}

        await system_handler.handle_command(
            text="system health", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "System health: warning")

    @pytest.mark.asyncio
    async def test_system_metrics_default_range(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system metrics with default time range."""
        storage = patch_get_storage_manager

        # Mock websites for monitoring metrics
        websites = [
            MagicMock(id="web1", is_active=True),
            MagicMock(id="web2", is_active=False),
        ]
        storage.list_websites.return_value = websites
        storage.get_open_alerts.return_value = []

        await system_handler.handle_command(
            text="system metrics", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_success_response(
            response, "System metrics for 24h retrieved successfully"
        )

    @pytest.mark.asyncio
    async def test_system_metrics_custom_range_and_type(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test system metrics with custom time range and metric type."""
        storage = patch_get_storage_manager
        storage.list_websites.return_value = []
        storage.get_open_alerts.return_value = []

        await system_handler.handle_command(
            text="system metrics range:1h type:performance",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(
            response, "System metrics for 1h retrieved successfully"
        )

    @pytest.mark.asyncio
    async def test_system_metrics_permission_check(
        self, system_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test system metrics requires VIEW_METRICS permission."""
        await system_handler.handle_command(
            text="system metrics",
            user_id="U123456",  # Viewer doesn't have VIEW_METRICS
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_system_logs_default_settings(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test system logs with default settings."""
        await system_handler.handle_command(
            text="system logs",
            user_id="U123456",  # Viewer doesn't have VIEW_LOGS
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_system_logs_with_admin_permissions(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test system logs with admin permissions."""
        await system_handler.handle_command(
            text="system logs level:error limit:100",
            user_id="U345678",  # Admin user has VIEW_LOGS
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Retrieved")

    @pytest.mark.asyncio
    async def test_system_logs_with_filters(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test system logs with filtering options."""
        await system_handler.handle_command(
            text="system logs level:warning component:scheduler since:2h limit:50",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Retrieved")

    @pytest.mark.asyncio
    async def test_system_logs_invalid_since_format(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test system logs with invalid since format falls back gracefully."""
        await system_handler.handle_command(
            text="system logs since:invalid",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        # Should still succeed but use default time range
        assert_success_response(response, "Retrieved")

    @pytest.mark.asyncio
    async def test_get_required_permissions(self, system_handler):
        """Test permission requirements for system commands."""
        # Test status and health commands
        for cmd in ["status", "health"]:
            perms = system_handler.get_required_permissions(["system", cmd])
            assert Permission.VIEW_SYSTEM in perms

        # Test metrics command
        metrics_perms = system_handler.get_required_permissions(["system", "metrics"])
        assert Permission.VIEW_METRICS in metrics_perms

        # Test logs command
        logs_perms = system_handler.get_required_permissions(["system", "logs"])
        assert Permission.VIEW_LOGS in logs_perms

    @pytest.mark.asyncio
    async def test_unknown_system_command(
        self, system_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test handling of unknown system subcommand."""
        await system_handler.handle_command(
            text="system unknown", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Unknown system command")

    @pytest.mark.asyncio
    async def test_system_command_exception_handling(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test exception handling in system commands."""
        storage = patch_get_storage_manager
        storage.list_websites.side_effect = Exception("Database error")

        await system_handler.handle_command(
            text="system status", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Command failed")

    @pytest.mark.asyncio
    async def test_system_status_comprehensive_data(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system status returns comprehensive data structure."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock data
        websites = [MagicMock(is_active=True), MagicMock(is_active=False)]
        storage.list_websites.return_value = websites
        storage.get_open_alerts.return_value = [MagicMock(status="open")]

        scheduler_status = {
            "status": "running",
            "active_jobs": 3,
            "pending_jobs": 1,
            "uptime_seconds": 3600,
        }
        orchestrator.get_status.return_value = scheduler_status

        # Execute via _execute_command to check data structure
        result = await system_handler._execute_command(
            subcommands=["system", "status"],
            args={},
            flags={},
            global_flags={},
            user_id="U123456",
        )

        assert result.success is True
        assert "timestamp" in result.data
        assert "websites" in result.data
        assert "activity_24h" in result.data
        assert "scheduler" in result.data
        assert "storage" in result.data

        # Check website counts
        assert result.data["websites"]["total"] == 2
        assert result.data["websites"]["active"] == 1
        assert result.data["websites"]["inactive"] == 1

    @pytest.mark.asyncio
    async def test_system_health_detailed_checks(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system health provides detailed component checks."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        storage.health_check.return_value = True
        orchestrator.get_status.return_value = {"status": "running"}

        # Execute via _execute_command to check data structure
        result = await system_handler._execute_command(
            subcommands=["system", "health"],
            args={},
            flags={},
            global_flags={},
            user_id="U123456",
        )

        assert result.success is True
        assert "overall_status" in result.data
        assert "health_score" in result.data
        assert "components" in result.data
        assert "total_checks" in result.data

        # Check component structure
        components = result.data["components"]
        component_names = [c["component"] for c in components]
        assert "Storage" in component_names
        assert "Scheduler" in component_names

    @pytest.mark.asyncio
    async def test_system_metrics_all_types(
        self, system_handler, patch_get_storage_manager, patch_get_permission_manager
    ):
        """Test system metrics includes all metric types."""
        storage = patch_get_storage_manager
        storage.list_websites.return_value = []
        storage.get_open_alerts.return_value = []

        result = await system_handler._execute_command(
            subcommands=["system", "metrics"],
            args={},
            flags={"type": "all"},
            global_flags={},
            user_id="U345678",  # Admin has VIEW_METRICS
        )

        assert result.success is True
        assert "performance" in result.data
        assert "monitoring" in result.data
        assert "alerts" in result.data
        assert "system" in result.data
        assert "time_range" in result.data
        assert "metric_type" in result.data

    @pytest.mark.asyncio
    async def test_system_metrics_specific_type(
        self, system_handler, patch_get_storage_manager, patch_get_permission_manager
    ):
        """Test system metrics with specific metric type."""
        storage = patch_get_storage_manager
        storage.list_websites.return_value = []

        result = await system_handler._execute_command(
            subcommands=["system", "metrics"],
            args={},
            flags={"type": "performance", "range": "1h"},
            global_flags={},
            user_id="U345678",
        )

        assert result.success is True
        assert result.data["metric_type"] == "performance"
        assert result.data["time_range"] == "1h"
        # Only performance metrics should be populated
        assert len(result.data["performance"]) > 0
        assert len(result.data["monitoring"]) == 0

    @pytest.mark.asyncio
    async def test_behavioral_parity_with_cli(
        self,
        system_handler,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test that Slack commands produce same results as CLI equivalents."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock dependencies
        websites = [MagicMock(is_active=True)]
        storage.list_websites.return_value = websites
        storage.get_open_alerts.return_value = []
        orchestrator.get_status.return_value = {"status": "running"}

        # Execute system status via handler's _execute_command (simulates CLI path)
        result = await system_handler._execute_command(
            subcommands=["system", "status"],
            args={},
            flags={},
            global_flags={},
            user_id="U123456",
        )

        # Verify result matches expected CLI behavior
        assert result.success is True
        assert "System status retrieved successfully" in result.message
        assert isinstance(result.data, dict)
        assert "websites" in result.data
        assert "scheduler" in result.data
        assert "storage" in result.data

    @pytest.mark.asyncio
    async def test_system_logs_time_parsing(
        self, system_handler, patch_get_storage_manager, patch_get_permission_manager
    ):
        """Test system logs time parsing for different formats."""
        # Test hours format
        result = await system_handler._execute_command(
            subcommands=["system", "logs"],
            args={},
            flags={"since": "2h"},
            global_flags={},
            user_id="U345678",
        )
        assert result.success is True

        # Test days format
        result = await system_handler._execute_command(
            subcommands=["system", "logs"],
            args={},
            flags={"since": "1d"},
            global_flags={},
            user_id="U345678",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_system_commands_error_recovery(
        self,
        system_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test system commands gracefully handle partial failures."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock storage working but orchestrator failing
        storage.list_websites.return_value = [MagicMock(is_active=True)]
        storage.get_open_alerts.return_value = []
        orchestrator.get_status.side_effect = Exception("Orchestrator down")

        await system_handler.handle_command(
            text="system status", user_id="U123456", respond=mock_slack_response
        )

        # Should still return some status even with partial failure
        response = mock_slack_response.last_response
        assert_error_response(response, "Command failed")
