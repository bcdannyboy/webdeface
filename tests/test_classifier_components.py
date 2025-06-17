"""Comprehensive tests for classifier business logic components."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.webdeface.classifier import (
    AlertContext,
    AlertGenerator,
    AlertSeverity,
    AlertType,
    Classification,
    ClassificationOrchestrator,
    EnhancedClassificationPipeline,
    ClassificationRequest,
    ClassificationResult,
    ClaudeClient,
    AdvancedConfidenceCalculator,
    ConfidenceLevel,
    ContentVector,
    ContentVectorizer,
    DefacementPromptLibrary,
    FeedbackCollector,
    ModelPerformanceTracker,
    ComprehensiveRuleBasedClassifier,
)
from src.webdeface.classifier.pipeline import ThreatCategory


class TestClassification:
    """Test the Classification enum and related types."""

    def test_classification_enum_values(self):
        """Test classification enum has correct values."""
        assert Classification.BENIGN.value == "benign"
        assert Classification.DEFACEMENT.value == "defacement"
        assert Classification.UNCLEAR.value == "unclear"

    def test_classification_result_creation(self):
        """Test ClassificationResult creation."""
        result = ClassificationResult(
            label=Classification.DEFACEMENT,
            explanation="Test explanation",
            confidence=0.85,
        )

        assert result.label == Classification.DEFACEMENT
        assert result.explanation == "Test explanation"
        assert result.confidence == 0.85
        assert result.classified_at is not None


class TestDefacementPromptLibrary:
    """Test the DefacementPromptLibrary implementation."""

    @pytest.fixture
    def prompt_library(self):
        return DefacementPromptLibrary()

    def test_prompt_library_initialization(self, prompt_library):
        """Test prompt library is properly initialized."""
        assert len(prompt_library.prompts) > 0
        assert "general_analysis" in prompt_library.prompts
        assert "content_injection" in prompt_library.prompts
        assert "visual_defacement" in prompt_library.prompts

    def test_get_prompt(self, prompt_library):
        """Test getting prompts from library."""
        general_prompt = prompt_library.get_prompt("general_analysis")
        assert general_prompt is not None
        assert hasattr(general_prompt, "system_prompt")
        assert hasattr(general_prompt, "user_prompt_template")

        # Test default fallback
        default_prompt = prompt_library.get_prompt("nonexistent")
        assert default_prompt == prompt_library.prompts["general_analysis"]

    def test_list_available_prompts(self, prompt_library):
        """Test listing available prompts."""
        prompts = prompt_library.list_available_prompts()
        assert isinstance(prompts, list)
        assert "general_analysis" in prompts
        assert len(prompts) >= 3


class TestClaudeClient:
    """Test the ClaudeClient implementation."""

    @pytest.fixture
    def claude_client(self):
        with patch("src.webdeface.classifier.claude.get_settings") as mock_settings:
            mock_claude_settings = Mock()
            mock_claude_settings.api_key.get_secret_value.return_value = "test-key"
            mock_claude_settings.model = "claude-3-sonnet-20240229"
            mock_claude_settings.max_tokens = 4000
            mock_claude_settings.temperature = 0.1

            mock_settings.return_value.claude = mock_claude_settings
            return ClaudeClient()

    @pytest.mark.asyncio
    async def test_claude_client_initialization(self, claude_client):
        """Test Claude client initialization."""
        assert claude_client.prompt_library is not None
        assert claude_client.client is None  # Not initialized until first use

    @pytest.mark.asyncio
    async def test_classify_content(self, claude_client):
        """Test content classification with Claude."""
        # Mock the Claude client completely to prevent real API calls
        with patch("src.webdeface.classifier.claude.AsyncAnthropic") as mock_anthropic_class:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic_class.return_value = mock_anthropic_instance
            
            # Mock Claude API response
            mock_response = Mock()
            mock_response.content = [
                Mock(
                    text='{"classification": "defacement", "confidence": 0.9, "reasoning": "Test"}'
                )
            ]
            mock_response.usage = Mock()
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 50

            mock_anthropic_instance.messages.create = AsyncMock(return_value=mock_response)

            result = await claude_client.classify_content(
                changed_content=["Hacked by test"],
                static_context=["Original content"],
                site_url="https://example.com",
            )

            assert isinstance(result, ClassificationResult)
            assert result.label == Classification.DEFACEMENT
            assert result.confidence == 0.9
            assert result.tokens_used == 150
            
            # Verify no real API calls were made
            mock_anthropic_instance.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_classify(self, claude_client):
        """Test batch classification."""
        # Mock the Claude client completely to prevent any real API calls
        with patch("src.webdeface.classifier.claude.AsyncAnthropic") as mock_anthropic_class:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic_class.return_value = mock_anthropic_instance
            
            # Mock response for each call
            mock_response = Mock()
            mock_response.content = [Mock(text='{"classification": "benign", "confidence": 0.7, "reasoning": "Test"}')]
            mock_response.usage = Mock()
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 50
            
            mock_anthropic_instance.messages.create = AsyncMock(return_value=mock_response)

            requests = [
                {
                    "changed_content": ["Content 1"],
                    "static_context": ["Context 1"],
                    "site_url": "https://example1.com",
                },
                {
                    "changed_content": ["Content 2"],
                    "static_context": ["Context 2"],
                    "site_url": "https://example2.com",
                },
            ]

            results = await claude_client.batch_classify(requests)

            assert len(results) == 2
            assert all(isinstance(r, ClassificationResult) for r in results)
            # Verify that no real API calls were made, only mocked ones
            assert mock_anthropic_instance.messages.create.call_count >= 2


class TestContentVectorizer:
    """Test the ContentVectorizer implementation."""

    @pytest.fixture
    def vectorizer(self):
        return ContentVectorizer()

    def test_preprocess_text(self, vectorizer):
        """Test text preprocessing."""
        text = "  This is a <b>test</b> with HTML tags and   extra spaces!  "
        processed = vectorizer._preprocess_text(text)

        assert "<b>" not in processed
        assert "</b>" not in processed
        assert processed.strip() == processed
        assert "  " not in processed  # No double spaces

    def test_split_long_content(self, vectorizer):
        """Test splitting long content into chunks."""
        short_text = "Short text that doesn't need splitting."
        chunks = vectorizer._split_long_content(short_text)
        assert len(chunks) == 1
        assert chunks[0] == short_text

        # Create long text
        long_text = "Long sentence. " * 100  # Create text longer than threshold
        chunks = vectorizer._split_long_content(long_text)
        assert len(chunks) > 1

    @pytest.mark.asyncio
    async def test_vectorize_content(self, vectorizer):
        """Test content vectorization."""
        with patch.object(vectorizer, "_ensure_model"), patch.object(
            vectorizer, "model"
        ) as mock_model:
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.rand(384)

            content = "This is test content for vectorization"
            vector = await vectorizer.vectorize_content(content)

            assert isinstance(vector, ContentVector)
            assert len(vector.vector) == 384
            assert vector.content_type == "text"
            assert vector.model_name == vectorizer.model_name


class TestRuleBasedClassifier:
    """Test the ComprehensiveRuleBasedClassifier implementation."""

    @pytest.fixture
    def classifier(self):
        return ComprehensiveRuleBasedClassifier()

    def test_defacement_detection(self, classifier):
        """Test detection of defacement keywords."""
        defacement_content = ["This website has been hacked by Anonymous"]
        result = classifier.classify(defacement_content)

        assert result.classification == Classification.DEFACEMENT
        assert result.confidence > 0.5
        assert len(result.triggered_rules) > 0
        assert any("hacked" in rule for rule in result.triggered_rules)

    def test_benign_content_detection(self, classifier):
        """Test detection of benign content."""
        benign_content = ["Welcome to our website. Check our latest news and updates."]
        result = classifier.classify(benign_content)

        # Should not be classified as defacement
        assert result.classification != Classification.DEFACEMENT
        assert result.confidence >= 0.0

    def test_mixed_content(self, classifier):
        """Test content with both suspicious and benign indicators."""
        mixed_content = ["Site maintenance update: Our privacy policy has been updated"]
        result = classifier.classify(mixed_content)

        # Should handle mixed signals appropriately
        assert isinstance(result.classification, Classification)
        assert 0.0 <= result.confidence <= 1.0


class TestConfidenceCalculator:
    """Test the AdvancedConfidenceCalculator implementation."""

    @pytest.fixture
    def calculator(self):
        return AdvancedConfidenceCalculator()

    def test_calculate_agreement(self, calculator):
        """Test agreement calculation between classifiers."""
        # Mock results with high agreement
        claude_result = Mock()
        claude_result.label = Classification.DEFACEMENT

        rule_result = Mock()
        rule_result.classification = Classification.DEFACEMENT

        results = {"claude": claude_result, "rule_based": rule_result}
        agreement = calculator._calculate_agreement(results)

        assert agreement >= 0.5  # High agreement expected

    def test_calculate_confidence(self, calculator):
        """Test overall confidence calculation."""
        claude_result = ClassificationResult(
            label=Classification.DEFACEMENT, explanation="Test", confidence=0.9
        )

        rule_result = Mock()
        rule_result.confidence = 0.8
        rule_result.classification = Classification.DEFACEMENT
        rule_result.threat_indicators = []  # Empty list for mock
        rule_result.threat_category = ThreatCategory.DEFACEMENT

        confidence, weights, metrics = calculator.calculate_confidence(
            claude_result=claude_result,
            semantic_analysis=None,
            rule_based_result=rule_result,
        )

        assert 0.0 <= confidence <= 1.0
        assert isinstance(weights, dict)
        assert isinstance(metrics, dict)

    def test_get_confidence_level(self, calculator):
        """Test confidence level categorization."""
        assert calculator.get_confidence_level(0.9) == ConfidenceLevel.VERY_HIGH
        assert calculator.get_confidence_level(0.7) == ConfidenceLevel.HIGH
        assert calculator.get_confidence_level(0.5) == ConfidenceLevel.MEDIUM
        assert calculator.get_confidence_level(0.3) == ConfidenceLevel.LOW
        assert calculator.get_confidence_level(0.1) == ConfidenceLevel.VERY_LOW


class TestClassificationPipeline:
    """Test the EnhancedClassificationPipeline implementation."""

    @pytest.fixture
    def pipeline(self):
        return EnhancedClassificationPipeline()

    @pytest.mark.asyncio
    async def test_classification_pipeline(self, pipeline):
        """Test complete classification pipeline."""
        request = ClassificationRequest(
            changed_content=["Test content that might be suspicious"],
            static_context=["Original website content"],
            site_url="https://example.com",
        )

        with patch.object(
            pipeline, "_run_claude_classification"
        ) as mock_claude, patch.object(
            pipeline, "_run_semantic_analysis"
        ) as mock_semantic, patch.object(
            pipeline, "_run_rule_based_classification"
        ) as mock_rule:
            # Mock classifier results
            mock_claude.return_value = ClassificationResult(
                label=Classification.BENIGN, explanation="Test", confidence=0.8
            )

            mock_semantic.return_value = {
                "change_summary": {"risk_level": "low"},
                "semantic_similarity": {"main_content": 0.9},
            }

            mock_rule_result = Mock()
            mock_rule_result.classification = Classification.BENIGN
            mock_rule_result.confidence = 0.7
            mock_rule_result.threat_indicators = []  # Empty list for mock
            mock_rule_result.threat_category = ThreatCategory.UNKNOWN
            mock_rule.return_value = mock_rule_result

            result = await pipeline.classify(request)

            assert result is not None
            assert hasattr(result, "final_classification")
            assert hasattr(result, "confidence_score")
            assert hasattr(result, "confidence_level")


class TestAlertGenerator:
    """Test the AlertGenerator implementation."""

    @pytest.fixture
    def alert_generator(self):
        return AlertGenerator()

    @pytest.mark.asyncio
    async def test_alert_generation(self, alert_generator):
        """Test alert generation for defacement detection."""
        from src.webdeface.classifier.pipeline import ClassificationPipelineResult

        pipeline_result = ClassificationPipelineResult(
            final_classification=Classification.DEFACEMENT,
            confidence_score=0.9,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            reasoning="Test reasoning",
            threat_category=ThreatCategory.DEFACEMENT,
        )

        context = AlertContext(
            website_id="test-site",
            website_url="https://example.com",
            website_name="Test Site",
        )

        alert = await alert_generator.generate_alert(pipeline_result, context)

        assert alert is not None
        assert alert.alert_type == AlertType.DEFACEMENT_DETECTED
        assert alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        assert "defacement" in alert.title.lower()

    def test_suppression_logic(self, alert_generator):
        """Test alert suppression logic."""
        context = AlertContext(
            website_id="test-site",
            website_url="https://example.com",
            website_name="Test Site",
        )

        suppression_key = alert_generator._generate_suppression_key(
            context, AlertType.DEFACEMENT_DETECTED
        )

        # First alert should not be suppressed
        is_suppressed = alert_generator._is_suppressed(
            suppression_key, AlertSeverity.HIGH
        )
        assert not is_suppressed

        # Mark as recently alerted
        alert_generator.recent_alerts[suppression_key] = datetime.utcnow()

        # Second alert should be suppressed
        is_suppressed = alert_generator._is_suppressed(
            suppression_key, AlertSeverity.HIGH
        )
        assert is_suppressed


class TestFeedbackCollector:
    """Test the FeedbackCollector implementation."""

    @pytest.fixture
    def feedback_collector(self):
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_submit_classification_correction(self, feedback_collector):
        """Test submitting classification correction feedback."""
        from src.webdeface.classifier.pipeline import ClassificationPipelineResult

        original_result = ClassificationPipelineResult(
            final_classification=Classification.BENIGN,
            confidence_score=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning="Original reasoning",
            threat_category=ThreatCategory.UNKNOWN,
        )

        with patch.object(feedback_collector, "_store_feedback"), patch.object(
            feedback_collector, "_process_feedback"
        ):
            feedback_id = await feedback_collector.submit_classification_correction(
                website_id="test-site",
                original_result=original_result,
                corrected_classification=Classification.DEFACEMENT,
                corrected_confidence=0.9,
                analyst_id="analyst-1",
                reasoning="Manual review found defacement",
            )

            assert feedback_id is not None
            assert feedback_id.startswith("feedback-")

    @pytest.mark.asyncio
    async def test_submit_false_positive_feedback(self, feedback_collector):
        """Test submitting false positive feedback."""
        with patch.object(feedback_collector, "_store_feedback"), patch.object(
            feedback_collector, "_process_feedback"
        ):
            feedback_id = await feedback_collector.submit_false_positive_feedback(
                website_id="test-site",
                snapshot_id="snapshot-123",
                alert_id="alert-123",
                analyst_id="analyst-1",
                reasoning="Alert was incorrect",
            )

            assert feedback_id is not None
            assert feedback_id.startswith("feedback-fp-")


class TestModelPerformanceTracker:
    """Test the ModelPerformanceTracker implementation."""

    @pytest.fixture
    def performance_tracker(self):
        return ModelPerformanceTracker()

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, performance_tracker):
        """Test performance metrics calculation."""
        with patch(
            "src.webdeface.classifier.feedback.get_feedback_collector"
        ) as mock_get_collector:
            mock_collector = Mock()
            mock_collector.feedback_storage = {}
            mock_get_collector.return_value = mock_collector

            metrics = await performance_tracker.calculate_performance_metrics()

            assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_generate_performance_report(self, performance_tracker):
        """Test performance report generation."""
        with patch.object(
            performance_tracker, "calculate_performance_metrics"
        ) as mock_metrics, patch.object(
            performance_tracker, "get_performance_trends"
        ) as mock_trends, patch(
            "src.webdeface.classifier.feedback.get_feedback_collector"
        ) as mock_get_collector:
            mock_metrics.return_value = {"precision": 0.8, "recall": 0.7}
            mock_trends.return_value = {"precision": [0.7, 0.8, 0.8]}

            mock_collector = Mock()
            mock_collector.feedback_storage = {}
            mock_get_collector.return_value = mock_collector

            report = await performance_tracker.generate_performance_report()

            assert isinstance(report, dict)
            assert "generated_at" in report
            assert "current_metrics" in report
            assert "performance_trends" in report


class TestClassificationOrchestrator:
    """Test the ClassificationOrchestrator implementation."""

    @pytest.fixture
    def orchestrator(self):
        return ClassificationOrchestrator(max_workers=1, max_queue_size=10)

    @pytest.mark.asyncio
    async def test_orchestrator_setup(self, orchestrator):
        """Test orchestrator setup and initialization."""
        await orchestrator.setup()

        assert orchestrator.is_running
        assert len(orchestrator.workers) == 1
        assert len(orchestrator.worker_tasks) == 1

    @pytest.mark.asyncio
    async def test_schedule_classification(self, orchestrator):
        """Test scheduling a classification job."""
        await orchestrator.setup()

        job_id = await orchestrator.schedule_classification(
            website_id="test-site",
            website_url="https://example.com",
            website_name="Test Site",
            snapshot_id="snapshot-123",
            content_data={"main_content": "Test content"},
        )

        assert job_id is not None
        assert job_id.startswith("classification-")
        assert orchestrator.total_jobs_queued == 1

    @pytest.mark.asyncio
    async def test_orchestrator_cleanup(self, orchestrator):
        """Test orchestrator cleanup."""
        await orchestrator.setup()
        await orchestrator.cleanup()

        assert not orchestrator.is_running
        assert len(orchestrator.workers) == 0
        assert len(orchestrator.worker_tasks) == 0


@pytest.mark.integration
class TestClassifierIntegration:
    """Integration tests for classifier components."""

    @pytest.mark.asyncio
    async def test_end_to_end_classification(self):
        """Test end-to-end classification pipeline."""
        # This would test the complete flow from content input to alert generation
        request = ClassificationRequest(
            changed_content=["Suspicious content that might indicate defacement"],
            static_context=["Original website content"],
            site_url="https://example.com",
        )

        # Mock external dependencies
        with patch("src.webdeface.classifier.claude.AsyncAnthropic"), patch(
            "src.webdeface.classifier.vectorizer.SentenceTransformer"
        ), patch("src.webdeface.classifier.alerts.get_storage_manager"), patch(
            "src.webdeface.classifier.alerts.get_slack_delivery_manager"
        ):
            from src.webdeface.classifier.pipeline import get_classification_pipeline

            pipeline = await get_classification_pipeline()

            # Mock the individual classifier components
            with patch.object(
                pipeline, "_run_claude_classification"
            ) as mock_claude, patch.object(
                pipeline, "_run_semantic_analysis"
            ) as mock_semantic, patch.object(
                pipeline, "_run_rule_based_classification"
            ) as mock_rule:
                # Set up mock returns
                mock_claude.return_value = ClassificationResult(
                    label=Classification.DEFACEMENT,
                    explanation="AI detected defacement patterns",
                    confidence=0.9,
                )

                mock_semantic.return_value = {
                    "change_summary": {"risk_level": "high"},
                    "semantic_similarity": {"main_content": 0.3},
                }

                mock_rule_result = Mock()
                mock_rule_result.classification = Classification.DEFACEMENT
                mock_rule_result.confidence = 0.8
                mock_rule_result.threat_indicators = []  # Empty list for mock
                mock_rule_result.threat_category = ThreatCategory.DEFACEMENT
                mock_rule.return_value = mock_rule_result

                # Run classification
                result = await pipeline.classify(request)

                # Verify results
                assert result is not None
                assert result.final_classification == Classification.DEFACEMENT
                assert result.confidence_score > 0.0

    @pytest.mark.asyncio
    async def test_alert_generation_integration(self):
        """Test alert generation integration."""
        from src.webdeface.classifier.alerts import get_alert_generator
        from src.webdeface.classifier.pipeline import ClassificationPipelineResult

        pipeline_result = ClassificationPipelineResult(
            final_classification=Classification.DEFACEMENT,
            confidence_score=0.9,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            reasoning="High confidence defacement detection",
            threat_category=ThreatCategory.DEFACEMENT,
        )

        context = AlertContext(
            website_id="test-site",
            website_url="https://example.com",
            website_name="Test Site",
        )

        with patch("src.webdeface.classifier.alerts.get_storage_manager"), patch(
            "src.webdeface.classifier.alerts.get_slack_delivery_manager"
        ):
            alert_generator = await get_alert_generator()
            alert = await alert_generator.generate_alert(pipeline_result, context)

            assert alert is not None
            assert alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]


if __name__ == "__main__":
    pytest.main([__file__])
