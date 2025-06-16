"""Tests for Slack website management commands."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.webdeface.notification.slack.permissions import Permission
from tests.slack.conftest import (
    assert_error_response,
    assert_success_response,
)


class TestWebsiteHandler:
    """Test website command handler."""

    @pytest.mark.asyncio
    async def test_website_add_success(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test successful website add command."""
        # Mock dependencies
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator
        storage.get_website_by_url.return_value = None  # Website doesn't exist

        # Mock website creation
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = datetime.utcnow()
        storage.create_website.return_value = mock_website

        # Execute command
        await website_handler.handle_command(
            text="website add https://example.com name:TestSite interval:600",
            user_id="U345678",  # Admin user
            respond=mock_slack_response,
            channel_id="C123456",
        )

        # Verify response
        assert len(mock_slack_response.responses) == 1
        response = mock_slack_response.last_response
        assert_success_response(response, "Website added successfully")

        # Verify storage calls
        storage.get_website_by_url.assert_called_once_with("https://example.com")
        storage.create_website.assert_called_once()
        orchestrator.schedule_website_monitoring.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_website_add_duplicate_url(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test website add with duplicate URL."""
        storage = patch_get_storage_manager

        # Mock existing website
        existing_website = MagicMock()
        existing_website.name = "Existing Website"
        storage.get_website_by_url.return_value = existing_website

        await website_handler.handle_command(
            text="website add https://example.com",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Website already exists")

    @pytest.mark.asyncio
    async def test_website_add_permission_denied(
        self, website_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test website add with insufficient permissions."""
        await website_handler.handle_command(
            text="website add https://example.com",
            user_id="U123456",  # Viewer user
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_website_add_invalid_url(
        self, website_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test website add with invalid URL."""
        await website_handler.handle_command(
            text="website add invalid-url",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response)

    @pytest.mark.asyncio
    async def test_website_add_missing_url(
        self, website_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test website add without URL argument."""
        await website_handler.handle_command(
            text="website add", user_id="U345678", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "URL is required")

    @pytest.mark.asyncio
    async def test_website_remove_success(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test successful website remove command."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock existing website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        storage.get_website.return_value = mock_website

        await website_handler.handle_command(
            text="website remove website123",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website removed successfully")

        # Verify storage calls
        storage.get_website.assert_called_once_with("website123")
        orchestrator.unschedule_website_monitoring.assert_called_once_with("website123")
        storage.delete_website.assert_called_once_with("website123")

    @pytest.mark.asyncio
    async def test_website_remove_not_found(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test website remove with non-existent website."""
        storage = patch_get_storage_manager
        storage.get_website.return_value = None

        await website_handler.handle_command(
            text="website remove nonexistent",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Website not found")

    @pytest.mark.asyncio
    async def test_website_list_success(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test successful website list command."""
        storage = patch_get_storage_manager

        # Mock websites
        websites = [
            MagicMock(
                id="web1",
                name="Site 1",
                url="https://site1.com",
                is_active=True,
                created_at=datetime.utcnow(),
                last_checked_at=datetime.utcnow(),
                check_interval_seconds=900,
            ),
            MagicMock(
                id="web2",
                name="Site 2",
                url="https://site2.com",
                is_active=False,
                created_at=datetime.utcnow(),
                last_checked_at=None,
                check_interval_seconds=600,
            ),
        ]
        storage.list_websites.return_value = websites

        await website_handler.handle_command(
            text="website list",
            user_id="U123456",  # Viewer can list
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Found 2 websites")
        storage.list_websites.assert_called_once()

    @pytest.mark.asyncio
    async def test_website_list_with_filters(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test website list with status filter."""
        storage = patch_get_storage_manager

        active_website = MagicMock(
            id="web1",
            name="Active Site",
            url="https://active.com",
            is_active=True,
            created_at=datetime.utcnow(),
            last_checked_at=datetime.utcnow(),
            check_interval_seconds=900,
        )
        storage.list_websites.return_value = [active_website]

        await website_handler.handle_command(
            text="website list status:active format:json",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Found 1 websites")

    @pytest.mark.asyncio
    async def test_website_status_success(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test successful website status command."""
        storage = patch_get_storage_manager

        # Mock website and related data
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = datetime.utcnow()
        mock_website.last_checked_at = datetime.utcnow()
        mock_website.check_interval_seconds = 900
        storage.get_website.return_value = mock_website

        # Mock snapshots and alerts
        storage.get_website_snapshots.return_value = []
        storage.get_website_alerts.return_value = []

        await website_handler.handle_command(
            text="website status website123",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website status retrieved")

        storage.get_website.assert_called_once_with("website123")
        storage.get_website_snapshots.assert_called_once_with("website123", limit=5)
        storage.get_website_alerts.assert_called_once_with("website123", limit=5)

    @pytest.mark.asyncio
    async def test_website_status_not_found(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test website status with non-existent website."""
        storage = patch_get_storage_manager
        storage.get_website.return_value = None

        await website_handler.handle_command(
            text="website status nonexistent",
            user_id="U123456",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Website not found")

    @pytest.mark.asyncio
    async def test_get_required_permissions(self, website_handler):
        """Test permission requirements for website commands."""
        # Test add command permissions
        add_perms = website_handler.get_required_permissions(["website", "add"])
        assert Permission.ADD_SITES in add_perms

        # Test remove command permissions
        remove_perms = website_handler.get_required_permissions(["website", "remove"])
        assert Permission.REMOVE_SITES in remove_perms

        # Test list command permissions
        list_perms = website_handler.get_required_permissions(["website", "list"])
        assert Permission.VIEW_SITES in list_perms

        # Test status command permissions
        status_perms = website_handler.get_required_permissions(["website", "status"])
        assert Permission.VIEW_SITES in status_perms

    @pytest.mark.asyncio
    async def test_unknown_website_command(
        self, website_handler, mock_slack_response, patch_get_permission_manager
    ):
        """Test handling of unknown website subcommand."""
        await website_handler.handle_command(
            text="website unknown", user_id="U345678", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Unknown website command")

    @pytest.mark.asyncio
    async def test_website_command_exception_handling(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test exception handling in website commands."""
        storage = patch_get_storage_manager
        storage.list_websites.side_effect = Exception("Database error")

        await website_handler.handle_command(
            text="website list", user_id="U123456", respond=mock_slack_response
        )

        response = mock_slack_response.last_response
        assert_error_response(response, "Command failed")

    @pytest.mark.asyncio
    async def test_website_add_with_protocol_auto_detection(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test website add with automatic protocol detection."""
        storage = patch_get_storage_manager
        storage.get_website_by_url.return_value = None

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "example.com"
        mock_website.url = "https://example.com"
        storage.create_website.return_value = mock_website

        await website_handler.handle_command(
            text="website add example.com",
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website added successfully")

    @pytest.mark.asyncio
    async def test_website_add_with_custom_flags(
        self,
        website_handler,
        mock_slack_response,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test website add with custom name and interval flags."""
        storage = patch_get_storage_manager
        storage.get_website_by_url.return_value = None

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Custom Site Name"
        mock_website.url = "https://example.com"
        storage.create_website.return_value = mock_website

        await website_handler.handle_command(
            text='website add https://example.com name:"Custom Site Name" interval:300',
            user_id="U345678",
            respond=mock_slack_response,
        )

        response = mock_slack_response.last_response
        assert_success_response(response, "Website added successfully")

    @pytest.mark.asyncio
    async def test_behavioral_parity_with_cli(
        self,
        website_handler,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test that Slack commands produce same results as CLI equivalents."""
        storage = patch_get_storage_manager
        storage.get_website_by_url.return_value = None

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        storage.create_website.return_value = mock_website

        # Execute website add via handler's _execute_command (simulates CLI path)
        result = await website_handler._execute_command(
            subcommands=["website", "add"],
            args={0: "https://example.com"},
            flags={"name": "Test Website", "interval": 600},
            global_flags={},
            user_id="U345678",
        )

        # Verify result matches expected CLI behavior
        assert result.success is True
        assert "Website added successfully" in result.message
        assert result.data["website_id"] == "website123"
        assert result.data["website"]["name"] == "Test Website"
        assert result.data["website"]["url"] == "https://example.com"
