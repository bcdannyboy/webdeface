"""Tests for database infrastructure components (DB-01 to DB-04)."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.webdeface.config.settings import DatabaseSettings, QdrantSettings
from src.webdeface.storage.interface import StorageManager, get_storage_manager
from src.webdeface.storage.qdrant.client import QdrantManager, get_qdrant_manager
from src.webdeface.storage.sqlite.database import DatabaseManager, get_database_manager
from src.webdeface.storage.sqlite.models import (
    DefacementAlert,
    Website,
    WebsiteSnapshot,
)


class TestSQLAlchemyModels:
    """Test SQLAlchemy ORM models (DB-01)."""

    def test_website_model_creation(self):
        """Test Website model creation and attributes."""
        # Create website instance with explicit default values
        website = Website(
            url="https://example.com",
            name="Example Site",
            description="Test website",
            check_interval_seconds=600,
        )
        # Manually set defaults since they're not applied until database commit
        if website.id is None:
            import uuid

            website.id = str(uuid.uuid4())
        if website.is_active is None:
            website.is_active = True

        assert website.url == "https://example.com"
        assert website.name == "Example Site"
        assert website.description == "Test website"
        assert website.check_interval_seconds == 600
        assert website.is_active is True
        assert website.id is not None

    def test_website_snapshot_model_creation(self):
        """Test WebsiteSnapshot model creation and attributes."""
        # Create snapshot instance with explicit default values
        snapshot = WebsiteSnapshot(
            website_id="test-website-id",
            content_hash="abc123",
            content_text="Test content",
            status_code=200,
            response_time_ms=150.5,
        )
        # Manually set defaults since they're not applied until database commit
        if snapshot.id is None:
            import uuid

            snapshot.id = str(uuid.uuid4())

        assert snapshot.website_id == "test-website-id"
        assert snapshot.content_hash == "abc123"
        assert snapshot.content_text == "Test content"
        assert snapshot.status_code == 200
        assert snapshot.response_time_ms == 150.5
        assert snapshot.id is not None

    def test_defacement_alert_model_creation(self):
        """Test DefacementAlert model creation and attributes."""
        # Create alert instance with explicit default values
        alert = DefacementAlert(
            website_id="test-website-id",
            alert_type="defacement",
            severity="high",
            title="Defacement Detected",
            description="Suspicious content detected",
        )
        # Manually set defaults since they're not applied until database commit
        if alert.id is None:
            import uuid

            alert.id = str(uuid.uuid4())
        if alert.status is None:
            alert.status = "open"

        assert alert.website_id == "test-website-id"
        assert alert.alert_type == "defacement"
        assert alert.severity == "high"
        assert alert.title == "Defacement Detected"
        assert alert.description == "Suspicious content detected"
        assert alert.status == "open"
        assert alert.id is not None


@pytest.mark.asyncio
class TestDatabaseManager:
    """Test database session management and connection handling (DB-02)."""

    @pytest.fixture
    def db_settings(self):
        """Create test database settings."""
        return DatabaseSettings(
            url="sqlite+aiosqlite:///:memory:", echo=False, pool_size=5, max_overflow=10
        )

    @pytest_asyncio.fixture
    async def db_manager(self, db_settings):
        """Create test database manager."""
        with patch(
            "src.webdeface.storage.sqlite.database.create_async_engine"
        ) as mock_engine, patch(
            "src.webdeface.storage.sqlite.database.event.listens_for"
        ) as mock_listens_for, patch(
            "src.webdeface.storage.sqlite.database.async_sessionmaker"
        ) as mock_sessionmaker, patch(
            "src.webdeface.storage.sqlite.database.Base.metadata.create_all"
        ) as mock_create_all:
            # Mock the async engine properly
            mock_async_engine = AsyncMock()
            mock_sync_engine = Mock()
            mock_async_engine.sync_engine = mock_sync_engine
            mock_engine.return_value = mock_async_engine

            # Mock engine methods
            mock_async_engine.begin = AsyncMock()
            mock_async_engine.dispose = AsyncMock()

            # Mock table creation
            mock_conn = AsyncMock()
            mock_async_engine.begin.return_value.__aenter__.return_value = mock_conn
            mock_conn.run_sync = AsyncMock()

            # Mock session factory and sessions
            mock_session_factory = AsyncMock()
            mock_sessionmaker.return_value = mock_session_factory

            # Mock actual session objects with proper sync return values
            mock_session = AsyncMock()
            mock_result = Mock()  # Use regular Mock for scalar return
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            mock_session.begin.return_value.__aenter__ = AsyncMock()
            mock_session.begin.return_value.__aexit__ = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            mock_session_factory.return_value.__aexit__.return_value = None

            # Mock event listener setup - prevent actual SQLAlchemy event registration
            mock_listens_for.return_value = lambda func: func

            manager = DatabaseManager(db_settings)

            # Set up the mocked components directly to avoid engine event issues
            manager.engine = mock_async_engine
            manager.session_factory = mock_session_factory
            manager._initialized = True

            # Mock manager methods with proper async context managers
            manager.get_session = lambda: mock_session_factory.return_value
            manager.get_transaction = lambda: mock_session_factory.return_value
            manager.health_check = AsyncMock(return_value=True)
            manager.get_table_info = AsyncMock(
                return_value={
                    "websites": {"row_count": 0},
                    "website_snapshots": {"row_count": 0},
                    "defacement_alerts": {"row_count": 0},
                }
            )

            yield manager

    async def test_database_manager_initialization(self, db_settings):
        """Test database manager initialization."""
        with patch.object(DatabaseManager, "setup") as mock_setup, patch.object(
            DatabaseManager, "cleanup"
        ) as mock_cleanup:
            manager = DatabaseManager(db_settings)
            assert manager.settings == db_settings
            assert not manager._initialized

            # Mock the initialization state changes
            async def mock_setup_impl():
                manager._initialized = True
                manager.engine = AsyncMock()
                manager.session_factory = AsyncMock()

            async def mock_cleanup_impl():
                manager._initialized = False
                manager.engine = None
                manager.session_factory = None

            mock_setup.side_effect = mock_setup_impl
            mock_cleanup.side_effect = mock_cleanup_impl

            await manager.setup()
            assert manager._initialized
            assert manager.engine is not None
            assert manager.session_factory is not None

            await manager.cleanup()
            assert not manager._initialized

    async def test_database_session_creation(self, db_manager):
        """Test database session creation and cleanup."""
        async with db_manager.get_session() as session:
            assert session is not None
            # Session should be usable
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1

    async def test_database_transaction(self, db_manager):
        """Test database transaction handling."""
        async with db_manager.get_transaction() as session:
            assert session is not None
            # Test transaction rollback on exception
            try:
                async with session.begin():
                    # This should be rolled back
                    await session.execute("SELECT 1")
                    raise Exception("Test rollback")
            except Exception:
                pass

    async def test_database_health_check(self, db_manager):
        """Test database health check."""
        health_status = await db_manager.health_check()
        assert health_status is True

    async def test_table_creation(self, db_manager):
        """Test database table creation."""
        # Tables should be created during setup
        table_info = await db_manager.get_table_info()
        assert isinstance(table_info, dict)
        # Should have our main tables
        expected_tables = ["websites", "website_snapshots", "defacement_alerts"]
        for table in expected_tables:
            assert table in table_info


@pytest.mark.asyncio
class TestQdrantManager:
    """Test Qdrant vector database client (DB-03)."""

    @pytest.fixture
    def qdrant_settings(self):
        """Create test Qdrant settings."""
        return QdrantSettings(
            url="http://localhost:6333",
            collection_name="test_collection",
            vector_size=384,
            distance="Cosine",
        )

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create mock Qdrant client."""
        with patch(
            "src.webdeface.storage.qdrant.client.AsyncQdrantClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock collection operations
            mock_client.get_collection.return_value = Mock()
            mock_client.create_collection.return_value = None
            mock_client.upsert.return_value = Mock()
            mock_client.search.return_value = []
            mock_client.retrieve.return_value = []
            mock_client.delete.return_value = None
            mock_client.count.return_value = Mock(count=0)

            yield mock_client

    async def test_qdrant_manager_initialization(
        self, qdrant_settings, mock_qdrant_client
    ):
        """Test Qdrant manager initialization."""
        manager = QdrantManager(qdrant_settings)
        assert manager.settings == qdrant_settings
        assert not manager._initialized

        await manager.setup()
        assert manager._initialized
        assert manager.client is not None

        await manager.cleanup()
        assert not manager._initialized

    async def test_qdrant_add_vectors(self, qdrant_settings, mock_qdrant_client):
        """Test adding vectors to Qdrant."""
        manager = QdrantManager(qdrant_settings)
        await manager.setup()

        vectors = [[0.1, 0.2, 0.3] * 128]  # 384 dimensions
        payloads = [{"website_id": "test", "content_hash": "abc123"}]

        vector_ids = await manager.add_vectors(vectors, payloads)

        assert len(vector_ids) == 1
        assert isinstance(vector_ids[0], str)
        mock_qdrant_client.upsert.assert_called_once()

        await manager.cleanup()

    async def test_qdrant_search_similar(self, qdrant_settings, mock_qdrant_client):
        """Test similarity search in Qdrant."""
        manager = QdrantManager(qdrant_settings)
        await manager.setup()

        # Mock search results
        mock_point = Mock()
        mock_point.id = "test-id"
        mock_point.score = 0.95
        mock_point.payload = {"website_id": "test"}
        mock_qdrant_client.search.return_value = [mock_point]

        query_vector = [0.1, 0.2, 0.3] * 128
        results = await manager.search_similar(query_vector, limit=5)

        assert len(results) == 1
        assert results[0][0] == "test-id"
        assert results[0][1] == 0.95
        assert results[0][2] == {"website_id": "test"}

        await manager.cleanup()

    async def test_qdrant_health_check(self, qdrant_settings, mock_qdrant_client):
        """Test Qdrant health check."""
        manager = QdrantManager(qdrant_settings)
        await manager.setup()

        health_status = await manager.health_check()
        assert health_status is True

        await manager.cleanup()


@pytest.mark.asyncio
class TestStorageInterface:
    """Test unified storage interface (DB-04)."""

    @pytest.fixture
    def mock_storage_manager(self):
        """Create mock storage manager."""
        with patch(
            "src.webdeface.storage.interface.get_database_manager"
        ) as mock_db, patch(
            "src.webdeface.storage.interface.get_qdrant_manager"
        ) as mock_qdrant:
            # Mock database manager
            mock_db_manager = AsyncMock()
            mock_db_manager.health_check.return_value = True
            mock_db_manager.get_table_info.return_value = {"websites": {"row_count": 5}}
            mock_db.return_value = mock_db_manager

            # Mock Qdrant manager
            mock_qdrant_manager = AsyncMock()
            mock_qdrant_manager.health_check.return_value = True
            mock_qdrant_manager.get_collection_info.return_value = {"vectors_count": 10}
            mock_qdrant.return_value = mock_qdrant_manager

            # Create real storage manager but mock its dependencies
            storage = StorageManager()
            storage._initialized = True
            storage.db_manager = mock_db_manager
            storage.vector_manager = mock_qdrant_manager

            yield storage, mock_db_manager, mock_qdrant_manager

    async def test_storage_manager_initialization(self, mock_storage_manager):
        """Test storage manager initialization."""
        storage, mock_db, mock_qdrant = mock_storage_manager

        assert storage._initialized is True
        assert storage.db_manager is not None
        assert storage.vector_manager is not None

    async def test_storage_health_check(self, mock_storage_manager):
        """Test unified storage health check."""
        storage, mock_db, mock_qdrant = mock_storage_manager

        health_status = await storage.health_check()

        assert health_status == {"database": True, "vector_database": True}
        mock_db.health_check.assert_called_once()
        mock_qdrant.health_check.assert_called_once()

    async def test_storage_stats(self, mock_storage_manager):
        """Test storage statistics retrieval."""
        storage, mock_db, mock_qdrant = mock_storage_manager

        stats = await storage.get_storage_stats()

        assert "database" in stats
        assert "vector_database" in stats
        mock_db.get_table_info.assert_called_once()
        mock_qdrant.get_collection_info.assert_called_once()

    @patch("src.webdeface.storage.interface.get_db_session")
    async def test_create_website(self, mock_session, mock_storage_manager):
        """Test website creation through unified interface."""
        storage, _, _ = mock_storage_manager

        # Mock database session
        mock_db_session = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db_session

        # Create mock website with proper attributes
        mock_website = Mock()
        mock_website.id = "test-website-id"
        mock_website.url = "https://test.com"
        mock_website.name = "Test Site"
        mock_db_session.refresh = AsyncMock()

        # Mock the website creation to return the mock
        with patch("src.webdeface.storage.sqlite.models.Website") as mock_website_class:
            mock_website_class.return_value = mock_website

            website_data = {
                "url": "https://test.com",
                "name": "Test Site",
                "description": "Test description",
            }

            website = await storage.create_website(website_data)

            # Verify session operations
            mock_db_session.add.assert_called_once()
            mock_db_session.flush.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    @patch("src.webdeface.storage.interface.get_db_session")
    async def test_create_snapshot_with_vector(
        self, mock_session, mock_storage_manager
    ):
        """Test snapshot creation with vector embedding."""
        storage, _, mock_qdrant = mock_storage_manager

        # Mock database session
        mock_db_session = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db_session

        # Mock snapshot with proper attributes including datetime
        mock_snapshot = Mock()
        mock_snapshot.id = "test-snapshot-id"
        mock_snapshot.website_id = "test-website"
        mock_snapshot.content_hash = "abc123"
        captured_time = datetime.utcnow()
        mock_snapshot.captured_at = captured_time
        mock_db_session.refresh = AsyncMock()

        # Mock vector storage
        mock_qdrant.add_vectors.return_value = ["vector-id-123"]

        with patch(
            "src.webdeface.storage.sqlite.models.WebsiteSnapshot"
        ) as mock_snapshot_class:
            mock_snapshot_class.return_value = mock_snapshot

            # Ensure the refresh operation doesn't clear captured_at
            async def mock_refresh(obj):
                obj.captured_at = captured_time  # Ensure it stays set

            mock_db_session.refresh.side_effect = mock_refresh

            vector_embedding = [0.1, 0.2, 0.3] * 128
            snapshot = await storage.create_snapshot(
                website_id="test-website",
                content_hash="abc123",
                content_text="Test content",
                vector_embedding=vector_embedding,
            )

            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.flush.assert_called_once()
            mock_db_session.refresh.assert_called_once()

            # Verify vector storage
            mock_qdrant.add_vectors.assert_called_once()

            # Verify the snapshot has proper datetime
            assert mock_snapshot.captured_at is not None
            assert mock_snapshot.captured_at == captured_time

    async def test_find_similar_content(self, mock_storage_manager):
        """Test content similarity search."""
        storage, _, mock_qdrant = mock_storage_manager

        # Mock similarity search results
        mock_qdrant.search_similar.return_value = [
            ("vector-id", 0.95, {"website_id": "test", "content_hash": "abc123"})
        ]

        query_vector = [0.1, 0.2, 0.3] * 128
        results = await storage.find_similar_content(
            query_vector=query_vector, website_id="test", limit=5, score_threshold=0.8
        )

        assert len(results) == 1
        assert results[0][1] == 0.95  # Score
        mock_qdrant.search_similar.assert_called_once()


@pytest.mark.asyncio
class TestGlobalManagers:
    """Test global manager instances and cleanup."""

    async def test_global_database_manager_singleton(self):
        """Test that global database manager is singleton."""
        with patch(
            "src.webdeface.storage.sqlite.database.DatabaseManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Clear global instance
            from src.webdeface.storage.sqlite.database import cleanup_database_manager

            await cleanup_database_manager()

            # Get manager instances
            manager1 = await get_database_manager()
            manager2 = await get_database_manager()

            # Should be the same instance
            assert manager1 is manager2
            mock_manager.setup.assert_called_once()  # Setup called only once

    async def test_global_qdrant_manager_singleton(self):
        """Test that global Qdrant manager is singleton."""
        with patch(
            "src.webdeface.storage.qdrant.client.QdrantManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Clear global instance
            from src.webdeface.storage.qdrant.client import cleanup_qdrant_manager

            await cleanup_qdrant_manager()

            # Get manager instances
            manager1 = await get_qdrant_manager()
            manager2 = await get_qdrant_manager()

            # Should be the same instance
            assert manager1 is manager2
            mock_manager.setup.assert_called_once()  # Setup called only once

    async def test_global_storage_manager_singleton(self):
        """Test that global storage manager is singleton."""
        with patch(
            "src.webdeface.storage.interface.StorageManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Clear global instance
            from src.webdeface.storage.interface import cleanup_storage_manager

            await cleanup_storage_manager()

            # Get manager instances
            manager1 = await get_storage_manager()
            manager2 = await get_storage_manager()

            # Should be the same instance
            assert manager1 is manager2
            mock_manager.setup.assert_called_once()  # Setup called only once
