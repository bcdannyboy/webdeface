"""Website management API endpoints."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, HttpUrl

from ...utils.logging import get_structured_logger
from ..auth import require_permission
from ..dependencies import get_orchestrator, get_storage_manager

logger = get_structured_logger(__name__)

router = APIRouter()


class WebsiteCreateRequest(BaseModel):
    """Request model for creating a website."""

    url: HttpUrl
    name: Optional[str] = None
    description: Optional[str] = None
    check_interval_seconds: int = 900  # 15 minutes default
    is_active: bool = True


class WebsiteUpdateRequest(BaseModel):
    """Request model for updating a website."""

    name: Optional[str] = None
    description: Optional[str] = None
    check_interval_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class WebsiteResponse(BaseModel):
    """Response model for website information."""

    id: str
    url: str
    name: str
    description: Optional[str]
    check_interval_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_checked_at: Optional[datetime]


class WebsiteListResponse(BaseModel):
    """Response model for website list."""

    websites: list[WebsiteResponse]
    total: int
    page: int
    page_size: int


class WebsiteStatusResponse(BaseModel):
    """Response model for website status."""

    id: str
    name: str
    url: str
    is_active: bool
    last_checked_at: Optional[datetime]
    monitoring_status: str
    recent_snapshots_count: int
    active_alerts_count: int
    health_score: Optional[float]


@router.post("/", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def create_website(
    website_data: WebsiteCreateRequest,
    current_user: dict[str, Any] = Depends(require_permission("write")),
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
) -> WebsiteResponse:
    """Create a new website for monitoring."""

    logger.info(
        "Creating new website", url=str(website_data.url), user_id=current_user["id"]
    )

    try:
        # Check if website already exists
        existing = await storage.get_website_by_url(str(website_data.url))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": f"Website already exists: {website_data.url}"},
            )

        # Set default name if not provided
        if not website_data.name:
            from urllib.parse import urlparse

            parsed = urlparse(str(website_data.url))
            website_data.name = parsed.netloc or str(website_data.url)

        # Create website
        website_dict = website_data.dict()
        website_dict["url"] = str(website_data.url)  # Convert HttpUrl to string

        website = await storage.create_website(website_dict)

        # Schedule monitoring if active
        if website.is_active:
            await orchestrator.schedule_website_monitoring(website.id)

        logger.info(
            "Website created successfully", website_id=website.id, url=website.url
        )

        return WebsiteResponse(
            id=website.id,
            url=website.url,
            name=website.name,
            description=website.description,
            check_interval_seconds=website.check_interval_seconds,
            is_active=website.is_active,
            created_at=website.created_at,
            updated_at=website.updated_at,
            last_checked_at=website.last_checked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create website", error=str(e), url=str(website_data.url)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create website: {str(e)}",
        )


@router.get("/", response_model=WebsiteListResponse)
async def list_websites(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict[str, Any] = Depends(require_permission("read")),
    storage=Depends(get_storage_manager),
) -> WebsiteListResponse:
    """List all websites with pagination and filtering."""

    try:
        # Get websites with filters
        websites = await storage.list_websites()

        # Apply filters
        if is_active is not None:
            websites = [w for w in websites if w.is_active == is_active]

        # Apply pagination
        total = len(websites)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_websites = websites[start_idx:end_idx]

        # Convert to response models
        website_responses = [
            WebsiteResponse(
                id=w.id,
                url=w.url,
                name=w.name,
                description=w.description,
                check_interval_seconds=w.check_interval_seconds,
                is_active=w.is_active,
                created_at=w.created_at,
                updated_at=w.updated_at,
                last_checked_at=w.last_checked_at,
            )
            for w in paginated_websites
        ]

        return WebsiteListResponse(
            websites=website_responses, total=total, page=page, page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list websites", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list websites: {str(e)}",
        )


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: str,
    current_user: dict[str, Any] = Depends(require_permission("read")),
    storage=Depends(get_storage_manager),
) -> WebsiteResponse:
    """Get a specific website by ID."""

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Website not found: {website_id}"},
            )

        return WebsiteResponse(
            id=website.id,
            url=website.url,
            name=website.name,
            description=website.description,
            check_interval_seconds=website.check_interval_seconds,
            is_active=website.is_active,
            created_at=website.created_at,
            updated_at=website.updated_at,
            last_checked_at=website.last_checked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get website", error=str(e), website_id=website_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to get website: {str(e)}"},
        )


@router.put("/{website_id}", response_model=WebsiteResponse)
async def update_website(
    website_id: str,
    update_data: WebsiteUpdateRequest,
    current_user: dict[str, Any] = Depends(require_permission("write")),
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
) -> WebsiteResponse:
    """Update a website."""

    logger.info("Updating website", website_id=website_id, user_id=current_user["id"])

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Website not found: {website_id}"},
            )

        # Update website
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        updated_website = await storage.update_website(website_id, update_dict)

        # Handle monitoring schedule changes
        if "is_active" in update_dict:
            if update_dict["is_active"]:
                await orchestrator.schedule_website_monitoring(website_id)
            else:
                await orchestrator.unschedule_website_monitoring(website_id)

        logger.info("Website updated successfully", website_id=website_id)

        return WebsiteResponse(
            id=updated_website.id,
            url=updated_website.url,
            name=updated_website.name,
            description=updated_website.description,
            check_interval_seconds=updated_website.check_interval_seconds,
            is_active=updated_website.is_active,
            created_at=updated_website.created_at,
            updated_at=updated_website.updated_at,
            last_checked_at=updated_website.last_checked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update website", error=str(e), website_id=website_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to update website: {str(e)}"},
        )


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    website_id: str,
    current_user: dict[str, Any] = Depends(require_permission("write")),
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
) -> None:
    """Delete a website."""

    logger.info("Deleting website", website_id=website_id, user_id=current_user["id"])

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Website not found: {website_id}"},
            )

        # Unschedule monitoring
        await orchestrator.unschedule_website_monitoring(website_id)

        # Delete website
        await storage.delete_website(website_id)

        logger.info("Website deleted successfully", website_id=website_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete website", error=str(e), website_id=website_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to delete website: {str(e)}"},
        )


@router.get("/{website_id}/status", response_model=WebsiteStatusResponse)
async def get_website_status(
    website_id: str,
    current_user: dict[str, Any] = Depends(require_permission("read")),
    storage=Depends(get_storage_manager),
) -> WebsiteStatusResponse:
    """Get detailed status for a website."""

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Website not found: {website_id}"},
            )

        # Get additional status information
        snapshots = await storage.get_website_snapshots(website_id, limit=10)
        alerts = await storage.get_website_alerts(website_id, limit=10)

        # Calculate health score (simple implementation)
        health_score = None
        if snapshots:
            recent_successes = len([s for s in snapshots if s.status_code == 200])
            health_score = (recent_successes / len(snapshots)) * 10

        # Determine monitoring status
        monitoring_status = "active" if website.is_active else "inactive"

        return WebsiteStatusResponse(
            id=website.id,
            name=website.name,
            url=website.url,
            is_active=website.is_active,
            last_checked_at=website.last_checked_at,
            monitoring_status=monitoring_status,
            recent_snapshots_count=len(snapshots),
            active_alerts_count=len([a for a in alerts if a.status == "open"]),
            health_score=health_score,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get website status", error=str(e), website_id=website_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to get website status: {str(e)}"},
        )


@router.post("/{website_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def trigger_immediate_check(
    website_id: str,
    current_user: dict[str, Any] = Depends(require_permission("write")),
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
) -> dict[str, Any]:
    """Trigger immediate check for a website."""

    logger.info(
        "Triggering immediate check", website_id=website_id, user_id=current_user["id"]
    )

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Website not found: {website_id}"},
            )

        # Trigger immediate workflow execution
        execution_id = await orchestrator.execute_immediate_workflow(
            workflow_id="website_monitoring",
            website_id=website_id,
            parameters={"priority": "high", "immediate": True},
        )

        logger.info(
            "Immediate check triggered",
            website_id=website_id,
            execution_id=execution_id,
        )

        return {
            "message": "Immediate check triggered",
            "website_id": website_id,
            "execution_id": execution_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to trigger immediate check", error=str(e), website_id=website_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to trigger check: {str(e)}"},
        )
