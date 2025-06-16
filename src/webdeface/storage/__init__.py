"""Storage module providing unified access to SQLAlchemy and Qdrant."""

from .interface import StorageManager, cleanup_storage_manager, get_storage_manager
from .qdrant import (
    QdrantManager,
    cleanup_qdrant_manager,
    get_qdrant_manager,
    qdrant_health_check,
)

# Re-export from submodules for convenience
from .sqlite import (
    DatabaseManager,
    DefacementAlert,
    Website,
    WebsiteSnapshot,
    cleanup_database_manager,
    db_health_check,
    get_database_manager,
    get_db_session,
    get_db_transaction,
)
from .types import ScanRecord, SiteRecord, SiteStatus, StorageError

__all__ = [
    # Unified interface
    "StorageManager",
    "get_storage_manager",
    "cleanup_storage_manager",
    # Types
    "StorageError",
    "SiteStatus",
    "SiteRecord",
    "ScanRecord",
    # SQLite
    "DatabaseManager",
    "get_database_manager",
    "cleanup_database_manager",
    "get_db_session",
    "get_db_transaction",
    "db_health_check",
    "Website",
    "WebsiteSnapshot",
    "DefacementAlert",
    # Qdrant
    "QdrantManager",
    "get_qdrant_manager",
    "cleanup_qdrant_manager",
    "qdrant_health_check",
]
