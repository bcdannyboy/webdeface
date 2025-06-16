"""Type definitions for the classifier module."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Classification(str, Enum):
    """Classification labels for website changes."""

    BENIGN = "benign"
    DEFACEMENT = "defacement"
    UNCLEAR = "unclear"


class ClassificationError(Exception):
    """Base exception for classification-related errors."""

    pass


@dataclass
class ClassificationResult:
    """Result of content classification."""

    label: Classification
    explanation: str
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    classified_at: datetime = None

    def __post_init__(self):
        if self.classified_at is None:
            self.classified_at = datetime.utcnow()


@dataclass
class ClassificationRequest:
    """Request for content classification."""

    changed_content: list[str]
    static_context: list[str]
    site_url: str
    site_context: Optional[dict[str, Any]] = None
    previous_classification: Optional[ClassificationResult] = None
