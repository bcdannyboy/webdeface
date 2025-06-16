"""Tests for CLI interface components."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.webdeface.cli.main import cli
from src.webdeface.cli.types import CLIContext, CommandResult


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_storage():
    """Mock storage manager."""
    storage = AsyncMock()

    # Mock website data
    from datetime import datetime

    mock_website = MagicMock()
    mock_website.id = "test-website-123"
    mock_website.name = "Test Website"
    mock_website.url = "https://example.com"
    mock_website.is_active = True
    mock_website.created_at = datetime(2024, 1, 1, 0, 0, 0)
    mock_website.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    mock_website.last_checked_at = None
    mock_website.check_interval_seconds = 900
    mock_website.description = "Test description"

    storage.create_website.return_value = mock_website
    storage.get_website.return_value = mock_website
    storage.get_website_by_url.return_value = None
    storage.list_websites.return_value = [mock_website]
    storage.get_website_snapshots.return_value = []
    storage.get_website_alerts.return_value = []

    return storage


@pytest.fixture
def mock_orchestrator():
    """Mock scheduling orchestrator."""
    orchestrator = AsyncMock()
    orchestrator.is_running = True
    orchestrator.schedule_website_monitoring.return_value = "execution-123"
    orchestrator.unschedule_website_monitoring.return_value = True
    orchestrator.execute_immediate_workflow.return_value = "workflow-123"
    orchestrator.get_orchestrator_status.return_value = {
        "status": "running",
        "uptime_seconds": 3600,
        "total_jobs_scheduled": 5,
        "total_workflows_executed": 10,
        "components": {
            "scheduler_manager": True,
            "workflow_engine": True,
            "health_monitor": True,
        },
    }
    orchestrator.get_monitoring_report.return_value = None
    orchestrator.pause_all_jobs.return_value = {"paused_jobs": 3}
    orchestrator.resume_all_jobs.return_value = {"resumed_jobs": 3}

    return orchestrator


class TestWebsiteCommands:
    """Test website management CLI commands."""

    @patch("src.webdeface.cli.main.get_storage_manager")
    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_website_add_success(
        self,
        mock_get_orchestrator,
        mock_get_storage,
        cli_runner,
        mock_storage,
        mock_orchestrator,
    ):
        """Test successful website addition."""
        mock_get_storage.return_value = mock_storage
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(
            cli, ["website", "add", "https://example.com", "--name", "Test Website"]
        )

        assert result.exit_code == 0
        assert "Website added successfully" in result.output
        mock_storage.create_website.assert_called_once()
        mock_orchestrator.schedule_website_monitoring.assert_called_once()

    @patch("src.webdeface.cli.main.get_storage_manager")
    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_website_add_duplicate(
        self,
        mock_get_orchestrator,
        mock_get_storage,
        cli_runner,
        mock_storage,
        mock_orchestrator,
    ):
        """Test adding duplicate website."""
        mock_storage.get_website_by_url.return_value = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["website", "add", "https://example.com"])

        assert result.exit_code == 1
        assert "Website already exists" in result.output

    @patch("src.webdeface.cli.main.get_storage_manager")
    def test_website_list(self, mock_get_storage, cli_runner, mock_storage):
        """Test website listing."""
        mock_get_storage.return_value = mock_storage

        result = cli_runner.invoke(cli, ["website", "list"])

        assert result.exit_code == 0
        mock_storage.list_websites.assert_called_once()

    @patch("src.webdeface.cli.main.get_storage_manager")
    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_website_remove(
        self,
        mock_get_orchestrator,
        mock_get_storage,
        cli_runner,
        mock_storage,
        mock_orchestrator,
    ):
        """Test website removal."""
        mock_get_storage.return_value = mock_storage
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(
            cli, ["website", "remove", "test-website-123", "--force"]
        )

        assert result.exit_code == 0
        assert "Website removed successfully" in result.output
        mock_orchestrator.unschedule_website_monitoring.assert_called_once_with(
            "test-website-123"
        )
        mock_storage.delete_website.assert_called_once_with("test-website-123")

    @patch("src.webdeface.cli.main.get_storage_manager")
    def test_website_status(self, mock_get_storage, cli_runner, mock_storage):
        """Test website status command."""
        mock_get_storage.return_value = mock_storage

        result = cli_runner.invoke(cli, ["website", "status", "test-website-123"])

        assert result.exit_code == 0
        mock_storage.get_website.assert_called_once_with("test-website-123")


class TestMonitoringCommands:
    """Test monitoring control CLI commands."""

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_monitoring_start(
        self, mock_get_orchestrator, cli_runner, mock_orchestrator
    ):
        """Test monitoring start command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["monitoring", "start"])

        assert result.exit_code == 0
        assert "Monitoring system started" in result.output

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    @patch("src.webdeface.cli.main.cleanup_scheduling_orchestrator")
    def test_monitoring_stop(
        self, mock_cleanup, mock_get_orchestrator, cli_runner, mock_orchestrator
    ):
        """Test monitoring stop command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["monitoring", "stop"])

        assert result.exit_code == 0
        assert "Monitoring system stopped" in result.output

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_monitoring_pause(
        self, mock_get_orchestrator, cli_runner, mock_orchestrator
    ):
        """Test monitoring pause command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["monitoring", "pause"])

        assert result.exit_code == 0
        assert "All monitoring jobs paused" in result.output
        mock_orchestrator.pause_all_jobs.assert_called_once()

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_monitoring_resume(
        self, mock_get_orchestrator, cli_runner, mock_orchestrator
    ):
        """Test monitoring resume command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["monitoring", "resume"])

        assert result.exit_code == 0
        assert "All monitoring jobs resumed" in result.output
        mock_orchestrator.resume_all_jobs.assert_called_once()

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_monitoring_check(
        self, mock_get_orchestrator, cli_runner, mock_orchestrator
    ):
        """Test immediate check command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["monitoring", "check", "test-website-123"])

        assert result.exit_code == 0
        assert "Immediate check initiated" in result.output
        mock_orchestrator.execute_immediate_workflow.assert_called_once()


