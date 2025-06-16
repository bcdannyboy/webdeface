"""Classification pipeline with confidence scoring and multi-stage analysis."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import numpy as np

from ..config import get_settings
from ..utils.logging import get_structured_logger
from .claude import get_claude_client
from .types import (
    Classification,
    ClassificationError,
    ClassificationRequest,
    ClassificationResult,
)
from .vectorizer import SemanticAnalyzer

logger = get_structured_logger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for classification results."""

    VERY_LOW = "very_low"  # 0.0 - 0.2
    LOW = "low"  # 0.2 - 0.4
    MEDIUM = "medium"  # 0.4 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    VERY_HIGH = "very_high"  # 0.8 - 1.0


@dataclass
class ClassificationPipelineResult:
    """Result from the full classification pipeline."""

    final_classification: Classification
    confidence_score: float
    confidence_level: ConfidenceLevel
    reasoning: str

    # Individual classifier results
    claude_result: Optional[ClassificationResult] = None
    semantic_analysis: Optional[dict[str, Any]] = None
    rule_based_result: Optional[dict[str, Any]] = None

    # Aggregation metadata
    classifier_weights: dict[str, float] = None
    consensus_metrics: dict[str, Any] = None
    processing_time: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.classifier_weights is None:
            self.classifier_weights = {}


@dataclass
class RuleBasedResult:
    """Result from rule-based classification."""

    classification: Classification
    confidence: float
    triggered_rules: list[str]
    rule_scores: dict[str, float]
    reasoning: str


class RuleBasedClassifier:
    """Rule-based classifier for quick defacement detection."""

    def __init__(self):
        self.defacement_keywords = {
            "hacked": 0.9,
            "owned": 0.8,
            "pwned": 0.8,
            "defaced": 0.95,
            "unauthorized": 0.7,
            "breached": 0.7,
            "compromised": 0.7,
            "attacked": 0.6,
            "vandalized": 0.8,
            "hijacked": 0.8,
            "free palestine": 0.6,
            "anonymous": 0.5,
            "we are legion": 0.7,
        }

        self.suspicious_patterns = {
            r"(?i)hacked\s+by\s+\w+": 0.95,
            r"(?i)owned\s+by\s+\w+": 0.9,
            r"(?i)defaced\s+by\s+\w+": 0.95,
            r"(?i)fuck\s+\w+": 0.6,
            r"(?i)allah\s+akbar": 0.5,
            r"(?i)jihad": 0.5,
            r"(?i)cryptocurrency\s+miner": 0.8,
            r"(?i)bitcoin\s+mining": 0.8,
            r"<script[^>]*>.*?crypto.*?</script>": 0.9,
            r'<iframe[^>]*src=["\'][^"\']*suspicious[^"\']*["\']': 0.8,
        }

        self.benign_indicators = {
            "maintenance": -0.3,
            "update": -0.2,
            "upgrade": -0.2,
            "news": -0.1,
            "announcement": -0.1,
            "copyright": -0.1,
            "privacy policy": -0.1,
            "terms of service": -0.1,
        }

    def classify(
        self, content: list[str], context: dict[str, Any] = None
    ) -> RuleBasedResult:
        """Classify content using rule-based approach."""
        combined_content = " ".join(content).lower()
        triggered_rules = []
        rule_scores = {}
        total_score = 0.0

        # Check defacement keywords
        for keyword, score in self.defacement_keywords.items():
            if keyword in combined_content:
                triggered_rules.append(f"defacement_keyword: {keyword}")
                rule_scores[f"keyword_{keyword}"] = score
                total_score += score

        # Check suspicious patterns
        import re

        for pattern, score in self.suspicious_patterns.items():
            matches = re.findall(pattern, combined_content)
            if matches:
                triggered_rules.append(f"suspicious_pattern: {pattern}")
                rule_scores[f"pattern_{pattern[:20]}"] = score
                total_score += score

        # Check benign indicators
        for indicator, score in self.benign_indicators.items():
            if indicator in combined_content:
                triggered_rules.append(f"benign_indicator: {indicator}")
                rule_scores[f"benign_{indicator}"] = score
                total_score += score

        # Normalize score
        confidence = min(1.0, max(0.0, total_score))

        # Determine classification
        if confidence >= 0.6:
            classification = Classification.DEFACEMENT
        elif confidence <= -0.2:
            classification = Classification.BENIGN
        else:
            classification = Classification.UNCLEAR

        # Generate reasoning
        reasoning_parts = []
        if triggered_rules:
            reasoning_parts.append(f"Triggered rules: {', '.join(triggered_rules[:5])}")
        reasoning_parts.append(f"Rule-based score: {confidence:.2f}")

        reasoning = ". ".join(reasoning_parts)

        return RuleBasedResult(
            classification=classification,
            confidence=abs(confidence),
            triggered_rules=triggered_rules,
            rule_scores=rule_scores,
            reasoning=reasoning,
        )


