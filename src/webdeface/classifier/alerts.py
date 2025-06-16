"""Alert generation and severity assessment for defacement detection."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.logging import get_structured_logger
from .pipeline import ClassificationPipelineResult, ConfidenceLevel
from .types import Classification

logger = get_structured_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts that can be generated."""

    DEFACEMENT_DETECTED = "defacement_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONTENT_ANOMALY = "content_anomaly"
    CLASSIFICATION_UNCERTAINTY = "classification_uncertainty"
    SYSTEM_ERROR = "system_error"
    PATTERN_DETECTED = "pattern_detected"


@dataclass
class AlertContext:
    """Context information for alert generation."""

    website_id: str
    website_url: str
    website_name: str
    snapshot_id: Optional[str] = None
    classification_result: Optional[ClassificationPipelineResult] = None
    change_details: Optional[dict[str, Any]] = None
    historical_context: Optional[dict[str, Any]] = None
    visual_changes: Optional[dict[str, Any]] = None


@dataclass
class GeneratedAlert:
    """Generated alert with all necessary information."""

    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    context: AlertContext

    # Classification details
    classification_label: Optional[str] = None
    confidence_score: Optional[float] = None
    similarity_score: Optional[float] = None

    # Metadata
    created_at: datetime = None
    alert_id: Optional[str] = None
    recommended_actions: list[str] = None
    escalation_level: int = 1
    suppression_key: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.recommended_actions is None:
            self.recommended_actions = []


