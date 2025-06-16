"""Metrics and analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...utils.logging import get_structured_logger
from ..auth import require_permission
from ..dependencies import get_orchestrator, get_storage_manager

logger = get_structured_logger(__name__)

router = APIRouter()


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary."""

    total_websites: int
    active_websites: int
    inactive_websites: int
    total_scans_today: int
    total_scans_this_week: int
    defacements_detected_today: int
    defacements_detected_this_week: int
    average_scan_duration_seconds: float
    last_scan_time: Optional[datetime]
    system_uptime_seconds: float
    health_score: Optional[float]


class WebsiteMetricsResponse(BaseModel):
    """Response model for website-specific metrics."""

    website_id: str
    website_name: str
    website_url: str
    total_scans: int
    successful_scans: int
    failed_scans: int
    defacements_detected: int
    last_scan_time: Optional[datetime]
    average_response_time_ms: float
    uptime_percentage: float
    health_score: Optional[float]


class PerformanceMetricsResponse(BaseModel):
    """Response model for system performance metrics."""

    timestamp: datetime
    active_jobs: int
    completed_jobs_last_hour: int
    failed_jobs_last_hour: int
    average_job_duration_seconds: float
    queue_size: int
    memory_usage_mb: Optional[float]
    cpu_usage_percentage: Optional[float]


class TimeSeriesPoint(BaseModel):
    """Response model for time series data point."""

    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesResponse(BaseModel):
    """Response model for time series data."""

    metric_name: str
    time_range: str
    data_points: list[TimeSeriesPoint]
    total_points: int


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    storage=Depends(get_storage_manager),
    orchestrator=Depends(get_orchestrator),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> MetricsSummaryResponse:
    """Get overall system metrics summary."""

    try:
        # Get website statistics
        websites = await storage.list_websites()
        total_websites = len(websites)
        active_websites = len([w for w in websites if w.is_active])
        inactive_websites = total_websites - active_websites

        # Get time-based metrics
        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)

        # Get scan statistics
        total_scans_today = 0
        total_scans_this_week = 0
        defacements_detected_today = 0
        defacements_detected_this_week = 0
        last_scan_time = None
        total_response_time = 0
        scan_count = 0

        for website in websites:
            snapshots = await storage.get_website_snapshots(website.id, limit=100)

            # Count scans
            scans_today = len([s for s in snapshots if s.captured_at.date() == today])
            scans_this_week = len([s for s in snapshots if s.captured_at >= week_ago])
            total_scans_today += scans_today
            total_scans_this_week += scans_this_week

            # Get alerts for defacement detection
            alerts = await storage.get_website_alerts(website.id)
            defacement_alerts_today = len(
                [
                    a
                    for a in alerts
                    if a.alert_type == "defacement" and a.created_at.date() == today
                ]
            )
            defacement_alerts_week = len(
                [
                    a
                    for a in alerts
                    if a.alert_type == "defacement" and a.created_at >= week_ago
                ]
            )
            defacements_detected_today += defacement_alerts_today
            defacements_detected_this_week += defacement_alerts_week

            # Track response times and last scan
            for snapshot in snapshots:
                if snapshot.response_time_ms:
                    total_response_time += snapshot.response_time_ms
                    scan_count += 1

                if not last_scan_time or snapshot.captured_at > last_scan_time:
                    last_scan_time = snapshot.captured_at

        # Calculate average response time
        average_scan_duration = (
            (total_response_time / scan_count / 1000) if scan_count > 0 else 0
        )

        # Get system metrics
        status_data = await orchestrator.get_orchestrator_status()
        system_uptime = status_data.get("uptime_seconds", 0)

        # Get health score
        report = await orchestrator.get_monitoring_report()
        health_score = report.overall_health_score if report else None

        return MetricsSummaryResponse(
            total_websites=total_websites,
            active_websites=active_websites,
            inactive_websites=inactive_websites,
            total_scans_today=total_scans_today,
            total_scans_this_week=total_scans_this_week,
            defacements_detected_today=defacements_detected_today,
            defacements_detected_this_week=defacements_detected_this_week,
            average_scan_duration_seconds=average_scan_duration,
            last_scan_time=last_scan_time,
            system_uptime_seconds=system_uptime,
            health_score=health_score,
        )

    except Exception as e:
        logger.error("Failed to get metrics summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics summary: {str(e)}",
        )


