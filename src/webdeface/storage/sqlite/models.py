"""SQLAlchemy ORM models for web defacement monitoring data."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()


class Website(Base):
    """Website entity for monitoring."""

    __tablename__ = "websites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Monitoring configuration
    check_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=300
    )  # 5 minutes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    snapshots: Mapped[list[WebsiteSnapshot]] = relationship(
        "WebsiteSnapshot", back_populates="website", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[DefacementAlert]] = relationship(
        "DefacementAlert", back_populates="website", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_websites_url", "url"),
        Index("ix_websites_is_active", "is_active"),
        Index("ix_websites_last_checked", "last_checked_at"),
    )

    def __repr__(self) -> str:
        return f"<Website(id={self.id}, url={self.url}, name={self.name})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "url", self.url
        yield "name", self.name
        yield "description", self.description
        yield "is_active", self.is_active
        yield "created_at", self.created_at
        yield "updated_at", self.updated_at
        yield "last_checked_at", self.last_checked_at
        # Exclude relationships to prevent circular references


class WebsiteSnapshot(Base):
    """Snapshot of website content at a specific point in time."""

    __tablename__ = "website_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("websites.id"), nullable=False
    )

    # Content data
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    raw_html: Mapped[Optional[bytes]] = mapped_column(LargeBinary)

    # HTTP response metadata
    status_code: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[float] = mapped_column(Float)
    content_length: Mapped[Optional[int]] = mapped_column(Integer)
    content_type: Mapped[Optional[str]] = mapped_column(String(255))

    # Vector database reference
    vector_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Analysis results
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    is_defaced: Mapped[Optional[bool]] = mapped_column(Boolean)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    website: Mapped[Website] = relationship("Website", back_populates="snapshots")

    # Indexes
    __table_args__ = (
        Index("ix_snapshots_website_id", "website_id"),
        Index("ix_snapshots_content_hash", "content_hash"),
        Index("ix_snapshots_captured_at", "captured_at"),
        Index("ix_snapshots_is_defaced", "is_defaced"),
        Index("ix_snapshots_website_captured", "website_id", "captured_at"),
    )

    def __repr__(self) -> str:
        return f"<WebsiteSnapshot(id={self.id}, website_id={self.website_id}, captured_at={self.captured_at})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "website_id", self.website_id
        yield "content_hash", self.content_hash
        yield "status_code", self.status_code
        yield "response_time_ms", self.response_time_ms
        yield "content_length", self.content_length
        yield "similarity_score", self.similarity_score
        yield "is_defaced", self.is_defaced
        yield "confidence_score", self.confidence_score
        yield "captured_at", self.captured_at
        yield "analyzed_at", self.analyzed_at
        # Exclude relationships to prevent circular references


class DefacementAlert(Base):
    """Alert record for detected defacements."""

    __tablename__ = "defacement_alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("websites.id"), nullable=False
    )
    snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("website_snapshots.id")
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # defacement, site_down, etc.
    severity: Mapped[str] = mapped_column(
        String(20), default="medium"
    )  # low, medium, high, critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification details
    classification_label: Mapped[Optional[str]] = mapped_column(String(100))
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="open"
    )  # open, acknowledged, resolved
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Notification tracking
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_notification_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    website: Mapped[Website] = relationship("Website", back_populates="alerts")

    # Indexes
    __table_args__ = (
        Index("ix_alerts_website_id", "website_id"),
        Index("ix_alerts_alert_type", "alert_type"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_website_status", "website_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<DefacementAlert(id={self.id}, website_id={self.website_id}, alert_type={self.alert_type})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "website_id", self.website_id
        yield "snapshot_id", self.snapshot_id
        yield "alert_type", self.alert_type
        yield "severity", self.severity
        yield "title", self.title
        yield "description", self.description
        yield "classification_label", self.classification_label
        yield "confidence_score", self.confidence_score
        yield "similarity_score", self.similarity_score
        yield "status", self.status
        yield "acknowledged_by", self.acknowledged_by
        yield "acknowledged_at", self.acknowledged_at
        yield "resolved_at", self.resolved_at
        yield "notifications_sent", self.notifications_sent
        yield "last_notification_at", self.last_notification_at
        yield "created_at", self.created_at
        yield "updated_at", self.updated_at
        # Exclude relationships to prevent circular references


class ScheduledJob(Base):
    """Scheduled job configuration and tracking."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("websites.id"), nullable=False
    )

    # Job configuration
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    interval_expression: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Retry configuration
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[float] = mapped_column(Float, default=1.0)

    # Status and timing
    status: Mapped[str] = mapped_column(String(20), default="pending")
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Metadata
    job_metadata: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    website: Mapped[Website] = relationship("Website")
    executions: Mapped[list[JobExecution]] = relationship(
        "JobExecution", back_populates="job", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_scheduled_jobs_job_id", "job_id"),
        Index("ix_scheduled_jobs_website_id", "website_id"),
        Index("ix_scheduled_jobs_job_type", "job_type"),
        Index("ix_scheduled_jobs_status", "status"),
        Index("ix_scheduled_jobs_enabled", "enabled"),
        Index("ix_scheduled_jobs_next_run", "next_run_at"),
        Index("ix_scheduled_jobs_website_type", "website_id", "job_type"),
    )

    def __repr__(self) -> str:
        return f"<ScheduledJob(job_id={self.job_id}, website_id={self.website_id}, job_type={self.job_type})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "job_id", self.job_id
        yield "website_id", self.website_id
        yield "job_type", self.job_type
        yield "interval_expression", self.interval_expression
        yield "priority", self.priority
        yield "enabled", self.enabled
        yield "max_retries", self.max_retries
        yield "retry_delay", self.retry_delay
        yield "status", self.status
        yield "next_run_at", self.next_run_at
        yield "last_run_at", self.last_run_at
        yield "last_success_at", self.last_success_at
        yield "created_at", self.created_at
        yield "updated_at", self.updated_at
        # Exclude relationships to prevent circular references


