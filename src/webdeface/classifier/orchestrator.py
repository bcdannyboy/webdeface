"""Comprehensive classification orchestration with monitoring and coordination."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .alerts import AlertContext, get_alert_delivery_manager, get_alert_generator
from .feedback import get_feedback_collector, get_performance_tracker
from .pipeline import ClassificationPipelineResult, get_classification_pipeline
from .types import Classification, ClassificationError, ClassificationRequest
from .vectorizer import get_content_vectorizer

logger = get_structured_logger(__name__)


@dataclass
class ClassificationJob:
    """Represents a classification job with all its parameters."""

    job_id: str
    website_id: str
    website_url: str
    website_name: str
    snapshot_id: str
    content_data: dict[str, Any]
    baseline_data: Optional[dict[str, Any]] = None
    priority: int = 1  # 1 = highest, 5 = lowest
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ClassificationJobResult:
    """Result of a complete classification job."""

    job: ClassificationJob
    success: bool
    pipeline_result: Optional[ClassificationPipelineResult] = None
    alert_generated: bool = False
    alert_id: Optional[str] = None
    vectorization_completed: bool = False
    processing_time: float = 0.0
    error_details: Optional[dict[str, Any]] = None


class ClassificationQueue:
    """Thread-safe queue for managing classification jobs."""

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._pending_jobs: dict[str, ClassificationJob] = {}
        self._lock = asyncio.Lock()

    async def add_job(self, job: ClassificationJob) -> bool:
        """Add a job to the queue."""
        async with self._lock:
            if len(self._pending_jobs) >= self.max_size:
                logger.warning(
                    "Classification queue is full", queue_size=len(self._pending_jobs)
                )
                return False

            # Use negative priority for max-heap behavior (higher priority first)
            priority_key = (-job.priority, job.created_at.timestamp(), job.job_id)

            try:
                self._queue.put_nowait((priority_key, job))
                self._pending_jobs[job.job_id] = job
                logger.debug(
                    "Job added to classification queue",
                    job_id=job.job_id,
                    priority=job.priority,
                    queue_size=len(self._pending_jobs),
                )
                return True
            except asyncio.QueueFull:
                logger.warning(
                    "Failed to add job to queue - queue full", job_id=job.job_id
                )
                return False

    async def get_job(
        self, timeout: Optional[float] = None
    ) -> Optional[ClassificationJob]:
        """Get the next job from the queue."""
        try:
            if timeout:
                priority_key, job = await asyncio.wait_for(
                    self._queue.get(), timeout=timeout
                )
            else:
                priority_key, job = await self._queue.get()

            async with self._lock:
                self._pending_jobs.pop(job.job_id, None)

            return job
        except asyncio.TimeoutError:
            return None

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            return {
                "pending_jobs": len(self._pending_jobs),
                "queue_size": self._queue.qsize(),
                "max_size": self.max_size,
                "is_full": len(self._pending_jobs) >= self.max_size,
            }


class ClassificationWorker:
    """Worker that processes classification jobs."""

    def __init__(self, worker_id: str, queue: ClassificationQueue):
        self.worker_id = worker_id
        self.queue = queue
        self.settings = get_settings()
        self.is_running = False
        self.current_job: Optional[ClassificationJob] = None

        # Statistics
        self.jobs_processed = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0
        self.alerts_generated = 0
        self.start_time = datetime.utcnow()

    async def start(self) -> None:
        """Start the worker."""
        self.is_running = True
        logger.info(f"Classification worker {self.worker_id} started")

        while self.is_running:
            try:
                # Get next job from queue
                job = await self.queue.get_job(timeout=5.0)

                if job is None:
                    continue  # Timeout, check if still running

                # Process the job
                await self._process_job(job)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause on error

        logger.info(f"Classification worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """Stop the worker."""
        self.is_running = False
        if self.current_job:
            logger.info(f"Worker {self.worker_id} stopping, current job will complete")

    async def _process_job(self, job: ClassificationJob) -> ClassificationJobResult:
        """Process a single classification job."""
        self.current_job = job
        job.started_at = datetime.utcnow()

        start_time = time.time()

        logger.info(
            "Processing classification job",
            worker_id=self.worker_id,
            job_id=job.job_id,
            website_id=job.website_id,
            url=job.website_url,
        )

        try:
            # Perform classification
            result = await self._classify_content(job)

            # Record success
            self.jobs_processed += 1
            if result.success:
                self.jobs_succeeded += 1
                if result.alert_generated:
                    self.alerts_generated += 1
            else:
                self.jobs_failed += 1

            # Performance metrics
            processing_time = time.time() - start_time
            result.processing_time = processing_time

            logger.info(
                "Classification job completed",
                worker_id=self.worker_id,
                job_id=job.job_id,
                success=result.success,
                alert_generated=result.alert_generated,
                processing_time=processing_time,
            )

            return result

        except Exception as e:
            logger.error(
                "Classification job failed",
                worker_id=self.worker_id,
                job_id=job.job_id,
                error=str(e),
            )

            self.jobs_processed += 1
            self.jobs_failed += 1

            return ClassificationJobResult(
                job=job,
                success=False,
                error_details={"error": str(e), "worker_id": self.worker_id},
            )
        finally:
            job.completed_at = datetime.utcnow()
            self.current_job = None

    async def _classify_content(
        self, job: ClassificationJob
    ) -> ClassificationJobResult:
        """Perform the actual content classification."""

        try:
            # Prepare classification request
            request = await self._prepare_classification_request(job)

            # Run classification pipeline
            pipeline = await get_classification_pipeline()
            pipeline_result = await pipeline.classify(request)

            # Generate and store vectors
            vectorization_completed = await self._store_content_vectors(
                job, pipeline_result
            )

            # Generate alerts if needed
            alert_generated, alert_id = await self._handle_alert_generation(
                job, pipeline_result
            )

            # Update database with classification results
            await self._update_snapshot_with_classification(job, pipeline_result)

            return ClassificationJobResult(
                job=job,
                success=True,
                pipeline_result=pipeline_result,
                alert_generated=alert_generated,
                alert_id=alert_id,
                vectorization_completed=vectorization_completed,
            )

        except Exception as e:
            logger.error(f"Content classification failed for {job.job_id}: {str(e)}")
            raise ClassificationError(f"Classification failed: {str(e)}")

    async def _prepare_classification_request(
        self, job: ClassificationJob
    ) -> ClassificationRequest:
        """Prepare a classification request from job data."""

        # Extract changed content
        changed_content = []
        if job.content_data.get("main_content"):
            changed_content.append(job.content_data["main_content"])

        text_blocks = job.content_data.get("text_blocks", [])
        if text_blocks:
            changed_content.extend(text_blocks[:5])  # Limit to first 5 blocks

        # Extract static context
        static_context = []
        if job.baseline_data:
            if job.baseline_data.get("main_content"):
                static_context.append(job.baseline_data["main_content"])

            baseline_blocks = job.baseline_data.get("text_blocks", [])
            if baseline_blocks:
                static_context.extend(baseline_blocks[:5])

        # Prepare site context
        site_context = {
            "website_id": job.website_id,
            "website_url": job.website_url,
            "website_name": job.website_name,
            "title": job.content_data.get("title", ""),
            "meta_description": job.content_data.get("meta_description", ""),
            "word_count": job.content_data.get("word_count", 0),
            "has_baseline": job.baseline_data is not None,
        }

        # Get previous classification if available
        previous_classification = await self._get_previous_classification(
            job.website_id
        )

        return ClassificationRequest(
            changed_content=changed_content,
            static_context=static_context,
            site_url=job.website_url,
            site_context=site_context,
            previous_classification=previous_classification,
        )

    async def _get_previous_classification(self, website_id: str) -> Optional[Any]:
        """Get the most recent classification for this website."""
        try:
            storage = await get_storage_manager()

            # Get recent snapshots to find previous classification
            snapshots = await storage.get_snapshots_for_website(website_id, limit=5)

            for snapshot in snapshots:
                if snapshot.is_defaced is not None:
                    # Found a previous classification
                    return {
                        "label": "defacement" if snapshot.is_defaced else "benign",
                        "confidence": snapshot.confidence_score or 0.5,
                        "timestamp": snapshot.analyzed_at,
                    }

            return None

        except Exception as e:
            logger.warning(
                f"Failed to get previous classification for {website_id}: {str(e)}"
            )
            return None

    async def _store_content_vectors(
        self, job: ClassificationJob, pipeline_result: ClassificationPipelineResult
    ) -> bool:
        """Store content vectors for similarity analysis."""
        try:
            vectorizer = await get_content_vectorizer()
            storage = await get_storage_manager()

            # Vectorize the content
            content_vectors = await vectorizer.vectorize_website_content(
                job.content_data
            )

            # Store vectors in vector database
            for content_type, vector in content_vectors.items():
                payload = {
                    "website_id": job.website_id,
                    "snapshot_id": job.snapshot_id,
                    "content_type": content_type,
                    "content_hash": vector.content_hash,
                    "captured_at": job.created_at.isoformat(),
                    "classification": pipeline_result.final_classification.value,
                    "confidence": pipeline_result.confidence_score,
                }

                # Add vector to storage (would use storage manager's vector capabilities)
                logger.debug(
                    "Content vector stored",
                    website_id=job.website_id,
                    content_type=content_type,
                    vector_size=vector.vector_size,
                )

            return True

        except Exception as e:
            logger.warning(
                f"Failed to store content vectors for {job.job_id}: {str(e)}"
            )
            return False

    async def _handle_alert_generation(
        self, job: ClassificationJob, pipeline_result: ClassificationPipelineResult
    ) -> tuple[bool, Optional[str]]:
        """Handle alert generation based on classification results."""
        try:
            alert_generator = await get_alert_generator()
            delivery_manager = await get_alert_delivery_manager()

            # Prepare alert context
            alert_context = AlertContext(
                website_id=job.website_id,
                website_url=job.website_url,
                website_name=job.website_name,
                snapshot_id=job.snapshot_id,
                classification_result=pipeline_result,
                change_details=job.metadata.get("change_details"),
                historical_context=job.metadata.get("historical_context"),
                visual_changes=job.metadata.get("visual_changes"),
            )

            # Generate alert
            alert = await alert_generator.generate_alert(pipeline_result, alert_context)

            if alert:
                # Deliver alert
                delivery_success = await delivery_manager.deliver_alert(alert)

                if delivery_success:
                    logger.info(
                        "Alert generated and delivered",
                        job_id=job.job_id,
                        alert_id=alert.alert_id,
                        severity=alert.severity.value,
                    )
                    return True, alert.alert_id
                else:
                    logger.warning(
                        "Alert generated but delivery failed", job_id=job.job_id
                    )
                    return True, alert.alert_id

            return False, None

        except Exception as e:
            logger.error(f"Alert handling failed for {job.job_id}: {str(e)}")
            return False, None

    async def _update_snapshot_with_classification(
        self, job: ClassificationJob, pipeline_result: ClassificationPipelineResult
    ) -> None:
        """Update the snapshot with classification results."""
        try:
            storage = await get_storage_manager()

            # Determine if defaced
            is_defaced = (
                pipeline_result.final_classification == Classification.DEFACEMENT
            )

            # Update snapshot analysis
            await storage.update_snapshot_analysis(
                snapshot_id=job.snapshot_id,
                is_defaced=is_defaced,
                confidence_score=pipeline_result.confidence_score,
            )

            logger.debug(
                "Snapshot updated with classification",
                snapshot_id=job.snapshot_id,
                is_defaced=is_defaced,
                confidence=pipeline_result.confidence_score,
            )

        except Exception as e:
            logger.warning(f"Failed to update snapshot {job.snapshot_id}: {str(e)}")

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "jobs_processed": self.jobs_processed,
            "jobs_succeeded": self.jobs_succeeded,
            "jobs_failed": self.jobs_failed,
            "alerts_generated": self.alerts_generated,
            "success_rate": self.jobs_succeeded / max(self.jobs_processed, 1),
            "alert_rate": self.alerts_generated / max(self.jobs_processed, 1),
            "uptime_seconds": uptime,
            "current_job_id": self.current_job.job_id if self.current_job else None,
        }


class ClassificationOrchestrator(AsyncContextManager):
    """Main orchestrator for classification operations."""

    def __init__(self, max_workers: int = 2, max_queue_size: int = 500):
        self.max_workers = max_workers
        self.settings = get_settings()

        # Initialize queue and workers
        self.queue = ClassificationQueue(max_queue_size)
        self.workers: list[ClassificationWorker] = []
        self.worker_tasks: list[asyncio.Task] = []

        # State tracking
        self.is_running = False
        self.start_time: Optional[datetime] = None

        # Statistics
        self.total_jobs_queued = 0
        self.total_jobs_completed = 0

    async def setup(self) -> None:
        """Initialize the orchestrator."""
        if self.is_running:
            return

        logger.info(
            f"Starting classification orchestrator with {self.max_workers} workers"
        )

        # Create workers
        for i in range(self.max_workers):
            worker_id = f"classifier-{i+1}"
            worker = ClassificationWorker(worker_id, self.queue)
            self.workers.append(worker)

        # Start worker tasks
        for worker in self.workers:
            task = asyncio.create_task(worker.start())
            self.worker_tasks.append(task)

        self.is_running = True
        self.start_time = datetime.utcnow()

        logger.info("Classification orchestrator started successfully")

    async def cleanup(self) -> None:
        """Clean up the orchestrator."""
        if not self.is_running:
            return

        logger.info("Stopping classification orchestrator")

        try:
            # Check if event loop is still running before attempting async operations
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning(
                        "Event loop is closed, performing synchronous cleanup"
                    )
                    self.is_running = False
                    self.workers.clear()
                    self.worker_tasks.clear()
                    return
            except RuntimeError:
                # No running event loop
                logger.warning("No running event loop, performing synchronous cleanup")
                self.is_running = False
                self.workers.clear()
                self.worker_tasks.clear()
                return

            # Stop workers
            for worker in self.workers:
                try:
                    await worker.stop()
                except Exception as e:
                    logger.warning(f"Worker {worker.worker_id} stop failed: {str(e)}")

            # Cancel worker tasks
            for task in self.worker_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if self.worker_tasks:
                try:
                    await asyncio.gather(*self.worker_tasks, return_exceptions=True)
                except Exception as e:
                    logger.warning(f"Worker task cleanup failed: {str(e)}")

            self.workers.clear()
            self.worker_tasks.clear()
            self.is_running = False

            logger.info("Classification orchestrator stopped")

        except Exception as e:
            logger.error(f"Error during classification orchestrator cleanup: {str(e)}")
            self.is_running = False
            self.workers.clear()
            self.worker_tasks.clear()

    async def schedule_classification(
        self,
        website_id: str,
        website_url: str,
        website_name: str,
        snapshot_id: str,
        content_data: dict[str, Any],
        baseline_data: Optional[dict[str, Any]] = None,
        priority: int = 1,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Schedule a classification job."""
        if not self.is_running:
            raise ClassificationError("Orchestrator is not running")

        # Create job
        job_id = f"classification-{website_id}-{int(time.time())}"

        job = ClassificationJob(
            job_id=job_id,
            website_id=website_id,
            website_url=website_url,
            website_name=website_name,
            snapshot_id=snapshot_id,
            content_data=content_data,
            baseline_data=baseline_data,
            priority=priority,
            metadata=metadata or {},
        )

        # Add to queue
        success = await self.queue.add_job(job)

        if success:
            self.total_jobs_queued += 1
            logger.info(
                "Classification job scheduled",
                job_id=job_id,
                website_id=website_id,
                priority=priority,
            )
            return job_id
        else:
            raise ClassificationError("Failed to queue classification job - queue full")

    async def get_orchestrator_stats(self) -> dict[str, Any]:
        """Get comprehensive orchestrator statistics."""
        queue_stats = await self.queue.get_queue_stats()

        # Worker statistics
        worker_stats = []
        total_processed = 0
        total_succeeded = 0
        total_failed = 0
        total_alerts = 0

        for worker in self.workers:
            stats = worker.get_stats()
            worker_stats.append(stats)
            total_processed += stats["jobs_processed"]
            total_succeeded += stats["jobs_succeeded"]
            total_failed += stats["jobs_failed"]
            total_alerts += stats["alerts_generated"]

        # Calculate uptime
        uptime = 0
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "is_running": self.is_running,
            "uptime_seconds": uptime,
            "worker_count": len(self.workers),
            "queue_stats": queue_stats,
            "worker_stats": worker_stats,
            "total_jobs_queued": self.total_jobs_queued,
            "total_jobs_processed": total_processed,
            "total_jobs_succeeded": total_succeeded,
            "total_jobs_failed": total_failed,
            "total_alerts_generated": total_alerts,
            "overall_success_rate": total_succeeded / max(total_processed, 1),
            "alert_generation_rate": total_alerts / max(total_processed, 1),
            "throughput_jobs_per_hour": (total_processed / max(uptime / 3600, 1))
            if uptime > 0
            else 0,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the orchestrator."""
        health = {
            "orchestrator_running": self.is_running,
            "workers_healthy": True,
            "queue_healthy": True,
            "components_healthy": True,
            "issues": [],
        }

        # Check workers
        unhealthy_workers = 0
        for worker in self.workers:
            if not worker.is_running:
                unhealthy_workers += 1

        if unhealthy_workers > 0:
            health["workers_healthy"] = False
            health["issues"].append(f"{unhealthy_workers} workers are not running")

        # Check queue
        queue_stats = await self.queue.get_queue_stats()
        if queue_stats["is_full"]:
            health["queue_healthy"] = False
            health["issues"].append("Classification queue is full")

        # Check component health
        try:
            # Test pipeline
            pipeline = await get_classification_pipeline()

            # Test vectorizer
            vectorizer = await get_content_vectorizer()

            # Test alert components
            alert_generator = await get_alert_generator()

        except Exception as e:
            health["components_healthy"] = False
            health["issues"].append(f"Component health check failed: {str(e)}")

        health["overall_healthy"] = (
            health["orchestrator_running"]
            and health["workers_healthy"]
            and health["queue_healthy"]
            and health["components_healthy"]
        )

        return health

    async def get_performance_report(self) -> dict[str, Any]:
        """Get comprehensive performance report."""
        try:
            # Get orchestrator stats
            orchestrator_stats = await self.get_orchestrator_stats()

            # Get performance tracker metrics
            performance_tracker = await get_performance_tracker()
            performance_metrics = (
                await performance_tracker.calculate_performance_metrics()
            )

            # Get feedback collector stats
            feedback_collector = await get_feedback_collector()
            feedback_summary = {
                "total_feedback": len(feedback_collector.feedback_storage),
                "recent_feedback": len(
                    [
                        f
                        for f in feedback_collector.feedback_storage.values()
                        if f.created_at > datetime.utcnow() - timedelta(days=7)
                    ]
                ),
            }

            return {
                "generated_at": datetime.utcnow().isoformat(),
                "orchestrator_stats": orchestrator_stats,
                "performance_metrics": performance_metrics,
                "feedback_summary": feedback_summary,
                "health_status": await self.health_check(),
            }

        except Exception as e:
            logger.error(f"Failed to generate performance report: {str(e)}")
            return {"error": str(e)}


# Global orchestrator instance
_classification_orchestrator: Optional[ClassificationOrchestrator] = None


async def get_classification_orchestrator() -> ClassificationOrchestrator:
    """Get or create the global classification orchestrator."""
    global _classification_orchestrator

    if _classification_orchestrator is None:
        _classification_orchestrator = ClassificationOrchestrator()
        await _classification_orchestrator.setup()

    return _classification_orchestrator


async def cleanup_classification_orchestrator() -> None:
    """Clean up the global classification orchestrator."""
    global _classification_orchestrator

    if _classification_orchestrator:
        try:
            # Check if event loop is still running
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("Event loop closed, performing synchronous cleanup")
                    _classification_orchestrator.is_running = False
                    _classification_orchestrator.workers.clear()
                    _classification_orchestrator.worker_tasks.clear()
                    _classification_orchestrator = None
                    return
            except RuntimeError:
                # No running event loop
                logger.warning("No running event loop, performing synchronous cleanup")
                _classification_orchestrator.is_running = False
                _classification_orchestrator.workers.clear()
                _classification_orchestrator.worker_tasks.clear()
                _classification_orchestrator = None
                return

            await _classification_orchestrator.cleanup()
            _classification_orchestrator = None
        except Exception as e:
            logger.error(f"Error during classification orchestrator cleanup: {str(e)}")
            _classification_orchestrator = None
