"""Content hashing and change detection algorithms."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Optional

import blake3

from ..utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


@dataclass
class ContentHash:
    """Content hash with metadata."""

    hash_value: str
    hash_type: str
    content_length: int
    created_at: datetime
    metadata: dict[str, Any]


@dataclass
class ChangeDetectionResult:
    """Result of change detection analysis."""

    has_changed: bool
    change_type: str  # content, structure, visual, metadata
    similarity_score: float  # 0.0 to 1.0
    change_details: dict[str, Any]
    confidence: float  # 0.0 to 1.0
    risk_level: str  # low, medium, high, critical


class ContentHasher:
    """Generates various types of content hashes for change detection."""

    def __init__(self):
        self.normalize_whitespace = True
        self.ignore_dynamic_content = True
        self.dynamic_patterns = [
            r"\d{4}-\d{2}-\d{2}",  # Dates
            r"\d{1,2}:\d{2}(?::\d{2})?",  # Times
            r"(?i)copyright\s+\d{4}",  # Copyright dates
            r"(?i)last\s+updated?:?\s*\d+",  # Update timestamps
            r'session[_-]?id["\']?\s*[:=]\s*["\']?[\w\-]+',  # Session IDs
            r'csrf[_-]?token["\']?\s*[:=]\s*["\']?[\w\-]+',  # CSRF tokens
            r'nonce["\']?\s*[:=]\s*["\']?[\w\-]+',  # Nonces
        ]

    def hash_content(self, content: str, hash_type: str = "blake3") -> ContentHash:
        """Generate a hash of the content."""
        normalized_content = self._normalize_content(content)

        if hash_type == "blake3":
            hasher = blake3.blake3()
            hasher.update(normalized_content.encode("utf-8"))
            hash_value = hasher.hexdigest()
        elif hash_type == "sha256":
            hash_value = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        elif hash_type == "md5":
            hash_value = hashlib.md5(normalized_content.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"Unsupported hash type: {hash_type}")

        return ContentHash(
            hash_value=hash_value,
            hash_type=hash_type,
            content_length=len(normalized_content),
            created_at=datetime.utcnow(),
            metadata={
                "original_length": len(content),
                "normalized": self.normalize_whitespace,
                "ignore_dynamic": self.ignore_dynamic_content,
            },
        )

    def hash_structure(self, dom_outline: list[dict[str, Any]]) -> ContentHash:
        """Generate a hash of the DOM structure."""
        # Create a simplified structure representation
        structure_elements = []
        for element in dom_outline:
            # Create a signature for each element
            signature = f"{element.get('tag', '')}:{element.get('depth', 0)}"

            # Add classes if present
            classes = element.get("classes", [])
            if classes:
                signature += f".{'.'.join(sorted(classes))}"

            # Add ID if present
            element_id = element.get("id")
            if element_id:
                signature += f"#{element_id}"

            structure_elements.append(signature)

        structure_string = "|".join(structure_elements)

        return ContentHash(
            hash_value=hashlib.blake2b(
                structure_string.encode("utf-8"), digest_size=32
            ).hexdigest(),
            hash_type="blake2b",
            content_length=len(structure_string),
            created_at=datetime.utcnow(),
            metadata={
                "element_count": len(dom_outline),
                "structure_type": "dom_outline",
            },
        )

    def hash_text_blocks(self, text_blocks: list[str]) -> ContentHash:
        """Generate a hash of text blocks."""
        # Normalize and sort text blocks for consistent hashing
        normalized_blocks = []
        for block in text_blocks:
            normalized = self._normalize_content(block)
            if normalized:  # Skip empty blocks
                normalized_blocks.append(normalized)

        # Sort blocks to handle reordering
        normalized_blocks.sort()

        combined_text = "\n".join(normalized_blocks)

        return ContentHash(
            hash_value=hashlib.blake2b(
                combined_text.encode("utf-8"), digest_size=32
            ).hexdigest(),
            hash_type="blake2b",
            content_length=len(combined_text),
            created_at=datetime.utcnow(),
            metadata={
                "block_count": len(normalized_blocks),
                "original_count": len(text_blocks),
            },
        )

    def hash_semantic_content(self, content: str) -> ContentHash:
        """Generate a semantic hash focusing on meaningful content."""
        # Extract semantic elements
        semantic_content = self._extract_semantic_content(content)

        return ContentHash(
            hash_value=hashlib.blake2b(
                semantic_content.encode("utf-8"), digest_size=32
            ).hexdigest(),
            hash_type="semantic_blake2b",
            content_length=len(semantic_content),
            created_at=datetime.utcnow(),
            metadata={"semantic_extraction": True, "original_length": len(content)},
        )

    def _normalize_content(self, content: str) -> str:
        """Normalize content for consistent hashing."""
        if not content:
            return ""

        normalized = content

        # Remove dynamic content if enabled
        if self.ignore_dynamic_content:
            for pattern in self.dynamic_patterns:
                normalized = re.sub(pattern, "", normalized)

        # Normalize whitespace if enabled
        if self.normalize_whitespace:
            normalized = re.sub(r"\s+", " ", normalized.strip())

        # Convert to lowercase for case-insensitive comparison
        normalized = normalized.lower()

        return normalized

    def _extract_semantic_content(self, content: str) -> str:
        """Extract semantically meaningful content."""
        # Remove HTML tags if present
        clean_content = re.sub(r"<[^>]+>", " ", content)

        # Remove common non-semantic patterns
        patterns_to_remove = [
            r"(?i)click\s+here",
            r"(?i)read\s+more",
            r"(?i)continue\s+reading",
            r"(?i)home\s*\|\s*about\s*\|\s*contact",  # Navigation
            r"(?i)privacy\s+policy",
            r"(?i)terms\s+of\s+service",
            r"(?i)copyright\s+\d{4}",
            r"\b\d+\b",  # Remove standalone numbers
        ]

        for pattern in patterns_to_remove:
            clean_content = re.sub(pattern, " ", clean_content)

        # Normalize whitespace
        clean_content = re.sub(r"\s+", " ", clean_content.strip())

        return clean_content


class ChangeDetector:
    """Detects and analyzes changes between content versions."""

    def __init__(self):
        self.similarity_threshold = 0.85
        self.structural_threshold = 0.90
        self.critical_change_threshold = 0.50

    def detect_changes(
        self, old_content: dict[str, Any], new_content: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Detect changes between two content snapshots."""
        change_details = {}
        max_risk_level = "low"
        overall_confidence = 0.0
        change_types = []

        # Content hash comparison
        content_similarity = self._compare_content_hashes(
            old_content, new_content, change_details
        )

        if content_similarity < self.similarity_threshold:
            change_types.append("content")
            if content_similarity < self.critical_change_threshold:
                max_risk_level = "critical"
            elif content_similarity < 0.70:
                max_risk_level = "high"
            elif max_risk_level == "low":
                max_risk_level = "medium"

        # Structure comparison
        structure_similarity = self._compare_structure(
            old_content, new_content, change_details
        )

        if structure_similarity < self.structural_threshold:
            change_types.append("structure")
            if structure_similarity < 0.70:
                max_risk_level = max(
                    max_risk_level, "high", key=self._risk_level_weight
                )
            elif max_risk_level == "low":
                max_risk_level = "medium"

        # Visual comparison if available
        visual_similarity = self._compare_visual_hashes(
            old_content, new_content, change_details
        )

        if visual_similarity is not None and visual_similarity < 0.90:
            change_types.append("visual")
            if visual_similarity < 0.60:
                max_risk_level = max(
                    max_risk_level, "high", key=self._risk_level_weight
                )

        # Metadata comparison
        metadata_changes = self._compare_metadata(
            old_content, new_content, change_details
        )

        if metadata_changes:
            change_types.append("metadata")

        # Calculate overall similarity and confidence
        similarities = [
            s
            for s in [content_similarity, structure_similarity, visual_similarity]
            if s is not None
        ]
        overall_similarity = (
            sum(similarities) / len(similarities) if similarities else 1.0
        )

        # Calculate confidence based on available data
        confidence_factors = []
        if "content_hash" in old_content and "content_hash" in new_content:
            confidence_factors.append(0.4)
        if "structure_hash" in old_content and "structure_hash" in new_content:
            confidence_factors.append(0.3)
        if "visual_hash" in old_content and "visual_hash" in new_content:
            confidence_factors.append(0.3)

        overall_confidence = sum(confidence_factors)

        # Determine if there are significant changes
        has_changed = (
            overall_similarity < self.similarity_threshold or len(change_types) > 0
        )

        return ChangeDetectionResult(
            has_changed=has_changed,
            change_type=",".join(change_types) if change_types else "none",
            similarity_score=overall_similarity,
            change_details=change_details,
            confidence=overall_confidence,
            risk_level=max_risk_level,
        )

    def _compare_content_hashes(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
        change_details: dict[str, Any],
    ) -> float:
        """Compare content hashes between old and new content."""
        old_hash = old_content.get("content_hash")
        new_hash = new_content.get("content_hash")

        if not old_hash or not new_hash:
            change_details["content_comparison"] = "missing_hash"
            return 1.0  # Assume no change if hashes missing

        if old_hash == new_hash:
            similarity = 1.0
        else:
            # If hashes differ, try to calculate text similarity
            old_text = old_content.get("main_content", "")
            new_text = new_content.get("main_content", "")
            similarity = self._calculate_text_similarity(old_text, new_text)

        change_details["content_similarity"] = similarity
        change_details["content_hash_changed"] = old_hash != new_hash

        return similarity

    def _compare_structure(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
        change_details: dict[str, Any],
    ) -> float:
        """Compare DOM structure between old and new content."""
        old_structure = old_content.get("structure_hash")
        new_structure = new_content.get("structure_hash")

        if not old_structure or not new_structure:
            change_details["structure_comparison"] = "missing_hash"
            return 1.0

        if old_structure == new_structure:
            similarity = 1.0
        else:
            # Calculate structural similarity based on DOM outline
            old_outline = old_content.get("dom_outline", [])
            new_outline = new_content.get("dom_outline", [])
            similarity = self._calculate_structural_similarity(old_outline, new_outline)

        change_details["structure_similarity"] = similarity
        change_details["structure_hash_changed"] = old_structure != new_structure

        return similarity

    def _compare_visual_hashes(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
        change_details: dict[str, Any],
    ) -> Optional[float]:
        """Compare visual hashes if available."""
        old_visual = old_content.get("visual_hash")
        new_visual = new_content.get("visual_hash")

        if not old_visual or not new_visual:
            return None

        if old_visual == new_visual:
            similarity = 1.0
        else:
            # Visual hashes are different
            similarity = 0.0

        change_details["visual_similarity"] = similarity
        change_details["visual_hash_changed"] = old_visual != new_visual

        return similarity

    def _compare_metadata(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
        change_details: dict[str, Any],
    ) -> bool:
        """Compare metadata between old and new content."""
        metadata_changes = []

        # Compare title
        old_title = old_content.get("title", "")
        new_title = new_content.get("title", "")
        if old_title != new_title:
            metadata_changes.append("title")

        # Compare meta description
        old_desc = old_content.get("meta_description", "")
        new_desc = new_content.get("meta_description", "")
        if old_desc != new_desc:
            metadata_changes.append("meta_description")

        # Compare word count
        old_words = old_content.get("word_count", 0)
        new_words = new_content.get("word_count", 0)
        word_change_ratio = abs(old_words - new_words) / max(old_words, 1)
        if word_change_ratio > 0.1:  # 10% change threshold
            metadata_changes.append("word_count")

        change_details["metadata_changes"] = metadata_changes

        return len(metadata_changes) > 0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for similarity calculation
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def _calculate_structural_similarity(
        self, old_outline: list[dict[str, Any]], new_outline: list[dict[str, Any]]
    ) -> float:
        """Calculate similarity between DOM structures."""
        if not old_outline and not new_outline:
            return 1.0
        if not old_outline or not new_outline:
            return 0.0

        # Create simplified signatures for comparison
        old_signatures = [self._create_element_signature(elem) for elem in old_outline]
        new_signatures = [self._create_element_signature(elem) for elem in new_outline]

        # Calculate sequence similarity
        matcher = SequenceMatcher(None, old_signatures, new_signatures)
        return matcher.ratio()

    def _create_element_signature(self, element: dict[str, Any]) -> str:
        """Create a signature for a DOM element."""
        tag = element.get("tag", "")
        depth = element.get("depth", 0)
        classes = element.get("classes", [])

        signature = f"{tag}:{depth}"
        if classes:
            signature += f".{'.'.join(sorted(classes))}"

        return signature

    def _risk_level_weight(self, risk_level: str) -> int:
        """Get numeric weight for risk level comparison."""
        weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return weights.get(risk_level, 0)


