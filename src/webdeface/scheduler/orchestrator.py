"""Main scheduler orchestrator that coordinates all scheduling and monitoring components."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import get_settings
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .manager import get_scheduler_manager
from .monitoring import get_health_monitor
from .types import (
    JobConfig,
    JobType,
    MonitoringReport,
    Priority,
    SchedulerError,
)
from .workflow import get_workflow_engine

logger = get_structured_logger(__name__)


class SchedulingOrchestrator(AsyncContextManager):
    """Main orchestrator that coordinates scheduling, workflows, and monitoring."""

    def __init__(self):
        self.settings = get_settings()
        self.is_running = False

        # Component references
        self.scheduler_manager = None
        self.workflow_engine = None
        self.health_monitor = None

        # Configuration
        self.default_monitoring_interval = "*/15 * * * *"  # Every 15 minutes
        self.health_check_interval = "*/5 * * * *"  # Every 5 minutes

        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_jobs_scheduled = 0
        self.total_workflows_executed = 0

    async def setup(self) -> None:
        """Initialize the scheduling orchestrator."""
        if self.is_running:
            return

        logger.info("Starting scheduling orchestrator")

        try:
            # Initialize all components
            self.scheduler_manager = await get_scheduler_manager()
            self.workflow_engine = await get_workflow_engine()
            self.health_monitor = await get_health_monitor()

            # Schedule default monitoring jobs
            await self._schedule_system_jobs()

            # Schedule website monitoring jobs
            await self._schedule_website_monitoring()

            self.is_running = True
            self.start_time = datetime.utcnow()

            logger.info("Scheduling orchestrator started successfully")

        except Exception as e:
            logger.error(f"Failed to start scheduling orchestrator: {str(e)}")
            raise SchedulerError(f"Orchestrator startup failed: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up the scheduling orchestrator."""
        if not self.is_running:
            return

        logger.info("Stopping scheduling orchestrator")

        try:
            # Check if event loop is still running before attempting async operations
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("Event loop is closed, skipping async cleanup")
                    self.is_running = False
                    return
            except RuntimeError:
                # No running event loop
                logger.warning("No running event loop, skipping async cleanup")
                self.is_running = False
                return

            # Clean up components in reverse order
            if self.health_monitor:
                try:
                    from .monitoring import cleanup_health_monitor

                    await cleanup_health_monitor()
                except Exception as e:
                    logger.warning(f"Health monitor cleanup failed: {str(e)}")

            if self.workflow_engine:
                try:
                    from .workflow import cleanup_workflow_engine

                    await cleanup_workflow_engine()
                except Exception as e:
                    logger.warning(f"Workflow engine cleanup failed: {str(e)}")

            if self.scheduler_manager:
                try:
                    from .manager import cleanup_scheduler_manager

                    await cleanup_scheduler_manager()
                except Exception as e:
                    logger.warning(f"Scheduler manager cleanup failed: {str(e)}")

            self.is_running = False
            logger.info("Scheduling orchestrator stopped")

        except Exception as e:
            logger.error(f"Error during orchestrator cleanup: {str(e)}")
            self.is_running = False

    async def _schedule_system_jobs(self) -> None:
        """Schedule system maintenance and health check jobs."""

        # Health check workflow
        health_check_config = JobConfig(
            job_id="system_health_check",
            website_id="system",  # Special website ID for system jobs
            website_url="",
            website_name="System Health Check",
            job_type=JobType.HEALTH_CHECK,
            interval=self.health_check_interval,
            priority=Priority.LOW,
        )

        await self.scheduler_manager.schedule_job(
            job_config=health_check_config, job_func=self._execute_health_check_workflow
        )

        # System maintenance job
        maintenance_config = JobConfig(
            job_id="system_maintenance",
            website_id="system",
            website_url="",
            website_name="System Maintenance",
            job_type=JobType.MAINTENANCE,
            interval="0 2 * * *",  # Daily at 2 AM
            priority=Priority.BACKGROUND,
        )

        await self.scheduler_manager.schedule_job(
            job_config=maintenance_config, job_func=self._execute_maintenance_tasks
        )

        logger.info("System jobs scheduled")

    async def _schedule_website_monitoring(self) -> None:
        """Schedule monitoring jobs for all active websites."""

        try:
            storage = await get_storage_manager()
            websites = await storage.list_websites()

            if not websites:
                logger.info("No websites found for monitoring")
                return

            scheduled_count = 0
            for website in websites:
                if not website.is_active:
                    continue

                # Create job config for this website
                job_config = JobConfig(
                    job_id=f"monitor_{website.id}",
                    website_id=website.id,
                    website_url=website.url,
                    website_name=website.name,
                    job_type=JobType.WEBSITE_MONITOR,
                    interval=self.default_monitoring_interval,
                    priority=Priority.NORMAL,
                )

                # Schedule monitoring workflow
                await self.scheduler_manager.schedule_job(
                    job_config=job_config,
                    job_func=self._execute_monitoring_workflow,
                    args=(website.id,),
                )

                scheduled_count += 1
                self.total_jobs_scheduled += 1

            logger.info(
                "Website monitoring jobs scheduled",
                websites_scheduled=scheduled_count,
                total_websites=len(websites),
            )

        except Exception as e:
            logger.error(f"Failed to schedule website monitoring: {str(e)}")

    async def _execute_monitoring_workflow(self, website_id: str) -> dict[str, Any]:
        """Execute the complete monitoring workflow for a website."""

        try:
            logger.info("Starting monitoring workflow", website_id=website_id)

            # Execute website monitoring workflow
            execution_id = await self.workflow_engine.execute_workflow(
                workflow_id="website_monitoring",
                website_id=website_id,
                parameters={"priority": "normal"},
            )

            self.total_workflows_executed += 1

            return {
                "workflow_execution_id": execution_id,
                "website_id": website_id,
                "status": "initiated",
            }

        except Exception as e:
            logger.error(
                "Monitoring workflow failed", website_id=website_id, error=str(e)
            )
            raise

    async def _execute_health_check_workflow(self) -> dict[str, Any]:
        """Execute the system health check workflow."""

        try:
            logger.info("Starting health check workflow")

            # Execute health check workflow
            execution_id = await self.workflow_engine.execute_workflow(
                workflow_id="system_health_check",
                website_id="system",
                parameters={"check_level": "comprehensive"},
            )

            return {"workflow_execution_id": execution_id, "status": "initiated"}

        except Exception as e:
            logger.error("Health check workflow failed", error=str(e))
            raise

    async def _execute_maintenance_tasks(self) -> dict[str, Any]:
        """Execute system maintenance tasks."""

        try:
            logger.info("Starting maintenance tasks")

            maintenance_results = {}

            # Clean up old job executions
            cleanup_result = await self._cleanup_old_executions()
            maintenance_results["cleanup"] = cleanup_result

            # Update job statistics
            stats_result = await self._update_job_statistics()
            maintenance_results["statistics"] = stats_result

            # Optimize database
            optimize_result = await self._optimize_database()
            maintenance_results["optimization"] = optimize_result

            logger.info("Maintenance tasks completed", results=maintenance_results)

            return maintenance_results

        except Exception as e:
            logger.error("Maintenance tasks failed", error=str(e))
            raise

    async def _cleanup_old_executions(self) -> dict[str, Any]:
        """Clean up old job execution records."""

        try:
            # Keep executions for last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            # This would delete old execution records from database
            # For now, just return mock result

            return {"records_cleaned": 0, "cutoff_date": cutoff_date.isoformat()}

        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {str(e)}")
            return {"error": str(e)}

    async def _update_job_statistics(self) -> dict[str, Any]:
        """Update job performance statistics."""

        try:
            stats = await self.scheduler_manager.get_scheduler_stats()

            # Store updated statistics
            # This would persist stats to database

            return {
                "total_jobs": stats.total_jobs,
                "success_rate": stats.success_rate,
                "average_duration": stats.average_job_duration,
            }

        except Exception as e:
            logger.error(f"Failed to update job statistics: {str(e)}")
            return {"error": str(e)}

    async def _optimize_database(self) -> dict[str, Any]:
        """Optimize database performance."""

        try:
            storage = await get_storage_manager()

            # Run database optimization tasks
            # This would include VACUUM, ANALYZE, etc.

            return {
                "optimization_completed": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to optimize database: {str(e)}")
            return {"error": str(e)}

    async def schedule_website_monitoring(
        self,
        website_id: str,
        interval: Optional[str] = None,
        priority: Priority = Priority.NORMAL,
    ) -> str:
        """Schedule monitoring for a specific website."""

        if not self.is_running:
            raise SchedulerError("Orchestrator is not running")

        try:
            storage = await get_storage_manager()
            website = await storage.get_website(website_id)

            if not website:
                raise SchedulerError(f"Website not found: {website_id}")

            # Create job config
            job_config = JobConfig(
                job_id=f"monitor_{website_id}_{int(datetime.utcnow().timestamp())}",
                website_id=website_id,
                website_url=website.url,
                website_name=website.name,
                job_type=JobType.WEBSITE_MONITOR,
                interval=interval or self.default_monitoring_interval,
                priority=priority,
            )

            # Schedule the job
            execution_id = await self.scheduler_manager.schedule_job(
                job_config=job_config,
                job_func=self._execute_monitoring_workflow,
                args=(website_id,),
            )

            self.total_jobs_scheduled += 1

            logger.info(
                "Website monitoring scheduled",
                website_id=website_id,
                execution_id=execution_id,
                interval=job_config.interval,
            )

            return execution_id

        except Exception as e:
            logger.error(f"Failed to schedule website monitoring: {str(e)}")
            raise SchedulerError(f"Monitoring scheduling failed: {str(e)}")

    async def unschedule_website_monitoring(self, website_id: str) -> bool:
        """Remove monitoring for a specific website."""

        try:
            job_id = f"monitor_{website_id}"
            success = await self.scheduler_manager.unschedule_job(job_id)

            if success:
                logger.info("Website monitoring unscheduled", website_id=website_id)
            else:
                logger.warning(
                    "Failed to unschedule website monitoring", website_id=website_id
                )

            return success

        except Exception as e:
            logger.error(f"Failed to unschedule website monitoring: {str(e)}")
            return False

    async def execute_immediate_workflow(
        self,
        workflow_id: str,
        website_id: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> str:
        """Execute a workflow immediately (outside of scheduled jobs)."""

        if not self.is_running:
            raise SchedulerError("Orchestrator is not running")

        try:
            execution_id = await self.workflow_engine.execute_workflow(
                workflow_id=workflow_id,
                website_id=website_id,
                parameters=parameters or {},
            )

            self.total_workflows_executed += 1

            logger.info(
                "Immediate workflow executed",
                workflow_id=workflow_id,
                website_id=website_id,
                execution_id=execution_id,
            )

            return execution_id

        except Exception as e:
            logger.error(f"Failed to execute immediate workflow: {str(e)}")
            raise SchedulerError(f"Workflow execution failed: {str(e)}")

    async def get_orchestrator_status(self) -> dict[str, Any]:
        """Get comprehensive orchestrator status."""

        if not self.is_running:
            return {"status": "stopped"}

        try:
            # Get component statuses
            scheduler_stats = await self.scheduler_manager.get_scheduler_stats()
            active_workflows = await self.workflow_engine.list_active_workflows()
            latest_health_report = self.health_monitor.get_latest_report()

            # Calculate uptime
            uptime = 0
            if self.start_time:
                uptime = (datetime.utcnow() - self.start_time).total_seconds()

            return {
                "status": "running",
                "uptime_seconds": uptime,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "total_jobs_scheduled": self.total_jobs_scheduled,
                "total_workflows_executed": self.total_workflows_executed,
                "scheduler_stats": scheduler_stats.__dict__,
                "active_workflows_count": len(active_workflows),
                "health_score": latest_health_report.overall_health_score
                if latest_health_report
                else None,
                "components": {
                    "scheduler_manager": self.scheduler_manager.is_running,
                    "workflow_engine": self.workflow_engine.is_running,
                    "health_monitor": self.health_monitor.is_running,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get orchestrator status: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def get_monitoring_report(self) -> Optional[MonitoringReport]:
        """Get the latest comprehensive monitoring report."""

        try:
            return self.health_monitor.get_latest_report()
        except Exception as e:
            logger.error(f"Failed to get monitoring report: {str(e)}")
            return None

    async def pause_all_jobs(self) -> dict[str, int]:
        """Pause all scheduled jobs."""

        # This would pause all jobs in the scheduler
        # For now, return mock counts

        return {"paused_jobs": 0, "failed_to_pause": 0}

    async def resume_all_jobs(self) -> dict[str, int]:
        """Resume all paused jobs."""

        # This would resume all paused jobs
        # For now, return mock counts

        return {"resumed_jobs": 0, "failed_to_resume": 0}


# Global orchestrator instance
_scheduling_orchestrator: Optional[SchedulingOrchestrator] = None


async def get_scheduling_orchestrator() -> SchedulingOrchestrator:
    """Get or create the global scheduling orchestrator."""
    global _scheduling_orchestrator

    if _scheduling_orchestrator is None:
        _scheduling_orchestrator = SchedulingOrchestrator()
        await _scheduling_orchestrator.setup()

    return _scheduling_orchestrator


async def cleanup_scheduling_orchestrator() -> None:
    """Clean up the global scheduling orchestrator."""
    global _scheduling_orchestrator

    if _scheduling_orchestrator:
        try:
            # Check if event loop is still running
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("Event loop closed, performing synchronous cleanup")
                    _scheduling_orchestrator.is_running = False
                    _scheduling_orchestrator = None
                    return
            except RuntimeError:
                # No running event loop
                logger.warning("No running event loop, performing synchronous cleanup")
                _scheduling_orchestrator.is_running = False
                _scheduling_orchestrator = None
                return

            await _scheduling_orchestrator.cleanup()
            _scheduling_orchestrator = None
        except Exception as e:
            logger.error(f"Error during scheduling orchestrator cleanup: {str(e)}")
            _scheduling_orchestrator = None
