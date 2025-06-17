"""Test configuration and fixtures for webdeface test suite."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Global patches to prevent real service connections at import time
def pytest_configure(config):
    """Configure pytest with global patches to prevent external service connections."""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Apply patches that prevent external service connections during imports
@pytest.fixture(scope="session", autouse=True)
def global_service_patches():
    """Apply global patches to prevent external service connections during test runs."""
    with patch(
        "src.webdeface.config.loader.ConfigLoader.load_yaml_config"
    ) as mock_config, patch(
        "src.webdeface.storage.sqlite.database.create_async_engine"
    ) as mock_engine, patch(
        "src.webdeface.storage.sqlite.database.get_database_manager"
    ) as mock_get_db_manager, patch(
        "src.webdeface.storage.get_storage_manager"
    ) as mock_get_storage_manager, patch(
        "src.webdeface.storage.qdrant.client.AsyncQdrantClient"
    ) as mock_qdrant_client, patch(
        "src.webdeface.classifier.claude.AsyncAnthropic"
    ) as mock_anthropic, patch(
        "src.webdeface.classifier.vectorizer.SentenceTransformer"
    ) as mock_transformer, patch(
        "src.webdeface.scraper.browser.async_playwright"
    ) as mock_playwright, patch(
        "slack_bolt.async_app.AsyncApp"
    ) as mock_slack_app, patch(
        "builtins.open", side_effect=FileNotFoundError("Test mode - no config file")
    ):
        # Mock config loader to return empty config
        mock_config.return_value = {}

        # Mock database engine with proper async mock
        mock_async_engine = AsyncMock()
        mock_async_engine.sync_engine = AsyncMock()
        mock_async_engine.dispose = AsyncMock()
        mock_async_engine.begin = AsyncMock()
        mock_engine.return_value = mock_async_engine

        # Mock database manager
        mock_db_manager = AsyncMock()
        mock_db_manager._initialized = True
        mock_db_manager.engine = mock_async_engine
        mock_db_manager.session_factory = AsyncMock()
        mock_db_manager.setup = AsyncMock()
        mock_db_manager.cleanup = AsyncMock()
        mock_db_manager.health_check = AsyncMock(return_value=True)
        mock_db_manager.get_session = AsyncMock()
        mock_db_manager.get_transaction = AsyncMock()
        mock_get_db_manager.return_value = mock_db_manager

        # Mock storage manager
        mock_storage_manager = AsyncMock()
        mock_storage_manager.setup = AsyncMock()
        mock_storage_manager.cleanup = AsyncMock()
        mock_storage_manager.health_check = AsyncMock(return_value=True)
        mock_get_storage_manager.return_value = mock_storage_manager

        # Mock Qdrant client
        mock_qdrant_instance = AsyncMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        # Mock Claude/Anthropic client
        mock_anthropic_instance = AsyncMock()
        mock_anthropic.return_value = mock_anthropic_instance

        # Mock sentence transformer
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = [0.1] * 384
        mock_transformer.return_value = mock_model

        # Mock playwright
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value = mock_playwright_instance

        # Mock Slack app
        mock_slack_instance = AsyncMock()
        mock_slack_app.return_value = mock_slack_instance

        yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_settings():
    """Create test settings for use across test session."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Mock settings object
        mock_settings = Mock()
        mock_settings.database_url = f"sqlite:///{temp_path}/test.db"
        mock_settings.storage_path = str(temp_path)
        mock_settings.log_level = "DEBUG"
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.development = True
        mock_settings.api_tokens = ["test-token-123"]

        # Database settings
        mock_database = Mock()
        mock_database.url = f"sqlite+aiosqlite:///{temp_path}/test.db"
        mock_database.echo = False
        mock_database.pool_size = 5
        mock_database.max_overflow = 10
        mock_settings.database = mock_database

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

        yield mock_settings


