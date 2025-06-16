"""Feedback loop for model improvement and classification refinement."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.logging import get_structured_logger
from .pipeline import ClassificationPipelineResult
from .types import Classification

logger = get_structured_logger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback that can be provided."""

    CLASSIFICATION_CORRECTION = "classification_correction"
    CONFIDENCE_ADJUSTMENT = "confidence_adjustment"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    ALERT_FEEDBACK = "alert_feedback"
    MANUAL_REVIEW = "manual_review"


class FeedbackSource(str, Enum):
    """Sources of feedback."""

    HUMAN_ANALYST = "human_analyst"
    AUTOMATED_VALIDATION = "automated_validation"
    SLACK_INTERACTION = "slack_interaction"
    EXTERNAL_SYSTEM = "external_system"
    SELF_CORRECTION = "self_correction"


@dataclass
class ClassificationFeedback:
    """Feedback record for a classification result."""

    # Required fields (no defaults) - MUST come first
    feedback_id: str
    website_id: str
    snapshot_id: Optional[str]
    alert_id: Optional[str]
    original_classification: Classification
    original_confidence: float
    feedback_type: FeedbackType
    feedback_source: FeedbackSource

    # Optional fields (with defaults) - MUST come after required fields
    original_pipeline_result: Optional[dict[str, Any]] = None
    corrected_classification: Optional[Classification] = None
    corrected_confidence: Optional[float] = None
    feedback_reasoning: str = ""
    feedback_metadata: dict[str, Any] = None
    analyst_id: Optional[str] = None
    analyst_notes: str = ""
    created_at: datetime = None
    processed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.feedback_metadata is None:
            self.feedback_metadata = {}


@dataclass
class FeedbackStats:
    """Statistics about feedback and model performance."""

    total_feedback_count: int
    feedback_by_type: dict[str, int]
    feedback_by_source: dict[str, int]
    accuracy_metrics: dict[str, float]
    improvement_trends: dict[str, Any]
    recent_corrections: list[dict[str, Any]]


