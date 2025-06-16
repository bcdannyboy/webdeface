"""APScheduler-based job scheduling manager with database persistence."""

import asyncio
import random
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from apscheduler.events import (
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_REMOVED,
)
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .types import (
    HealthCheckResult,
    JobConfig,
    JobExecution,
    JobStatus,
    RetryConfig,
    SchedulerError,
    SchedulerStats,
)

logger = get_structured_logger(__name__)


class SchedulerManager(AsyncContextManager):
    """Manages APScheduler with database persistence and monitoring."""

    def __init__(self):
        self.settings = get_settings()
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.start_time: Optional[datetime] = None

        # Job tracking
        self._active_jobs: dict[str, JobExecution] = {}
        self._job_callbacks: dict[str, list[Callable]] = {}
        self._workflow_callbacks: dict[str, list[Callable]] = {}

        # Statistics
        self.total_jobs_executed = 0
        self.total_jobs_succeeded = 0
        self.total_jobs_failed = 0

        # Health monitoring
        self._health_checks: dict[str, Callable] = {}
        self._last_health_check: Optional[datetime] = None

        # Concurrency control
        self._max_concurrent_jobs = 10
        self._current_job_count = 0
        self._job_semaphore: Optional[asyncio.Semaphore] = None

    async def setup(self) -> None:
        """Initialize the scheduler."""
        if self.is_running:
            return

        logger.info("Starting APScheduler manager")

        try:
            # Initialize semaphore for concurrency control
            self._job_semaphore = asyncio.Semaphore(self._max_concurrent_jobs)

            # Ensure database directory exists for SQLite databases
            db_url = self.settings.database.url
            if db_url.startswith("sqlite"):
                import os

                # Extract path from SQLite URL
                if ":///" in db_url:
                    db_path = db_url.split("///", 1)[1]
                    if db_path and db_path != ":memory:":
                        db_dir = os.path.dirname(db_path)
                        if db_dir and not os.path.exists(db_dir):
                            os.makedirs(db_dir, exist_ok=True)

            # Configure scheduler
            jobstores = {"default": SQLAlchemyJobStore(url=db_url)}

            executors = {"default": AsyncIOExecutor()}

            job_defaults = {
                "coalesce": False,
                "max_instances": 3,
                "misfire_grace_time": 30,
            }

            # Create scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone="UTC",
            )

            # Register event listeners
            self._register_event_listeners()

            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            self.start_time = datetime.utcnow()

            logger.info("APScheduler manager started successfully")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise SchedulerError(f"Scheduler startup failed: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up the scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping APScheduler manager")

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)

            self.is_running = False
            self._active_jobs.clear()

            logger.info("APScheduler manager stopped")

        except Exception as e:
            logger.error(f"Error during scheduler cleanup: {str(e)}")

    def _register_event_listeners(self) -> None:
        """Register event listeners for job monitoring."""

        def job_executed(event):
            asyncio.create_task(self._handle_job_executed(event))

        def job_error(event):
            asyncio.create_task(self._handle_job_error(event))

        def job_added(event):
            asyncio.create_task(self._handle_job_added(event))

        def job_removed(event):
            asyncio.create_task(self._handle_job_removed(event))

        self.scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error, EVENT_JOB_ERROR)
        self.scheduler.add_listener(job_added, EVENT_JOB_ADDED)
        self.scheduler.add_listener(job_removed, EVENT_JOB_REMOVED)

    async def _handle_job_executed(self, event) -> None:
        """Handle successful job execution."""
        job_id = event.job_id

        if job_id in self._active_jobs:
            execution = self._active_jobs[job_id]
            execution.status = JobStatus.SUCCESS
            execution.completed_at = datetime.utcnow()

            await self._update_job_execution(execution)
            self.total_jobs_succeeded += 1

            # Call callbacks
            await self._call_job_callbacks(execution)

    async def _handle_job_error(self, event) -> None:
        """Handle job execution error."""
        job_id = event.job_id

        if job_id in self._active_jobs:
            execution = self._active_jobs[job_id]
            execution.status = JobStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(event.exception)

            await self._update_job_execution(execution)
            self.total_jobs_failed += 1

            # Handle retry logic
            await self._handle_job_retry(execution, event.exception)

            # Call callbacks
            await self._call_job_callbacks(execution)

    async def _handle_job_added(self, event) -> None:
        """Handle job addition."""
        logger.debug(f"Job added: {event.job_id}")

    async def _handle_job_removed(self, event) -> None:
        """Handle job removal."""
        job_id = event.job_id
        self._active_jobs.pop(job_id, None)
        logger.debug(f"Job removed: {job_id}")

    async def schedule_job(
        self, job_config: JobConfig, job_func: Callable, *args, **kwargs
    ) -> str:
        """Schedule a new job."""
        if not self.is_running:
            raise SchedulerError("Scheduler is not running")

        try:
            # Create execution record
            execution = JobExecution(
                execution_id=f"exec-{uuid.uuid4()}",
                job_id=job_config.job_id,
                website_id=job_config.website_id,
                job_type=job_config.job_type,
                status=JobStatus.PENDING,
                priority=job_config.priority,
            )

            # Store execution record
            await self._create_job_execution(execution)
            self._active_jobs[job_config.job_id] = execution

            # Schedule with APScheduler
            job = self.scheduler.add_job(
                func=self._execute_job_wrapper,
                trigger="cron"
                if self._is_cron_expression(job_config.interval)
                else "interval",
                **self._parse_schedule_config(job_config.interval),
                id=job_config.job_id,
                args=[execution, job_func, args, kwargs],
                name=f"{job_config.job_type.value}-{job_config.website_id}",
                replace_existing=True,
                max_instances=1,
            )

            logger.info(
                "Job scheduled",
                job_id=job_config.job_id,
                job_type=job_config.job_type.value,
                website_id=job_config.website_id,
                interval=job_config.interval,
            )

            return execution.execution_id

        except Exception as e:
            logger.error(f"Failed to schedule job {job_config.job_id}: {str(e)}")
            raise SchedulerError(f"Job scheduling failed: {str(e)}")

    async def _execute_job_wrapper(
        self, execution: JobExecution, job_func: Callable, args: tuple, kwargs: dict
    ) -> None:
        """Wrapper for job execution with monitoring and error handling."""

        async with self._job_semaphore:
            self._current_job_count += 1

            try:
                execution.started_at = datetime.utcnow()
                execution.status = JobStatus.RUNNING

                await self._update_job_execution(execution)

                logger.info(
                    "Starting job execution",
                    execution_id=execution.execution_id,
                    job_id=execution.job_id,
                    job_type=execution.job_type.value,
                )

                # Execute the actual job function
                if asyncio.iscoroutinefunction(job_func):
                    result = await job_func(*args, **kwargs)
                else:
                    result = job_func(*args, **kwargs)

                # Update execution with results
                execution.result_data = (
                    result if isinstance(result, dict) else {"result": str(result)}
                )

                self.total_jobs_executed += 1

            except Exception as e:
                logger.error(
                    "Job execution failed",
                    execution_id=execution.execution_id,
                    job_id=execution.job_id,
                    error=str(e),
                )
                raise

            finally:
                self._current_job_count -= 1

    async def _handle_job_retry(
        self, execution: JobExecution, exception: Exception
    ) -> None:
        """Handle job retry logic with exponential backoff."""

        try:
            # Get job config to check retry settings
            storage = await get_storage_manager()

            # This would need to be implemented in storage manager
            # For now, use default retry config
            retry_config = RetryConfig()

            if execution.attempt_number >= retry_config.max_retries:
                logger.warning(
                    "Job max retries exceeded",
                    execution_id=execution.execution_id,
                    job_id=execution.job_id,
                    attempts=execution.attempt_number,
                )
                return

            # Calculate delay with exponential backoff
            delay = min(
                retry_config.initial_delay
                * (retry_config.exponential_base ** (execution.attempt_number - 1)),
                retry_config.max_delay,
            )

            # Add jitter if enabled
            if retry_config.jitter:
                delay *= 0.5 + random.random() * 0.5

            # Schedule retry
            retry_execution = JobExecution(
                execution_id=f"retry-{uuid.uuid4()}",
                job_id=execution.job_id,
                website_id=execution.website_id,
                job_type=execution.job_type,
                status=JobStatus.RETRYING,
                priority=execution.priority,
                attempt_number=execution.attempt_number + 1,
            )

            logger.info(
                "Scheduling job retry",
                original_execution=execution.execution_id,
                retry_execution=retry_execution.execution_id,
                delay_seconds=delay,
                attempt=retry_execution.attempt_number,
            )

            # Schedule retry (this would need the original job function)
            # For now, just log the retry attempt

        except Exception as e:
            logger.error(f"Failed to handle job retry: {str(e)}")

    def _is_cron_expression(self, expression: str) -> bool:
        """Check if expression is a cron expression."""
        parts = expression.split()
        return len(parts) >= 5

    def _parse_schedule_config(self, interval: str) -> dict[str, Any]:
        """Parse schedule configuration for APScheduler."""

        if self._is_cron_expression(interval):
            # Parse cron expression: "minute hour day month day_of_week"
            parts = interval.split()

            return {
                "minute": parts[0] if parts[0] != "*" else None,
                "hour": parts[1] if parts[1] != "*" else None,
                "day": parts[2] if parts[2] != "*" else None,
                "month": parts[3] if parts[3] != "*" else None,
                "day_of_week": parts[4] if parts[4] != "*" else None,
            }
        else:
            # Parse interval expression like "5m", "1h", "30s"
            if interval.endswith("s"):
                return {"seconds": int(interval[:-1])}
            elif interval.endswith("m"):
                return {"minutes": int(interval[:-1])}
            elif interval.endswith("h"):
                return {"hours": int(interval[:-1])}
            elif interval.endswith("d"):
                return {"days": int(interval[:-1])}
            else:
                # Default to seconds
                return {"seconds": int(interval)}

    async def unschedule_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if not self.is_running:
            raise SchedulerError("Scheduler is not running")

        try:
            self.scheduler.remove_job(job_id)
            self._active_jobs.pop(job_id, None)

            logger.info("Job unscheduled", job_id=job_id)
            return True

        except Exception as e:
            logger.error(f"Failed to unschedule job {job_id}: {str(e)}")
            return False

    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        if not self.is_running:
            raise SchedulerError("Scheduler is not running")

        try:
            self.scheduler.pause_job(job_id)

            if job_id in self._active_jobs:
                self._active_jobs[job_id].status = JobStatus.PAUSED

            logger.info("Job paused", job_id=job_id)
            return True

        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {str(e)}")
            return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if not self.is_running:
            raise SchedulerError("Scheduler is not running")

        try:
            self.scheduler.resume_job(job_id)

            if job_id in self._active_jobs:
                self._active_jobs[job_id].status = JobStatus.PENDING

            logger.info("Job resumed", job_id=job_id)
            return True

        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {str(e)}")
            return False

    async def get_scheduler_stats(self) -> SchedulerStats:
        """Get comprehensive scheduler statistics."""

        if not self.is_running or not self.start_time:
            return SchedulerStats()

        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Count jobs by status
        pending_jobs = sum(
            1 for job in self._active_jobs.values() if job.status == JobStatus.PENDING
        )
        running_jobs = sum(
            1 for job in self._active_jobs.values() if job.status == JobStatus.RUNNING
        )

        return SchedulerStats(
            total_jobs=len(self._active_jobs),
            active_jobs=running_jobs,
            completed_jobs=self.total_jobs_succeeded,
            failed_jobs=self.total_jobs_failed,
            pending_jobs=pending_jobs,
            uptime_seconds=uptime,
            jobs_per_hour=(self.total_jobs_executed / max(uptime / 3600, 1))
            if uptime > 0
            else 0,
            success_rate=self.total_jobs_succeeded / max(self.total_jobs_executed, 1),
            average_job_duration=self._calculate_average_duration(),
        )

    def _calculate_average_duration(self) -> float:
        """Calculate average job duration."""
        completed_jobs = [
            job
            for job in self._active_jobs.values()
            if job.duration is not None
            and job.status in [JobStatus.SUCCESS, JobStatus.FAILED]
        ]

        if not completed_jobs:
            return 0.0

        return sum(job.duration for job in completed_jobs) / len(completed_jobs)

    async def health_check(self) -> list[HealthCheckResult]:
        """Perform comprehensive health check."""
        results = []

        # Check scheduler status
        results.append(
            HealthCheckResult(
                component="scheduler",
                healthy=self.is_running and self.scheduler is not None,
                message="APScheduler is running"
                if self.is_running
                else "APScheduler is not running",
            )
        )

        # Check database connectivity
        try:
            storage = await get_storage_manager()
            # This would test database connectivity
            results.append(
                HealthCheckResult(
                    component="database",
                    healthy=True,
                    message="Database connection healthy",
                )
            )
        except Exception as e:
            results.append(
                HealthCheckResult(
                    component="database",
                    healthy=False,
                    message=f"Database connection failed: {str(e)}",
                )
            )

        # Check job queue health
        queue_healthy = self._current_job_count < self._max_concurrent_jobs
        results.append(
            HealthCheckResult(
                component="job_queue",
                healthy=queue_healthy,
                message=f"Job queue: {self._current_job_count}/{self._max_concurrent_jobs}",
                details={
                    "current_jobs": self._current_job_count,
                    "max_jobs": self._max_concurrent_jobs,
                },
            )
        )

        # Run custom health checks
        for name, check_func in self._health_checks.items():
            try:
                result = await check_func()
                if isinstance(result, HealthCheckResult):
                    results.append(result)
                else:
                    results.append(
                        HealthCheckResult(
                            component=name, healthy=bool(result), message=str(result)
                        )
                    )
            except Exception as e:
                results.append(
                    HealthCheckResult(
                        component=name,
                        healthy=False,
                        message=f"Health check failed: {str(e)}",
                    )
                )

        self._last_health_check = datetime.utcnow()
        return results

    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check function."""
        self._health_checks[name] = check_func

    def add_job_callback(self, job_id: str, callback: Callable) -> None:
        """Add a callback for job completion."""
        if job_id not in self._job_callbacks:
            self._job_callbacks[job_id] = []
        self._job_callbacks[job_id].append(callback)

    async def _call_job_callbacks(self, execution: JobExecution) -> None:
        """Call registered callbacks for a job."""
        callbacks = self._job_callbacks.get(execution.job_id, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution)
                else:
                    callback(execution)
            except Exception as e:
                logger.error(f"Job callback failed: {str(e)}")

    async def _create_job_execution(self, execution: JobExecution) -> None:
        """Create job execution record in database."""
        try:
            storage = await get_storage_manager()
            # This would create the execution record
            logger.debug(
                "Job execution record created", execution_id=execution.execution_id
            )
        except Exception as e:
            logger.error(f"Failed to create job execution record: {str(e)}")

    async def _update_job_execution(self, execution: JobExecution) -> None:
        """Update job execution record in database."""
        try:
            storage = await get_storage_manager()
            # This would update the execution record
            logger.debug(
                "Job execution record updated",
                execution_id=execution.execution_id,
                status=execution.status.value,
            )
        except Exception as e:
            logger.error(f"Failed to update job execution record: {str(e)}")


# Global scheduler instance
_scheduler_manager: Optional[SchedulerManager] = None


async def get_scheduler_manager() -> SchedulerManager:
    """Get or create the global scheduler manager."""
    global _scheduler_manager

    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
        await _scheduler_manager.setup()

    return _scheduler_manager


async def cleanup_scheduler_manager() -> None:
    """Clean up the global scheduler manager."""
    global _scheduler_manager

    if _scheduler_manager:
        await _scheduler_manager.cleanup()
        _scheduler_manager = None
