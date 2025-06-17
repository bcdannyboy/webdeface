"""ML classification module for defacement detection.

This module provides comprehensive ML-based classification capabilities including:
- Claude AI integration for intelligent defacement detection
- Content vectorization for semantic similarity analysis
- Multi-stage classification pipeline with confidence scoring
- Alert generation with severity assessment
- Feedback loop for continuous model improvement
- Orchestrated classification with monitoring and coordination
"""

from .alerts import (
    AlertContext,
    AlertDeliveryManager,
    AlertGenerator,
    AlertSeverity,
    AlertType,
    GeneratedAlert,
    cleanup_alert_components,
    get_alert_delivery_manager,
    get_alert_generator,
)
from .claude import (
    ClaudeClient,
    DefacementPromptLibrary,
    cleanup_claude_client,
    get_claude_client,
)
from .feedback import (
    ClassificationFeedback,
    FeedbackCollector,
    FeedbackSource,
    FeedbackType,
    ModelPerformanceTracker,
    cleanup_feedback_components,
    get_feedback_collector,
    get_performance_tracker,
)
from .orchestrator import (
    ClassificationJob,
    ClassificationJobResult,
    ClassificationOrchestrator,
    ClassificationQueue,
    ClassificationWorker,
    cleanup_classification_orchestrator,
    get_classification_orchestrator,
)
from .pipeline import (
    EnhancedClassificationPipeline,
    ClassificationPipelineResult,
    AdvancedConfidenceCalculator,
    ConfidenceLevel,
    ComprehensiveRuleBasedClassifier,
    cleanup_classification_pipeline,
    get_classification_pipeline,
)
from .types import (
    Classification,
    ClassificationError,
    ClassificationRequest,
    ClassificationResult,
)
from .vectorizer import (
    ContentVector,
    ContentVectorizer,
    SemanticAnalyzer,
    SimilarityResult,
    cleanup_content_vectorizer,
    get_content_vectorizer,
)

__all__ = [
    # Types
    "Classification",
    "ClassificationResult",
    "ClassificationRequest",
    "ClassificationError",
    "ContentVector",
    "SimilarityResult",
    "ClassificationPipelineResult",
    "ConfidenceLevel",
    "GeneratedAlert",
    "AlertContext",
    "AlertSeverity",
    "AlertType",
    "ClassificationFeedback",
    "FeedbackType",
    "FeedbackSource",
    "ClassificationJob",
    "ClassificationJobResult",
    # Claude AI
    "ClaudeClient",
    "DefacementPromptLibrary",
    "get_claude_client",
    "cleanup_claude_client",
    # Vectorization
    "ContentVectorizer",
    "SemanticAnalyzer",
    "get_content_vectorizer",
    "cleanup_content_vectorizer",
    # Classification Pipeline
    "EnhancedClassificationPipeline",
    "ComprehensiveRuleBasedClassifier",
    "AdvancedConfidenceCalculator",
    "get_classification_pipeline",
    "cleanup_classification_pipeline",
    # Alerts
    "AlertGenerator",
    "AlertDeliveryManager",
    "get_alert_generator",
    "get_alert_delivery_manager",
    "cleanup_alert_components",
    # Feedback
    "FeedbackCollector",
    "ModelPerformanceTracker",
    "get_feedback_collector",
    "get_performance_tracker",
    "cleanup_feedback_components",
    # Orchestration
    "ClassificationOrchestrator",
    "ClassificationQueue",
    "ClassificationWorker",
    "get_classification_orchestrator",
    "cleanup_classification_orchestrator",
]