@router.get("/websites", response_model=list[WebsiteMetricsResponse])
async def get_website_metrics(
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> list[WebsiteMetricsResponse]:
    """Get metrics for all websites."""

    try:
        websites = await storage.list_websites()

        website_metrics = []

        for website in websites:
            # Get snapshots and alerts
            snapshots = await storage.get_website_snapshots(website.id, limit=100)
            alerts = await storage.get_website_alerts(website.id)

            # Calculate metrics
            total_scans = len(snapshots)
            successful_scans = len([s for s in snapshots if s.status_code == 200])
            failed_scans = total_scans - successful_scans

            defacements_detected = len(
                [a for a in alerts if a.alert_type == "defacement"]
            )

            last_scan_time = (
                max([s.captured_at for s in snapshots]) if snapshots else None
            )

            # Calculate average response time
            response_times = [
                s.response_time_ms for s in snapshots if s.response_time_ms
            ]
            average_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            # Calculate uptime percentage
            uptime_percentage = (
                (successful_scans / total_scans * 100) if total_scans > 0 else 100
            )

            # Simple health score calculation
            health_score = None
            if total_scans > 0:
                health_score = (successful_scans / total_scans) * 10
                # Reduce score if defacements detected
                if defacements_detected > 0:
                    health_score = max(0, health_score - (defacements_detected * 2))

            website_metrics.append(
                WebsiteMetricsResponse(
                    website_id=website.id,
                    website_name=website.name,
                    website_url=website.url,
                    total_scans=total_scans,
                    successful_scans=successful_scans,
                    failed_scans=failed_scans,
                    defacements_detected=defacements_detected,
                    last_scan_time=last_scan_time,
                    average_response_time_ms=average_response_time,
                    uptime_percentage=uptime_percentage,
                    health_score=health_score,
                )
            )

        return website_metrics

    except Exception as e:
        logger.error("Failed to get website metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get website metrics: {str(e)}",
        )


@router.get("/websites/{website_id}", response_model=WebsiteMetricsResponse)
async def get_website_metrics_detail(
    website_id: str,
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> WebsiteMetricsResponse:
    """Get detailed metrics for a specific website."""

    try:
        website = await storage.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website not found: {website_id}",
            )

        # Get all snapshots and alerts for detailed analysis
        snapshots = await storage.get_website_snapshots(website_id)
        alerts = await storage.get_website_alerts(website_id)

        # Calculate detailed metrics
        total_scans = len(snapshots)
        successful_scans = len([s for s in snapshots if s.status_code == 200])
        failed_scans = total_scans - successful_scans

        defacements_detected = len([a for a in alerts if a.alert_type == "defacement"])

        last_scan_time = max([s.captured_at for s in snapshots]) if snapshots else None

        # Calculate average response time
        response_times = [s.response_time_ms for s in snapshots if s.response_time_ms]
        average_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Calculate uptime percentage
        uptime_percentage = (
            (successful_scans / total_scans * 100) if total_scans > 0 else 100
        )

        # Enhanced health score calculation
        health_score = None
        if total_scans > 0:
            base_score = (successful_scans / total_scans) * 10

            # Factor in response time (penalize slow responses)
            if average_response_time > 5000:  # 5 seconds
                base_score -= 2
            elif average_response_time > 3000:  # 3 seconds
                base_score -= 1

            # Factor in recent failures
            recent_snapshots = snapshots[-10:] if len(snapshots) > 10 else snapshots
            recent_failures = len([s for s in recent_snapshots if s.status_code != 200])
            if recent_failures > 0:
                base_score -= recent_failures * 0.5

            # Factor in defacements
            if defacements_detected > 0:
                base_score -= defacements_detected * 3

            health_score = max(0, min(10, base_score))

        return WebsiteMetricsResponse(
            website_id=website.id,
            website_name=website.name,
            website_url=website.url,
            total_scans=total_scans,
            successful_scans=successful_scans,
            failed_scans=failed_scans,
            defacements_detected=defacements_detected,
            last_scan_time=last_scan_time,
            average_response_time_ms=average_response_time,
            uptime_percentage=uptime_percentage,
            health_score=health_score,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get website metrics detail", error=str(e), website_id=website_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get website metrics: {str(e)}",
        )


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    orchestrator=Depends(get_orchestrator),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> PerformanceMetricsResponse:
    """Get system performance metrics."""

    try:
        # Get orchestrator status
        status_data = await orchestrator.get_orchestrator_status()

        # Get scheduler stats
        scheduler_stats = status_data.get("scheduler_stats", {})

        # Calculate job metrics for last hour
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Mock performance data (in production, this would come from actual monitoring)
        return PerformanceMetricsResponse(
            timestamp=now,
            active_jobs=scheduler_stats.get("active_jobs", 0),
            completed_jobs_last_hour=scheduler_stats.get("completed_jobs", 0),
            failed_jobs_last_hour=scheduler_stats.get("failed_jobs", 0),
            average_job_duration_seconds=scheduler_stats.get("average_job_duration", 0),
            queue_size=scheduler_stats.get("pending_jobs", 0),
            memory_usage_mb=None,  # Would integrate with system monitoring
            cpu_usage_percentage=None,  # Would integrate with system monitoring
        )

    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}",
        )