class ConfidenceCalculator:
    """Calculates confidence scores for classification results."""

    def __init__(self):
        self.base_weights = {"claude": 0.5, "semantic": 0.3, "rule_based": 0.2}

        self.confidence_factors = {
            "agreement": 0.3,  # Agreement between classifiers
            "clarity": 0.2,  # Clarity of individual results
            "context": 0.2,  # Contextual information quality
            "historical": 0.15,  # Historical pattern consistency
            "semantic": 0.15,  # Semantic analysis quality
        }

    def calculate_confidence(
        self,
        claude_result: Optional[ClassificationResult],
        semantic_analysis: Optional[dict[str, Any]],
        rule_based_result: Optional[RuleBasedResult],
        context: Optional[dict[str, Any]] = None,
    ) -> tuple[float, dict[str, float], dict[str, Any]]:
        """Calculate overall confidence and weights."""

        confidence_components = {}
        classifier_weights = {}
        consensus_metrics = {}

        # Collect available results
        available_results = {}
        if claude_result:
            available_results["claude"] = claude_result
        if semantic_analysis:
            available_results["semantic"] = semantic_analysis
        if rule_based_result:
            available_results["rule_based"] = rule_based_result

        # Calculate agreement factor
        agreement_score = self._calculate_agreement(available_results)
        confidence_components["agreement"] = agreement_score

        # Calculate clarity factor
        clarity_score = self._calculate_clarity(available_results)
        confidence_components["clarity"] = clarity_score

        # Calculate context factor
        context_score = self._calculate_context_quality(context)
        confidence_components["context"] = context_score

        # Calculate historical factor
        historical_score = self._calculate_historical_consistency(context)
        confidence_components["historical"] = historical_score

        # Calculate semantic factor
        semantic_score = self._calculate_semantic_quality(semantic_analysis)
        confidence_components["semantic"] = semantic_score

        # Adjust classifier weights based on performance
        classifier_weights = self._adjust_classifier_weights(
            available_results, confidence_components
        )

        # Calculate overall confidence
        overall_confidence = sum(
            self.confidence_factors[factor] * score
            for factor, score in confidence_components.items()
        )

        # Store consensus metrics
        consensus_metrics = {
            "available_classifiers": list(available_results.keys()),
            "agreement_score": agreement_score,
            "clarity_score": clarity_score,
            "confidence_components": confidence_components,
        }

        return overall_confidence, classifier_weights, consensus_metrics

    def _calculate_agreement(self, results: dict[str, Any]) -> float:
        """Calculate agreement between classifiers."""
        if len(results) < 2:
            return 0.5  # Neutral if only one classifier

        classifications = []
        for name, result in results.items():
            if name == "claude" and hasattr(result, "label"):
                classifications.append(result.label.value)
            elif name == "rule_based" and hasattr(result, "classification"):
                classifications.append(result.classification.value)
            elif name == "semantic" and isinstance(result, dict):
                # Extract classification from semantic analysis
                summary = result.get("change_summary", {})
                risk_level = summary.get("risk_level", "medium")
                if risk_level in ["high", "critical"]:
                    classifications.append("defacement")
                elif risk_level == "low":
                    classifications.append("benign")
                else:
                    classifications.append("unclear")

        # Calculate agreement rate
        if not classifications:
            return 0.5

        most_common = max(set(classifications), key=classifications.count)
        agreement_rate = classifications.count(most_common) / len(classifications)

        return agreement_rate

    def _calculate_clarity(self, results: dict[str, Any]) -> float:
        """Calculate clarity of individual classifier results."""
        clarity_scores = []

        for name, result in results.items():
            if name == "claude" and hasattr(result, "confidence"):
                clarity_scores.append(result.confidence)
            elif name == "rule_based" and hasattr(result, "confidence"):
                clarity_scores.append(result.confidence)
            elif name == "semantic" and isinstance(result, dict):
                # Estimate clarity from semantic analysis
                similarities = result.get("semantic_similarity", {})
                if similarities:
                    avg_similarity = np.mean(list(similarities.values()))
                    clarity = 1.0 - avg_similarity  # More change = clearer signal
                    clarity_scores.append(clarity)

        return np.mean(clarity_scores) if clarity_scores else 0.5

    def _calculate_context_quality(self, context: Optional[dict[str, Any]]) -> float:
        """Calculate quality of contextual information."""
        if not context:
            return 0.3

        quality_factors = []

        # Check for historical data
        if context.get("has_baseline"):
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.3)

        # Check for website metadata
        if context.get("site_context"):
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.4)

        # Check for previous classifications
        if context.get("previous_classification"):
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.4)

        return np.mean(quality_factors)

    def _calculate_historical_consistency(
        self, context: Optional[dict[str, Any]]
    ) -> float:
        """Calculate consistency with historical patterns."""
        if not context:
            return 0.5

        # This would typically analyze historical classification patterns
        # For now, return a default based on available context
        if context.get("website_classification_history"):
            return 0.7
        else:
            return 0.5

    def _calculate_semantic_quality(
        self, semantic_analysis: Optional[dict[str, Any]]
    ) -> float:
        """Calculate quality of semantic analysis."""
        if not semantic_analysis:
            return 0.3

        quality_factors = []

        # Check semantic similarity data
        similarities = semantic_analysis.get("semantic_similarity", {})
        if similarities:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.4)

        # Check for suspicious patterns
        patterns = semantic_analysis.get("suspicious_patterns", [])
        if patterns:
            quality_factors.append(0.9)
        else:
            quality_factors.append(0.6)

        # Check error conditions
        if "error" in semantic_analysis:
            quality_factors.append(0.2)

        return np.mean(quality_factors) if quality_factors else 0.5

    def _adjust_classifier_weights(
        self, results: dict[str, Any], confidence_components: dict[str, float]
    ) -> dict[str, float]:
        """Adjust classifier weights based on performance."""
        weights = self.base_weights.copy()

        # Adjust based on agreement
        agreement = confidence_components.get("agreement", 0.5)
        if agreement > 0.8:
            # High agreement - maintain weights
            pass
        elif agreement < 0.3:
            # Low agreement - reduce all weights slightly
            for key in weights:
                weights[key] *= 0.8

        # Adjust based on availability
        available_classifiers = list(results.keys())
        total_available_weight = sum(
            weights[name] for name in available_classifiers if name in weights
        )

        # Normalize weights for available classifiers
        if total_available_weight > 0:
            normalization_factor = 1.0 / total_available_weight
            for name in weights:
                if name in available_classifiers:
                    weights[name] *= normalization_factor
                else:
                    weights[name] = 0.0

        return weights

    def get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if confidence_score >= 0.8:
            return ConfidenceLevel.VERY_HIGH
        elif confidence_score >= 0.6:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.4:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class ClassificationPipeline:
    """Main classification pipeline coordinating multiple classifiers."""

    def __init__(self):
        self.rule_based_classifier = RuleBasedClassifier()
        self.semantic_analyzer = SemanticAnalyzer()
        self.confidence_calculator = ConfidenceCalculator()
        self.settings = get_settings()

        # Pipeline configuration
        self.enable_claude = True
        self.enable_semantic = True
        self.enable_rule_based = True
        self.parallel_execution = True

    async def classify(
        self, request: ClassificationRequest
    ) -> ClassificationPipelineResult:
        """Run the full classification pipeline."""
        start_time = asyncio.get_event_loop().time()

        logger.info(
            "Starting classification pipeline",
            url=request.site_url,
            changed_content_blocks=len(request.changed_content),
        )

        try:
            # Run classifiers
            if self.parallel_execution:
                results = await self._run_parallel_classification(request)
            else:
                results = await self._run_sequential_classification(request)

            claude_result, semantic_analysis, rule_based_result = results

            # Calculate final classification and confidence
            final_result = await self._aggregate_results(
                claude_result, semantic_analysis, rule_based_result, request
            )

            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            final_result.processing_time = processing_time

            logger.info(
                "Classification pipeline completed",
                url=request.site_url,
                classification=final_result.final_classification.value,
                confidence=final_result.confidence_score,
                processing_time=processing_time,
            )

            return final_result

        except Exception as e:
            logger.error(
                f"Classification pipeline failed for {request.site_url}: {str(e)}"
            )
            raise ClassificationError(f"Pipeline failed: {str(e)}")

    async def _run_parallel_classification(
        self, request: ClassificationRequest
    ) -> tuple[
        Optional[ClassificationResult],
        Optional[dict[str, Any]],
        Optional[RuleBasedResult],
    ]:
        """Run all classifiers in parallel."""
        tasks = []

        # Claude classification
        if self.enable_claude:
            tasks.append(self._run_claude_classification(request))
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        # Semantic analysis
        if self.enable_semantic:
            tasks.append(self._run_semantic_analysis(request))
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        # Rule-based classification
        if self.enable_rule_based:
            tasks.append(self._run_rule_based_classification(request))
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Classifier {i} failed: {str(result)}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return tuple(processed_results)

    async def _run_sequential_classification(
        self, request: ClassificationRequest
    ) -> tuple[
        Optional[ClassificationResult],
        Optional[dict[str, Any]],
        Optional[RuleBasedResult],
    ]:
        """Run classifiers sequentially."""
        claude_result = None
        semantic_analysis = None
        rule_based_result = None

        try:
            if self.enable_rule_based:
                rule_based_result = await self._run_rule_based_classification(request)
        except Exception as e:
            logger.warning(f"Rule-based classification failed: {str(e)}")

        try:
            if self.enable_semantic:
                semantic_analysis = await self._run_semantic_analysis(request)
        except Exception as e:
            logger.warning(f"Semantic analysis failed: {str(e)}")

        try:
            if self.enable_claude:
                claude_result = await self._run_claude_classification(request)
        except Exception as e:
            logger.warning(f"Claude classification failed: {str(e)}")

        return claude_result, semantic_analysis, rule_based_result

    async def _run_claude_classification(
        self, request: ClassificationRequest
    ) -> ClassificationResult:
        """Run Claude classification."""
        claude_client = await get_claude_client()

        return await claude_client.classify_content(
            changed_content=request.changed_content,
            static_context=request.static_context,
            site_url=request.site_url,
            site_context=request.site_context,
            previous_classification=request.previous_classification,
        )

    async def _run_semantic_analysis(
        self, request: ClassificationRequest
    ) -> dict[str, Any]:
        """Run semantic analysis."""
        # Prepare content for semantic analysis
        old_content = {
            "main_content": " ".join(request.static_context),
            "title": request.site_context.get("title", "")
            if request.site_context
            else "",
            "word_count": sum(len(text.split()) for text in request.static_context),
        }

        new_content = {
            "main_content": " ".join(request.changed_content),
            "title": request.site_context.get("title", "")
            if request.site_context
            else "",
            "word_count": sum(len(text.split()) for text in request.changed_content),
        }

        return await self.semantic_analyzer.analyze_semantic_changes(
            old_content, new_content
        )

    async def _run_rule_based_classification(
        self, request: ClassificationRequest
    ) -> RuleBasedResult:
        """Run rule-based classification."""
        return self.rule_based_classifier.classify(
            content=request.changed_content, context=request.site_context
        )

    async def _return_none(self):
        """Helper to return None asynchronously."""
        return None

    async def _aggregate_results(
        self,
        claude_result: Optional[ClassificationResult],
        semantic_analysis: Optional[dict[str, Any]],
        rule_based_result: Optional[RuleBasedResult],
        request: ClassificationRequest,
    ) -> ClassificationPipelineResult:
        """Aggregate results from all classifiers."""

        # Calculate confidence and weights
        (
            confidence_score,
            classifier_weights,
            consensus_metrics,
        ) = self.confidence_calculator.calculate_confidence(
            claude_result=claude_result,
            semantic_analysis=semantic_analysis,
            rule_based_result=rule_based_result,
            context=request.site_context,
        )

        # Determine final classification using weighted voting
        final_classification = self._weighted_vote(
            claude_result, semantic_analysis, rule_based_result, classifier_weights
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            claude_result,
            semantic_analysis,
            rule_based_result,
            classifier_weights,
            confidence_score,
        )

        # Get confidence level
        confidence_level = self.confidence_calculator.get_confidence_level(
            confidence_score
        )

        return ClassificationPipelineResult(
            final_classification=final_classification,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            reasoning=reasoning,
            claude_result=claude_result,
            semantic_analysis=semantic_analysis,
            rule_based_result=rule_based_result,
            classifier_weights=classifier_weights,
            consensus_metrics=consensus_metrics,
        )

    def _weighted_vote(
        self,
        claude_result: Optional[ClassificationResult],
        semantic_analysis: Optional[dict[str, Any]],
        rule_based_result: Optional[RuleBasedResult],
        weights: dict[str, float],
    ) -> Classification:
        """Perform weighted voting to determine final classification."""
        votes = {
            Classification.BENIGN: 0.0,
            Classification.DEFACEMENT: 0.0,
            Classification.UNCLEAR: 0.0,
        }

        # Claude vote
        if claude_result and weights.get("claude", 0) > 0:
            vote_weight = weights["claude"] * claude_result.confidence
            votes[claude_result.label] += vote_weight

        # Rule-based vote
        if rule_based_result and weights.get("rule_based", 0) > 0:
            vote_weight = weights["rule_based"] * rule_based_result.confidence
            votes[rule_based_result.classification] += vote_weight

        # Semantic vote
        if semantic_analysis and weights.get("semantic", 0) > 0:
            summary = semantic_analysis.get("change_summary", {})
            risk_level = summary.get("risk_level", "medium")

            vote_weight = weights["semantic"]
            if risk_level in ["high", "critical"]:
                votes[Classification.DEFACEMENT] += vote_weight * 0.8
            elif risk_level == "low":
                votes[Classification.BENIGN] += vote_weight * 0.8
            else:
                votes[Classification.UNCLEAR] += vote_weight * 0.6

        # Return classification with highest vote
        return max(votes, key=votes.get)

    def _generate_reasoning(
        self,
        claude_result: Optional[ClassificationResult],
        semantic_analysis: Optional[dict[str, Any]],
        rule_based_result: Optional[RuleBasedResult],
        weights: dict[str, float],
        confidence: float,
    ) -> str:
        """Generate comprehensive reasoning for the classification."""
        reasoning_parts = []

        reasoning_parts.append(f"Pipeline confidence: {confidence:.2f}")

        # Claude reasoning
        if claude_result:
            reasoning_parts.append(
                f"Claude (weight: {weights.get('claude', 0):.2f}): {claude_result.label.value} (confidence: {claude_result.confidence:.2f})"
            )
            if claude_result.explanation:
                reasoning_parts.append(
                    f"Claude explanation: {claude_result.explanation[:200]}..."
                )

        # Rule-based reasoning
        if rule_based_result:
            reasoning_parts.append(
                f"Rule-based (weight: {weights.get('rule_based', 0):.2f}): {rule_based_result.classification.value} (confidence: {rule_based_result.confidence:.2f})"
            )
            if (
                hasattr(rule_based_result, "triggered_rules")
                and rule_based_result.triggered_rules
            ):
                # Handle both actual triggered_rules list and Mock objects
                if hasattr(
                    rule_based_result.triggered_rules, "__iter__"
                ) and not isinstance(rule_based_result.triggered_rules, str):
                    try:
                        rules_list = list(rule_based_result.triggered_rules)
                        reasoning_parts.append(
                            f"Triggered rules: {', '.join(rules_list[:3])}"
                        )
                    except (TypeError, AttributeError):
                        reasoning_parts.append("Triggered rules: [mock data]")
                else:
                    reasoning_parts.append("Triggered rules: [mock data]")

        # Semantic reasoning
        if semantic_analysis:
            reasoning_parts.append(
                f"Semantic analysis (weight: {weights.get('semantic', 0):.2f})"
            )
            summary = semantic_analysis.get("change_summary", {})
            if summary:
                reasoning_parts.append(
                    f"Semantic risk: {summary.get('risk_level', 'unknown')}"
                )

        return ". ".join(reasoning_parts)


# Global pipeline instance
_classification_pipeline: Optional[ClassificationPipeline] = None


async def get_classification_pipeline() -> ClassificationPipeline:
    """Get or create the global classification pipeline."""
    global _classification_pipeline

    if _classification_pipeline is None:
        _classification_pipeline = ClassificationPipeline()

    return _classification_pipeline


def cleanup_classification_pipeline() -> None:
    """Clean up the global classification pipeline."""
    global _classification_pipeline
    _classification_pipeline = None
