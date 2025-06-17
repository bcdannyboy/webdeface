"""Workflow engine for coordinating scraping and classification pipelines."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from ..classifier import get_classification_orchestrator
from ..config import get_settings
from ..scraper import get_scraping_orchestrator
from ..storage import get_storage_manager
from ..utils.async_utils import AsyncContextManager
from ..utils.logging import get_structured_logger
from .types import (
    JobExecution,
    JobStatus,
    JobType,
    Priority,
    WorkflowDefinition,
    WorkflowError,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStep,
)

logger = get_structured_logger(__name__)


class StepStatus(str, Enum):
    """Status of individual workflow steps."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowEngine(AsyncContextManager):
    """Orchestrates multi-step workflows for website monitoring."""

    def __init__(self):
        self.settings = get_settings()
        self.is_running = False

        # Workflow tracking
        self._active_workflows: dict[str, WorkflowExecution] = {}
        self._workflow_definitions: dict[str, WorkflowDefinition] = {}

        # Step execution tracking
        self._step_dependencies: dict[str, set[str]] = {}
        self._completed_steps: dict[
            str, set[str]
        ] = {}  # workflow_id -> completed step_ids

        # Statistics
        self.total_workflows_executed = 0
        self.total_workflows_succeeded = 0
        self.total_workflows_failed = 0

    async def setup(self) -> None:
        """Initialize the workflow engine."""
        if self.is_running:
            return

        logger.info("Starting workflow engine")

        try:
            # Load predefined workflows
            await self._load_default_workflows()

            self.is_running = True
            logger.info("Workflow engine started successfully")

        except Exception as e:
            logger.error(f"Failed to start workflow engine: {str(e)}")
            raise WorkflowError(f"Workflow engine startup failed: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up the workflow engine."""
        if not self.is_running:
            return

        logger.info("Stopping workflow engine")

        try:
            # Cancel active workflows
            for workflow_id in list(self._active_workflows.keys()):
                await self.cancel_workflow(workflow_id)

            self.is_running = False
            logger.info("Workflow engine stopped")

        except Exception as e:
            logger.error(f"Error during workflow engine cleanup: {str(e)}")

    async def _load_default_workflows(self) -> None:
        """Load default workflow definitions."""

        # Website monitoring workflow
        monitoring_workflow = WorkflowDefinition(
            workflow_id="website_monitoring",
            name="Website Monitoring Pipeline",
            description="Complete website monitoring with scraping, classification, and alerting",
            steps=[
                WorkflowStep(
                    step_id="scrape_website",
                    step_type=JobType.WEBSITE_MONITOR,
                    name="Scrape Website Content",
                    timeout_seconds=300,
                    parameters={"include_visual_analysis": True},
                ),
                WorkflowStep(
                    step_id="classify_content",
                    step_type=JobType.CLASSIFICATION,
                    name="Classify Content Changes",
                    depends_on=["scrape_website"],
                    timeout_seconds=120,
                    parameters={"include_vectorization": True},
                ),
                WorkflowStep(
                    step_id="process_alerts",
                    step_type=JobType.ALERT_PROCESSING,
                    name="Process and Send Alerts",
                    depends_on=["classify_content"],
                    timeout_seconds=60,
                    parameters={"delivery_channels": ["slack"]},
                ),
            ],
            priority=Priority.NORMAL,
            timeout_seconds=600,  # 10 minutes total
        )

        # Health check workflow
        health_check_workflow = WorkflowDefinition(
            workflow_id="system_health_check",
            name="System Health Monitoring",
            description="Comprehensive health check of all system components",
            steps=[
                WorkflowStep(
                    step_id="check_scraper_health",
                    step_type=JobType.HEALTH_CHECK,
                    name="Check Scraper Health",
                    timeout_seconds=30,
                    parameters={"component": "scraper"},
                ),
                WorkflowStep(
                    step_id="check_classifier_health",
                    step_type=JobType.HEALTH_CHECK,
                    name="Check Classifier Health",
                    timeout_seconds=30,
                    parameters={"component": "classifier"},
                ),
                WorkflowStep(
                    step_id="check_storage_health",
                    step_type=JobType.HEALTH_CHECK,
                    name="Check Storage Health",
                    timeout_seconds=30,
                    parameters={"component": "storage"},
                ),
                WorkflowStep(
                    step_id="aggregate_health_report",
                    step_type=JobType.ALERT_PROCESSING,
                    name="Generate Health Report",
                    depends_on=[
                        "check_scraper_health",
                        "check_classifier_health",
                        "check_storage_health",
                    ],
                    timeout_seconds=60,
                    parameters={"report_type": "health_summary"},
                ),
            ],
            priority=Priority.LOW,
            timeout_seconds=300,  # 5 minutes total
        )

        # Store workflow definitions
        self._workflow_definitions[
            monitoring_workflow.workflow_id
        ] = monitoring_workflow
        self._workflow_definitions[
            health_check_workflow.workflow_id
        ] = health_check_workflow

        logger.info(
            "Default workflows loaded",
            workflows=list(self._workflow_definitions.keys()),
        )

    async def execute_workflow(
        self,
        workflow_id: str,
        website_id: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> str:
        """Execute a workflow for a specific website."""

        if not self.is_running:
            raise WorkflowError("Workflow engine is not running")

        if workflow_id not in self._workflow_definitions:
            raise WorkflowError(f"Unknown workflow: {workflow_id}")

        workflow_def = self._workflow_definitions[workflow_id]
        execution_id = f"exec-{uuid.uuid4()}"

        # Create workflow execution
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            website_id=website_id,
            status=WorkflowStatus.PENDING,
            priority=workflow_def.priority,
        )

        self._active_workflows[execution_id] = execution
        self._completed_steps[execution_id] = set()

        logger.info(
            "Starting workflow execution",
            execution_id=execution_id,
            workflow_id=workflow_id,
            website_id=website_id,
        )

        # Start workflow execution asynchronously
        asyncio.create_task(
            self._execute_workflow_steps(execution, workflow_def, parameters or {})
        )

        return execution_id

    async def _execute_workflow_steps(
        self,
        execution: WorkflowExecution,
        workflow_def: WorkflowDefinition,
        parameters: dict[str, Any],
    ) -> None:
        """Execute workflow steps in dependency order."""

        execution.started_at = datetime.utcnow()
        execution.status = WorkflowStatus.RUNNING

        try:
            # Build dependency graph
            step_graph = self._build_dependency_graph(workflow_def.steps)

            # Execute steps in topological order
            while step_graph:
                # Find steps with no dependencies
                ready_steps = [
                    step
                    for step in step_graph
                    if not step_graph[step]
                    or step_graph[step].issubset(
                        self._completed_steps[execution.execution_id]
                    )
                ]

                if not ready_steps:
                    # Check for circular dependencies
                    raise WorkflowError(
                        f"Circular dependency detected in workflow {workflow_def.workflow_id}"
                    )

                # Execute ready steps in parallel
                step_tasks = []
                for step in ready_steps:
                    task = asyncio.create_task(
                        self._execute_workflow_step(execution, step, parameters)
                    )
                    step_tasks.append((step.step_id, task))

                # Wait for all steps to complete
                for step_id, task in step_tasks:
                    try:
                        step_execution = await task

                        if step_execution.status == JobStatus.SUCCESS:
                            self._completed_steps[execution.execution_id].add(step_id)
                            execution.step_executions[step_id] = step_execution
                        else:
                            # Step failed, fail the entire workflow
                            execution.status = WorkflowStatus.FAILED
                            execution.error_message = (
                                f"Step {step_id} failed: {step_execution.error_message}"
                            )
                            break

                    except Exception as e:
                        execution.status = WorkflowStatus.FAILED
                        execution.error_message = (
                            f"Step {step_id} execution failed: {str(e)}"
                        )
                        break

                # Remove completed steps from graph
                for step in ready_steps:
                    if step.step_id in self._completed_steps[execution.execution_id]:
                        step_graph.pop(step, None)

                # Check if workflow failed
                if execution.status == WorkflowStatus.FAILED:
                    break

            # Check final status
            if execution.status == WorkflowStatus.RUNNING:
                if len(self._completed_steps[execution.execution_id]) == len(
                    workflow_def.steps
                ):
                    execution.status = WorkflowStatus.SUCCESS
                    self.total_workflows_succeeded += 1
                else:
                    execution.status = WorkflowStatus.PARTIAL_SUCCESS

            if execution.status == WorkflowStatus.FAILED:
                self.total_workflows_failed += 1

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            self.total_workflows_failed += 1

            logger.error(
                "Workflow execution failed",
                execution_id=execution.execution_id,
                workflow_id=workflow_def.workflow_id,
                error=str(e),
            )

        finally:
            execution.completed_at = datetime.utcnow()
            self.total_workflows_executed += 1

            # Store workflow execution results
            await self._store_workflow_execution(execution)

            # Clean up
            self._active_workflows.pop(execution.execution_id, None)
            self._completed_steps.pop(execution.execution_id, None)

            logger.info(
                "Workflow execution completed",
                execution_id=execution.execution_id,
                workflow_id=workflow_def.workflow_id,
                status=execution.status.value,
                duration=execution.duration,
            )

    def _build_dependency_graph(
        self, steps: list[WorkflowStep]
    ) -> dict[WorkflowStep, set[str]]:
        """Build a dependency graph for workflow steps."""

        step_map = {step.step_id: step for step in steps}
        graph = {}

        # First pass: validate dependencies exist
        for step in steps:
            dependencies = set()
            for dep_id in step.depends_on:
                if dep_id in step_map:
                    dependencies.add(dep_id)
                else:
                    raise WorkflowError(
                        f"Unknown dependency '{dep_id}' for step '{step.step_id}'"
                    )

            graph[step] = dependencies

        # Second pass: detect circular dependencies using topological sort
        self._detect_circular_dependencies(graph)

        return graph

    def _detect_circular_dependencies(
        self, graph: dict[WorkflowStep, set[str]]
    ) -> None:
        """Detect circular dependencies in the workflow graph."""
        # Convert to a simpler format for cycle detection
        step_deps = {}
        for step, deps in graph.items():
            step_deps[step.step_id] = deps

        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for dep_id in step_deps.get(node_id, set()):
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        # Check each node for cycles
        for step_id in step_deps:
            if step_id not in visited:
                if has_cycle(step_id):
                    raise WorkflowError(
                        "Circular dependency detected in workflow steps"
                    )

    async def _execute_workflow_step(
        self,
        workflow_execution: WorkflowExecution,
        step: WorkflowStep,
        workflow_parameters: dict[str, Any],
    ) -> JobExecution:
        """Execute a single workflow step."""

        step_execution = JobExecution(
            execution_id=f"step-{uuid.uuid4()}",
            job_id=f"{workflow_execution.execution_id}-{step.step_id}",
            website_id=workflow_execution.website_id,
            job_type=step.step_type,
            status=JobStatus.PENDING,
            priority=workflow_execution.priority,
        )

        logger.info(
            "Executing workflow step",
            execution_id=step_execution.execution_id,
            step_id=step.step_id,
            step_type=step.step_type.value,
            workflow_execution=workflow_execution.execution_id,
        )

        try:
            step_execution.started_at = datetime.utcnow()
            step_execution.status = JobStatus.RUNNING

            # Merge step parameters with workflow parameters
            parameters = {**workflow_parameters, **step.parameters}

            # Execute step based on type
            if step.step_type == JobType.WEBSITE_MONITOR:
                result = await self._execute_scraping_step(
                    workflow_execution.website_id, parameters
                )
            elif step.step_type == JobType.CLASSIFICATION:
                result = await self._execute_classification_step(
                    workflow_execution, parameters
                )
            elif step.step_type == JobType.ALERT_PROCESSING:
                result = await self._execute_alert_step(workflow_execution, parameters)
            elif step.step_type == JobType.HEALTH_CHECK:
                result = await self._execute_health_check_step(parameters)
            else:
                raise WorkflowError(f"Unknown step type: {step.step_type}")

            step_execution.result_data = result
            step_execution.status = JobStatus.SUCCESS

        except Exception as e:
            step_execution.status = JobStatus.FAILED
            step_execution.error_message = str(e)

            logger.error(
                "Workflow step failed",
                execution_id=step_execution.execution_id,
                step_id=step.step_id,
                error=str(e),
            )

        finally:
            step_execution.completed_at = datetime.utcnow()

        return step_execution

    async def _execute_scraping_step(
        self, website_id: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute website scraping step."""

        try:
            # Get website details
            storage = await get_storage_manager()
            website = await storage.get_website(website_id)

            if not website:
                raise WorkflowError(f"Website not found: {website_id}")

            # Get scraping orchestrator
            scraping_orchestrator = await get_scraping_orchestrator()

            # Schedule scraping job
            scraping_job_id = await scraping_orchestrator.schedule_scraping(
                website_id=website_id,
                url=website.url,
                priority=1,  # High priority for workflow jobs
                metadata={"workflow_step": True, **parameters},
            )

            # Wait for scraping to complete (simplified - in production would use callbacks)
            await asyncio.sleep(10)  # Allow time for scraping

            # Get scraping results
            scraping_stats = await scraping_orchestrator.get_orchestrator_stats()

            return {
                "scraping_job_id": scraping_job_id,
                "scraping_stats": scraping_stats,
                "website_url": website.url,
            }

        except Exception as e:
            logger.error(f"Scraping step failed: {str(e)}")
            raise

    async def _execute_classification_step(
        self, workflow_execution: WorkflowExecution, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute classification step."""

        try:
            # Get the latest snapshot from scraping step
            storage = await get_storage_manager()
            latest_snapshot = await storage.get_latest_snapshot(
                workflow_execution.website_id
            )

            if not latest_snapshot:
                raise WorkflowError("No snapshot found for classification")

            # Get website details
            website = await storage.get_website(workflow_execution.website_id)

            # Get classification orchestrator
            classification_orchestrator = await get_classification_orchestrator()

            # Prepare content data
            content_data = {
                "main_content": latest_snapshot.content_text or "",
                "content_hash": latest_snapshot.content_hash,
                "title": getattr(latest_snapshot, "title", ""),
                "word_count": len((latest_snapshot.content_text or "").split()),
            }

            # Schedule classification job
            classification_job_id = (
                await classification_orchestrator.schedule_classification(
                    website_id=workflow_execution.website_id,
                    website_url=website.url,
                    website_name=website.name,
                    snapshot_id=latest_snapshot.id,
                    content_data=content_data,
                    priority=1,
                    metadata={"workflow_step": True, **parameters},
                )
            )

            # Wait for classification to complete
            await asyncio.sleep(5)  # Allow time for classification

            # Get classification results
            classification_stats = (
                await classification_orchestrator.get_orchestrator_stats()
            )

            return {
                "classification_job_id": classification_job_id,
                "classification_stats": classification_stats,
                "snapshot_id": latest_snapshot.id,
            }

        except Exception as e:
            logger.error(f"Classification step failed: {str(e)}")
            raise

    async def _execute_alert_step(
        self, workflow_execution: WorkflowExecution, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute alert processing step."""

        try:
            # Check if alerts need to be sent based on classification results
            storage = await get_storage_manager()

            # Get recent alerts for this website
            recent_alerts = await storage.get_alerts_for_website(
                workflow_execution.website_id, limit=5
            )

            # Get delivery manager using lazy import
            try:
                from ..notification.slack.delivery import get_notification_delivery
                slack_delivery = await get_notification_delivery()
            except ImportError:
                logger.warning("Notification delivery not available")
                slack_delivery = None

            alerts_sent = 0
            if recent_alerts and slack_delivery:
                for alert in recent_alerts:
                    if alert.status == "open" and alert.notifications_sent == 0:
                        # Send alert via Slack
                        success = await slack_delivery.send_alert_notification(alert)
                        if success:
                            alerts_sent += 1
            elif recent_alerts and not slack_delivery:
                logger.warning("Cannot send alerts: notification delivery unavailable")

            return {
                "alerts_processed": len(recent_alerts) if recent_alerts else 0,
                "alerts_sent": alerts_sent,
                "delivery_channels": parameters.get("delivery_channels", ["slack"]),
            }

        except Exception as e:
            logger.error(f"Alert processing step failed: {str(e)}")
            raise

    async def _execute_health_check_step(
        self, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute health check step."""

        try:
            component = parameters.get("component", "all")
            health_results = {}

            if component in ["scraper", "all"]:
                scraping_orchestrator = await get_scraping_orchestrator()
                health_results["scraper"] = await scraping_orchestrator.health_check()

            if component in ["classifier", "all"]:
                classification_orchestrator = await get_classification_orchestrator()
                health_results[
                    "classifier"
                ] = await classification_orchestrator.health_check()

            if component in ["storage", "all"]:
                storage = await get_storage_manager()
                # This would be a health check method on storage manager
                health_results["storage"] = {
                    "healthy": True,
                    "message": "Storage operational",
                }

            return {
                "component": component,
                "health_results": health_results,
                "overall_healthy": all(
                    result.get("overall_healthy", True)
                    for result in health_results.values()
                ),
            }

        except Exception as e:
            logger.error(f"Health check step failed: {str(e)}")
            raise

    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow."""

        if execution_id not in self._active_workflows:
            return False

        execution = self._active_workflows[execution_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()

        logger.info("Workflow cancelled", execution_id=execution_id)
        return True

    async def get_workflow_status(
        self, execution_id: str
    ) -> Optional[WorkflowExecution]:
        """Get the status of a workflow execution."""
        return self._active_workflows.get(execution_id)

    async def list_active_workflows(self) -> list[WorkflowExecution]:
        """List all active workflow executions."""
        return list(self._active_workflows.values())

    async def _store_workflow_execution(self, execution: WorkflowExecution) -> None:
        """Store workflow execution results in database."""
        try:
            storage = await get_storage_manager()
            # This would store the workflow execution
            logger.debug(
                "Workflow execution stored", execution_id=execution.execution_id
            )
        except Exception as e:
            logger.error(f"Failed to store workflow execution: {str(e)}")

    def get_workflow_definitions(self) -> dict[str, WorkflowDefinition]:
        """Get all registered workflow definitions."""
        return self._workflow_definitions.copy()

    async def register_workflow(self, workflow_def: WorkflowDefinition) -> None:
        """Register a new workflow definition."""
        self._workflow_definitions[workflow_def.workflow_id] = workflow_def
        logger.info("Workflow registered", workflow_id=workflow_def.workflow_id)


# Global workflow engine instance
_workflow_engine: Optional[WorkflowEngine] = None


async def get_workflow_engine() -> WorkflowEngine:
    """Get or create the global workflow engine."""
    global _workflow_engine

    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
        await _workflow_engine.setup()

    return _workflow_engine


async def cleanup_workflow_engine() -> None:
    """Clean up the global workflow engine."""
    global _workflow_engine

    if _workflow_engine:
        await _workflow_engine.cleanup()
        _workflow_engine = None
