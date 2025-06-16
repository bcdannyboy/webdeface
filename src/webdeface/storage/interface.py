"""Unified storage interface abstracting SQLAlchemy and Qdrant operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import desc, select

from ..config import get_settings
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .qdrant import QdrantManager, get_qdrant_manager
from .sqlite import (
    DatabaseManager,
    DefacementAlert,
    Website,
    WebsiteSnapshot,
    get_database_manager,
    get_db_session,
)

logger = get_structured_logger(__name__)


class StorageManager(AsyncContextManager):
    """Unified storage interface for both SQLAlchemy and Qdrant operations."""

    def __init__(self):
        self.settings = get_settings()
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_manager: Optional[QdrantManager] = None
        self._initialized = False

    async def setup(self) -> None:
        """Initialize both database and vector storage."""
        if self._initialized:
            return

        logger.info("Initializing unified storage manager")

        # Initialize database manager
        self.db_manager = await get_database_manager(self.settings.database)

        # Initialize vector manager
        self.vector_manager = await get_qdrant_manager(self.settings.qdrant)

        self._initialized = True
        logger.info("Unified storage manager initialization complete")

    async def cleanup(self) -> None:
        """Clean up both storage systems."""
        logger.info("Cleaning up unified storage manager")

        # Cleanup is handled by the global managers
        self._initialized = False

    # Website Management

    async def create_website(self, website_data: dict[str, Any]) -> Website:
        """Create a new website for monitoring."""
        async with get_db_session() as session:
            website = Website(**website_data)
            session.add(website)
            await session.flush()
            await session.refresh(website)
            logger.info("Website created", website_id=website.id, url=website.url)
            return website

    async def get_website(self, website_id: str) -> Optional[Website]:
        """Get a website by ID."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Website).where(Website.id == website_id)
            )
            return result.scalar_one_or_none()

    async def get_website_by_url(self, url: str) -> Optional[Website]:
        """Get a website by URL."""
        async with get_db_session() as session:
            result = await session.execute(select(Website).where(Website.url == url))
            return result.scalar_one_or_none()

    async def list_websites(
        self, active_only: bool = False, limit: Optional[int] = None
    ) -> list[Website]:
        """List all websites, optionally filtered by active status."""
        async with get_db_session() as session:
            query = select(Website)

            if active_only:
                query = query.where(Website.is_active == True)

            if limit:
                query = query.limit(limit)

            query = query.order_by(Website.created_at)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def update_website(
        self, website_id: str, update_data: dict[str, Any]
    ) -> Website:
        """Update a website."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Website).where(Website.id == website_id)
            )
            website = result.scalar_one_or_none()
            if not website:
                raise ValueError(f"Website not found: {website_id}")

            for key, value in update_data.items():
                if hasattr(website, key):
                    setattr(website, key, value)

            website.updated_at = datetime.utcnow()
            await session.flush()
            await session.refresh(website)
            logger.info("Website updated", website_id=website_id)
            return website

    async def delete_website(self, website_id: str) -> bool:
        """Delete a website and all its associated data."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Website).where(Website.id == website_id)
            )
            website = result.scalar_one_or_none()
            if not website:
                return False

            await session.delete(website)
            logger.info("Website deleted", website_id=website_id)
            return True

    async def update_website_last_checked(self, website_id: str) -> None:
        """Update the last checked timestamp for a website."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Website).where(Website.id == website_id)
            )
            website = result.scalar_one_or_none()
            if website:
                website.last_checked_at = datetime.utcnow()
                logger.debug("Updated website last checked", website_id=website_id)

    async def deactivate_website(self, website_id: str) -> bool:
        """Deactivate a website."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Website).where(Website.id == website_id)
            )
            website = result.scalar_one_or_none()
            if website:
                website.is_active = False
                logger.info("Website deactivated", website_id=website_id)
                return True
            return False

    # Website Snapshot Management

    async def create_snapshot(
        self,
        website_id: str,
        content_hash: str,
        content_text: Optional[str] = None,
        raw_html: Optional[bytes] = None,
        status_code: int = 200,
        response_time_ms: float = 0.0,
        content_length: Optional[int] = None,
        content_type: Optional[str] = None,
        vector_embedding: Optional[list[float]] = None,
    ) -> WebsiteSnapshot:
        """Create a new website snapshot with optional vector embedding."""
        async with get_db_session() as session:
            snapshot = WebsiteSnapshot(
                website_id=website_id,
                content_hash=content_hash,
                content_text=content_text,
                raw_html=raw_html,
                status_code=status_code,
                response_time_ms=response_time_ms,
                content_length=content_length,
                content_type=content_type,
            )

            session.add(snapshot)
            await session.flush()
            await session.refresh(snapshot)

            # Store vector embedding if provided
            if vector_embedding and self.vector_manager:
                payload = {
                    "website_id": website_id,
                    "snapshot_id": snapshot.id,
                    "content_hash": content_hash,
                    "captured_at": snapshot.captured_at.isoformat(),
                    "status_code": status_code,
                }

                vector_ids = await self.vector_manager.add_vectors(
                    vectors=[vector_embedding],
                    payloads=[payload],
                )

                if vector_ids:
                    snapshot.vector_id = vector_ids[0]
                    logger.debug(
                        "Vector stored for snapshot",
                        snapshot_id=snapshot.id,
                        vector_id=vector_ids[0],
                    )

            logger.info(
                "Snapshot created", snapshot_id=snapshot.id, website_id=website_id
            )
            return snapshot

    async def get_latest_snapshot(self, website_id: str) -> Optional[WebsiteSnapshot]:
        """Get the latest snapshot for a website."""
        async with get_db_session() as session:
            result = await session.execute(
                select(WebsiteSnapshot)
                .where(WebsiteSnapshot.website_id == website_id)
                .order_by(desc(WebsiteSnapshot.captured_at))
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_snapshots_for_website(
        self, website_id: str, limit: int = 50
    ) -> list[WebsiteSnapshot]:
        """Get recent snapshots for a website."""
        async with get_db_session() as session:
            result = await session.execute(
                select(WebsiteSnapshot)
                .where(WebsiteSnapshot.website_id == website_id)
                .order_by(desc(WebsiteSnapshot.captured_at))
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_website_snapshots(
        self, website_id: str, limit: Optional[int] = None
    ) -> list[WebsiteSnapshot]:
        """Get snapshots for a website with optional limit."""
        async with get_db_session() as session:
            query = select(WebsiteSnapshot).where(
                WebsiteSnapshot.website_id == website_id
            )
            query = query.order_by(desc(WebsiteSnapshot.captured_at))

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def find_similar_content(
        self,
        query_vector: list[float],
        website_id: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.8,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Find similar content using vector similarity search."""
        if not self.vector_manager:
            logger.warning("Vector manager not available for similarity search")
            return []

        filter_conditions = {}
        if website_id:
            filter_conditions["website_id"] = website_id

        return await self.vector_manager.search_similar(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions,
        )

    async def update_snapshot_analysis(
        self,
        snapshot_id: str,
        similarity_score: Optional[float] = None,
        is_defaced: Optional[bool] = None,
        confidence_score: Optional[float] = None,
    ) -> None:
        """Update analysis results for a snapshot."""
        async with get_db_session() as session:
            result = await session.execute(
                select(WebsiteSnapshot).where(WebsiteSnapshot.id == snapshot_id)
            )
            snapshot = result.scalar_one_or_none()
            if snapshot:
                if similarity_score is not None:
                    snapshot.similarity_score = similarity_score
                if is_defaced is not None:
                    snapshot.is_defaced = is_defaced
                if confidence_score is not None:
                    snapshot.confidence_score = confidence_score
                snapshot.analyzed_at = datetime.utcnow()

                logger.debug(
                    "Snapshot analysis updated",
                    snapshot_id=snapshot_id,
                    is_defaced=is_defaced,
                    confidence=confidence_score,
                )

    # Alert Management

    async def create_alert(
        self,
        website_id: str,
        snapshot_id: Optional[str],
        alert_type: str,
        title: str,
        description: str,
        severity: str = "medium",
        classification_label: Optional[str] = None,
        confidence_score: Optional[float] = None,
        similarity_score: Optional[float] = None,
    ) -> DefacementAlert:
        """Create a new defacement alert."""
        async with get_db_session() as session:
            alert = DefacementAlert(
                website_id=website_id,
                snapshot_id=snapshot_id,
                alert_type=alert_type,
                title=title,
                description=description,
                severity=severity,
                classification_label=classification_label,
                confidence_score=confidence_score,
                similarity_score=similarity_score,
            )

            session.add(alert)
            await session.flush()
            await session.refresh(alert)

            logger.info(
                "Alert created",
                alert_id=alert.id,
                website_id=website_id,
                alert_type=alert_type,
                severity=severity,
            )
            return alert

    async def get_open_alerts(
        self, website_id: Optional[str] = None, limit: int = 100
    ) -> list[DefacementAlert]:
        """Get open alerts, optionally filtered by website."""
        async with get_db_session() as session:
            query = select(DefacementAlert).where(DefacementAlert.status == "open")

            if website_id:
                query = query.where(DefacementAlert.website_id == website_id)

            query = query.order_by(desc(DefacementAlert.created_at)).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_website_alerts(
        self, website_id: str, limit: Optional[int] = None
    ) -> list[DefacementAlert]:
        """Get all alerts for a website."""
        async with get_db_session() as session:
            query = select(DefacementAlert).where(
                DefacementAlert.website_id == website_id
            )
            query = query.order_by(desc(DefacementAlert.created_at))

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_alert(self, alert_id: str) -> Optional[DefacementAlert]:
        """Get a specific alert by ID."""
        async with get_db_session() as session:
            result = await session.execute(
                select(DefacementAlert).where(DefacementAlert.id == alert_id)
            )
            return result.scalar_one_or_none()

    async def update_alert(
        self, alert_id: str, update_data: dict[str, Any]
    ) -> DefacementAlert:
        """Update an alert."""
        async with get_db_session() as session:
            result = await session.execute(
                select(DefacementAlert).where(DefacementAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            if not alert:
                raise ValueError(f"Alert not found: {alert_id}")

            for key, value in update_data.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)

            alert.updated_at = datetime.utcnow()
            await session.flush()
            await session.refresh(alert)
            logger.info("Alert updated", alert_id=alert_id)
            return alert

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        async with get_db_session() as session:
            result = await session.execute(
                select(DefacementAlert).where(DefacementAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            if alert and alert.status == "open":
                alert.status = "acknowledged"
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                logger.info("Alert acknowledged", alert_id=alert_id, by=acknowledged_by)
                return True
            return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        async with get_db_session() as session:
            result = await session.execute(
                select(DefacementAlert).where(DefacementAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            if alert and alert.status != "resolved":
                alert.status = "resolved"
                alert.resolved_at = datetime.utcnow()
                logger.info("Alert resolved", alert_id=alert_id)
                return True
            return False

    # Health Checks and Stats

    async def health_check(self) -> dict[str, bool]:
        """Perform health checks on both storage systems."""
        health_status = {}

        # Database health check
        try:
            db_healthy = (
                await self.db_manager.health_check() if self.db_manager else False
            )
            health_status["database"] = db_healthy
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            health_status["database"] = False

        # Vector database health check
        try:
            vector_healthy = (
                await self.vector_manager.health_check()
                if self.vector_manager
                else False
            )
            health_status["vector_database"] = vector_healthy
        except Exception as e:
            logger.error("Vector database health check failed", error=str(e))
            health_status["vector_database"] = False

        return health_status

    async def get_storage_stats(self) -> dict[str, Any]:
        """Get statistics about storage usage."""
        stats = {}

        # Database stats
        try:
            if self.db_manager:
                table_info = await self.db_manager.get_table_info()
                stats["database"] = table_info
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            stats["database"] = {}

        # Vector database stats
        try:
            if self.vector_manager:
                collection_info = await self.vector_manager.get_collection_info()
                stats["vector_database"] = collection_info
        except Exception as e:
            logger.error("Failed to get vector database stats", error=str(e))
            stats["vector_database"] = {}

        return stats


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


async def get_storage_manager() -> StorageManager:
    """Get or create the global storage manager."""
    global _storage_manager

    if _storage_manager is None:
        _storage_manager = StorageManager()
        await _storage_manager.setup()

    return _storage_manager


async def cleanup_storage_manager() -> None:
    """Clean up the global storage manager."""
    global _storage_manager

    if _storage_manager:
        await _storage_manager.cleanup()
        _storage_manager = None
