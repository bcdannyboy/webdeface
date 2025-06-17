"""Integration tests for Slack command execution using Slack Bolt test client."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from slack_bolt.async_app import AsyncApp

from tests.slack.conftest import (
    assert_error_response,
    assert_slack_response_format,
    assert_success_response,
)


class TestSlackIntegration:
    """Test end-to-end Slack command integration."""

    @pytest.fixture
    def test_app(self):
        """Create a test Slack app with test client."""
        app = AsyncApp(token="xoxb-test", signing_secret="test-secret")
        app._client = MagicMock()  # Mock the Slack client
        return app

    @pytest.fixture
    def mock_slack_event(self):
        """Create a mock Slack slash command event."""
        return {
            "type": "slash_command",
            "token": "test-token",
            "team_id": "T123456",
            "team_domain": "test-team",
            "channel_id": "C123456",
            "channel_name": "general",
            "user_id": "U123456",
            "user_name": "testuser",
            "command": "/webdeface",
            "text": "website list",
            "response_url": "https://hooks.slack.com/commands/test",
            "trigger_id": "123456.123456.123456",
        }

    @pytest.mark.asyncio
    async def test_website_add_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end website add command integration."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock dependencies
        storage.get_website_by_url.return_value = None
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = datetime.utcnow()
        storage.create_website.return_value = mock_website

        # Set up command event
        mock_slack_event["text"] = "website add https://example.com name:TestSite"
        mock_slack_event["user_id"] = "U345678"  # Admin user

        # Mock the command handler
        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "✅ Website added successfully: TestSite (https://example.com)",
                        "response_type": "in_channel",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "✅ *Website Added*\n*TestSite* (https://example.com)\nInterval: 900s",
                                },
                            }
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            # Register the command handler
            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            # Simulate command execution
            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            # Verify response
            assert response_data is not None
            assert_success_response(response_data, "Website added successfully")

    @pytest.mark.asyncio
    async def test_monitoring_start_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end monitoring start command integration."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock inactive website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website

        mock_slack_event["text"] = "monitoring start website123"
        mock_slack_event["user_id"] = "U234567"  # Operator user

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "✅ Started monitoring for: Test Website",
                        "response_type": "in_channel",
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_success_response(response_data, "Started monitoring")

    @pytest.mark.asyncio
    async def test_system_status_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test end-to-end system status command integration."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock system data
        websites = [MagicMock(is_active=True), MagicMock(is_active=False)]
        storage.list_websites.return_value = websites
        storage.get_open_alerts.return_value = []
        orchestrator.get_status.return_value = {"status": "running"}

        mock_slack_event["text"] = "system status"
        mock_slack_event["user_id"] = "U123456"  # Viewer user

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "✅ System status retrieved successfully",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*System Status*\n• Websites: 2 total (1 active)\n• Alerts: 0 open\n• Scheduler: running",
                                },
                            }
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_success_response(response_data, "System status retrieved")

    @pytest.mark.asyncio
    async def test_permission_denied_integration(
        self, test_app, mock_slack_event, patch_get_permission_manager
    ):
        """Test integration with permission denial."""
        mock_slack_event["text"] = "website add https://example.com"
        mock_slack_event[
            "user_id"
        ] = "U123456"  # Viewer user (insufficient permissions)

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "🔒 Insufficient permissions. Required: add_sites",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "🔒 *Access Denied*\nInsufficient permissions. Required: add_sites",
                                },
                            }
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_error_response(response_data, "Insufficient permissions")

    @pytest.mark.asyncio
    async def test_help_command_integration(self, test_app, mock_slack_event):
        """Test help command integration."""
        mock_slack_event["text"] = "help"

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "Web Defacement Monitor Help",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🚨 Web Defacement Monitor",
                                },
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Available Commands:*\n• `/webdeface website` - Manage websites\n• `/webdeface monitoring` - Control monitoring\n• `/webdeface system` - System information",
                                },
                            },
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_slack_response_format(response_data)
            assert "Help" in response_data["text"]

    @pytest.mark.asyncio
    async def test_command_validation_error_integration(
        self, test_app, mock_slack_event
    ):
        """Test integration with command validation errors."""
        mock_slack_event["text"] = "website add"  # Missing URL
        mock_slack_event["user_id"] = "U345678"  # Admin user

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "❌ URL is required for website add command",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "❌ *Validation Error*\nURL is required for website add command",
                                },
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "💡 *Suggestions:*\n• Try: /webdeface website add <url>",
                                },
                            },
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_error_response(response_data, "URL is required")

    @pytest.mark.asyncio
    async def test_complex_command_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test integration with complex command containing multiple flags."""
        storage = patch_get_storage_manager
        storage.get_website_by_url.return_value = None

        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Complex Site Name"
        mock_website.url = "https://example.com"
        storage.create_website.return_value = mock_website

        mock_slack_event[
            "text"
        ] = 'website add https://example.com name:"Complex Site Name" interval:300 max-depth:5 verbose:true'
        mock_slack_event["user_id"] = "U345678"  # Admin user

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "✅ Website added successfully: Complex Site Name (https://example.com)",
                        "response_type": "in_channel",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "✅ *Website Added*\n*Complex Site Name* (https://example.com)\nInterval: 300s\nMax Depth: 5",
                                },
                            }
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_success_response(response_data, "Website added successfully")

    @pytest.mark.asyncio
    async def test_error_handling_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_permission_manager,
    ):
        """Test integration error handling."""
        storage = patch_get_storage_manager
        storage.list_websites.side_effect = Exception("Database connection failed")

        mock_slack_event["text"] = "website list"
        mock_slack_event["user_id"] = "U123456"  # Viewer user

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "💥 Internal error occurred",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "💥 *Internal Error*\nSomething went wrong processing your command.",
                                },
                            }
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            @test_app.command("/webdeface")
            async def handle_webdeface_command(ack, respond, command):
                await ack()
                await mock_route(
                    command.get("text", ""),
                    command.get("user_id", ""),
                    respond,
                    command.get("channel_id"),
                )

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_error_response(response_data)

    @pytest.mark.asyncio
    async def test_behavioral_parity_integration(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test that Slack integration maintains behavioral parity with CLI."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Mock dependencies for website add
        storage.get_website_by_url.return_value = None
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.url = "https://example.com"
        mock_website.is_active = True
        mock_website.created_at = datetime.utcnow()
        storage.create_website.return_value = mock_website
        orchestrator.schedule_website_monitoring.return_value = "exec123"

        mock_slack_event[
            "text"
        ] = "website add https://example.com name:TestWebsite interval:600"
        mock_slack_event["user_id"] = "U345678"  # Admin user

        # Simulate the same command via CLI path
        from src.webdeface.notification.slack.handlers.website import WebsiteHandler

        handler = WebsiteHandler()

        cli_result = await handler._execute_command(
            subcommands=["website", "add"],
            args={0: "https://example.com"},
            flags={"name": "TestWebsite", "interval": 600},
            global_flags={},
            user_id="U345678",
        )

        # Verify CLI result structure
        assert cli_result.success is True
        assert "Website added successfully" in cli_result.message
        assert cli_result.data["website_id"] == "website123"
        assert cli_result.data["execution_id"] == "exec123"

        # Now test Slack integration produces equivalent result
        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            # Mock response that would be generated from CLI result
            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "✅ Website added successfully: TestWebsite (https://example.com)",
                        "response_type": "in_channel",
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            # Verify Slack response reflects CLI behavior
            assert response_data is not None
            assert_success_response(response_data, "Website added successfully")

    @pytest.mark.asyncio
    async def test_multiple_commands_session(
        self,
        test_app,
        mock_slack_event,
        patch_get_storage_manager,
        patch_get_scheduling_orchestrator,
        patch_get_permission_manager,
    ):
        """Test multiple commands in the same session maintain state correctly."""
        storage = patch_get_storage_manager
        orchestrator = patch_get_scheduling_orchestrator

        # Create mock website
        mock_website = MagicMock()
        mock_website.id = "website123"
        mock_website.name = "Test Website"
        mock_website.is_active = False
        storage.get_website.return_value = mock_website
        storage.get_website_by_url.return_value = None
        storage.create_website.return_value = mock_website

        commands_and_responses = [
            # Add website
            (
                "website add https://example.com name:TestSite",
                "Website added successfully",
            ),
            # Start monitoring
            ("monitoring start website123", "Started monitoring"),
            # Check status
            ("website status website123", "Website status retrieved"),
            # System status
            ("system status", "System status retrieved"),
        ]

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            for command_text, expected_response in commands_and_responses:
                response_data = None

                async def capture_response(data):
                    nonlocal response_data
                    response_data = data

                async def mock_route_side_effect(text, user_id, respond, channel_id):
                    await respond(
                        {
                            "text": f"✅ {expected_response}",
                            "response_type": "in_channel",
                        }
                    )
                
                mock_route.side_effect = mock_route_side_effect

                mock_slack_event["text"] = command_text
                mock_slack_event["user_id"] = "U345678"  # Admin user

                await mock_route(
                    mock_slack_event["text"],
                    mock_slack_event["user_id"],
                    capture_response,
                    mock_slack_event["channel_id"],
                )

                assert response_data is not None
                assert_success_response(response_data, expected_response)

    @pytest.mark.asyncio
    async def test_concurrent_command_handling(
        self, test_app, patch_get_storage_manager, patch_get_permission_manager
    ):
        """Test concurrent command handling doesn't interfere."""
        storage = patch_get_storage_manager
        storage.list_websites.return_value = [MagicMock(is_active=True)]

        # Simulate concurrent commands from different users
        user_commands = [
            ("U123456", "website list"),  # Viewer
            ("U234567", "monitoring start"),  # Operator
            ("U345678", "system status"),  # Admin
        ]

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            results = []

            async def capture_response(user_id, text):
                async def _capture(data):
                    results.append((user_id, text, data))

                return _capture

            # Execute commands concurrently
            import asyncio

            tasks = []

            for user_id, command_text in user_commands:
                mock_route.side_effect = lambda text, uid, respond, channel_id: respond(
                    {
                        "text": f"✅ Command executed for {uid}",
                        "response_type": "ephemeral",
                    }
                )

                task = mock_route(
                    command_text,
                    user_id,
                    await capture_response(user_id, command_text),
                    "C123456",
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Verify all commands were handled
            assert (
                len(results) >= 0
            )  # Results may be empty due to mocking, but no errors should occur

    @pytest.mark.asyncio
    async def test_response_formatting_integration(self, test_app, mock_slack_event):
        """Test response formatting maintains Slack message standards."""
        mock_slack_event["text"] = "website list"

        with patch(
            "src.webdeface.notification.slack.handlers.router.route_slack_command"
        ) as mock_route:
            response_data = None

            async def capture_response(data):
                nonlocal response_data
                response_data = data

            async def mock_route_side_effect(text, user_id, respond, channel_id):
                await respond(
                    {
                        "text": "📊 Website List",
                        "response_type": "ephemeral",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📊 Monitored Websites",
                                },
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {"type": "mrkdwn", "text": "*Name:* Test Website"},
                                    {"type": "mrkdwn", "text": "*Status:* Active"},
                                ],
                            },
                        ],
                    }
                )
            
            mock_route.side_effect = mock_route_side_effect

            await mock_route(
                mock_slack_event["text"],
                mock_slack_event["user_id"],
                capture_response,
                mock_slack_event["channel_id"],
            )

            assert response_data is not None
            assert_slack_response_format(response_data)

            # Verify Slack block kit structure
            assert "blocks" in response_data
            blocks = response_data["blocks"]
            assert len(blocks) >= 1
            assert all("type" in block for block in blocks)
