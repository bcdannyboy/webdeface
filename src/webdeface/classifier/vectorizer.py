"""Content vectorization for similarity analysis and semantic understanding."""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ..storage import get_storage_manager
from ..utils.logging import get_structured_logger
from .types import ClassificationError

logger = get_structured_logger(__name__)


@dataclass
class ContentVector:
    """Represents a content vector with metadata."""

    vector: np.ndarray
    content_hash: str
    content_type: str  # 'text', 'title', 'combined', 'semantic'
    model_name: str
    vector_size: int
    created_at: datetime
    metadata: dict[str, Any]


@dataclass
class SimilarityResult:
    """Result of similarity comparison."""

    similarity_score: float  # 0.0 to 1.0
    content_hash: str
    vector_id: Optional[str]
    metadata: dict[str, Any]
    distance: float


class ContentVectorizer:
    """Vectorizes content for semantic similarity analysis."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_content_length = 8000  # Characters
        self.sentence_split_threshold = 1000  # Split long content into sentences
        self._model_lock = asyncio.Lock()

        # Text preprocessing patterns
        self.cleanup_patterns = [
            (r"<[^>]+>", " "),  # Remove HTML tags
            (r"\s+", " "),  # Normalize whitespace
            (
                r"[^\w\s\-\.\,\!\?]",
                " ",
            ),  # Remove special characters except basic punctuation
            (r"\b\d+\b", "[NUM]"),  # Replace numbers with placeholder
            (
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "[EMAIL]",
            ),  # Email placeholder
            (r"https?://\S+", "[URL]"),  # URL placeholder
        ]

    async def _ensure_model(self) -> None:
        """Ensure the sentence transformer model is loaded."""
        if self.model is None:
            async with self._model_lock:
                if self.model is None:
                    logger.info(
                        f"Loading sentence transformer model: {self.model_name}"
                    )

                    # Load model in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    self.model = await loop.run_in_executor(
                        None,
                        lambda: SentenceTransformer(
                            self.model_name, device=self.device
                        ),
                    )

                    logger.info(f"Model loaded successfully on device: {self.device}")

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for vectorization."""
        if not text:
            return ""

        # Apply cleanup patterns
        cleaned = text
        for pattern, replacement in self.cleanup_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)

        # Normalize case and strip
        cleaned = cleaned.lower().strip()

        # Truncate if too long
        if len(cleaned) > self.max_content_length:
            cleaned = cleaned[: self.max_content_length]

        return cleaned

    def _split_long_content(self, text: str) -> list[str]:
        """Split long content into smaller chunks for processing."""
        if len(text) <= self.sentence_split_threshold:
            return [text]

        # Try to split on sentences first
        sentences = re.split(r"[.!?]+\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.sentence_split_threshold:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[: self.sentence_split_threshold]]

    async def vectorize_content(
        self,
        content: str,
        content_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ContentVector:
        """Vectorize content into embeddings."""
        await self._ensure_model()

        # Preprocess content
        processed_content = self._preprocess_text(content)

        if not processed_content:
            # Return zero vector for empty content
            vector_size = self.model.get_sentence_embedding_dimension()
            zero_vector = np.zeros(vector_size)

            return ContentVector(
                vector=zero_vector,
                content_hash=hashlib.blake2b(b"", digest_size=16).hexdigest(),
                content_type=content_type,
                model_name=self.model_name,
                vector_size=vector_size,
                created_at=datetime.utcnow(),
                metadata=metadata or {},
            )

        try:
            # Split content if too long
            content_chunks = self._split_long_content(processed_content)

            # Generate embeddings for chunks
            loop = asyncio.get_event_loop()
            chunk_embeddings = await loop.run_in_executor(
                None, self.model.encode, content_chunks
            )

            # Ensure chunk_embeddings is always a 2D array
            if chunk_embeddings.ndim == 1:
                chunk_embeddings = chunk_embeddings.reshape(1, -1)

            # Average embeddings if multiple chunks
            if len(chunk_embeddings) > 1:
                final_embedding = np.mean(chunk_embeddings, axis=0)
            else:
                final_embedding = chunk_embeddings[0]

            # Generate content hash
            content_hash = hashlib.blake2b(
                processed_content.encode("utf-8"), digest_size=16
            ).hexdigest()

            # Get vector size properly
            if hasattr(final_embedding, "shape") and len(final_embedding.shape) > 0:
                vector_size = final_embedding.shape[0]
            elif hasattr(final_embedding, "__len__"):
                vector_size = len(final_embedding)
            else:
                # Fallback to model's embedding dimension
                vector_size = self.model.get_sentence_embedding_dimension()

            vector = ContentVector(
                vector=final_embedding,
                content_hash=content_hash,
                content_type=content_type,
                model_name=self.model_name,
                vector_size=vector_size,
                created_at=datetime.utcnow(),
                metadata={
                    **(metadata or {}),
                    "original_length": len(content),
                    "processed_length": len(processed_content),
                    "chunk_count": len(content_chunks),
                },
            )

            logger.debug(
                "Content vectorized",
                content_type=content_type,
                vector_size=len(final_embedding),
                chunks=len(content_chunks),
            )

            return vector

        except Exception as e:
            logger.error(f"Content vectorization failed: {str(e)}")
            raise ClassificationError(f"Vectorization failed: {str(e)}")

    async def vectorize_website_content(
        self, content_data: dict[str, Any]
    ) -> dict[str, ContentVector]:
        """Vectorize different aspects of website content."""
        vectors = {}

        # Vectorize main content
        main_content = content_data.get("main_content", "")
        if main_content:
            vectors["main_content"] = await self.vectorize_content(
                main_content,
                content_type="main_content",
                metadata={"source": "main_content_extraction"},
            )

        # Vectorize title
        title = content_data.get("title", "")
        if title:
            vectors["title"] = await self.vectorize_content(
                title, content_type="title", metadata={"source": "page_title"}
            )

        # Vectorize text blocks
        text_blocks = content_data.get("text_blocks", [])
        if text_blocks:
            combined_blocks = " ".join(text_blocks[:10])  # Limit to first 10 blocks
            vectors["text_blocks"] = await self.vectorize_content(
                combined_blocks,
                content_type="text_blocks",
                metadata={"source": "text_blocks", "block_count": len(text_blocks)},
            )

        # Vectorize metadata if present
        meta_description = content_data.get("meta_description", "")
        if meta_description:
            vectors["meta_description"] = await self.vectorize_content(
                meta_description,
                content_type="meta_description",
                metadata={"source": "meta_description"},
            )

        # Create combined semantic vector
        if vectors:
            combined_content_parts = []
            if "title" in vectors:
                combined_content_parts.append(title)
            if "main_content" in vectors:
                combined_content_parts.append(main_content[:2000])  # Limit main content
            if "meta_description" in vectors:
                combined_content_parts.append(meta_description)

            if combined_content_parts:
                combined_content = " ".join(combined_content_parts)
                vectors["combined"] = await self.vectorize_content(
                    combined_content,
                    content_type="combined",
                    metadata={
                        "source": "combined_content",
                        "parts": len(combined_content_parts),
                    },
                )

        return vectors

    async def calculate_similarity(
        self, vector1: np.ndarray, vector2: np.ndarray, method: str = "cosine"
    ) -> float:
        """Calculate similarity between two vectors."""
        try:
            if method == "cosine":
                # Cosine similarity
                dot_product = np.dot(vector1, vector2)
                norm1 = np.linalg.norm(vector1)
                norm2 = np.linalg.norm(vector2)

                if norm1 == 0 or norm2 == 0:
                    return 0.0

                similarity = dot_product / (norm1 * norm2)
                return float(similarity)

            elif method == "euclidean":
                # Euclidean distance converted to similarity
                distance = np.linalg.norm(vector1 - vector2)
                max_distance = np.sqrt(2)  # Max distance for normalized vectors
                similarity = 1.0 - (distance / max_distance)
                return max(0.0, float(similarity))

            elif method == "manhattan":
                # Manhattan distance converted to similarity
                distance = np.sum(np.abs(vector1 - vector2))
                max_distance = 2.0  # Max Manhattan distance for normalized vectors
                similarity = 1.0 - (distance / max_distance)
                return max(0.0, float(similarity))

            else:
                raise ValueError(f"Unknown similarity method: {method}")

        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.0

    async def find_similar_content(
        self,
        query_vector: np.ndarray,
        website_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
    ) -> list[SimilarityResult]:
        """Find similar content using vector similarity search."""
        storage = await get_storage_manager()

        try:
            # Convert numpy array to list for Qdrant
            query_vector_list = query_vector.tolist()

            # Build filter conditions
            filter_conditions = {}
            if website_id:
                filter_conditions["website_id"] = website_id
            if content_type:
                filter_conditions["content_type"] = content_type

            # Search for similar vectors
            similar_results = await storage.find_similar_content(
                query_vector=query_vector_list,
                website_id=website_id,
                limit=limit,
                score_threshold=similarity_threshold,
            )

            # Convert to SimilarityResult objects
            similarity_results = []
            for vector_id, score, payload in similar_results:
                result = SimilarityResult(
                    similarity_score=float(score),
                    content_hash=payload.get("content_hash", ""),
                    vector_id=vector_id,
                    metadata=payload,
                    distance=1.0 - float(score),  # Convert similarity to distance
                )
                similarity_results.append(result)

            return similarity_results

        except Exception as e:
            logger.error(f"Similar content search failed: {str(e)}")
            return []


class SemanticAnalyzer:
    """Analyzes semantic patterns in content changes."""

    def __init__(self):
        self.vectorizer = ContentVectorizer()
        self.change_threshold = 0.7  # Threshold for significant semantic change
        self.defacement_patterns = [
            "hacked",
            "owned",
            "pwned",
            "defaced",
            "unauthorized",
            "breached",
            "compromised",
            "attacked",
            "vandalized",
            "hijacked",
        ]

    async def analyze_semantic_changes(
        self, old_content: dict[str, Any], new_content: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze semantic changes between old and new content."""
        analysis = {
            "semantic_similarity": {},
            "content_drift": {},
            "suspicious_patterns": [],
            "change_summary": {},
            "risk_indicators": [],
        }

        try:
            # Vectorize both content sets
            old_vectors = await self.vectorizer.vectorize_website_content(old_content)
            new_vectors = await self.vectorizer.vectorize_website_content(new_content)

            # Compare vectors for each content type
            for content_type in set(old_vectors.keys()) | set(new_vectors.keys()):
                if content_type in old_vectors and content_type in new_vectors:
                    similarity = await self.vectorizer.calculate_similarity(
                        old_vectors[content_type].vector,
                        new_vectors[content_type].vector,
                    )
                    analysis["semantic_similarity"][content_type] = similarity

                    # Check for significant drift
                    if similarity < self.change_threshold:
                        analysis["content_drift"][content_type] = {
                            "similarity": similarity,
                            "drift_magnitude": 1.0 - similarity,
                            "is_significant": True,
                        }
                elif content_type in new_vectors:
                    # New content type appeared
                    analysis["content_drift"][content_type] = {
                        "similarity": 0.0,
                        "drift_magnitude": 1.0,
                        "is_significant": True,
                        "change_type": "new_content",
                    }
                elif content_type in old_vectors:
                    # Content type disappeared
                    analysis["content_drift"][content_type] = {
                        "similarity": 0.0,
                        "drift_magnitude": 1.0,
                        "is_significant": True,
                        "change_type": "removed_content",
                    }

            # Analyze suspicious patterns
            main_content = new_content.get("main_content", "").lower()
            for pattern in self.defacement_patterns:
                if pattern in main_content:
                    analysis["suspicious_patterns"].append(
                        {
                            "pattern": pattern,
                            "content_type": "main_content",
                            "risk_level": "high",
                        }
                    )
                    analysis["risk_indicators"].append(
                        f"Suspicious keyword detected: {pattern}"
                    )

            # Generate overall change summary
            overall_similarity = (
                np.mean(list(analysis["semantic_similarity"].values()))
                if analysis["semantic_similarity"]
                else 1.0
            )
            analysis["change_summary"] = {
                "overall_similarity": overall_similarity,
                "has_significant_drift": any(
                    drift.get("is_significant", False)
                    for drift in analysis["content_drift"].values()
                ),
                "suspicious_pattern_count": len(analysis["suspicious_patterns"]),
                "risk_level": self._assess_semantic_risk(analysis),
            }

            return analysis

        except Exception as e:
            logger.error(f"Semantic analysis failed: {str(e)}")
            return {"error": str(e)}

    def _assess_semantic_risk(self, analysis: dict[str, Any]) -> str:
        """Assess overall semantic risk level."""
        risk_score = 0.0

        # Risk from semantic similarity
        similarities = list(analysis["semantic_similarity"].values())
        if similarities:
            avg_similarity = np.mean(similarities)
            if avg_similarity < 0.3:
                risk_score += 0.4
            elif avg_similarity < 0.6:
                risk_score += 0.2

        # Risk from suspicious patterns
        pattern_count = len(analysis["suspicious_patterns"])
        if pattern_count > 0:
            risk_score += min(0.3, pattern_count * 0.1)

        # Risk from content drift
        significant_drifts = sum(
            1
            for drift in analysis["content_drift"].values()
            if drift.get("is_significant", False)
        )
        if significant_drifts > 0:
            risk_score += min(0.3, significant_drifts * 0.1)

        # Convert to risk level
        if risk_score >= 0.7:
            return "critical"
        elif risk_score >= 0.5:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"

    async def extract_content_features(
        self, content_vectors: dict[str, ContentVector]
    ) -> dict[str, Any]:
        """Extract semantic features from content vectors."""
        features = {
            "vector_features": {},
            "content_statistics": {},
            "semantic_properties": {},
        }

        for content_type, vector in content_vectors.items():
            # Basic vector statistics
            features["vector_features"][content_type] = {
                "vector_norm": float(np.linalg.norm(vector.vector)),
                "vector_mean": float(np.mean(vector.vector)),
                "vector_std": float(np.std(vector.vector)),
                "vector_max": float(np.max(vector.vector)),
                "vector_min": float(np.min(vector.vector)),
                "non_zero_components": int(np.count_nonzero(vector.vector)),
                "sparsity": float(
                    1.0 - np.count_nonzero(vector.vector) / len(vector.vector)
                ),
            }

            # Content metadata
            features["content_statistics"][content_type] = vector.metadata

        # Overall semantic properties
        if content_vectors:
            all_vectors = [v.vector for v in content_vectors.values()]
            combined_vector = np.mean(all_vectors, axis=0)

            features["semantic_properties"] = {
                "content_diversity": float(
                    np.std([np.linalg.norm(v) for v in all_vectors])
                ),
                "semantic_density": float(np.linalg.norm(combined_vector)),
                "content_types_count": len(content_vectors),
            }

        return features


# Global vectorizer instance
_vectorizer: Optional[ContentVectorizer] = None


async def get_content_vectorizer() -> ContentVectorizer:
    """Get or create the global content vectorizer."""
    global _vectorizer

    if _vectorizer is None:
        _vectorizer = ContentVectorizer()

    return _vectorizer


def cleanup_content_vectorizer() -> None:
    """Clean up the global content vectorizer."""
    global _vectorizer
    _vectorizer = None