class HashStore:
    """Manages storage and retrieval of content hashes."""

    def __init__(self):
        self.hashes: dict[str, list[ContentHash]] = {}
        self.max_history = 50  # Keep last 50 hashes per URL

    def store_hash(self, url: str, content_hash: ContentHash) -> None:
        """Store a content hash for a URL."""
        if url not in self.hashes:
            self.hashes[url] = []

        self.hashes[url].append(content_hash)

        # Limit history size
        if len(self.hashes[url]) > self.max_history:
            self.hashes[url] = self.hashes[url][-self.max_history :]

        logger.debug(
            f"Stored hash for {url}",
            hash_type=content_hash.hash_type,
            history_size=len(self.hashes[url]),
        )

    def get_latest_hash(
        self, url: str, hash_type: Optional[str] = None
    ) -> Optional[ContentHash]:
        """Get the latest hash for a URL."""
        if url not in self.hashes:
            return None

        url_hashes = self.hashes[url]
        if not url_hashes:
            return None

        if hash_type:
            # Find latest hash of specific type
            for content_hash in reversed(url_hashes):
                if content_hash.hash_type == hash_type:
                    return content_hash
            return None

        # Return latest hash regardless of type
        return url_hashes[-1]

    def get_hash_history(self, url: str, limit: int = 10) -> list[ContentHash]:
        """Get hash history for a URL."""
        if url not in self.hashes:
            return []

        return self.hashes[url][-limit:]

    def detect_pattern_changes(self, url: str, window_size: int = 5) -> dict[str, Any]:
        """Detect patterns in hash changes over time."""
        history = self.get_hash_history(url, window_size * 2)
        if len(history) < window_size:
            return {"insufficient_data": True}

        # Analyze change frequency
        changes = []
        for i in range(1, len(history)):
            prev_hash = history[i - 1]
            curr_hash = history[i]

            if prev_hash.hash_value != curr_hash.hash_value:
                time_diff = (
                    curr_hash.created_at - prev_hash.created_at
                ).total_seconds()
                changes.append(time_diff)

        if not changes:
            return {"stable": True, "change_count": 0}

        avg_change_interval = sum(changes) / len(changes)
        change_frequency = len(changes) / len(history)

        return {
            "change_count": len(changes),
            "change_frequency": change_frequency,
            "avg_change_interval_seconds": avg_change_interval,
            "is_frequently_changing": change_frequency > 0.3,
            "is_stable": change_frequency < 0.1,
        }


# Global hash store instance
_hash_store: Optional[HashStore] = None


def get_hash_store() -> HashStore:
    """Get or create the global hash store."""
    global _hash_store

    if _hash_store is None:
        _hash_store = HashStore()

    return _hash_store