class SeverityAssessor:
    """Assesses severity levels for alerts based on multiple factors."""

    def __init__(self):
        self.severity_matrix = {
            # (classification, confidence_level) -> base_severity
            (
                Classification.DEFACEMENT,
                ConfidenceLevel.VERY_HIGH,
            ): AlertSeverity.CRITICAL,
            (Classification.DEFACEMENT, ConfidenceLevel.HIGH): AlertSeverity.HIGH,
            (Classification.DEFACEMENT, ConfidenceLevel.MEDIUM): AlertSeverity.MEDIUM,
            (Classification.DEFACEMENT, ConfidenceLevel.LOW): AlertSeverity.LOW,
            (Classification.DEFACEMENT, ConfidenceLevel.VERY_LOW): AlertSeverity.LOW,
            (Classification.UNCLEAR, ConfidenceLevel.VERY_HIGH): AlertSeverity.MEDIUM,
            (Classification.UNCLEAR, ConfidenceLevel.HIGH): AlertSeverity.MEDIUM,
            (Classification.UNCLEAR, ConfidenceLevel.MEDIUM): AlertSeverity.LOW,
            (Classification.UNCLEAR, ConfidenceLevel.LOW): AlertSeverity.LOW,
            (Classification.UNCLEAR, ConfidenceLevel.VERY_LOW): AlertSeverity.LOW,
        }

        # Severity modifiers
        self.escalation_factors = {
            "multiple_changes": 0.5,
            "visual_changes": 0.3,
            "suspicious_patterns": 0.4,
            "historical_anomaly": 0.3,
            "rapid_changes": 0.6,
            "external_links": 0.2,
            "script_injection": 0.8,
            "content_replacement": 0.6,
        }

    def assess_severity(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> tuple[AlertSeverity, dict[str, Any]]:
        """Assess alert severity based on classification and context."""

        # Get base severity from matrix
        base_severity = self.severity_matrix.get(
            (
                classification_result.final_classification,
                classification_result.confidence_level,
            ),
            AlertSeverity.LOW,
        )

        # Calculate severity modifiers
        severity_score = self._get_severity_score(base_severity)
        severity_factors = {}

        # Analyze change details for escalation factors
        change_details = context.change_details or {}

        # Multiple content changes
        if change_details.get("change_type", "").count(",") > 1:
            severity_factors["multiple_changes"] = True
            severity_score += self.escalation_factors["multiple_changes"]

        # Visual changes detected
        if context.visual_changes and context.visual_changes.get(
            "has_significant_change"
        ):
            severity_factors["visual_changes"] = True
            severity_score += self.escalation_factors["visual_changes"]

        # Suspicious patterns from rule-based classifier
        if classification_result.rule_based_result:
            suspicious_rules = classification_result.rule_based_result.triggered_rules
            if any(
                "defacement" in rule or "hacked" in rule for rule in suspicious_rules
            ):
                severity_factors["suspicious_patterns"] = True
                severity_score += self.escalation_factors["suspicious_patterns"]

        # Script injection detected
        if self._detect_script_injection(change_details):
            severity_factors["script_injection"] = True
            severity_score += self.escalation_factors["script_injection"]

        # Content replacement (high similarity change)
        similarity_score = change_details.get("content_similarity", 1.0)
        if similarity_score < 0.3:
            severity_factors["content_replacement"] = True
            severity_score += self.escalation_factors["content_replacement"]

        # Historical pattern analysis
        historical_context = context.historical_context or {}
        if self._is_historical_anomaly(historical_context):
            severity_factors["historical_anomaly"] = True
            severity_score += self.escalation_factors["historical_anomaly"]

        # Convert back to severity level
        final_severity = self._score_to_severity(severity_score)

        severity_details = {
            "base_severity": base_severity.value,
            "final_severity": final_severity.value,
            "severity_score": severity_score,
            "escalation_factors": severity_factors,
            "confidence_level": classification_result.confidence_level.value,
        }

        return final_severity, severity_details

    def _get_severity_score(self, severity: AlertSeverity) -> float:
        """Convert severity to numeric score."""
        severity_scores = {
            AlertSeverity.LOW: 1.0,
            AlertSeverity.MEDIUM: 2.0,
            AlertSeverity.HIGH: 3.0,
            AlertSeverity.CRITICAL: 4.0,
        }
        return severity_scores.get(severity, 1.0)

    def _score_to_severity(self, score: float) -> AlertSeverity:
        """Convert numeric score back to severity."""
        if score >= 3.5:
            return AlertSeverity.CRITICAL
        elif score >= 2.5:
            return AlertSeverity.HIGH
        elif score >= 1.5:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def _detect_script_injection(self, change_details: dict[str, Any]) -> bool:
        """Detect potential script injection patterns."""
        # This would analyze the change details for script injection indicators
        change_summary = change_details.get("change_summary", [])
        for change in change_summary:
            if any(
                indicator in str(change).lower()
                for indicator in ["<script", "javascript:", "eval(", "iframe"]
            ):
                return True
        return False

    def _is_historical_anomaly(self, historical_context: dict[str, Any]) -> bool:
        """Check if current changes represent a historical anomaly."""
        # Analyze historical patterns
        change_frequency = historical_context.get("change_frequency", 0.0)
        avg_change_interval = historical_context.get("avg_change_interval_seconds", 0)

        # Flag as anomaly if changes are much more frequent than normal
        if (
            change_frequency > 0.5 and avg_change_interval < 3600
        ):  # More than 50% change rate with <1hr intervals
            return True

        return False


class AlertGenerator:
    """Generates alerts based on classification results and context."""

    def __init__(self):
        self.severity_assessor = SeverityAssessor()
        self.settings = get_settings()

        # Alert suppression settings
        self.suppression_windows = {
            AlertSeverity.CRITICAL: timedelta(minutes=5),
            AlertSeverity.HIGH: timedelta(minutes=15),
            AlertSeverity.MEDIUM: timedelta(minutes=30),
            AlertSeverity.LOW: timedelta(hours=2),
        }

        # Track recent alerts for suppression
        self.recent_alerts: dict[str, datetime] = {}

    async def generate_alert(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> Optional[GeneratedAlert]:
        """Generate an alert based on classification results."""

        try:
            # Determine if alert should be generated
            if not self._should_generate_alert(classification_result, context):
                return None

            # Assess severity
            severity, severity_details = self.severity_assessor.assess_severity(
                classification_result, context
            )

            # Determine alert type
            alert_type = self._determine_alert_type(classification_result, severity)

            # Check for suppression
            suppression_key = self._generate_suppression_key(context, alert_type)
            if self._is_suppressed(suppression_key, severity):
                logger.debug(
                    "Alert suppressed",
                    website_id=context.website_id,
                    alert_type=alert_type.value,
                    severity=severity.value,
                )
                return None

            # Generate alert content
            title, description = self._generate_alert_content(
                classification_result, context, severity, alert_type
            )

            # Generate recommended actions
            recommended_actions = self._generate_recommended_actions(
                classification_result, severity, alert_type
            )

            # Create alert
            alert = GeneratedAlert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                context=context,
                classification_label=classification_result.final_classification.value,
                confidence_score=classification_result.confidence_score,
                similarity_score=context.change_details.get("content_similarity")
                if context.change_details
                else None,
                recommended_actions=recommended_actions,
                escalation_level=self._get_escalation_level(severity),
                suppression_key=suppression_key,
            )

            # Record alert for suppression tracking
            self.recent_alerts[suppression_key] = datetime.utcnow()

            logger.info(
                "Alert generated",
                website_id=context.website_id,
                alert_type=alert_type.value,
                severity=severity.value,
                confidence=classification_result.confidence_score,
            )

            return alert

        except Exception as e:
            logger.error(f"Alert generation failed for {context.website_id}: {str(e)}")
            return None

    def _should_generate_alert(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> bool:
        """Determine if an alert should be generated."""

        # Always alert on defacement detection
        if classification_result.final_classification == Classification.DEFACEMENT:
            return True

        # Alert on unclear classification with high confidence
        if (
            classification_result.final_classification == Classification.UNCLEAR
            and classification_result.confidence_level
            in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]
        ):
            return True

        # Alert on significant visual changes
        if context.visual_changes and context.visual_changes.get(
            "has_significant_change"
        ):
            return True

        # Alert on suspicious patterns from rule-based classifier
        if (
            classification_result.rule_based_result
            and classification_result.rule_based_result.confidence > 0.7
        ):
            return True

        return False

    def _determine_alert_type(
        self,
        classification_result: ClassificationPipelineResult,
        severity: AlertSeverity,
    ) -> AlertType:
        """Determine the type of alert to generate."""

        if classification_result.final_classification == Classification.DEFACEMENT:
            if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                return AlertType.DEFACEMENT_DETECTED
            else:
                return AlertType.SUSPICIOUS_ACTIVITY

        elif classification_result.final_classification == Classification.UNCLEAR:
            if classification_result.confidence_level in [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.VERY_HIGH,
            ]:
                return AlertType.CONTENT_ANOMALY
            else:
                return AlertType.CLASSIFICATION_UNCERTAINTY

        else:
            return AlertType.SUSPICIOUS_ACTIVITY

    def _generate_suppression_key(
        self, context: AlertContext, alert_type: AlertType
    ) -> str:
        """Generate a key for alert suppression."""
        return f"{context.website_id}:{alert_type.value}"

    def _is_suppressed(self, suppression_key: str, severity: AlertSeverity) -> bool:
        """Check if alert should be suppressed."""
        if suppression_key not in self.recent_alerts:
            return False

        last_alert_time = self.recent_alerts[suppression_key]
        suppression_window = self.suppression_windows.get(
            severity, timedelta(minutes=30)
        )

        return datetime.utcnow() - last_alert_time < suppression_window

    def _generate_alert_content(
        self,
        classification_result: ClassificationPipelineResult,
        context: AlertContext,
        severity: AlertSeverity,
        alert_type: AlertType,
    ) -> tuple[str, str]:
        """Generate alert title and description."""

        if alert_type == AlertType.DEFACEMENT_DETECTED:
            title = f"🚨 Website Defacement Detected: {context.website_name}"
            description = self._generate_defacement_description(
                classification_result, context
            )

        elif alert_type == AlertType.SUSPICIOUS_ACTIVITY:
            title = f"⚠️ Suspicious Activity: {context.website_name}"
            description = self._generate_suspicious_activity_description(
                classification_result, context
            )

        elif alert_type == AlertType.CONTENT_ANOMALY:
            title = f"📊 Content Anomaly Detected: {context.website_name}"
            description = self._generate_anomaly_description(
                classification_result, context
            )

        elif alert_type == AlertType.CLASSIFICATION_UNCERTAINTY:
            title = f"❓ Classification Uncertainty: {context.website_name}"
            description = self._generate_uncertainty_description(
                classification_result, context
            )

        else:
            title = f"🔍 Alert: {context.website_name}"
            description = f"An alert has been generated for {context.website_url}"

        return title, description

    def _generate_defacement_description(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> str:
        """Generate description for defacement alert."""
        parts = [
            f"Website: {context.website_url}",
            f"Classification: {classification_result.final_classification.value.title()}",
            f"Confidence: {classification_result.confidence_score:.2f} ({classification_result.confidence_level.value})",
        ]

        if classification_result.claude_result:
            parts.append(
                f"AI Analysis: {classification_result.claude_result.explanation[:200]}..."
            )

        if (
            classification_result.rule_based_result
            and classification_result.rule_based_result.triggered_rules
        ):
            rules = ", ".join(
                classification_result.rule_based_result.triggered_rules[:3]
            )
            parts.append(f"Triggered Rules: {rules}")

        if context.change_details:
            similarity = context.change_details.get("content_similarity", "unknown")
            parts.append(f"Content Similarity: {similarity}")

        return "\n".join(parts)

    def _generate_suspicious_activity_description(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> str:
        """Generate description for suspicious activity alert."""
        parts = [
            f"Website: {context.website_url}",
            f"Suspicious patterns detected with {classification_result.confidence_score:.2f} confidence",
        ]

        if classification_result.rule_based_result:
            if classification_result.rule_based_result.triggered_rules:
                parts.append(
                    f"Patterns: {', '.join(classification_result.rule_based_result.triggered_rules[:3])}"
                )

        if context.visual_changes and context.visual_changes.get(
            "has_significant_change"
        ):
            parts.append("Visual changes detected")

        return "\n".join(parts)

    def _generate_anomaly_description(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> str:
        """Generate description for content anomaly alert."""
        parts = [
            f"Website: {context.website_url}",
            "Significant content changes detected",
            f"Analysis confidence: {classification_result.confidence_score:.2f}",
        ]

        if context.change_details:
            change_types = context.change_details.get("change_type", "").split(",")
            if change_types:
                parts.append(f"Change types: {', '.join(change_types)}")

        return "\n".join(parts)

    def _generate_uncertainty_description(
        self, classification_result: ClassificationPipelineResult, context: AlertContext
    ) -> str:
        """Generate description for classification uncertainty alert."""
        parts = [
            f"Website: {context.website_url}",
            f"Classification uncertain despite {classification_result.confidence_level.value} confidence",
            "Manual review recommended",
        ]

        if classification_result.claude_result:
            parts.append(
                f"AI reasoning: {classification_result.claude_result.reasoning[:150]}..."
            )

        return "\n".join(parts)

    def _generate_recommended_actions(
        self,
        classification_result: ClassificationPipelineResult,
        severity: AlertSeverity,
        alert_type: AlertType,
    ) -> list[str]:
        """Generate recommended actions based on alert details."""
        actions = []

        if alert_type == AlertType.DEFACEMENT_DETECTED:
            if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                actions.extend(
                    [
                        "Immediately verify website content",
                        "Check server logs for unauthorized access",
                        "Contact web administrator",
                        "Consider taking website offline if confirmed",
                    ]
                )
            else:
                actions.extend(
                    [
                        "Verify website content",
                        "Review recent content changes",
                        "Monitor for additional changes",
                    ]
                )

        elif alert_type == AlertType.SUSPICIOUS_ACTIVITY:
            actions.extend(
                [
                    "Review website content manually",
                    "Check for unauthorized script injections",
                    "Verify content changes are legitimate",
                    "Monitor closely for additional changes",
                ]
            )

        elif alert_type == AlertType.CONTENT_ANOMALY:
            actions.extend(
                [
                    "Manual content review recommended",
                    "Verify changes are authorized",
                    "Check content management system logs",
                ]
            )

        elif alert_type == AlertType.CLASSIFICATION_UNCERTAINTY:
            actions.extend(
                [
                    "Manual classification needed",
                    "Review AI analysis results",
                    "Provide feedback to improve classification",
                ]
            )

        # Add severity-based actions
        if severity == AlertSeverity.CRITICAL:
            actions.insert(0, "URGENT: Immediate action required")

        return actions

    def _get_escalation_level(self, severity: AlertSeverity) -> int:
        """Get escalation level based on severity."""
        escalation_levels = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }
        return escalation_levels.get(severity, 1)


class AlertDeliveryManager:
    """Manages alert delivery through various channels."""

    def __init__(self):
        self.settings = get_settings()

    async def deliver_alert(self, alert: GeneratedAlert) -> bool:
        """Deliver alert through appropriate channels."""
        try:
            # Store alert in database
            await self._store_alert(alert)

            # Deliver via Slack
            slack_success = await self._deliver_to_slack(alert)

            # Future: Add other delivery channels (email, webhook, etc.)

            return slack_success

        except Exception as e:
            logger.error(f"Alert delivery failed: {str(e)}")
            return False

    async def _store_alert(self, alert: GeneratedAlert) -> str:
        """Store alert in database."""
        storage = await get_storage_manager()

        # Create defacement alert record
        db_alert = await storage.create_alert(
            website_id=alert.context.website_id,
            snapshot_id=alert.context.snapshot_id,
            alert_type=alert.alert_type.value,
            title=alert.title,
            description=alert.description,
            severity=alert.severity.value,
            classification_label=alert.classification_label,
            confidence_score=alert.confidence_score,
            similarity_score=alert.similarity_score,
        )

        alert.alert_id = db_alert.id
        return db_alert.id

    async def _deliver_to_slack(self, alert: GeneratedAlert) -> bool:
        """Deliver alert via Slack."""
        try:
            # Lazy import to avoid circular dependency
            from ..notification.slack import get_notification_delivery

            slack_delivery = await get_notification_delivery()

            # Format alert for Slack
            slack_message = self._format_slack_message(alert)

            # Determine channel based on severity
            channel = self._get_slack_channel(alert.severity)

            # Send message
            result = await slack_delivery.send_alert(
                channel=channel,
                message=slack_message,
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
            )

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Slack delivery failed: {str(e)}")
            return False

    def _format_slack_message(self, alert: GeneratedAlert) -> dict[str, Any]:
        """Format alert for Slack delivery."""
        color_map = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.HIGH: "warning",
            AlertSeverity.MEDIUM: "good",
            AlertSeverity.LOW: "#2eb886",
        }

        message = {
            "text": alert.title,
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "good"),
                    "fields": [
                        {
                            "title": "Website",
                            "value": alert.context.website_url,
                            "short": True,
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.value.title(),
                            "short": True,
                        },
                        {
                            "title": "Classification",
                            "value": alert.classification_label or "Unknown",
                            "short": True,
                        },
                        {
                            "title": "Confidence",
                            "value": f"{alert.confidence_score:.2f}"
                            if alert.confidence_score
                            else "Unknown",
                            "short": True,
                        },
                    ],
                    "text": alert.description,
                    "footer": f"Alert ID: {alert.alert_id}" if alert.alert_id else None,
                    "ts": int(alert.created_at.timestamp()),
                }
            ],
        }

        # Add actions if available
        if alert.recommended_actions:
            actions_text = "Recommended Actions:\n" + "\n".join(
                f"• {action}" for action in alert.recommended_actions[:5]
            )
            message["attachments"][0]["fields"].append(
                {"title": "Recommended Actions", "value": actions_text, "short": False}
            )

        return message

    def _get_slack_channel(self, severity: AlertSeverity) -> str:
        """Get appropriate Slack channel based on severity."""
        # This would be configurable
        channel_map = {
            AlertSeverity.CRITICAL: "#defacement-alerts",
            AlertSeverity.HIGH: "#defacement-alerts",
            AlertSeverity.MEDIUM: "#security-monitoring",
            AlertSeverity.LOW: "#security-monitoring",
        }
        return channel_map.get(severity, "#security-monitoring")


# Global alert generator and delivery manager
_alert_generator: Optional[AlertGenerator] = None
_alert_delivery_manager: Optional[AlertDeliveryManager] = None


async def get_alert_generator() -> AlertGenerator:
    """Get or create the global alert generator."""
    global _alert_generator

    if _alert_generator is None:
        _alert_generator = AlertGenerator()

    return _alert_generator


async def get_alert_delivery_manager() -> AlertDeliveryManager:
    """Get or create the global alert delivery manager."""
    global _alert_delivery_manager

    if _alert_delivery_manager is None:
        _alert_delivery_manager = AlertDeliveryManager()

    return _alert_delivery_manager


async def get_slack_delivery_manager():
    """Get the Slack delivery manager for notifications."""
    # Lazy import to avoid circular dependency
    from ..notification.slack import get_notification_delivery

    return await get_notification_delivery()


def cleanup_alert_components() -> None:
    """Clean up global alert components."""
    global _alert_generator, _alert_delivery_manager
    _alert_generator = None
    _alert_delivery_manager = None
