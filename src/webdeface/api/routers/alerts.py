"""Alert management API endpoints."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...utils.logging import get_structured_logger
from ..auth import require_permission
from ..dependencies import get_storage_manager

logger = get_structured_logger(__name__)

router = APIRouter()


class AlertResponse(BaseModel):
    """Response model for alert information."""

    id: str
    website_id: str
    website_name: str
    website_url: str
    alert_type: str
    severity: str
    title: str
    description: str
    classification_label: Optional[str]
    confidence_score: Optional[float]
    similarity_score: Optional[float]
    status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    notifications_sent: int
    last_notification_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    """Response model for alert list."""

    alerts: list[AlertResponse]
    total: int
    page: int
    page_size: int


class AlertUpdateRequest(BaseModel):
    """Request model for updating alert."""

    status: Optional[str] = None
    acknowledged_by: Optional[str] = None


class AlertStatsResponse(BaseModel):
    """Response model for alert statistics."""

    total_alerts: int
    open_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    alerts_today: int
    alerts_this_week: int
    avg_resolution_time_hours: Optional[float]


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    website_id: Optional[str] = Query(None, description="Filter by website"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> AlertListResponse:
    """List alerts with filtering and pagination."""

    try:
        # Get all alerts (in production, this would support database-level filtering)
        all_alerts = []

        if website_id:
            # Get alerts for specific website
            alerts = await storage.get_website_alerts(website_id)
            all_alerts.extend(alerts)
        else:
            # Get alerts for all websites
            websites = await storage.list_websites()
            for website in websites:
                website_alerts = await storage.get_website_alerts(website.id)
                all_alerts.extend(website_alerts)

        # Apply filters
        filtered_alerts = all_alerts
        if status:
            filtered_alerts = [a for a in filtered_alerts if a.status == status]
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]

        # Sort by created_at descending
        filtered_alerts.sort(key=lambda x: x.created_at, reverse=True)

        # Apply pagination
        total = len(filtered_alerts)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_alerts = filtered_alerts[start_idx:end_idx]

        # Convert to response models
        alert_responses = []
        for alert in paginated_alerts:
            # Get website info
            website = await storage.get_website(alert.website_id)
            website_name = website.name if website else "Unknown"
            website_url = website.url if website else ""

            alert_responses.append(
                AlertResponse(
                    id=alert.id,
                    website_id=alert.website_id,
                    website_name=website_name,
                    website_url=website_url,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    title=alert.title,
                    description=alert.description,
                    classification_label=alert.classification_label,
                    confidence_score=alert.confidence_score,
                    similarity_score=alert.similarity_score,
                    status=alert.status,
                    acknowledged_by=alert.acknowledged_by,
                    acknowledged_at=alert.acknowledged_at,
                    resolved_at=alert.resolved_at,
                    notifications_sent=alert.notifications_sent,
                    last_notification_at=alert.last_notification_at,
                    created_at=alert.created_at,
                    updated_at=alert.updated_at,
                )
            )

        return AlertListResponse(
            alerts=alert_responses, total=total, page=page, page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list alerts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list alerts: {str(e)}",
        )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> AlertResponse:
    """Get a specific alert by ID."""

    try:
        alert = await storage.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}",
            )

        # Get website info
        website = await storage.get_website(alert.website_id)
        website_name = website.name if website else "Unknown"
        website_url = website.url if website else ""

        return AlertResponse(
            id=alert.id,
            website_id=alert.website_id,
            website_name=website_name,
            website_url=website_url,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            classification_label=alert.classification_label,
            confidence_score=alert.confidence_score,
            similarity_score=alert.similarity_score,
            status=alert.status,
            acknowledged_by=alert.acknowledged_by,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            notifications_sent=alert.notifications_sent,
            last_notification_at=alert.last_notification_at,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get alert", error=str(e), alert_id=alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}",
        )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    update_data: AlertUpdateRequest,
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> AlertResponse:
    """Update an alert (acknowledge, resolve, etc.)."""

    logger.info("Updating alert", alert_id=alert_id, user_id=current_user["id"])

    try:
        alert = await storage.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}",
            )

        # Prepare update data
        update_dict = {}

        if update_data.status is not None:
            update_dict["status"] = update_data.status

            # Set timestamps based on status
            if update_data.status == "acknowledged":
                update_dict["acknowledged_by"] = (
                    update_data.acknowledged_by or current_user["username"]
                )
                update_dict["acknowledged_at"] = datetime.utcnow()
            elif update_data.status == "resolved":
                update_dict["resolved_at"] = datetime.utcnow()

        if update_data.acknowledged_by is not None:
            update_dict["acknowledged_by"] = update_data.acknowledged_by
            if "acknowledged_at" not in update_dict:
                update_dict["acknowledged_at"] = datetime.utcnow()

        # Update alert
        updated_alert = await storage.update_alert(alert_id, update_dict)

        # Get website info
        website = await storage.get_website(updated_alert.website_id)
        website_name = website.name if website else "Unknown"
        website_url = website.url if website else ""

        logger.info("Alert updated successfully", alert_id=alert_id)

        return AlertResponse(
            id=updated_alert.id,
            website_id=updated_alert.website_id,
            website_name=website_name,
            website_url=website_url,
            alert_type=updated_alert.alert_type,
            severity=updated_alert.severity,
            title=updated_alert.title,
            description=updated_alert.description,
            classification_label=updated_alert.classification_label,
            confidence_score=updated_alert.confidence_score,
            similarity_score=updated_alert.similarity_score,
            status=updated_alert.status,
            acknowledged_by=updated_alert.acknowledged_by,
            acknowledged_at=updated_alert.acknowledged_at,
            resolved_at=updated_alert.resolved_at,
            notifications_sent=updated_alert.notifications_sent,
            last_notification_at=updated_alert.last_notification_at,
            created_at=updated_alert.created_at,
            updated_at=updated_alert.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update alert", error=str(e), alert_id=alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}",
        )


@router.post("/bulk/acknowledge", response_model=dict[str, Any])
async def bulk_acknowledge_alerts(
    alert_ids: list[str],
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> dict[str, Any]:
    """Acknowledge multiple alerts at once."""

    logger.info(
        "Bulk acknowledging alerts",
        alert_count=len(alert_ids),
        user_id=current_user["id"],
    )

    try:
        successful_updates = []
        failed_updates = []

        for alert_id in alert_ids:
            try:
                update_dict = {
                    "status": "acknowledged",
                    "acknowledged_by": current_user.get("username", "api-user"),
                    "acknowledged_at": datetime.utcnow(),
                }

                await storage.update_alert(alert_id, update_dict)
                successful_updates.append(alert_id)

            except Exception as e:
                failed_updates.append({"alert_id": alert_id, "error": str(e)})

        logger.info(
            "Bulk acknowledge completed",
            successful=len(successful_updates),
            failed=len(failed_updates),
        )

        return {
            "message": f"Acknowledged {len(successful_updates)} alerts",
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "total_requested": len(alert_ids),
        }

    except Exception as e:
        logger.error("Failed to bulk acknowledge alerts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk acknowledge alerts: {str(e)}",
        )


@router.get("/stats/summary", response_model=AlertStatsResponse)
async def get_alert_stats(
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> AlertStatsResponse:
    """Get alert statistics and summary."""

    try:
        # Get all alerts
        all_alerts = []
        websites = await storage.list_websites()
        for website in websites:
            website_alerts = await storage.get_website_alerts(website.id)
            all_alerts.extend(website_alerts)

        # Calculate statistics
        total_alerts = len(all_alerts)
        open_alerts = len([a for a in all_alerts if a.status == "open"])
        acknowledged_alerts = len([a for a in all_alerts if a.status == "acknowledged"])
        resolved_alerts = len([a for a in all_alerts if a.status == "resolved"])

        # Count by severity
        critical_alerts = len([a for a in all_alerts if a.severity == "critical"])
        high_alerts = len([a for a in all_alerts if a.severity == "high"])
        medium_alerts = len([a for a in all_alerts if a.severity == "medium"])
        low_alerts = len([a for a in all_alerts if a.severity == "low"])

        # Time-based counts
        from datetime import timedelta

        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)

        alerts_today = len([a for a in all_alerts if a.created_at.date() == today])
        alerts_this_week = len([a for a in all_alerts if a.created_at >= week_ago])

        # Calculate average resolution time
        resolved_with_times = [
            a
            for a in all_alerts
            if a.status == "resolved" and a.resolved_at and a.created_at
        ]

        avg_resolution_time_hours = None
        if resolved_with_times:
            resolution_times = [
                (a.resolved_at - a.created_at).total_seconds() / 3600
                for a in resolved_with_times
            ]
            avg_resolution_time_hours = sum(resolution_times) / len(resolution_times)

        return AlertStatsResponse(
            total_alerts=total_alerts,
            open_alerts=open_alerts,
            acknowledged_alerts=acknowledged_alerts,
            resolved_alerts=resolved_alerts,
            critical_alerts=critical_alerts,
            high_alerts=high_alerts,
            medium_alerts=medium_alerts,
            low_alerts=low_alerts,
            alerts_today=alerts_today,
            alerts_this_week=alerts_this_week,
            avg_resolution_time_hours=avg_resolution_time_hours,
        )

    except Exception as e:
        logger.error("Failed to get alert stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert stats: {str(e)}",
        )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> AlertResponse:
    """Acknowledge an alert."""

    logger.info("Acknowledging alert", alert_id=alert_id, user_id=current_user["id"])

    update_data = AlertUpdateRequest(
        status="acknowledged", acknowledged_by=current_user.get("username", "api-user")
    )

    return await update_alert(alert_id, update_data, storage, current_user)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("write")),
) -> AlertResponse:
    """Resolve an alert."""

    logger.info("Resolving alert", alert_id=alert_id, user_id=current_user["id"])

    update_data = AlertUpdateRequest(status="resolved")

    return await update_alert(alert_id, update_data, storage, current_user)
