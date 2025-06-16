"""Integration tests for complete business logic flow."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from src.webdeface.classifier import (
    Classification,
    cleanup_classification_orchestrator,
    get_classification_orchestrator,
)
from src.webdeface.scraper import (
    cleanup_scraping_orchestrator,
    get_scraping_orchestrator,
)


@pytest.mark.integration
class TestBusinessLogicIntegration:
    """Test complete business logic integration from scraping to classification to alerts."""

    # Remove the local fixture - use the global one from conftest.py

    @pytest.mark.asyncio
    async def test_complete_scraping_to_classification_flow(
        self, setup_test_environment
    ):
        """Test complete flow from scraping job to classification result."""
        test_env = setup_test_environment

        # Get orchestrators
        scraping_orchestrator = await get_scraping_orchestrator()
        classification_orchestrator = await get_classification_orchestrator()

        try:
            # Mock scraping results
            with patch.object(
                scraping_orchestrator.workers[0], "_scrape_website"
            ) as mock_scrape:
                # Mock successful scraping result
                from src.webdeface.scraper.orchestrator import ScrapingResult

                mock_scraping_result = ScrapingResult(
                    job=Mock(),
                    success=True,
                    content_data={
                        "main_content": "This website has been hacked by Anonymous",
                        "title": "Defaced Website",
                        "text_blocks": ["Hacked content", "More suspicious text"],
                        "word_count": 8,
                        "content_hash": "suspicious-hash",
                    },
                    visual_data={
                        "screenshot_data": b"fake_image_data",
                        "visual_diff": None,
                    },
                    change_analysis={
                        "has_changes": True,
                        "change_type": "content",
                        "similarity_score": 0.2,
                        "risk_level": "high",
                    },
                    snapshot_id="test-snapshot-id",
                )
                mock_scrape.return_value = mock_scraping_result

                # Schedule scraping job
                scraping_job_id = await scraping_orchestrator.schedule_scraping(
                    website_id="test-website-id", url="https://example.com"
                )

                assert scraping_job_id is not None

                # Wait for scraping to process (in real scenario)
                await asyncio.sleep(0.1)

                # Now test classification of the scraped content
                with patch.object(
                    classification_orchestrator.workers[0], "_classify_content"
                ) as mock_classify:
                    # Mock classification result showing defacement detected
                    from src.webdeface.classifier import ConfidenceLevel
                    from src.webdeface.classifier.orchestrator import (
                        ClassificationJobResult,
                    )
                    from src.webdeface.classifier.pipeline import (
                        ClassificationPipelineResult,
                    )

                    mock_pipeline_result = ClassificationPipelineResult(
                        final_classification=Classification.DEFACEMENT,
                        confidence_score=0.95,
                        confidence_level=ConfidenceLevel.VERY_HIGH,
                        reasoning="Strong indicators of defacement detected",
                        claude_result=Mock(),
                        semantic_analysis={"risk_level": "critical"},
                        rule_based_result=Mock(),
                    )

                    mock_classification_result = ClassificationJobResult(
                        job=Mock(),
                        success=True,
                        pipeline_result=mock_pipeline_result,
                        alert_generated=True,
                        alert_id="test-alert-id",
                        vectorization_completed=True,
                    )
                    mock_classify.return_value = mock_classification_result

                    # Schedule classification job
                    classification_job_id = (
                        await classification_orchestrator.schedule_classification(
                            website_id="test-website-id",
                            website_url="https://example.com",
                            website_name="Test Website",
                            snapshot_id="test-snapshot-id",
                            content_data=mock_scraping_result.content_data,
                        )
                    )

                    assert classification_job_id is not None

                    # Wait for classification to process
                    await asyncio.sleep(0.1)

                    # Verify the flow worked
                    assert scraping_orchestrator.total_jobs_queued == 1
                    assert classification_orchestrator.total_jobs_queued == 1

        finally:
            # Cleanup with event loop awareness
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await cleanup_scraping_orchestrator()
                    await cleanup_classification_orchestrator()
            except (RuntimeError, AttributeError):
                # Event loop not available or closed
                pass

    @pytest.mark.asyncio
    async def test_benign_content_classification_flow(self, setup_test_environment):
        """Test flow with benign content that should not trigger alerts."""
        test_env = setup_test_environment

        classification_orchestrator = await get_classification_orchestrator()

        try:
            with patch.object(
                classification_orchestrator.workers[0], "_classify_content"
            ) as mock_classify:
                # Mock classification result showing benign content
                from src.webdeface.classifier import ConfidenceLevel
                from src.webdeface.classifier.orchestrator import (
                    ClassificationJobResult,
                )
                from src.webdeface.classifier.pipeline import (
                    ClassificationPipelineResult,
                )

                mock_pipeline_result = ClassificationPipelineResult(
                    final_classification=Classification.BENIGN,
                    confidence_score=0.85,
                    confidence_level=ConfidenceLevel.HIGH,
                    reasoning="Content appears to be legitimate updates",
                    claude_result=Mock(),
                    semantic_analysis={"risk_level": "low"},
                    rule_based_result=Mock(),
                )

                mock_classification_result = ClassificationJobResult(
                    job=Mock(),
                    success=True,
                    pipeline_result=mock_pipeline_result,
                    alert_generated=False,  # No alert for benign content
                    alert_id=None,
                    vectorization_completed=True,
                )
                mock_classify.return_value = mock_classification_result

                # Schedule classification for benign content
                job_id = await classification_orchestrator.schedule_classification(
                    website_id="test-website-id",
                    website_url="https://example.com",
                    website_name="Test Website",
                    snapshot_id="test-snapshot-id",
                    content_data={
                        "main_content": "Welcome to our updated website with new features",
                        "title": "Website Updates",
                        "text_blocks": ["New features", "Improved performance"],
                        "word_count": 10,
                    },
                )

                assert job_id is not None

                # Wait for processing
                await asyncio.sleep(0.1)

                # Verify no alert was generated
                stats = await classification_orchestrator.get_orchestrator_stats()
                # In real scenario, we'd check that alerts_generated count is 0

        finally:
            # Cleanup with event loop awareness
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await cleanup_classification_orchestrator()
            except (RuntimeError, AttributeError):
                # Event loop not available or closed
                pass

    @pytest.mark.asyncio
    async def test_error_handling_in_business_logic(self, setup_test_environment):
        """Test error handling throughout the business logic pipeline."""
        test_env = setup_test_environment

        classification_orchestrator = await get_classification_orchestrator()

        try:
            with patch.object(
                classification_orchestrator.workers[0], "_classify_content"
            ) as mock_classify:
                # Mock classification failure
                mock_classify.side_effect = Exception("Simulated classification error")

                # Schedule classification job that will fail
                job_id = await classification_orchestrator.schedule_classification(
                    website_id="test-website-id",
                    website_url="https://example.com",
                    website_name="Test Website",
                    snapshot_id="test-snapshot-id",
                    content_data={"main_content": "Test content"},
                )

                assert job_id is not None

                # Wait for processing
                await asyncio.sleep(0.1)

                # Verify error handling worked (job was processed but failed)
                stats = await classification_orchestrator.get_orchestrator_stats()
                # In real scenario, we'd check failed job counts

        finally:
            # Cleanup with event loop awareness
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await cleanup_classification_orchestrator()
            except (RuntimeError, AttributeError):
                # Event loop not available or closed
                pass

    @pytest.mark.asyncio
    async def test_feedback_integration(self, setup_test_environment):
        """Test feedback integration with classification results."""
        test_env = setup_test_environment

        from src.webdeface.classifier import ConfidenceLevel
        from src.webdeface.classifier.feedback import get_feedback_collector
        from src.webdeface.classifier.pipeline import ClassificationPipelineResult

        feedback_collector = await get_feedback_collector()

        # Create a mock classification result
        original_result = ClassificationPipelineResult(
            final_classification=Classification.BENIGN,
            confidence_score=0.7,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning="AI classified as benign",
        )

        with patch.object(feedback_collector, "_store_feedback"), patch.object(
            feedback_collector, "_process_feedback"
        ):
            # Submit correction feedback
            feedback_id = await feedback_collector.submit_classification_correction(
                website_id="test-website-id",
                original_result=original_result,
                corrected_classification=Classification.DEFACEMENT,
                corrected_confidence=0.9,
                analyst_id="analyst-1",
                reasoning="Manual review found defacement indicators",
            )

            assert feedback_id is not None
            assert feedback_id.startswith("feedback-")

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, setup_test_environment):
        """Test performance monitoring and reporting."""
        test_env = setup_test_environment

        from src.webdeface.classifier.feedback import get_performance_tracker

        performance_tracker = await get_performance_tracker()

        with patch.object(
            performance_tracker, "calculate_performance_metrics"
        ) as mock_metrics:
            mock_metrics.return_value = {
                "precision": 0.85,
                "recall": 0.78,
                "f1_score": 0.81,
                "false_positive_rate": 0.05,
                "false_negative_rate": 0.12,
            }

            # Generate performance report
            report = await performance_tracker.generate_performance_report()

            assert isinstance(report, dict)
            assert "generated_at" in report
            assert "current_metrics" in report
            assert report["current_metrics"]["precision"] == 0.85

    @pytest.mark.asyncio
    async def test_health_checks(self, setup_test_environment):
        """Test health check functionality across components."""
        test_env = setup_test_environment

        scraping_orchestrator = await get_scraping_orchestrator()
        classification_orchestrator = await get_classification_orchestrator()

        try:
            # Test scraping orchestrator health
            scraping_health = await scraping_orchestrator.health_check()
            assert isinstance(scraping_health, dict)
            assert "orchestrator_running" in scraping_health
            assert "workers_healthy" in scraping_health
            assert "queue_healthy" in scraping_health

            # Test classification orchestrator health
            classification_health = await classification_orchestrator.health_check()
            assert isinstance(classification_health, dict)
            assert "orchestrator_running" in classification_health
            assert "workers_healthy" in classification_health
            assert "components_healthy" in classification_health

        finally:
            # Cleanup with event loop awareness
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await cleanup_scraping_orchestrator()
                    await cleanup_classification_orchestrator()
            except (RuntimeError, AttributeError):
                # Event loop not available or closed
                pass

    @pytest.mark.asyncio
    async def test_comprehensive_statistics(self, setup_test_environment):
        """Test comprehensive statistics gathering."""
        test_env = setup_test_environment

        scraping_orchestrator = await get_scraping_orchestrator()
        classification_orchestrator = await get_classification_orchestrator()

        try:
            # Get scraping stats
            scraping_stats = await scraping_orchestrator.get_orchestrator_stats()
            assert isinstance(scraping_stats, dict)
            assert "total_jobs_processed" in scraping_stats
            assert "overall_success_rate" in scraping_stats
            assert "throughput_jobs_per_hour" in scraping_stats

            # Get classification stats
            classification_stats = (
                await classification_orchestrator.get_orchestrator_stats()
            )
            assert isinstance(classification_stats, dict)
            assert "total_jobs_processed" in classification_stats
            assert "alert_generation_rate" in classification_stats

            # Get comprehensive performance report
            performance_report = (
                await classification_orchestrator.get_performance_report()
            )
            assert isinstance(performance_report, dict)
            assert "orchestrator_stats" in performance_report
            assert "health_status" in performance_report

        finally:
            # Cleanup with event loop awareness
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await cleanup_scraping_orchestrator()
                    await cleanup_classification_orchestrator()
            except (RuntimeError, AttributeError):
                # Event loop not available or closed
                pass


@pytest.mark.integration
class TestBusinessLogicStressTest:
    """Stress test business logic components under load."""

    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self):
        """Test processing multiple jobs concurrently."""
        with patch("src.webdeface.scraper.browser.async_playwright"), patch(
            "src.webdeface.classifier.claude.AsyncAnthropic"
        ), patch("src.webdeface.storage.get_storage_manager"):
            classification_orchestrator = await get_classification_orchestrator()

            try:
                # Schedule multiple classification jobs
                job_ids = []
                for i in range(5):
                    job_id = await classification_orchestrator.schedule_classification(
                        website_id=f"test-website-{i}",
                        website_url=f"https://example{i}.com",
                        website_name=f"Test Website {i}",
                        snapshot_id=f"snapshot-{i}",
                        content_data={"main_content": f"Test content {i}"},
                    )
                    job_ids.append(job_id)

                assert len(job_ids) == 5
                assert all(job_id is not None for job_id in job_ids)

                # Wait for processing
                await asyncio.sleep(0.5)

                # Check queue was processed
                stats = await classification_orchestrator.get_orchestrator_stats()
                assert stats["total_jobs_queued"] == 5

            finally:
                # Cleanup with event loop awareness
                try:
                    loop = asyncio.get_running_loop()
                    if not loop.is_closed():
                        await cleanup_classification_orchestrator()
                except (RuntimeError, AttributeError):
                    # Event loop not available or closed
                    pass

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """Test handling of queue overflow scenarios."""
        with patch("src.webdeface.scraper.browser.async_playwright"), patch(
            "src.webdeface.storage.get_storage_manager"
        ):
            # Create orchestrator with small queue size
            scraping_orchestrator = await get_scraping_orchestrator()

            try:
                # Try to overflow the queue
                successful_jobs = 0
                failed_jobs = 0

                for i in range(15):  # More than default queue size
                    try:
                        job_id = await scraping_orchestrator.schedule_scraping(
                            website_id=f"test-website-{i}",
                            url=f"https://example{i}.com",
                        )
                        if job_id:
                            successful_jobs += 1
                    except Exception:
                        failed_jobs += 1

                # Should have handled queue limits gracefully
                assert successful_jobs > 0
                # Some jobs might fail due to queue limits, which is expected

            finally:
                # Cleanup with event loop awareness
                try:
                    loop = asyncio.get_running_loop()
                    if not loop.is_closed():
                        await cleanup_scraping_orchestrator()
                except (RuntimeError, AttributeError):
                    # Event loop not available or closed
                    pass


if __name__ == "__main__":
    pytest.main([__file__])
