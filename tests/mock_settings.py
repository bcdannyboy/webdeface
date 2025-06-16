"""Mock settings for testing to prevent external service connections."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock


def create_mock_settings():
    """Create comprehensive mock settings that prevent all external service connections."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        mock_settings = Mock()

        # Basic settings
        mock_settings.development = True
        mock_settings.log_level = "DEBUG"
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.api_tokens = ["test-token-123"]
        mock_settings.storage_path = str(temp_path)

        # Database settings
        mock_database = Mock()
        mock_database.url = f"sqlite+aiosqlite:///{temp_path}/test.db"
        mock_database.echo = False
        mock_database.pool_size = 5
        mock_database.max_overflow = 10
        mock_settings.database = mock_database
        mock_settings.database_url = f"sqlite:///{temp_path}/test.db"

        # Claude settings
        mock_claude = Mock()
        mock_claude.api_key = Mock()
        mock_claude.api_key.get_secret_value.return_value = "test-claude-key"
        mock_claude.model = "claude-3-sonnet-20240229"
        mock_claude.max_tokens = 4000
        mock_claude.temperature = 0.1
        mock_settings.claude = mock_claude

        # Qdrant settings
        mock_qdrant = Mock()
        mock_qdrant.url = "http://localhost:6333"
        mock_qdrant.api_key = None
        mock_qdrant.collection_name = "test_vectors"
        mock_qdrant.vector_size = 384
        mock_qdrant.distance = "Cosine"
        mock_settings.qdrant = mock_qdrant

        # Slack settings
        mock_slack = Mock()
        mock_slack.bot_token = Mock()
        mock_slack.bot_token.get_secret_value.return_value = "test-slack-token"
        mock_slack.app_token = Mock()
        mock_slack.app_token.get_secret_value.return_value = "test-app-token"
        mock_slack.signing_secret = Mock()
        mock_slack.signing_secret.get_secret_value.return_value = "test-signing-secret"
        mock_slack.allowed_users = ["U123456", "U789012"]
        mock_settings.slack = mock_slack

        # Logging settings
        mock_logging = Mock()
        mock_logging.level = "DEBUG"
        mock_logging.json_logs = False
        mock_settings.logging = mock_logging

        return mock_settings


def create_mock_async_managers():
    """Create mock async managers to prevent service connections."""
    return {
        "storage_manager": AsyncMock(),
        "database_manager": AsyncMock(),
        "qdrant_manager": AsyncMock(),
        "slack_manager": AsyncMock(),
        "scheduler_manager": AsyncMock(),
        "workflow_engine": AsyncMock(),
        "health_monitor": AsyncMock(),
        "orchestrator": AsyncMock(),
        "browser_pool": AsyncMock(),
        "classification_pipeline": AsyncMock(),
        "alert_generator": AsyncMock(),
        "feedback_collector": AsyncMock(),
        "performance_tracker": AsyncMock(),
    }
