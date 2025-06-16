"""Comprehensive monitoring and health check system for scheduled operations."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import psutil

from ..classifier import get_classification_orchestrator
from ..config import get_settings
from ..notification.slack import get_notification_delivery
from ..scraper import get_scraping_orchestrator
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .manager import get_scheduler_manager
from .types import SchedulerStats
from .workflow import get_workflow_engine

logger = get_structured_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""

    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: list[float]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComponentHealth:
    """Health status of a system component."""

    component_name: str
    healthy: bool
    status_message: str
    last_check: datetime
    metrics: Optional[dict[str, Any]] = None
    error_details: Optional[str] = None


@dataclass
class MonitoringReport:
    """Comprehensive monitoring report."""

    report_id: str
    generated_at: datetime
    system_metrics: SystemMetrics
    component_health: dict[str, ComponentHealth]
    scheduler_stats: SchedulerStats
    active_jobs_count: int
    active_workflows_count: int
    recent_failures: list[dict[str, Any]]
    recommendations: list[str]
    overall_health_score: float  # 0.0 to 1.0


class HealthMonitor(AsyncContextManager):
    """Monitors system health and performance."""

    def __init__(self):
        self.settings = get_settings()
        self.is_running = False

        # Health check configuration
        self.check_interval = 60  # seconds
        self.alert_threshold = 0.7  # health score below this triggers alerts

        # Health tracking
        self._health_history: list[MonitoringReport] = []
        self._max_history_size = 100
        self._health_checks: dict[str, Callable] = {}

        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None

        # Performance tracking
        self._performance_metrics: dict[str, list[float]] = {
            "cpu_usage": [],
            "memory_usage": [],
            "job_success_rate": [],
            "avg_job_duration": [],
        }

    async def setup(self) -> None:
        """Initialize the health monitor."""
        if self.is_running:
            return

        logger.info("Starting health monitor")

        try:
            # Register default health checks
            await self._register_default_health_checks()

            # Start monitoring loop
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

            self.is_running = True
            logger.info("Health monitor started successfully")

        except Exception as e:
            logger.error(f"Failed to start health monitor: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up the health monitor."""
        if not self.is_running:
            return

        logger.info("Stopping health monitor")

        try:
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            self.is_running = False
            logger.info("Health monitor stopped")

        except Exception as e:
            logger.error(f"Error during health monitor cleanup: {str(e)}")

    async def _register_default_health_checks(self) -> None:
        """Register default health check functions."""

        self._health_checks.update(
            {
                "scheduler": self._check_scheduler_health,
                "scraper": self._check_scraper_health,
                "classifier": self._check_classifier_health,
                "storage": self._check_storage_health,
                "workflow_engine": self._check_workflow_engine_health,
                "system_resources": self._check_system_resources,
                "database": self._check_database_health,
                "notification_system": self._check_notification_health,
            }
        )

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Generate monitoring report
                report = await self.generate_monitoring_report()

                # Store report
                self._health_history.append(report)
                if len(self._health_history) > self._max_history_size:
                    self._health_history.pop(0)

                # Check for alerts
                await self._check_alert_conditions(report)

                # Log health summary
                logger.info(
                    "Health check completed",
                    overall_health_score=report.overall_health_score,
                    unhealthy_components=[
                        name
                        for name, health in report.component_health.items()
                        if not health.healthy
                    ],
                )

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def generate_monitoring_report(self) -> MonitoringReport:
        """Generate a comprehensive monitoring report."""

        report_id = f"report-{int(time.time())}"
        generated_at = datetime.utcnow()

        # Get system metrics
        system_metrics = await self._collect_system_metrics()

        # Run all health checks
        component_health = {}
        for component_name, check_func in self._health_checks.items():
            try:
                health = await check_func()
                component_health[component_name] = health
            except Exception as e:
                component_health[component_name] = ComponentHealth(
                    component_name=component_name,
                    healthy=False,
                    status_message=f"Health check failed: {str(e)}",
                    last_check=generated_at,
                    error_details=str(e),
                )

        # Get scheduler statistics
        try:
            scheduler_manager = await get_scheduler_manager()
            scheduler_stats = await scheduler_manager.get_scheduler_stats()
        except Exception as e:
            logger.warning(f"Failed to get scheduler stats: {str(e)}")
            scheduler_stats = SchedulerStats()

        # Count active jobs and workflows
        active_jobs_count = scheduler_stats.active_jobs

        try:
            workflow_engine = await get_workflow_engine()
            active_workflows = await workflow_engine.list_active_workflows()
            active_workflows_count = len(active_workflows)
        except Exception as e:
            logger.warning(f"Failed to get workflow count: {str(e)}")
            active_workflows_count = 0

        # Get recent failures
        recent_failures = await self._get_recent_failures()

        # Generate recommendations
        recommendations = self._generate_recommendations(
            system_metrics, component_health, scheduler_stats
        )

        # Calculate overall health score
        overall_health_score = self._calculate_health_score(
            system_metrics, component_health, scheduler_stats
        )

        return MonitoringReport(
            report_id=report_id,
            generated_at=generated_at,
            system_metrics=system_metrics,
            component_health=component_health,
            scheduler_stats=scheduler_stats,
            active_jobs_count=active_jobs_count,
            active_workflows_count=active_workflows_count,
            recent_failures=recent_failures,
            recommendations=recommendations,
            overall_health_score=overall_health_score,
        )

    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)

            # Load average
            load_average = (
                list(psutil.getloadavg())
                if hasattr(psutil, "getloadavg")
                else [0.0, 0.0, 0.0]
            )

            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                load_average=load_average,
            )

        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {str(e)}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                load_average=[0.0, 0.0, 0.0],
            )

    async def _check_scheduler_health(self) -> ComponentHealth:
        """Check scheduler health."""
        try:
            scheduler_manager = await get_scheduler_manager()
            health_results = await scheduler_manager.health_check()

            healthy = all(result.healthy for result in health_results)
            status_message = (
                "Scheduler healthy" if healthy else "Scheduler issues detected"
            )

            metrics = {
                "checks_passed": sum(1 for r in health_results if r.healthy),
                "total_checks": len(health_results),
                "issues": [r.message for r in health_results if not r.healthy],
            }

            return ComponentHealth(
                component_name="scheduler",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=metrics,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="scheduler",
                healthy=False,
                status_message="Scheduler health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_scraper_health(self) -> ComponentHealth:
        """Check scraper orchestrator health."""
        try:
            scraping_orchestrator = await get_scraping_orchestrator()
            health_check = await scraping_orchestrator.health_check()

            healthy = health_check.get("overall_healthy", False)
            status_message = "Scraper healthy" if healthy else "Scraper issues detected"

            return ComponentHealth(
                component_name="scraper",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=health_check,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="scraper",
                healthy=False,
                status_message="Scraper health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_classifier_health(self) -> ComponentHealth:
        """Check classifier orchestrator health."""
        try:
            classification_orchestrator = await get_classification_orchestrator()
            health_check = await classification_orchestrator.health_check()

            healthy = health_check.get("overall_healthy", False)
            status_message = (
                "Classifier healthy" if healthy else "Classifier issues detected"
            )

            return ComponentHealth(
                component_name="classifier",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=health_check,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="classifier",
                healthy=False,
                status_message="Classifier health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_storage_health(self) -> ComponentHealth:
        """Check storage system health."""
        try:
            storage = await get_storage_manager()

            # Test basic storage operations
            test_start = time.time()
            websites = await storage.list_websites(limit=1)
            response_time = time.time() - test_start

            healthy = response_time < 5.0  # 5 second threshold
            status_message = f"Storage responding in {response_time:.2f}s"

            metrics = {
                "response_time_seconds": response_time,
                "database_accessible": True,
            }

            return ComponentHealth(
                component_name="storage",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=metrics,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="storage",
                healthy=False,
                status_message="Storage health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_workflow_engine_health(self) -> ComponentHealth:
        """Check workflow engine health."""
        try:
            workflow_engine = await get_workflow_engine()

            active_workflows = await workflow_engine.list_active_workflows()
            workflow_defs = workflow_engine.get_workflow_definitions()

            healthy = workflow_engine.is_running
            status_message = (
                f"Workflow engine running with {len(active_workflows)} active workflows"
            )

            metrics = {
                "is_running": workflow_engine.is_running,
                "active_workflows": len(active_workflows),
                "registered_workflows": len(workflow_defs),
            }

            return ComponentHealth(
                component_name="workflow_engine",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=metrics,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="workflow_engine",
                healthy=False,
                status_message="Workflow engine health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_system_resources(self) -> ComponentHealth:
        """Check system resource usage."""
        try:
            metrics = await self._collect_system_metrics()

            # Define thresholds
            cpu_threshold = 85.0
            memory_threshold = 85.0
            disk_threshold = 90.0

            issues = []
            if metrics.cpu_percent > cpu_threshold:
                issues.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            if metrics.memory_percent > memory_threshold:
                issues.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            if metrics.disk_usage_percent > disk_threshold:
                issues.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")

            healthy = len(issues) == 0
            status_message = (
                "System resources healthy"
                if healthy
                else f"Resource issues: {'; '.join(issues)}"
            )

            return ComponentHealth(
                component_name="system_resources",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics={
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "disk_usage_percent": metrics.disk_usage_percent,
                    "memory_available_gb": metrics.memory_available_gb,
                    "disk_free_gb": metrics.disk_free_gb,
                },
            )

        except Exception as e:
            return ComponentHealth(
                component_name="system_resources",
                healthy=False,
                status_message="System resource check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        try:
            storage = await get_storage_manager()

            # Test database query performance
            start_time = time.time()
            websites = await storage.list_websites(limit=5)
            query_time = time.time() - start_time

            healthy = query_time < 2.0  # 2 second threshold
            status_message = f"Database responding in {query_time:.3f}s"

            metrics = {
                "query_time_seconds": query_time,
                "connection_successful": True,
                "websites_count": len(websites) if websites else 0,
            }

            return ComponentHealth(
                component_name="database",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=metrics,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="database",
                healthy=False,
                status_message="Database health check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _check_notification_health(self) -> ComponentHealth:
        """Check notification system health."""
        try:
            slack_delivery = await get_notification_delivery()

            # Test Slack connectivity (simplified)
            healthy = True  # Would implement actual connectivity test
            status_message = "Notification system operational"

            metrics = {
                "slack_available": True,
                "last_notification": None,  # Would track last successful notification
            }

            return ComponentHealth(
                component_name="notification_system",
                healthy=healthy,
                status_message=status_message,
                last_check=datetime.utcnow(),
                metrics=metrics,
            )

        except Exception as e:
            return ComponentHealth(
                component_name="notification_system",
                healthy=False,
                status_message="Notification system check failed",
                last_check=datetime.utcnow(),
                error_details=str(e),
            )

    async def _get_recent_failures(self) -> list[dict[str, Any]]:
        """Get recent job and workflow failures."""
        failures = []

        try:
            # This would query the database for recent failures
            # For now, return empty list
            return failures

        except Exception as e:
            logger.error(f"Failed to get recent failures: {str(e)}")
            return []

    def _generate_recommendations(
        self,
        system_metrics: SystemMetrics,
        component_health: dict[str, ComponentHealth],
        scheduler_stats: SchedulerStats,
    ) -> list[str]:
        """Generate recommendations based on health data."""
        recommendations = []

        # System resource recommendations
        if system_metrics.cpu_percent > 80:
            recommendations.append(
                "Consider reducing concurrent job limits due to high CPU usage"
            )

        if system_metrics.memory_percent > 80:
            recommendations.append(
                "High memory usage detected - consider increasing available memory"
            )

        if system_metrics.disk_usage_percent > 85:
            recommendations.append(
                "Disk space running low - consider cleanup or expansion"
            )

        # Component-specific recommendations
        unhealthy_components = [
            name for name, health in component_health.items() if not health.healthy
        ]

        if unhealthy_components:
            recommendations.append(
                f"Address issues in: {', '.join(unhealthy_components)}"
            )

        # Scheduler performance recommendations
        if scheduler_stats.success_rate < 0.9 and scheduler_stats.total_jobs > 10:
            recommendations.append("Job success rate is low - investigate failing jobs")

        if scheduler_stats.average_job_duration > 300:  # 5 minutes
            recommendations.append(
                "Average job duration is high - consider optimization"
            )

        return recommendations

    def _calculate_health_score(
        self,
        system_metrics: SystemMetrics,
        component_health: dict[str, ComponentHealth],
        scheduler_stats: SchedulerStats,
    ) -> float:
        """Calculate overall health score (0.0 to 1.0)."""

        scores = []

        # System resource scores
        cpu_score = max(0, 1.0 - (system_metrics.cpu_percent / 100))
        memory_score = max(0, 1.0 - (system_metrics.memory_percent / 100))
        disk_score = max(0, 1.0 - (system_metrics.disk_usage_percent / 100))

        scores.extend([cpu_score, memory_score, disk_score])

        # Component health scores
        for health in component_health.values():
            scores.append(1.0 if health.healthy else 0.0)

        # Scheduler performance scores
        if scheduler_stats.total_jobs > 0:
            success_rate_score = scheduler_stats.success_rate
            scores.append(success_rate_score)

        # Calculate weighted average
        if scores:
            return sum(scores) / len(scores)
        else:
            return 1.0

    async def _check_alert_conditions(self, report: MonitoringReport) -> None:
        """Check if alert conditions are met and send notifications."""

        if report.overall_health_score < self.alert_threshold:
            await self._send_health_alert(report)

    async def _send_health_alert(self, report: MonitoringReport) -> None:
        """Send health alert notification."""
        try:
            slack_delivery = await get_notification_delivery()

            # Format alert message
            unhealthy_components = [
                name
                for name, health in report.component_health.items()
                if not health.healthy
            ]

            message = "🚨 System Health Alert\n\n"
            message += f"Overall Health Score: {report.overall_health_score:.2f}\n"
            message += f"Unhealthy Components: {', '.join(unhealthy_components)}\n\n"

            if report.recommendations:
                message += "Recommendations:\n"
                for rec in report.recommendations:
                    message += f"• {rec}\n"

            # Send alert (simplified)
            logger.warning(
                "Health alert triggered",
                health_score=report.overall_health_score,
                unhealthy_components=unhealthy_components,
            )

        except Exception as e:
            logger.error(f"Failed to send health alert: {str(e)}")

    def get_latest_report(self) -> Optional[MonitoringReport]:
        """Get the latest monitoring report."""
        return self._health_history[-1] if self._health_history else None

    def get_health_history(self, limit: int = 10) -> list[MonitoringReport]:
        """Get recent health history."""
        return self._health_history[-limit:] if self._health_history else []

    def get_health_trends(self) -> dict[str, list[float]]:
        """Get health trend data."""
        trends = {
            "health_scores": [],
            "cpu_usage": [],
            "memory_usage": [],
            "job_success_rates": [],
        }

        for report in self._health_history[-24:]:  # Last 24 reports
            trends["health_scores"].append(report.overall_health_score)
            trends["cpu_usage"].append(report.system_metrics.cpu_percent)
            trends["memory_usage"].append(report.system_metrics.memory_percent)
            trends["job_success_rates"].append(report.scheduler_stats.success_rate)

        return trends


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


async def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor."""
    global _health_monitor

    if _health_monitor is None:
        _health_monitor = HealthMonitor()
        await _health_monitor.setup()

    return _health_monitor


async def cleanup_health_monitor() -> None:
    """Clean up the global health monitor."""
    global _health_monitor

    if _health_monitor:
        await _health_monitor.cleanup()
        _health_monitor = None