class JobExecution(Base):
    """Individual job execution record."""

    __tablename__ = "job_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    execution_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scheduled_jobs.id"), nullable=False
    )
    website_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("websites.id"), nullable=False
    )

    # Execution details
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Results
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    result_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    job: Mapped[ScheduledJob] = relationship(
        "ScheduledJob", back_populates="executions"
    )
    website: Mapped[Website] = relationship("Website")

    # Indexes
    __table_args__ = (
        Index("ix_job_executions_execution_id", "execution_id"),
        Index("ix_job_executions_job_id", "job_id"),
        Index("ix_job_executions_website_id", "website_id"),
        Index("ix_job_executions_status", "status"),
        Index("ix_job_executions_job_type", "job_type"),
        Index("ix_job_executions_started_at", "started_at"),
        Index("ix_job_executions_website_status", "website_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<JobExecution(execution_id={self.execution_id}, job_id={self.job_id}, status={self.status})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "execution_id", self.execution_id
        yield "job_id", self.job_id
        yield "website_id", self.website_id
        yield "job_type", self.job_type
        yield "status", self.status
        yield "priority", self.priority
        yield "attempt_number", self.attempt_number
        yield "started_at", self.started_at
        yield "completed_at", self.completed_at
        yield "duration_seconds", self.duration_seconds
        yield "error_message", self.error_message
        yield "created_at", self.created_at
        # Exclude relationships to prevent circular references


class WorkflowDefinition(Base):
    """Workflow definition with multiple steps."""

    __tablename__ = "workflow_definitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Workflow details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)

    # Configuration
    workflow_steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    executions: Mapped[list[WorkflowExecution]] = relationship(
        "WorkflowExecution", back_populates="workflow_def", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_workflow_definitions_workflow_id", "workflow_id"),
        Index("ix_workflow_definitions_enabled", "enabled"),
        Index("ix_workflow_definitions_priority", "priority"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowDefinition(workflow_id={self.workflow_id}, name={self.name})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "workflow_id", self.workflow_id
        yield "name", self.name
        yield "description", self.description
        yield "priority", self.priority
        yield "timeout_seconds", self.timeout_seconds
        yield "enabled", self.enabled
        yield "created_at", self.created_at
        yield "updated_at", self.updated_at
        # Exclude relationships to prevent circular references


class WorkflowExecution(Base):
    """Individual workflow execution record."""

    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    execution_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_definitions.id"), nullable=False
    )
    website_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("websites.id"), nullable=False
    )

    # Execution details
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Results
    step_executions: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    result_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    workflow_def: Mapped[WorkflowDefinition] = relationship(
        "WorkflowDefinition", back_populates="executions"
    )
    website: Mapped[Website] = relationship("Website")

    # Indexes
    __table_args__ = (
        Index("ix_workflow_executions_execution_id", "execution_id"),
        Index("ix_workflow_executions_workflow_id", "workflow_id"),
        Index("ix_workflow_executions_website_id", "website_id"),
        Index("ix_workflow_executions_status", "status"),
        Index("ix_workflow_executions_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution(execution_id={self.execution_id}, workflow_id={self.workflow_id}, status={self.status})>"

    def __rich_repr__(self):
        """Rich-compatible representation that avoids circular references."""
        yield "id", self.id
        yield "execution_id", self.execution_id
        yield "workflow_id", self.workflow_id
        yield "website_id", self.website_id
        yield "status", self.status
        yield "priority", self.priority
        yield "started_at", self.started_at
        yield "completed_at", self.completed_at
        yield "duration_seconds", self.duration_seconds
        yield "error_message", self.error_message
        yield "created_at", self.created_at
        # Exclude relationships to prevent circular references