class TestSystemCommands:
    """Test system status CLI commands."""

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_system_status(self, mock_get_orchestrator, cli_runner, mock_orchestrator):
        """Test system status command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["system", "status"])

        assert result.exit_code == 0
        mock_orchestrator.get_orchestrator_status.assert_called_once()

    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_system_health(self, mock_get_orchestrator, cli_runner, mock_orchestrator):
        """Test system health command."""
        mock_get_orchestrator.return_value = mock_orchestrator

        result = cli_runner.invoke(cli, ["system", "health"])

        assert result.exit_code == 0
        mock_orchestrator.get_monitoring_report.assert_called_once()

    @patch("src.webdeface.cli.main.get_storage_manager")
    def test_system_metrics(self, mock_get_storage, cli_runner, mock_storage):
        """Test system metrics command."""
        mock_get_storage.return_value = mock_storage

        result = cli_runner.invoke(cli, ["system", "metrics"])

        assert result.exit_code == 0
        mock_storage.list_websites.assert_called_once()

    def test_system_logs(self, cli_runner):
        """Test system logs command."""
        result = cli_runner.invoke(cli, ["system", "logs"])

        assert result.exit_code == 0
        assert "log entries" in result.output


class TestCLIContext:
    """Test CLI context functionality."""

    def test_cli_context_creation(self):
        """Test CLI context creation."""
        ctx = CLIContext(verbose=True, debug=True)
        assert ctx.verbose is True
        assert ctx.debug is True
        assert ctx.start_time is not None

    def test_cli_context_logging(self, capsys):
        """Test CLI context logging."""
        ctx = CLIContext(verbose=True)
        ctx.log("Test message", "info")

        captured = capsys.readouterr()
        assert "INFO: Test message" in captured.out

    def test_command_result_creation(self):
        """Test command result creation."""
        result = CommandResult(
            success=True, message="Operation successful", data={"key": "value"}
        )

        assert result.success is True
        assert result.message == "Operation successful"
        assert result.data == {"key": "value"}
        assert result.exit_code == 0
        assert bool(result) is True

    def test_command_result_failure(self):
        """Test command result for failure."""
        result = CommandResult(success=False, message="Operation failed", exit_code=1)

        assert result.success is False
        assert result.exit_code == 1
        assert bool(result) is False


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    @patch("src.webdeface.cli.main.get_storage_manager")
    @patch("src.webdeface.cli.main.get_scheduling_orchestrator")
    def test_complete_workflow(
        self,
        mock_get_orchestrator,
        mock_get_storage,
        cli_runner,
        mock_storage,
        mock_orchestrator,
    ):
        """Test complete CLI workflow: add website, start monitoring, check status."""
        mock_get_storage.return_value = mock_storage
        mock_get_orchestrator.return_value = mock_orchestrator

        # Add website
        result1 = cli_runner.invoke(
            cli, ["website", "add", "https://example.com", "--name", "Test Site"]
        )
        assert result1.exit_code == 0

        # Start monitoring
        result2 = cli_runner.invoke(cli, ["monitoring", "start"])
        assert result2.exit_code == 0

        # Check system status
        result3 = cli_runner.invoke(cli, ["system", "status"])
        assert result3.exit_code == 0

        # List websites
        result4 = cli_runner.invoke(cli, ["website", "list"])
        assert result4.exit_code == 0

    def test_cli_help_commands(self, cli_runner):
        """Test CLI help commands."""
        # Main help
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "WebDeface Monitor" in result.output

        # Website help
        result = cli_runner.invoke(cli, ["website", "--help"])
        assert result.exit_code == 0

        # Monitoring help
        result = cli_runner.invoke(cli, ["monitoring", "--help"])
        assert result.exit_code == 0

        # System help
        result = cli_runner.invoke(cli, ["system", "--help"])
        assert result.exit_code == 0

    def test_cli_verbose_mode(self, cli_runner):
        """Test CLI verbose mode."""
        result = cli_runner.invoke(cli, ["--verbose", "system", "logs"])
        assert result.exit_code == 0

    def test_cli_error_handling(self, cli_runner):
        """Test CLI error handling."""
        # Invalid command
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

        # Invalid subcommand
        result = cli_runner.invoke(cli, ["website", "invalid-action"])
        assert result.exit_code != 0


@pytest.mark.asyncio
class TestAsyncCLIComponents:
    """Test async components used by CLI."""

    async def test_async_command_wrapper(self):
        """Test async command wrapper functionality."""
        from src.webdeface.cli.main import async_command

        @async_command
        async def test_async_func():
            await asyncio.sleep(0.01)
            return "success"

        # This would be called by Click in real usage
        result = test_async_func()
        assert result == "success"