class FeedbackCollector:
    """Collects and processes feedback from various sources."""

    def __init__(self):
        self.settings = get_settings()
        self.feedback_storage: dict[str, ClassificationFeedback] = {}

    async def submit_classification_correction(
        self,
        website_id: str,
        original_result: ClassificationPipelineResult,
        corrected_classification: Classification,
        corrected_confidence: float,
        analyst_id: str,
        reasoning: str,
        snapshot_id: Optional[str] = None,
        alert_id: Optional[str] = None,
    ) -> str:
        """Submit a classification correction."""

        feedback_id = f"feedback-{website_id}-{int(datetime.utcnow().timestamp())}"

        feedback = ClassificationFeedback(
            feedback_id=feedback_id,
            website_id=website_id,
            snapshot_id=snapshot_id,
            alert_id=alert_id,
            original_classification=original_result.final_classification,
            original_confidence=original_result.confidence_score,
            original_pipeline_result=self._serialize_pipeline_result(original_result),
            feedback_type=FeedbackType.CLASSIFICATION_CORRECTION,
            feedback_source=FeedbackSource.HUMAN_ANALYST,
            corrected_classification=corrected_classification,
            corrected_confidence=corrected_confidence,
            feedback_reasoning=reasoning,
            analyst_id=analyst_id,
            analyst_notes=reasoning,
        )

        await self._store_feedback(feedback)
        await self._process_feedback(feedback)

        logger.info(
            "Classification correction submitted",
            feedback_id=feedback_id,
            website_id=website_id,
            original=original_result.final_classification.value,
            corrected=corrected_classification.value,
            analyst=analyst_id,
        )

        return feedback_id

    async def submit_false_positive_feedback(
        self,
        website_id: str,
        alert_id: str,
        analyst_id: str,
        reasoning: str,
        snapshot_id: Optional[str] = None,
    ) -> str:
        """Submit feedback indicating a false positive alert."""

        feedback_id = f"feedback-fp-{alert_id}-{int(datetime.utcnow().timestamp())}"

        feedback = ClassificationFeedback(
            feedback_id=feedback_id,
            website_id=website_id,
            snapshot_id=snapshot_id,
            alert_id=alert_id,
            original_classification=Classification.DEFACEMENT,  # Assumed since it triggered alert
            original_confidence=0.0,  # Will be updated with actual data
            feedback_type=FeedbackType.FALSE_POSITIVE,
            feedback_source=FeedbackSource.HUMAN_ANALYST,
            corrected_classification=Classification.BENIGN,
            feedback_reasoning=reasoning,
            analyst_id=analyst_id,
            analyst_notes=reasoning,
        )

        await self._store_feedback(feedback)
        await self._process_feedback(feedback)

        logger.info(
            "False positive feedback submitted",
            feedback_id=feedback_id,
            alert_id=alert_id,
            analyst=analyst_id,
        )

        return feedback_id

    async def submit_false_negative_feedback(
        self,
        website_id: str,
        snapshot_id: str,
        analyst_id: str,
        reasoning: str,
        detected_issues: list[str],
    ) -> str:
        """Submit feedback indicating a false negative (missed defacement)."""

        feedback_id = f"feedback-fn-{snapshot_id}-{int(datetime.utcnow().timestamp())}"

        feedback = ClassificationFeedback(
            feedback_id=feedback_id,
            website_id=website_id,
            snapshot_id=snapshot_id,
            original_classification=Classification.BENIGN,  # Assumed since no alert was triggered
            original_confidence=0.0,
            feedback_type=FeedbackType.FALSE_NEGATIVE,
            feedback_source=FeedbackSource.HUMAN_ANALYST,
            corrected_classification=Classification.DEFACEMENT,
            corrected_confidence=0.9,  # High confidence for human-identified defacement
            feedback_reasoning=reasoning,
            analyst_id=analyst_id,
            analyst_notes=reasoning,
            feedback_metadata={"detected_issues": detected_issues},
        )

        await self._store_feedback(feedback)
        await self._process_feedback(feedback)

        logger.info(
            "False negative feedback submitted",
            feedback_id=feedback_id,
            snapshot_id=snapshot_id,
            analyst=analyst_id,
        )

        return feedback_id

    async def submit_slack_feedback(
        self,
        alert_id: str,
        user_id: str,
        action: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Submit feedback from Slack interactions."""

        feedback_id = f"feedback-slack-{alert_id}-{int(datetime.utcnow().timestamp())}"

        # Determine feedback type based on action
        feedback_type = self._slack_action_to_feedback_type(action)
        corrected_classification = self._slack_action_to_classification(action)

        feedback = ClassificationFeedback(
            feedback_id=feedback_id,
            website_id="",  # Will be populated from alert data
            alert_id=alert_id,
            original_classification=Classification.UNCLEAR,  # Will be updated
            original_confidence=0.0,
            feedback_type=feedback_type,
            feedback_source=FeedbackSource.SLACK_INTERACTION,
            corrected_classification=corrected_classification,
            feedback_reasoning=f"Slack action: {action}",
            analyst_id=user_id,
            feedback_metadata=metadata or {},
        )

        await self._enrich_feedback_from_alert(feedback)
        await self._store_feedback(feedback)
        await self._process_feedback(feedback)

        logger.info(
            "Slack feedback submitted",
            feedback_id=feedback_id,
            alert_id=alert_id,
            action=action,
            user_id=user_id,
        )

        return feedback_id

    async def _store_feedback(self, feedback: ClassificationFeedback) -> None:
        """Store feedback in the database."""
        try:
            storage = await get_storage_manager()

            # Store in a feedback table (would need to add to database schema)
            # For now, we'll store as JSON metadata
            feedback_data = {
                "feedback_id": feedback.feedback_id,
                "website_id": feedback.website_id,
                "snapshot_id": feedback.snapshot_id,
                "alert_id": feedback.alert_id,
                "original_classification": feedback.original_classification.value,
                "original_confidence": feedback.original_confidence,
                "feedback_type": feedback.feedback_type.value,
                "feedback_source": feedback.feedback_source.value,
                "corrected_classification": feedback.corrected_classification.value
                if feedback.corrected_classification
                else None,
                "corrected_confidence": feedback.corrected_confidence,
                "feedback_reasoning": feedback.feedback_reasoning,
                "analyst_id": feedback.analyst_id,
                "analyst_notes": feedback.analyst_notes,
                "feedback_metadata": feedback.feedback_metadata,
                "created_at": feedback.created_at.isoformat(),
            }

            # Store in memory for now (would be database in production)
            self.feedback_storage[feedback.feedback_id] = feedback

            logger.debug("Feedback stored", feedback_id=feedback.feedback_id)

        except Exception as e:
            logger.error(f"Failed to store feedback {feedback.feedback_id}: {str(e)}")

    async def _process_feedback(self, feedback: ClassificationFeedback) -> None:
        """Process feedback for model improvement."""
        try:
            # Update classification accuracy metrics
            await self._update_accuracy_metrics(feedback)

            # Trigger model retraining if needed
            await self._check_retraining_trigger(feedback)

            # Update prompt engineering based on feedback
            await self._update_prompt_engineering(feedback)

            feedback.processed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to process feedback {feedback.feedback_id}: {str(e)}")

    async def _enrich_feedback_from_alert(
        self, feedback: ClassificationFeedback
    ) -> None:
        """Enrich feedback with data from the associated alert."""
        if not feedback.alert_id:
            return

        try:
            storage = await get_storage_manager()

            # Get alert details
            # This would query the database for alert information
            # For now, we'll use placeholder data
            feedback.website_id = "placeholder-website-id"
            feedback.original_classification = Classification.DEFACEMENT
            feedback.original_confidence = 0.8

        except Exception as e:
            logger.warning(
                f"Failed to enrich feedback from alert {feedback.alert_id}: {str(e)}"
            )

    def _serialize_pipeline_result(
        self, result: ClassificationPipelineResult
    ) -> dict[str, Any]:
        """Serialize pipeline result for storage."""
        return {
            "final_classification": result.final_classification.value,
            "confidence_score": result.confidence_score,
            "confidence_level": result.confidence_level.value,
            "reasoning": result.reasoning[:1000],  # Truncate for storage
            "classifier_weights": result.classifier_weights,
            "processing_time": result.processing_time,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

    def _slack_action_to_feedback_type(self, action: str) -> FeedbackType:
        """Convert Slack action to feedback type."""
        action_map = {
            "false_positive": FeedbackType.FALSE_POSITIVE,
            "confirm_defacement": FeedbackType.CLASSIFICATION_CORRECTION,
            "mark_benign": FeedbackType.CLASSIFICATION_CORRECTION,
            "needs_review": FeedbackType.MANUAL_REVIEW,
        }
        return action_map.get(action, FeedbackType.ALERT_FEEDBACK)

    def _slack_action_to_classification(self, action: str) -> Optional[Classification]:
        """Convert Slack action to corrected classification."""
        action_map = {
            "false_positive": Classification.BENIGN,
            "confirm_defacement": Classification.DEFACEMENT,
            "mark_benign": Classification.BENIGN,
            "needs_review": None,
        }
        return action_map.get(action)

    async def _update_accuracy_metrics(self, feedback: ClassificationFeedback) -> None:
        """Update classification accuracy metrics based on feedback."""
        # This would update running accuracy statistics
        # For now, just log the update
        logger.debug(
            "Updating accuracy metrics",
            feedback_type=feedback.feedback_type.value,
            original=feedback.original_classification.value,
            corrected=feedback.corrected_classification.value
            if feedback.corrected_classification
            else None,
        )

    async def _check_retraining_trigger(self, feedback: ClassificationFeedback) -> None:
        """Check if model retraining should be triggered based on feedback."""
        # Count recent feedback
        recent_feedback_count = len(
            [
                f
                for f in self.feedback_storage.values()
                if f.created_at > datetime.utcnow() - timedelta(days=7)
            ]
        )

        # Trigger retraining if we have enough feedback
        if recent_feedback_count >= 10:  # Configurable threshold
            logger.info(
                "Model retraining triggered by feedback volume",
                recent_feedback_count=recent_feedback_count,
            )
            # Would trigger actual retraining process here

    async def _update_prompt_engineering(
        self, feedback: ClassificationFeedback
    ) -> None:
        """Update prompt engineering based on feedback patterns."""
        # Analyze feedback patterns to improve prompts
        if feedback.feedback_type == FeedbackType.FALSE_POSITIVE:
            logger.debug("Analyzing false positive for prompt improvement")
            # Would update prompt library to reduce false positives
        elif feedback.feedback_type == FeedbackType.FALSE_NEGATIVE:
            logger.debug("Analyzing false negative for prompt improvement")
            # Would update prompt library to improve detection


class ModelPerformanceTracker:
    """Tracks model performance metrics over time."""

    def __init__(self):
        self.performance_history: list[dict[str, Any]] = []

    async def calculate_performance_metrics(
        self, time_period: timedelta = timedelta(days=30)
    ) -> dict[str, float]:
        """Calculate performance metrics for a given time period."""

        feedback_collector = await get_feedback_collector()

        # Get feedback from the time period
        cutoff_date = datetime.utcnow() - time_period
        recent_feedback = [
            f
            for f in feedback_collector.feedback_storage.values()
            if f.created_at > cutoff_date
        ]

        if not recent_feedback:
            return {}

        # Calculate metrics
        metrics = {}

        # Accuracy: correct classifications / total classifications
        corrections = [
            f
            for f in recent_feedback
            if f.feedback_type == FeedbackType.CLASSIFICATION_CORRECTION
        ]
        false_positives = [
            f for f in recent_feedback if f.feedback_type == FeedbackType.FALSE_POSITIVE
        ]
        false_negatives = [
            f for f in recent_feedback if f.feedback_type == FeedbackType.FALSE_NEGATIVE
        ]

        total_classifications = (
            len(corrections) + len(false_positives) + len(false_negatives)
        )

        if total_classifications > 0:
            # Precision: true positives / (true positives + false positives)
            true_positives = len(
                [
                    f
                    for f in corrections
                    if f.corrected_classification == Classification.DEFACEMENT
                ]
            )
            precision = (
                true_positives / (true_positives + len(false_positives))
                if (true_positives + len(false_positives)) > 0
                else 0
            )

            # Recall: true positives / (true positives + false negatives)
            recall = (
                true_positives / (true_positives + len(false_negatives))
                if (true_positives + len(false_negatives)) > 0
                else 0
            )

            # F1 Score: 2 * (precision * recall) / (precision + recall)
            f1_score = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0
            )

            metrics.update(
                {
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1_score,
                    "false_positive_rate": len(false_positives) / total_classifications,
                    "false_negative_rate": len(false_negatives) / total_classifications,
                    "total_feedback_count": total_classifications,
                }
            )

        return metrics

    async def get_performance_trends(
        self, periods: int = 12, period_length: timedelta = timedelta(days=7)
    ) -> dict[str, list[float]]:
        """Get performance trends over multiple time periods."""

        trends = {
            "precision": [],
            "recall": [],
            "f1_score": [],
            "false_positive_rate": [],
            "false_negative_rate": [],
        }

        for i in range(periods):
            end_date = datetime.utcnow() - (period_length * i)
            start_date = end_date - period_length

            # Calculate metrics for this period
            period_metrics = await self.calculate_performance_metrics(period_length)

            for metric in trends.keys():
                trends[metric].append(period_metrics.get(metric, 0.0))

        # Reverse to get chronological order
        for metric in trends.keys():
            trends[metric].reverse()

        return trends

    async def generate_performance_report(self) -> dict[str, Any]:
        """Generate a comprehensive performance report."""

        # Current metrics
        current_metrics = await self.calculate_performance_metrics(timedelta(days=30))

        # Performance trends
        trends = await self.get_performance_trends()

        # Feedback summary
        feedback_collector = await get_feedback_collector()
        feedback_summary = self._summarize_feedback(feedback_collector.feedback_storage)

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "current_metrics": current_metrics,
            "performance_trends": trends,
            "feedback_summary": feedback_summary,
            "recommendations": self._generate_recommendations(current_metrics, trends),
        }

        return report

    def _summarize_feedback(
        self, feedback_storage: dict[str, ClassificationFeedback]
    ) -> dict[str, Any]:
        """Summarize feedback data."""

        if not feedback_storage:
            return {"total_count": 0}

        feedback_list = list(feedback_storage.values())

        # Count by type
        feedback_by_type = {}
        for feedback_type in FeedbackType:
            count = len([f for f in feedback_list if f.feedback_type == feedback_type])
            feedback_by_type[feedback_type.value] = count

        # Count by source
        feedback_by_source = {}
        for feedback_source in FeedbackSource:
            count = len(
                [f for f in feedback_list if f.feedback_source == feedback_source]
            )
            feedback_by_source[feedback_source.value] = count

        # Recent feedback
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_feedback = [f for f in feedback_list if f.created_at > recent_cutoff]

        return {
            "total_count": len(feedback_list),
            "feedback_by_type": feedback_by_type,
            "feedback_by_source": feedback_by_source,
            "recent_count": len(recent_feedback),
            "avg_daily_feedback": len(recent_feedback) / 7,
        }

    def _generate_recommendations(
        self, current_metrics: dict[str, float], trends: dict[str, list[float]]
    ) -> list[str]:
        """Generate recommendations based on performance metrics."""

        recommendations = []

        # Check precision
        precision = current_metrics.get("precision", 0)
        if precision < 0.8:
            recommendations.append(
                "Consider adjusting classification thresholds to reduce false positives"
            )

        # Check recall
        recall = current_metrics.get("recall", 0)
        if recall < 0.8:
            recommendations.append(
                "Review detection rules to improve coverage of defacement patterns"
            )

        # Check false positive rate
        fp_rate = current_metrics.get("false_positive_rate", 0)
        if fp_rate > 0.1:
            recommendations.append(
                "High false positive rate - review and refine classification criteria"
            )

        # Check trends
        if trends.get("f1_score") and len(trends["f1_score"]) >= 3:
            recent_f1 = trends["f1_score"][-3:]
            if all(recent_f1[i] <= recent_f1[i - 1] for i in range(1, len(recent_f1))):
                recommendations.append(
                    "F1 score declining - consider model retraining or prompt updates"
                )

        if not recommendations:
            recommendations.append("Performance metrics are within acceptable ranges")

        return recommendations


# Global feedback components
_feedback_collector: Optional[FeedbackCollector] = None
_performance_tracker: Optional[ModelPerformanceTracker] = None


async def get_feedback_collector() -> FeedbackCollector:
    """Get or create the global feedback collector."""
    global _feedback_collector

    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()

    return _feedback_collector


async def get_performance_tracker() -> ModelPerformanceTracker:
    """Get or create the global performance tracker."""
    global _performance_tracker

    if _performance_tracker is None:
        _performance_tracker = ModelPerformanceTracker()

    return _performance_tracker


def cleanup_feedback_components() -> None:
    """Clean up global feedback components."""
    global _feedback_collector, _performance_tracker
    _feedback_collector = None
    _performance_tracker = None
