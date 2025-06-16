"""Comprehensive scraping orchestration with error handling and monitoring."""

import asyncio
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .browser import BrowserManager, get_browser_pool
from .extractor import ContentExtractor, ContentProcessor
from .hashing import ChangeDetector, ContentHasher
from .types import ScrapingError
from .visual import VisualAnalyzer

logger = get_structured_logger(__name__)


@dataclass
class ScrapingJob:
    """Represents a scraping job with all its parameters."""

    website_id: str
    url: str
    job_id: str
    priority: int = 1  # 1 = highest, 5 = lowest
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    scheduled_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.scheduled_at is None:
            self.scheduled_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ScrapingResult:
    """Result of a complete scraping operation."""

    job: ScrapingJob
    success: bool
    content_data: Optional[dict[str, Any]] = None
    visual_data: Optional[dict[str, Any]] = None
    change_analysis: Optional[dict[str, Any]] = None
    performance_metrics: Optional[dict[str, Any]] = None
    error_details: Optional[dict[str, Any]] = None
    snapshot_id: Optional[str] = None


class ScrapingQueue:
    """Thread-safe queue for managing scraping jobs."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._pending_jobs: dict[str, ScrapingJob] = {}
        self._lock = asyncio.Lock()

    async def add_job(self, job: ScrapingJob) -> bool:
        """Add a job to the queue."""
        async with self._lock:
            if len(self._pending_jobs) >= self.max_size:
                logger.warning(
                    "Scraping queue is full", queue_size=len(self._pending_jobs)
                )
                return False

            # Use negative priority for max-heap behavior (higher priority first)
            priority_key = (-job.priority, job.scheduled_at.timestamp(), job.job_id)

            try:
                self._queue.put_nowait((priority_key, job))
                self._pending_jobs[job.job_id] = job
                logger.debug(
                    "Job added to scraping queue",
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

    async def get_job(self, timeout: Optional[float] = None) -> Optional[ScrapingJob]:
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

    async def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue."""
        async with self._lock:
            if job_id in self._pending_jobs:
                del self._pending_jobs[job_id]
                return True
            return False

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            return {
                "pending_jobs": len(self._pending_jobs),
                "queue_size": self._queue.qsize(),
                "max_size": self.max_size,
                "is_full": len(self._pending_jobs) >= self.max_size,
            }


