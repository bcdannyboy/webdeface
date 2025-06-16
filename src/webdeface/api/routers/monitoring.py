"""Monitoring control API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...utils.logging import get_structured_logger
from ..auth import require_permission
from ..dependencies import get_orchestrator, get_storage_manager

logger = get_structured_logger(__name__)

router = APIRouter()


class MonitoringStartRequest(BaseModel):
    """Request model for starting monitoring."""

    website_ids: Optional[list[str]] = None
    priority: str = "normal"


class MonitoringResponse(BaseModel):
    """Response model for monitoring operations."""

    success: bool
    message: str
    website_ids: list[str]
    execution_ids: list[str]


class MonitoringStatusResponse(BaseModel):
    """Response model for monitoring status."""

    overall_status: str
    active_websites: int
    total_jobs_scheduled: int
    total_workflows_executed: int
    uptime_seconds: float
    components: dict[str, bool]


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""

    execution_id: str
    workflow_id: str
    website_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]


@router.post("/start", response_model=MonitoringResponse)
async def start_monitoring(
    request: MonitoringStartRequest,
    orchestrator=Depends(get_orchestrator),
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> MonitoringResponse:
    """Start monitoring for specified websites or all active websites."""

    logger.info(
        "Starting monitoring",
        user_id=current_user["id"],
        website_ids=request.website_ids,
    )

    try:
        execution_ids = []
        website_ids = []

        if request.website_ids:
            # Start monitoring for specific websites
            for website_id in request.website_ids:
                website = await storage.get_website(website_id)
                if not website:
                    logger.warning("Website not found", website_id=website_id)
                    continue

                execution_id = await orchestrator.schedule_website_monitoring(
                    website_id
                )
                execution_ids.append(execution_id)
                website_ids.append(website_id)
        else:
            # Start monitoring for all active websites
            websites = await storage.list_websites()
            active_websites = [w for w in websites if w.is_active]

            for website in active_websites:
                execution_id = await orchestrator.schedule_website_monitoring(
                    website.id
                )
                execution_ids.append(execution_id)
                website_ids.append(website.id)

        message = f"Monitoring started for {len(website_ids)} websites"
        logger.info("Monitoring started", website_count=len(website_ids))

        return MonitoringResponse(
            success=True,
            message=message,
            website_ids=website_ids,
            execution_ids=execution_ids,
        )

    except Exception as e:
        logger.error("Failed to start monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}",
        )


@router.post("/stop", response_model=MonitoringResponse)
async def stop_monitoring(
    request: MonitoringStartRequest,
    orchestrator=Depends(get_orchestrator),
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> MonitoringResponse:
    """Stop monitoring for specified websites or all websites."""

    logger.info(
        "Stopping monitoring",
        user_id=current_user["id"],
        website_ids=request.website_ids,
    )

    try:
        website_ids = []

        if request.website_ids:
            # Stop monitoring for specific websites
            for website_id in request.website_ids:
                success = await orchestrator.unschedule_website_monitoring(website_id)
                if success:
                    website_ids.append(website_id)
        else:
            # Stop monitoring for all websites
            websites = await storage.list_websites()

            for website in websites:
                success = await orchestrator.unschedule_website_monitoring(website.id)
                if success:
                    website_ids.append(website.id)

        message = f"Monitoring stopped for {len(website_ids)} websites"
        logger.info("Monitoring stopped", website_count=len(website_ids))

        return MonitoringResponse(
            success=True,
            message=message,
            website_ids=website_ids,
            execution_ids=[],  # No execution IDs for stop operations
        )

    except Exception as e:
        logger.error("Failed to stop monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}",
        )


@router.post("/pause", response_model=dict[str, Any])
async def pause_monitoring(
    orchestrator=Depends(get_orchestrator),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> dict[str, Any]:
    """Pause all monitoring operations."""

    logger.info("Pausing monitoring", user_id=current_user["id"])

    try:
        result = await orchestrator.pause_all_jobs()

        logger.info("Monitoring paused", result=result)

        return {"success": True, "message": "All monitoring jobs paused", **result}

    except Exception as e:
        logger.error("Failed to pause monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause monitoring: {str(e)}",
        )


@router.post("/resume", response_model=dict[str, Any])
async def resume_monitoring(
    orchestrator=Depends(get_orchestrator),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> dict[str, Any]:
    """Resume all monitoring operations."""

    logger.info("Resuming monitoring", user_id=current_user["id"])

    try:
        result = await orchestrator.resume_all_jobs()

        logger.info("Monitoring resumed", result=result)

        return {"success": True, "message": "All monitoring jobs resumed", **result}

    except Exception as e:
        logger.error("Failed to resume monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume monitoring: {str(e)}",
        )


@router.get("/status", response_model=MonitoringStatusResponse)
async def get_monitoring_status(
    orchestrator=Depends(get_orchestrator),
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> MonitoringStatusResponse:
    """Get current monitoring system status."""

    try:
        # Get orchestrator status
        status_data = await orchestrator.get_orchestrator_status()

        # Get active websites count
        websites = await storage.list_websites()
        active_websites = len([w for w in websites if w.is_active])

        return MonitoringStatusResponse(
            overall_status=status_data.get("status", "unknown"),
            active_websites=active_websites,
            total_jobs_scheduled=status_data.get("total_jobs_scheduled", 0),
            total_workflows_executed=status_data.get("total_workflows_executed", 0),
            uptime_seconds=status_data.get("uptime_seconds", 0),
            components=status_data.get("components", {}),
        )

    except Exception as e:
        logger.error("Failed to get monitoring status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}",
        )


@router.post(
    "/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse
)
async def execute_workflow(
    workflow_id: str,
    website_id: str,
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
    priority: str = "normal",
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> WorkflowExecutionResponse:
    """Execute a workflow immediately."""

    logger.info(
        "Executing workflow",
        workflow_id=workflow_id,
        website_id=website_id,
        user_id=current_user["id"],
    )

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website not found: {website_id}",
            )

        execution_id = await orchestrator.execute_immediate_workflow(
            workflow_id=workflow_id,
            website_id=website_id,
            parameters={"priority": priority, "immediate": True},
        )

        logger.info(
            "Workflow executed", execution_id=execution_id, workflow_id=workflow_id
        )

        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            website_id=website_id,
            status="initiated",
            started_at=None,  # Would be populated from actual execution data
            completed_at=None,
            duration_seconds=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to execute workflow", error=str(e), workflow_id=workflow_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}",
        )


@router.get("/workflows/active", response_model=list[WorkflowExecutionResponse])
async def list_active_workflows(
    orchestrator=Depends(get_orchestrator),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> list[WorkflowExecutionResponse]:
    """List currently active workflow executions."""

    try:
        # This would get active workflows from the workflow engine
        # For now, return empty list as placeholder
        active_workflows = []

        return active_workflows

    except Exception as e:
        logger.error("Failed to list active workflows", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active workflows: {str(e)}",
        )