@pytest_asyncio.fixture
async def mock_storage_manager():
    """Create a mock storage manager for tests."""
    mock_storage = AsyncMock()

    # Mock database manager
    mock_db = AsyncMock()
    mock_db.health_check.return_value = True
    mock_db.get_table_info.return_value = {"websites": {"row_count": 0}}
    mock_storage.db_manager = mock_db

    # Mock Qdrant manager
    mock_qdrant = AsyncMock()
    mock_qdrant.health_check.return_value = True
    mock_qdrant.get_collection_info.return_value = {"vectors_count": 0}
    mock_storage.qdrant_manager = mock_qdrant

    # Mock methods
    mock_storage.setup.return_value = None
    mock_storage.cleanup.return_value = None
    mock_storage.health_check.return_value = True

    # Mock website and snapshot operations
    mock_website = Mock()
    mock_website.id = "test-website-id"
    mock_website.url = "https://example.com"
    mock_website.name = "Test Website"

    mock_snapshot = Mock()
    mock_snapshot.id = "test-snapshot-id"
    mock_snapshot.website_id = "test-website-id"
    mock_snapshot.content_hash = "test-hash"
    mock_snapshot.content_text = "Test content"

    mock_storage.create_website.return_value = mock_website
    mock_storage.get_website.return_value = mock_website
    mock_storage.create_snapshot.return_value = mock_snapshot
    mock_storage.get_latest_snapshot.return_value = None

    return mock_storage


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for storage tests."""
    mock_db_manager = AsyncMock()

    # Mock basic properties
    mock_db_manager._initialized = True
    mock_db_manager.engine = AsyncMock()
    mock_db_manager.session_factory = AsyncMock()

    # Mock async context manager for sessions
    mock_session = AsyncMock()
    mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
    mock_db_manager.get_transaction.return_value.__aenter__.return_value = mock_session

    # Mock methods
    mock_db_manager.setup.return_value = None
    mock_db_manager.cleanup.return_value = None
    mock_db_manager.health_check.return_value = True
    mock_db_manager.get_table_info.return_value = {
        "websites": {"row_count": 5},
        "website_snapshots": {"row_count": 10},
        "defacement_alerts": {"row_count": 2},
    }

    return mock_db_manager


@pytest.fixture
def mock_qdrant_manager():
    """Create a mock Qdrant manager for storage tests."""
    mock_qdrant_manager = AsyncMock()

    # Mock basic properties
    mock_qdrant_manager._initialized = True
    mock_qdrant_manager.client = AsyncMock()

    # Mock methods
    mock_qdrant_manager.setup.return_value = None
    mock_qdrant_manager.cleanup.return_value = None
    mock_qdrant_manager.health_check.return_value = True
    mock_qdrant_manager.get_collection_info.return_value = {
        "status": "green",
        "vectors_count": 100,
        "points_count": 100,
        "segments_count": 1,
    }

    # Mock vector operations
    mock_qdrant_manager.add_vectors.return_value = ["vector-id-123", "vector-id-456"]
    mock_qdrant_manager.search_similar.return_value = [
        ("vector-id-123", 0.95, {"website_id": "test", "content_hash": "abc123"})
    ]
    mock_qdrant_manager.delete_vectors.return_value = True
    mock_qdrant_manager.count_vectors.return_value = 100

    return mock_qdrant_manager


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    mock_session = AsyncMock()

    # Mock session operations
    mock_session.add = Mock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.begin = AsyncMock()

    # Mock query results
    mock_result = Mock()
    mock_result.scalar.return_value = 1
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    return mock_session


@pytest.fixture
def storage_test_settings():
    """Create storage-specific test settings."""
    from src.webdeface.config.settings import DatabaseSettings, QdrantSettings

    # Database settings for in-memory SQLite
    db_settings = DatabaseSettings(
        url="sqlite+aiosqlite:///:memory:", echo=False, pool_size=5, max_overflow=10
    )

    # Qdrant settings for testing
    qdrant_settings = QdrantSettings(
        url="http://localhost:6333",
        collection_name="test_collection",
        vector_size=384,
        distance="Cosine",
    )

    return {"database": db_settings, "qdrant": qdrant_settings}


@pytest_asyncio.fixture
async def mock_claude_client():
    """Create a mock Claude client for tests."""
    mock_client = AsyncMock()

    # Mock response
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text='{"classification": "benign", "confidence": 0.8, "reasoning": "Test reasoning"}'
        )
    ]
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50

    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest_asyncio.fixture
async def mock_vectorizer():
    """Create a mock content vectorizer for tests."""
    mock_vectorizer = Mock()

    # Mock the model
    mock_model = Mock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = [0.1] * 384  # Simple list instead of numpy array
    mock_vectorizer.model = mock_model
    mock_vectorizer.model_name = "test-model"

    # Mock vectorization method
    async def mock_vectorize_content(content, content_type="text", metadata=None):
        import hashlib
        from datetime import datetime

        from src.webdeface.classifier.types import ContentVector

        return ContentVector(
            vector=[0.1] * 384,
            content_hash=hashlib.blake2b(
                content.encode("utf-8"), digest_size=16
            ).hexdigest(),
            content_type=content_type,
            model_name="test-model",
            vector_size=384,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    mock_vectorizer.vectorize_content = mock_vectorize_content

    return mock_vectorizer


@pytest_asyncio.fixture
async def mock_scheduler_manager():
    """Create a mock scheduler manager for tests."""
    mock_scheduler = AsyncMock()

    # Mock APScheduler instance
    mock_apscheduler = Mock()
    mock_apscheduler.start = Mock()
    mock_apscheduler.shutdown = Mock()
    mock_apscheduler.add_job = Mock(return_value=Mock())
    mock_scheduler.scheduler = mock_apscheduler

    # Mock properties
    mock_scheduler.is_running = True
    mock_scheduler.start_time = None
    mock_scheduler._current_job_count = 0
    mock_scheduler._max_concurrent_jobs = 10
    mock_scheduler._job_semaphore = AsyncMock()

    # Mock methods
    mock_scheduler.setup.return_value = None
    mock_scheduler.cleanup.return_value = None
    mock_scheduler.schedule_job.return_value = "exec-test-123"
    mock_scheduler.health_check.return_value = [
        Mock(component="scheduler", healthy=True, message="Scheduler is running"),
        Mock(component="job_queue", healthy=True, message="Queue is healthy"),
    ]

    return mock_scheduler


@pytest_asyncio.fixture
async def mock_workflow_engine():
    """Create a mock workflow engine for tests."""
    mock_engine = AsyncMock()

    mock_engine.is_running = True
    mock_engine._workflow_definitions = {}
    mock_engine._active_workflows = {}

    # Mock methods
    mock_engine.setup.return_value = None
    mock_engine.cleanup.return_value = None
    mock_engine.execute_workflow.return_value = "exec-workflow-123"
    mock_engine.list_active_workflows.return_value = []

    return mock_engine


@pytest_asyncio.fixture
async def mock_health_monitor():
    """Create a mock health monitor for tests."""
    mock_monitor = AsyncMock()

    mock_monitor.is_running = True
    mock_monitor._monitoring_task = None
    mock_monitor._health_checks = {}

    # Mock system metrics
    mock_metrics = Mock()
    mock_metrics.cpu_percent = 25.0
    mock_metrics.memory_percent = 60.0
    mock_metrics.memory_available_gb = 4.0
    mock_metrics.disk_usage_percent = 50.0
    mock_metrics.disk_free_gb = 50.0
    mock_metrics.load_average = [1.0, 2.0, 3.0]

    # Mock methods
    mock_monitor.setup.return_value = None
    mock_monitor.cleanup.return_value = None
    mock_monitor._collect_system_metrics.return_value = mock_metrics
    mock_monitor.generate_monitoring_report.return_value = Mock(
        report_id="test-report-123",
        generated_at=Mock(),
        system_metrics=mock_metrics,
        component_health={},
    )

    return mock_monitor


@pytest.fixture
def mock_browser_manager():
    """Create a mock browser manager for tests."""
    mock_browser = Mock()

    # Mock playwright setup
    mock_playwright = AsyncMock()
    mock_browser_instance = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_playwright.chromium.launch.return_value = mock_browser_instance
    mock_browser_instance.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_browser.playwright = mock_playwright
    mock_browser.browser = mock_browser_instance
    mock_browser.setup.return_value = None
    mock_browser.cleanup.return_value = None

    return mock_browser


@pytest_asyncio.fixture
async def setup_test_environment(
    test_settings, mock_storage_manager, mock_claude_client, mock_vectorizer
):
    """Set up complete test environment with all mocked dependencies."""
    # Patch global functions and classes
    with patch(
        "src.webdeface.config.settings.get_settings", return_value=test_settings
    ), patch(
        "src.webdeface.storage.get_storage_manager", return_value=mock_storage_manager
    ), patch(
        "src.webdeface.classifier.claude.AsyncAnthropic",
        return_value=mock_claude_client,
    ), patch(
        "src.webdeface.classifier.vectorizer.SentenceTransformer"
    ), patch(
        "src.webdeface.scraper.browser.async_playwright"
    ) as mock_playwright:
        # Mock playwright
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value = mock_playwright_instance
        mock_playwright_instance.start.return_value = mock_playwright_instance

        yield {
            "settings": test_settings,
            "storage": mock_storage_manager,
            "claude": mock_claude_client,
            "vectorizer": mock_vectorizer,
        }


# Async cleanup helper for orchestrators
@pytest_asyncio.fixture(scope="function", autouse=True)
async def async_cleanup():
    """Ensure proper async cleanup for each test."""
    yield
    # Cleanup happens automatically via pytest-asyncio
    # No manual event loop manipulation needed


# Mark all tests as asyncio by default for this test suite
def pytest_collection_modifyitems(config, items):
    """Automatically mark async tests with asyncio marker."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Set pytest-asyncio mode to auto
pytest_asyncio_mode = "auto"
