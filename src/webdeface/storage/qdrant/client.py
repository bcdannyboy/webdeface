"""Qdrant vector database client for content similarity search."""

import hashlib
from typing import Any, Optional

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from ...config.settings import QdrantSettings
from ...utils.async_utils import AsyncContextManager, retry_async
from ...utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class QdrantManager(AsyncContextManager):
    """Manages Qdrant vector database operations."""

    def __init__(self, settings: QdrantSettings):
        self.settings = settings
        self.client: Optional[AsyncQdrantClient] = None
        self._initialized = False

    async def setup(self) -> None:
        """Initialize Qdrant client and collection."""
        if self._initialized:
            return

        logger.info("Initializing Qdrant client", url=self.settings.url)

        # Initialize client
        self.client = AsyncQdrantClient(
            url=self.settings.url,
            timeout=30.0,
        )

        # Ensure collection exists
        await self._ensure_collection()

        self._initialized = True
        logger.info("Qdrant client initialization complete")

    async def cleanup(self) -> None:
        """Clean up Qdrant client."""
        if self.client:
            logger.info("Closing Qdrant client")
            await self.client.close()
            self.client = None
            self._initialized = False

    async def _ensure_collection(self) -> None:
        """Ensure the collection exists with proper configuration."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        try:
            # Check if collection exists
            await self.client.get_collection(self.settings.collection_name)
            logger.info(
                "Qdrant collection exists", collection=self.settings.collection_name
            )
        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                # Collection doesn't exist, create it
                logger.info(
                    "Creating Qdrant collection",
                    collection=self.settings.collection_name,
                )
                await self.client.create_collection(
                    collection_name=self.settings.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.settings.vector_size,
                        distance=models.Distance.COSINE
                        if self.settings.distance == "Cosine"
                        else models.Distance.EUCLIDEAN,
                    ),
                    optimizers_config=models.OptimizersConfig(
                        default_segment_number=2,
                        max_segment_size=None,
                        memmap_threshold=None,
                        indexing_threshold=20000,
                        flush_interval_sec=5,
                        max_optimization_threads=1,
                    ),
                    hnsw_config=models.HnswConfig(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                        max_indexing_threads=0,
                        on_disk=False,
                    ),
                )
                logger.info("Qdrant collection created successfully")
            else:
                raise

    async def add_vectors(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """Add vectors to the collection."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")

        # Generate IDs if not provided
        if ids is None:
            ids = [self._generate_id(payload) for payload in payloads]

        logger.debug(
            "Adding vectors to Qdrant",
            count=len(vectors),
            collection=self.settings.collection_name,
        )

        # Prepare points
        points = [
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        # Upload points with retry
        await retry_async(
            self.client.upsert(
                collection_name=self.settings.collection_name,
                points=points,
            ),
            max_retries=3,
            delay=1.0,
            exceptions=(Exception,),
        )

        logger.info("Vectors added successfully", count=len(vectors))
        return ids

    async def search_similar(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[dict[str, Any]] = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Search for similar vectors."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        logger.debug(
            "Searching for similar vectors", limit=limit, threshold=score_threshold
        )

        # Build search filter
        search_filter = None
        if filter_conditions:
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                    for key, value in filter_conditions.items()
                ]
            )

        # Perform search
        search_result = await retry_async(
            self.client.search(
                collection_name=self.settings.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            ),
            max_retries=3,
            delay=1.0,
            exceptions=(Exception,),
        )

        # Format results
        results = [
            (str(point.id), point.score, point.payload or {}) for point in search_result
        ]

        logger.debug("Similar vectors found", count=len(results))
        return results

    async def get_vector_by_id(
        self, vector_id: str
    ) -> Optional[tuple[list[float], dict[str, Any]]]:
        """Get a specific vector by ID."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        try:
            result = await self.client.retrieve(
                collection_name=self.settings.collection_name,
                ids=[vector_id],
                with_vectors=True,
                with_payload=True,
            )

            if result:
                point = result[0]
                return point.vector, point.payload or {}
            return None
        except Exception as e:
            logger.error("Failed to retrieve vector", vector_id=vector_id, error=str(e))
            return None

    async def delete_vectors(self, ids: list[str]) -> bool:
        """Delete vectors by IDs."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        try:
            await self.client.delete(
                collection_name=self.settings.collection_name,
                points_selector=models.PointIdsList(points=ids),
            )
            logger.info("Vectors deleted successfully", count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to delete vectors", ids=ids, error=str(e))
            return False

    async def update_vector_payload(
        self, vector_id: str, payload: dict[str, Any]
    ) -> bool:
        """Update the payload of a specific vector."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        try:
            await self.client.set_payload(
                collection_name=self.settings.collection_name,
                payload=payload,
                points=[vector_id],
            )
            logger.debug("Vector payload updated", vector_id=vector_id)
            return True
        except Exception as e:
            logger.error(
                "Failed to update vector payload", vector_id=vector_id, error=str(e)
            )
            return False

    async def count_vectors(
        self, filter_conditions: Optional[dict[str, Any]] = None
    ) -> int:
        """Count vectors in the collection."""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")

        try:
            # Build filter if provided
            count_filter = None
            if filter_conditions:
                count_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key, match=models.MatchValue(value=value)
                        )
                        for key, value in filter_conditions.items()
                    ]
                )

            result = await self.client.count(
                collection_name=self.settings.collection_name,
                count_filter=count_filter,
            )
            return result.count
        except Exception as e:
            logger.error("Failed to count vectors", error=str(e))
            return 0

    async def health_check(self) -> bool:
        """Perform Qdrant health check."""
        try:
            if not self.client:
                return False

            # Try to get collection info
            await self.client.get_collection(self.settings.collection_name)
            return True
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False

    async def get_collection_info(self) -> dict[str, Any]:
        """Get collection information."""
        if not self.client:
            return {}

        try:
            info = await self.client.get_collection(self.settings.collection_name)
            return {
                "status": info.status,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance,
                },
            }
        except Exception as e:
            logger.error("Failed to get collection info", error=str(e))
            return {}

    def _generate_id(self, payload: dict[str, Any]) -> str:
        """Generate a unique ID for a vector based on its payload."""
        # Create ID from website_id and content_hash if available
        if "website_id" in payload and "content_hash" in payload:
            data = f"{payload['website_id']}:{payload['content_hash']}"
        else:
            # Fallback to hash of entire payload
            data = str(sorted(payload.items()))

        return hashlib.sha256(data.encode()).hexdigest()[:16]


# Global Qdrant manager instance
_qdrant_manager: Optional[QdrantManager] = None


async def get_qdrant_manager(
    settings: Optional[QdrantSettings] = None,
) -> QdrantManager:
    """Get or create the global Qdrant manager."""
    global _qdrant_manager

    if _qdrant_manager is None:
        if settings is None:
            from ...config import get_settings

            app_settings = get_settings()
            settings = app_settings.qdrant

        _qdrant_manager = QdrantManager(settings)
        await _qdrant_manager.setup()

    return _qdrant_manager


async def cleanup_qdrant_manager() -> None:
    """Clean up the global Qdrant manager."""
    global _qdrant_manager

    if _qdrant_manager:
        await _qdrant_manager.cleanup()
        _qdrant_manager = None


async def qdrant_health_check() -> bool:
    """Perform Qdrant health check."""
    try:
        qdrant_manager = await get_qdrant_manager()
        return await qdrant_manager.health_check()
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        return False
