"""Type definitions for the scheduler module."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SchedulerError(Exception):
    """Base exception for scheduler-related errors."""

    pass


class JobError(SchedulerError):
    """Exception for job-specific errors."""

    pass


class WorkflowError(SchedulerError):
    """Exception for workflow-specific errors."""

    pass


class JobStatus(str, Enum):
    """Status of scheduled jobs."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(str, Enum):
    """Type of scheduled job."""

    WEBSITE_MONITOR = "website_monitor"
    CLASSIFICATION = "classification"
    HEALTH_CHECK = "health_check"
    MAINTENANCE = "maintenance"
    ALERT_PROCESSING = "alert_processing"


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"


class Priority(int, Enum):
    """Job priority levels."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class RetryConfig:
    """Configuration for job retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # 5 minutes
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class JobConfig:
    """Configuration for a scheduled job."""

    job_id: str
    website_id: str
    website_url: str
    website_name: str
    job_type: JobType
    interval: str  # Cron expression or interval
    priority: Priority = Priority.NORMAL
    enabled: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    metadata: dict[str, Any] = field(default_factory=dict)
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class JobExecution:
    """Represents a single job execution."""

    execution_id: str
    job_id: str
    website_id: str
    job_type: JobType
    status: JobStatus
    priority: Priority
    attempt_number: int = 1
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    result_data: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.completed_at and self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    step_id: str
    step_type: JobType
    name: str
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    parameters: dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        """Make WorkflowStep hashable for use as dict keys."""
        return hash(
            (
                self.step_id,
                self.step_type,
                self.name,
                tuple(self.depends_on),
                self.timeout_seconds,
                tuple(sorted(self.parameters.items())) if self.parameters else (),
            )
        )

    def __eq__(self, other):
        """Implement equality for hashable objects."""
        if not isinstance(other, WorkflowStep):
            return False
        return (
            self.step_id == other.step_id
            and self.step_type == other.step_type
            and self.name == other.name
            and self.depends_on == other.depends_on
            and self.timeout_seconds == other.timeout_seconds
            and self.parameters == other.parameters
        )


@dataclass
class WorkflowDefinition:
    """Definition of a workflow with multiple steps."""

    workflow_id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    priority: Priority = Priority.NORMAL
    timeout_seconds: int = 1800  # 30 minutes
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowExecution:
    """Represents a workflow execution."""

    execution_id: str
    workflow_id: str
    website_id: str
    status: WorkflowStatus
    priority: Priority
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    step_executions: dict[str, JobExecution] = field(default_factory=dict)
    error_message: Optional[str] = None
    result_data: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.completed_at and self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()


@dataclass
class SchedulerStats:
    """Statistics for the scheduler."""

    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    pending_jobs: int = 0
    total_workflows: int = 0
    active_workflows: int = 0
    completed_workflows: int = 0
    failed_workflows: int = 0
    uptime_seconds: float = 0
    jobs_per_hour: float = 0
    success_rate: float = 0
    average_job_duration: float = 0


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    component: str
    healthy: bool
    message: str
    details: Optional[dict[str, Any]] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MonitoringReport:
    """Comprehensive monitoring system report."""

    report_id: str
    timestamp: datetime
    overall_health_score: float
    health_checks: list[HealthCheckResult] = field(default_factory=list)
    system_metrics: dict[str, Any] = field(default_factory=dict)
    website_summary: dict[str, Any] = field(default_factory=dict)
    alert_summary: dict[str, Any] = field(default_factory=dict)
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, "report_id") or not self.report_id:
            import uuid

            self.report_id = str(uuid.uuid4())


# Type aliases for job functions
MonitorJobFunc = Callable[[str, str], Awaitable[JobExecution]]
ClassificationJobFunc = Callable[[str, dict[str, Any]], Awaitable[JobExecution]]
HealthCheckFunc = Callable[[], Awaitable[HealthCheckResult]]
JobCallback = Callable[[JobExecution], Awaitable[None]]
WorkflowCallback = Callable[[WorkflowExecution], Awaitable[None]]