class ScrapingWorker:
    """Worker that processes scraping jobs."""

    def __init__(self, worker_id: str, queue: ScrapingQueue):
        self.worker_id = worker_id
        self.queue = queue
        self.settings = get_settings()
        self.is_running = False
        self.current_job: Optional[ScrapingJob] = None

        # Initialize components
        self.browser_manager = BrowserManager()
        self.content_extractor = ContentExtractor()
        self.content_processor = ContentProcessor()
        self.visual_analyzer = VisualAnalyzer()
        self.content_hasher = ContentHasher()
        self.change_detector = ChangeDetector()

        # Statistics
        self.jobs_processed = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0
        self.start_time = datetime.utcnow()

    async def start(self) -> None:
        """Start the worker."""
        self.is_running = True
        logger.info(f"Scraping worker {self.worker_id} started")

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

        logger.info(f"Scraping worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """Stop the worker."""
        self.is_running = False
        if self.current_job:
            logger.info(f"Worker {self.worker_id} stopping, current job will complete")

    async def _process_job(self, job: ScrapingJob) -> ScrapingResult:
        """Process a single scraping job."""
        self.current_job = job
        job.started_at = datetime.utcnow()

        start_time = time.time()

        logger.info(
            "Processing scraping job",
            worker_id=self.worker_id,
            job_id=job.job_id,
            url=job.url,
            attempt=job.retry_count + 1,
        )

        try:
            # Perform scraping
            result = await self._scrape_website(job)

            # Record success
            self.jobs_processed += 1
            if result.success:
                self.jobs_succeeded += 1
            else:
                self.jobs_failed += 1

            # Performance metrics
            processing_time = time.time() - start_time
            if not result.performance_metrics:
                result.performance_metrics = {}
            result.performance_metrics["total_processing_time"] = processing_time

            logger.info(
                "Scraping job completed",
                worker_id=self.worker_id,
                job_id=job.job_id,
                success=result.success,
                processing_time=processing_time,
            )

            return result

        except Exception as e:
            logger.error(
                "Scraping job failed",
                worker_id=self.worker_id,
                job_id=job.job_id,
                error=str(e),
            )

            self.jobs_processed += 1
            self.jobs_failed += 1

            return ScrapingResult(
                job=job,
                success=False,
                error_details={"error": str(e), "worker_id": self.worker_id},
            )
        finally:
            job.completed_at = datetime.utcnow()
            self.current_job = None

    async def _scrape_website(self, job: ScrapingJob) -> ScrapingResult:
        """Perform the actual website scraping."""
        performance_metrics = {
            "browser_setup_time": 0,
            "navigation_time": 0,
            "content_extraction_time": 0,
            "visual_analysis_time": 0,
            "change_detection_time": 0,
        }

        browser_pool = await get_browser_pool()
        storage = await get_storage_manager()

        async with browser_pool.get_browser() as browser:
            async with browser.create_context() as context:
                async with browser.create_page(context) as page:
                    try:
                        # Browser setup and navigation
                        nav_start = time.time()
                        success = await self.browser_manager.navigate_with_retries(
                            page, job.url, max_retries=job.max_retries
                        )

                        if not success:
                            raise ScrapingError(f"Failed to navigate to {job.url}")

                        performance_metrics["navigation_time"] = time.time() - nav_start

                        # Wait for content to load
                        await self.browser_manager.wait_for_content(page)
                        await self.browser_manager.inject_stealth_scripts(page)

                        # Extract content
                        extract_start = time.time()
                        content_data = await self.content_extractor.extract_from_page(
                            page, job.url
                        )
                        performance_metrics["content_extraction_time"] = (
                            time.time() - extract_start
                        )

                        # Generate content hashes
                        main_content = content_data.get("main_content", "")
                        content_hash = self.content_hasher.hash_content(main_content)
                        content_data["content_hash"] = content_hash.hash_value

                        # Structure hash
                        dom_outline = content_data.get("dom_outline", [])
                        structure_hash = self.content_hasher.hash_structure(dom_outline)
                        content_data["structure_hash"] = structure_hash.hash_value

                        # Visual analysis
                        visual_start = time.time()
                        visual_data = await self._perform_visual_analysis(
                            page, job, storage
                        )
                        performance_metrics["visual_analysis_time"] = (
                            time.time() - visual_start
                        )

                        # Change detection
                        change_start = time.time()
                        change_analysis = await self._perform_change_detection(
                            job, content_data, visual_data, storage
                        )
                        performance_metrics["change_detection_time"] = (
                            time.time() - change_start
                        )

                        # Store snapshot
                        snapshot = await self._store_snapshot(
                            job, content_data, visual_data, storage
                        )

                        return ScrapingResult(
                            job=job,
                            success=True,
                            content_data=content_data,
                            visual_data=visual_data,
                            change_analysis=change_analysis,
                            performance_metrics=performance_metrics,
                            snapshot_id=snapshot.id if snapshot else None,
                        )

                    except Exception as e:
                        raise ScrapingError(f"Scraping failed: {str(e)}")

    async def _perform_visual_analysis(
        self, page, job: ScrapingJob, storage
    ) -> dict[str, Any]:
        """Perform visual analysis including screenshot capture and comparison."""
        try:
            # Get latest snapshot for comparison
            latest_snapshot = await storage.get_latest_snapshot(job.website_id)
            baseline_screenshot = None

            if latest_snapshot and hasattr(latest_snapshot, "screenshot_data"):
                baseline_screenshot = latest_snapshot.screenshot_data

            # Perform visual analysis
            visual_analysis = await self.visual_analyzer.analyze_visual_changes(
                page, baseline_screenshot
            )

            return visual_analysis

        except Exception as e:
            logger.warning(f"Visual analysis failed for {job.url}: {str(e)}")
            return {"error": str(e)}

    async def _perform_change_detection(
        self,
        job: ScrapingJob,
        content_data: dict[str, Any],
        visual_data: dict[str, Any],
        storage,
    ) -> dict[str, Any]:
        """Perform change detection against previous snapshots."""
        try:
            # Get latest snapshot for comparison
            latest_snapshot = await storage.get_latest_snapshot(job.website_id)

            if not latest_snapshot:
                return {
                    "is_first_snapshot": True,
                    "has_changes": False,
                    "change_summary": "Initial snapshot - no comparison available",
                }

            # Prepare old content data for comparison
            old_content = {
                "content_hash": latest_snapshot.content_hash,
                "main_content": latest_snapshot.content_text or "",
                "structure_hash": getattr(latest_snapshot, "structure_hash", ""),
                "word_count": len((latest_snapshot.content_text or "").split()),
                "title": getattr(latest_snapshot, "title", ""),
            }

            # Detect changes
            change_result = self.change_detector.detect_changes(
                old_content, content_data
            )

            # Add visual comparison if available
            if visual_data.get("visual_diff"):
                change_result.change_details["visual_diff"] = asdict(
                    visual_data["visual_diff"]
                )

            return {
                "has_changes": change_result.has_changed,
                "change_type": change_result.change_type,
                "similarity_score": change_result.similarity_score,
                "risk_level": change_result.risk_level,
                "confidence": change_result.confidence,
                "change_details": change_result.change_details,
                "change_summary": self._generate_change_summary(change_result),
            }

        except Exception as e:
            logger.warning(f"Change detection failed for {job.url}: {str(e)}")
            return {"error": str(e), "has_changes": False}

    async def _store_snapshot(
        self,
        job: ScrapingJob,
        content_data: dict[str, Any],
        visual_data: dict[str, Any],
        storage,
    ):
        """Store the snapshot in the database."""
        try:
            # Prepare snapshot data
            snapshot_data = {
                "website_id": job.website_id,
                "content_hash": content_data.get("content_hash", ""),
                "content_text": content_data.get("main_content"),
                "raw_html": content_data.get("html", "").encode("utf-8")
                if content_data.get("html")
                else None,
                "status_code": 200,  # Assuming success if we got here
                "response_time_ms": job.metadata.get("response_time_ms", 0),
                "content_length": content_data.get("character_count", 0),
                "content_type": "text/html",
            }

            # Create snapshot
            snapshot = await storage.create_snapshot(**snapshot_data)

            logger.debug(
                "Snapshot stored", snapshot_id=snapshot.id, website_id=job.website_id
            )

            return snapshot

        except Exception as e:
            logger.error(f"Failed to store snapshot for {job.url}: {str(e)}")
            return None

    def _generate_change_summary(self, change_result) -> str:
        """Generate a human-readable change summary."""
        if not change_result.has_changed:
            return "No significant changes detected"

        summary_parts = []

        if change_result.change_type:
            change_types = change_result.change_type.split(",")
            summary_parts.append(f"Changes detected: {', '.join(change_types)}")

        if change_result.similarity_score < 0.5:
            summary_parts.append("Major content differences")
        elif change_result.similarity_score < 0.8:
            summary_parts.append("Moderate content differences")
        else:
            summary_parts.append("Minor content differences")

        summary_parts.append(f"Risk level: {change_result.risk_level}")

        return ". ".join(summary_parts)

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "jobs_processed": self.jobs_processed,
            "jobs_succeeded": self.jobs_succeeded,
            "jobs_failed": self.jobs_failed,
            "success_rate": self.jobs_succeeded / max(self.jobs_processed, 1),
            "uptime_seconds": uptime,
            "current_job_id": self.current_job.job_id if self.current_job else None,
        }


class ScrapingOrchestrator(AsyncContextManager):
    """Main orchestrator for web scraping operations."""

    def __init__(self, max_workers: int = 3, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.settings = get_settings()

        # Initialize queue and workers
        self.queue = ScrapingQueue(max_queue_size)
        self.workers: list[ScrapingWorker] = []
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

        logger.info(f"Starting scraping orchestrator with {self.max_workers} workers")

        # Create workers
        for i in range(self.max_workers):
            worker_id = f"worker-{i+1}"
            worker = ScrapingWorker(worker_id, self.queue)
            self.workers.append(worker)

        # Start worker tasks
        for worker in self.workers:
            task = asyncio.create_task(worker.start())
            self.worker_tasks.append(task)

        self.is_running = True
        self.start_time = datetime.utcnow()

        logger.info("Scraping orchestrator started successfully")

    async def cleanup(self) -> None:
        """Clean up the orchestrator."""
        if not self.is_running:
            return

        logger.info("Stopping scraping orchestrator")

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

            logger.info("Scraping orchestrator stopped")

        except Exception as e:
            logger.error(f"Error during scraping orchestrator cleanup: {str(e)}")
            self.is_running = False
            self.workers.clear()
            self.worker_tasks.clear()

    async def schedule_scraping(
        self,
        website_id: str,
        url: str,
        priority: int = 1,
        delay_seconds: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Schedule a scraping job."""
        if not self.is_running:
            raise ScrapingError("Orchestrator is not running")

        # Create job
        job_id = f"job-{website_id}-{int(time.time())}"
        scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

        job = ScrapingJob(
            website_id=website_id,
            url=url,
            job_id=job_id,
            priority=priority,
            scheduled_at=scheduled_at,
            metadata=metadata or {},
        )

        # Add to queue
        success = await self.queue.add_job(job)

        if success:
            self.total_jobs_queued += 1
            logger.info(
                "Scraping job scheduled",
                job_id=job_id,
                website_id=website_id,
                url=url,
                priority=priority,
            )
            return job_id
        else:
            raise ScrapingError("Failed to queue scraping job - queue full")

    async def schedule_bulk_scraping(self, jobs: list[dict[str, Any]]) -> list[str]:
        """Schedule multiple scraping jobs."""
        job_ids = []

        for job_config in jobs:
            try:
                job_id = await self.schedule_scraping(**job_config)
                job_ids.append(job_id)
            except Exception as e:
                logger.error(f"Failed to schedule job: {str(e)}")
                job_ids.append(None)

        return job_ids

    async def get_orchestrator_stats(self) -> dict[str, Any]:
        """Get comprehensive orchestrator statistics."""
        queue_stats = await self.queue.get_queue_stats()

        # Worker statistics
        worker_stats = []
        total_processed = 0
        total_succeeded = 0
        total_failed = 0

        for worker in self.workers:
            stats = worker.get_stats()
            worker_stats.append(stats)
            total_processed += stats["jobs_processed"]
            total_succeeded += stats["jobs_succeeded"]
            total_failed += stats["jobs_failed"]

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
            "overall_success_rate": total_succeeded / max(total_processed, 1),
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
            health["issues"].append("Scraping queue is full")

        health["overall_healthy"] = (
            health["orchestrator_running"]
            and health["workers_healthy"]
            and health["queue_healthy"]
        )

        return health


# Global orchestrator instance
_orchestrator: Optional[ScrapingOrchestrator] = None


async def get_scraping_orchestrator() -> ScrapingOrchestrator:
    """Get or create the global scraping orchestrator."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = ScrapingOrchestrator()
        await _orchestrator.setup()

    return _orchestrator


async def cleanup_scraping_orchestrator() -> None:
    """Clean up the global scraping orchestrator."""
    global _orchestrator

    if _orchestrator:
        try:
            # Check if event loop is still running
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("Event loop closed, performing synchronous cleanup")
                    _orchestrator.is_running = False
                    _orchestrator.workers.clear()
                    _orchestrator.worker_tasks.clear()
                    _orchestrator = None
                    return
            except RuntimeError:
                # No running event loop
                logger.warning("No running event loop, performing synchronous cleanup")
                _orchestrator.is_running = False
                _orchestrator.workers.clear()
                _orchestrator.worker_tasks.clear()
                _orchestrator = None
                return

            await _orchestrator.cleanup()
            _orchestrator = None
        except Exception as e:
            logger.error(f"Error during scraping orchestrator cleanup: {str(e)}")
            _orchestrator = None