@router.get("/timeseries/{metric_name}", response_model=TimeSeriesResponse)
async def get_timeseries_data(
    metric_name: str,
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    website_id: Optional[str] = Query(None, description="Filter by website"),
    storage=Depends(get_storage_manager),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> TimeSeriesResponse:
    """Get time series data for a specific metric."""

    try:
        # Parse time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
            interval_minutes = 5
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
            interval_minutes = 60
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
            interval_minutes = 360  # 6 hours
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
            interval_minutes = 1440  # 24 hours
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time range. Use: 1h, 24h, 7d, or 30d",
            )

        data_points = []

        if metric_name == "response_time":
            # Get response time data
            websites = (
                [await storage.get_website(website_id)]
                if website_id
                else await storage.list_websites()
            )

            for website in websites:
                if not website:
                    continue

                snapshots = await storage.get_website_snapshots(website.id)
                recent_snapshots = [s for s in snapshots if s.captured_at >= start_time]

                # Group by time intervals
                for snapshot in recent_snapshots:
                    if snapshot.response_time_ms:
                        data_points.append(
                            TimeSeriesPoint(
                                timestamp=snapshot.captured_at,
                                value=snapshot.response_time_ms,
                                label=website.name,
                            )
                        )

        elif metric_name == "scan_count":
            # Get scan count data
            websites = (
                [await storage.get_website(website_id)]
                if website_id
                else await storage.list_websites()
            )

            # Generate time buckets
            current_time = start_time
            while current_time <= now:
                bucket_end = current_time + timedelta(minutes=interval_minutes)
                scan_count = 0

                for website in websites:
                    if not website:
                        continue
                    snapshots = await storage.get_website_snapshots(website.id)
                    bucket_scans = len(
                        [
                            s
                            for s in snapshots
                            if current_time <= s.captured_at < bucket_end
                        ]
                    )
                    scan_count += bucket_scans

                data_points.append(
                    TimeSeriesPoint(timestamp=current_time, value=float(scan_count))
                )

                current_time = bucket_end

        elif metric_name == "defacement_count":
            # Get defacement detection data
            websites = (
                [await storage.get_website(website_id)]
                if website_id
                else await storage.list_websites()
            )

            # Generate time buckets
            current_time = start_time
            while current_time <= now:
                bucket_end = current_time + timedelta(minutes=interval_minutes)
                defacement_count = 0

                for website in websites:
                    if not website:
                        continue
                    alerts = await storage.get_website_alerts(website.id)
                    bucket_defacements = len(
                        [
                            a
                            for a in alerts
                            if (
                                a.alert_type == "defacement"
                                and current_time <= a.created_at < bucket_end
                            )
                        ]
                    )
                    defacement_count += bucket_defacements

                data_points.append(
                    TimeSeriesPoint(
                        timestamp=current_time, value=float(defacement_count)
                    )
                )

                current_time = bucket_end

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown metric: {metric_name}. Available: response_time, scan_count, defacement_count",
            )

        # Sort by timestamp
        data_points.sort(key=lambda x: x.timestamp)

        return TimeSeriesResponse(
            metric_name=metric_name,
            time_range=time_range,
            data_points=data_points,
            total_points=len(data_points),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get timeseries data", error=str(e), metric_name=metric_name
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeseries data: {str(e)}",
        )


@router.get("/export/csv", response_model=dict[str, str])
async def export_metrics_csv(
    metric_type: str = Query("summary", description="Type of metrics to export"),
    time_range: str = Query("7d", description="Time range for export"),
    website_id: Optional[str] = Query(None, description="Filter by website"),
    current_user: dict[str, Any] = Depends(require_permission("read")),
) -> dict[str, str]:
    """Export metrics data as CSV."""

    logger.info(
        "Metrics export requested",
        metric_type=metric_type,
        time_range=time_range,
        user_id=current_user["id"],
    )

    try:
        # In production, this would generate actual CSV data and return a download URL
        # For now, return a placeholder

        export_id = f"export_{metric_type}_{time_range}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "message": "Export request processed",
            "export_id": export_id,
            "download_url": f"/api/v1/metrics/download/{export_id}",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    except Exception as e:
        logger.error("Failed to export metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export metrics: {str(e)}",
        )
