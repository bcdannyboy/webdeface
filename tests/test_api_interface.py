"""Tests for FastAPI interface components."""

from contextlib import ExitStack
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.webdeface.api.app import create_app
from src.webdeface.api.auth import verify_api_token


@pytest.fixture
def test_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.development = True
    settings.logging.level = "INFO"
    settings.api_tokens = ["test-token-123"]
    return settings


@pytest.fixture
def mock_storage():
    """Mock storage manager."""
    storage = AsyncMock()

    # Mock website data
    mock_website = MagicMock()
    mock_website.id = "test-website-123"
    mock_website.name = "Test Website"
    mock_website.url = "https://example.com"
    mock_website.is_active = True
    mock_website.created_at = datetime.utcnow()
    mock_website.updated_at = datetime.utcnow()
    mock_website.last_checked_at = None
    mock_website.check_interval_seconds = 900
    mock_website.description = "Test description"

    # Mock alert data
    mock_alert = MagicMock()
    mock_alert.id = "test-alert-123"
    mock_alert.website_id = "test-website-123"
    mock_alert.alert_type = "defacement"
    mock_alert.severity = "high"
    mock_alert.title = "Test Alert"
    mock_alert.description = "Test alert description"
    mock_alert.status = "open"
    mock_alert.created_at = datetime.utcnow()
    mock_alert.updated_at = datetime.utcnow()
    mock_alert.acknowledged_by = None
    mock_alert.acknowledged_at = None
    mock_alert.resolved_at = None
    mock_alert.notifications_sent = 0
    mock_alert.last_notification_at = None
    mock_alert.classification_label = "suspicious"
    mock_alert.confidence_score = 0.85
    mock_alert.similarity_score = 0.75

    storage.create_website.return_value = mock_website
    storage.get_website.return_value = mock_website
    storage.get_website_by_url.return_value = None
    storage.list_websites.return_value = [mock_website]
    storage.update_website.return_value = mock_website
    storage.delete_website.return_value = True
    storage.get_website_snapshots.return_value = []
    storage.get_website_alerts.return_value = [mock_alert]
    storage.get_alert.return_value = mock_alert
    storage.update_alert.return_value = mock_alert

    return storage


@pytest.fixture
def mock_orchestrator():
    """Mock scheduling orchestrator."""
    orchestrator = AsyncMock()
    orchestrator.is_running = True
    orchestrator.schedule_website_monitoring.return_value = "execution-123"
    orchestrator.unschedule_website_monitoring.return_value = True
    orchestrator.execute_immediate_workflow.return_value = "workflow-123"
    orchestrator.get_orchestrator_status.return_value = {
        "status": "running",
        "uptime_seconds": 3600,
        "start_time": datetime.utcnow().isoformat(),
        "total_jobs_scheduled": 5,
        "total_workflows_executed": 10,
        "components": {
            "scheduler_manager": True,
            "workflow_engine": True,
            "health_monitor": True,
        },
        "scheduler_stats": {"active_jobs": 2, "completed_jobs": 8, "failed_jobs": 0},
    }
    orchestrator.get_monitoring_report.return_value = None
    orchestrator.pause_all_jobs.return_value = {"paused_jobs": 3}
    orchestrator.resume_all_jobs.return_value = {"resumed_jobs": 3}

    return orchestrator


@pytest.fixture
def test_client(test_settings, mock_storage, mock_orchestrator):
    """Create test client with mocked dependencies."""

    # Create async mock functions for the dependencies
    async def mock_get_storage_manager():
        return mock_storage

    async def mock_get_scheduling_orchestrator():
        return mock_orchestrator

    # Ensure test_settings has the correct test token
    test_settings.api_tokens = ["test-token-123"]

    # DIRECT MODULE ATTRIBUTE PATCHING STRATEGY:
    # Patch the imported get_settings reference directly in the auth module
    # This addresses the module-level import issue

    # Clear any cached settings before starting
    from src.webdeface.config.settings import get_settings

    get_settings.cache_clear()

    # Import auth module to access its get_settings reference
    from src.webdeface.api import auth

    # Store original reference for cleanup
    original_get_settings = auth.get_settings

    # Replace the auth module's get_settings reference directly
    auth.get_settings = lambda: test_settings

    try:
        patches = [
            # Core settings patching for other modules
            patch("src.webdeface.config.get_settings", return_value=test_settings),
            patch(
                "src.webdeface.config.settings.get_settings", return_value=test_settings
            ),
            patch("src.webdeface.api.app.get_settings", return_value=test_settings),
            # Storage and orchestrator mocks
            patch(
                "src.webdeface.api.app.get_storage_manager",
                side_effect=mock_get_storage_manager,
            ),
            patch(
                "src.webdeface.api.app.get_scheduling_orchestrator",
                side_effect=mock_get_scheduling_orchestrator,
            ),
            patch(
                "src.webdeface.api.app.cleanup_scheduling_orchestrator",
                return_value=AsyncMock(),
            ),
        ]

        # Apply all patches using ExitStack for clean management
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)

            app = create_app(test_settings)

            # Set up app state with test dependencies and settings
            app.state.storage = mock_storage
            app.state.orchestrator = mock_orchestrator
            app.state.settings = test_settings
            app.state.api_tokens = ["test-token-123"]

            yield TestClient(app)

    finally:
        # Restore original reference
        auth.get_settings = original_get_settings


class TestAuthenticationAPI:
    """Test API authentication endpoints."""

    def test_token_verification(self, test_settings):
        """Test API token verification."""
        with patch("src.webdeface.api.auth.get_settings", return_value=test_settings):
            assert verify_api_token("test-token-123") is True
            assert verify_api_token("invalid-token") is False

    def test_token_info_endpoint(self, test_client):
        """Test token info endpoint."""
        response = test_client.get("/api/v1/auth/token/info")
        assert response.status_code == 200
        data = response.json()
        assert "API uses Bearer token authentication" in data["message"]

    def test_token_verify_endpoint(self, test_client):
        """Test token verification endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}
        response = test_client.get("/api/v1/auth/token/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == "api-user"

    def test_unauthorized_request(self, test_client):
        """Test request without authentication."""
        response = test_client.get("/api/v1/websites/")
        assert response.status_code == 401

    def test_invalid_token(self, test_client):
        """Test request with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = test_client.get("/api/v1/websites/", headers=headers)
        assert response.status_code == 401


class TestWebsiteAPI:
    """Test website management API endpoints."""

    def test_create_website(self, test_client, mock_storage):
        """Test website creation."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {
            "url": "https://example.com",
            "name": "Test Website",
            "description": "Test description",
        }

        response = test_client.post("/api/v1/websites/", json=data, headers=headers)
        assert response.status_code == 201

        response_data = response.json()
        assert response_data["url"] == "https://example.com"
        assert response_data["name"] == "Test Website"
        mock_storage.create_website.assert_called_once()

    def test_list_websites(self, test_client, mock_storage):
        """Test website listing."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/websites/", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "websites" in data
        assert data["total"] == 1
        assert len(data["websites"]) == 1
        mock_storage.list_websites.assert_called_once()

    def test_get_website(self, test_client, mock_storage):
        """Test getting specific website."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/websites/test-website-123", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-website-123"
        assert data["name"] == "Test Website"
        mock_storage.get_website.assert_called_once_with("test-website-123")

    def test_update_website(self, test_client, mock_storage):
        """Test website update."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {"name": "Updated Website"}

        response = test_client.put(
            "/api/v1/websites/test-website-123", json=data, headers=headers
        )
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["id"] == "test-website-123"
        mock_storage.update_website.assert_called_once()

    def test_delete_website(self, test_client, mock_storage, mock_orchestrator):
        """Test website deletion."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.delete(
            "/api/v1/websites/test-website-123", headers=headers
        )
        assert response.status_code == 204

        mock_storage.delete_website.assert_called_once_with("test-website-123")
        mock_orchestrator.unschedule_website_monitoring.assert_called_once()

    def test_website_status(self, test_client, mock_storage):
        """Test website status endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get(
            "/api/v1/websites/test-website-123/status", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-website-123"
        assert "monitoring_status" in data
        assert "recent_snapshots_count" in data

    def test_trigger_immediate_check(
        self, test_client, mock_storage, mock_orchestrator
    ):
        """Test triggering immediate website check."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post(
            "/api/v1/websites/test-website-123/check", headers=headers
        )
        assert response.status_code == 202

        data = response.json()
        assert data["website_id"] == "test-website-123"
        assert "execution_id" in data
        mock_orchestrator.execute_immediate_workflow.assert_called_once()


class TestMonitoringAPI:
    """Test monitoring control API endpoints."""

    def test_start_monitoring(self, test_client, mock_orchestrator):
        """Test starting monitoring."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {"website_ids": ["test-website-123"]}

        response = test_client.post(
            "/api/v1/monitoring/start", json=data, headers=headers
        )
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["success"] is True
        assert "test-website-123" in response_data["website_ids"]
        mock_orchestrator.schedule_website_monitoring.assert_called()

    def test_stop_monitoring(self, test_client, mock_orchestrator):
        """Test stopping monitoring."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {"website_ids": ["test-website-123"]}

        response = test_client.post(
            "/api/v1/monitoring/stop", json=data, headers=headers
        )
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["success"] is True
        mock_orchestrator.unschedule_website_monitoring.assert_called()

    def test_pause_monitoring(self, test_client, mock_orchestrator):
        """Test pausing monitoring."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post("/api/v1/monitoring/pause", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "paused_jobs" in data
        mock_orchestrator.pause_all_jobs.assert_called_once()

    def test_resume_monitoring(self, test_client, mock_orchestrator):
        """Test resuming monitoring."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post("/api/v1/monitoring/resume", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "resumed_jobs" in data
        mock_orchestrator.resume_all_jobs.assert_called_once()

    def test_monitoring_status(self, test_client, mock_orchestrator, mock_storage):
        """Test getting monitoring status."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/monitoring/status", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["overall_status"] == "running"
        assert "total_jobs_scheduled" in data
        assert "active_websites" in data

    def test_execute_workflow(self, test_client, mock_storage, mock_orchestrator):
        """Test executing workflow."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post(
            "/api/v1/monitoring/workflows/website_monitoring/execute?website_id=test-website-123",
            headers=headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["workflow_id"] == "website_monitoring"
        assert data["website_id"] == "test-website-123"
        mock_orchestrator.execute_immediate_workflow.assert_called_once()


class TestSystemAPI:
    """Test system status API endpoints."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        # Health endpoint should work without authentication
        response = test_client.get("/api/v1/system/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

    def test_system_status(self, test_client, mock_orchestrator):
        """Test system status endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/system/status", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["overall_status"] in ["healthy", "degraded"]
        assert "components" in data
        assert "uptime_seconds" in data
        mock_orchestrator.get_orchestrator_status.assert_called_once()

    def test_system_info(self, test_client):
        """Test system info endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/system/info", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["application"] == "WebDeface Monitor"
        assert data["version"] == "0.1.0"
        assert "configuration" in data

    def test_system_logs(self, test_client):
        """Test system logs endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/system/logs", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data

    def test_restart_system(self, test_client):
        """Test system restart endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post("/api/v1/system/restart", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "restart completed" in data["message"]

    def test_run_maintenance(self, test_client, mock_orchestrator):
        """Test maintenance endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post("/api/v1/system/maintenance", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "Maintenance tasks initiated" in data["message"]
        mock_orchestrator.execute_immediate_workflow.assert_called_once()


class TestAlertsAPI:
    """Test alert management API endpoints."""

    def test_list_alerts(self, test_client, mock_storage):
        """Test listing alerts."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/alerts/", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "alerts" in data
        assert data["total"] >= 0
        assert "page" in data

    def test_get_alert(self, test_client, mock_storage):
        """Test getting specific alert."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/alerts/test-alert-123", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-alert-123"
        assert data["alert_type"] == "defacement"
        mock_storage.get_alert.assert_called_once_with("test-alert-123")

    def test_update_alert(self, test_client, mock_storage):
        """Test updating alert."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {"status": "acknowledged"}

        response = test_client.put(
            "/api/v1/alerts/test-alert-123", json=data, headers=headers
        )
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["id"] == "test-alert-123"
        mock_storage.update_alert.assert_called_once()

    def test_acknowledge_alert(self, test_client, mock_storage):
        """Test acknowledging alert."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post(
            "/api/v1/alerts/test-alert-123/acknowledge", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-alert-123"
        mock_storage.update_alert.assert_called_once()

    def test_resolve_alert(self, test_client, mock_storage):
        """Test resolving alert."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.post(
            "/api/v1/alerts/test-alert-123/resolve", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-alert-123"
        mock_storage.update_alert.assert_called_once()

    def test_alert_stats(self, test_client, mock_storage):
        """Test alert statistics."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/alerts/stats/summary", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_alerts" in data
        assert "open_alerts" in data
        assert "critical_alerts" in data

    def test_bulk_acknowledge_alerts(self, test_client, mock_storage):
        """Test bulk acknowledging alerts."""
        headers = {"Authorization": "Bearer test-token-123"}
        alert_ids = ["alert-1", "alert-2", "alert-3"]

        response = test_client.post(
            "/api/v1/alerts/bulk/acknowledge", json=alert_ids, headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "successful_updates" in data
        assert "total_requested" in data


class TestMetricsAPI:
    """Test metrics and analytics API endpoints."""

    def test_metrics_summary(self, test_client, mock_storage, mock_orchestrator):
        """Test metrics summary endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/metrics/summary", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_websites" in data
        assert "active_websites" in data
        assert "total_scans_today" in data
        assert "system_uptime_seconds" in data

    def test_website_metrics(self, test_client, mock_storage):
        """Test website metrics endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/metrics/websites", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "website_id" in data[0]
            assert "total_scans" in data[0]

    def test_website_metrics_detail(self, test_client, mock_storage):
        """Test detailed website metrics."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get(
            "/api/v1/metrics/websites/test-website-123", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["website_id"] == "test-website-123"
        assert "uptime_percentage" in data
        assert "health_score" in data

    def test_performance_metrics(self, test_client, mock_orchestrator):
        """Test performance metrics endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/metrics/performance", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "active_jobs" in data
        assert "queue_size" in data

    def test_timeseries_data(self, test_client, mock_storage):
        """Test timeseries data endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get(
            "/api/v1/metrics/timeseries/response_time?time_range=24h", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metric_name"] == "response_time"
        assert data["time_range"] == "24h"
        assert "data_points" in data

    def test_export_metrics(self, test_client):
        """Test metrics export endpoint."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/metrics/export/csv", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "export_id" in data
        assert "download_url" in data


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_not_found_website(self, test_client, mock_storage):
        """Test 404 error for non-existent website."""
        mock_storage.get_website.return_value = None
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/websites/non-existent", headers=headers)
        assert response.status_code == 404

        data = response.json()
        assert "not found" in data["error"]["error"].lower()

    def test_invalid_input_data(self, test_client):
        """Test validation error for invalid input."""
        headers = {"Authorization": "Bearer test-token-123"}
        data = {"url": "invalid-url", "name": ""}  # Invalid URL

        response = test_client.post("/api/v1/websites/", json=data, headers=headers)
        assert response.status_code == 422  # Validation error

    def test_method_not_allowed(self, test_client):
        """Test method not allowed error."""
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.patch("/api/v1/websites/", headers=headers)
        assert response.status_code == 405

    def test_server_error_handling(self, test_client, mock_storage):
        """Test internal server error handling."""
        mock_storage.list_websites.side_effect = Exception("Database error")
        headers = {"Authorization": "Bearer test-token-123"}

        response = test_client.get("/api/v1/websites/", headers=headers)
        assert response.status_code == 500

        data = response.json()
        assert "error" in data


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema endpoint."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["info"]["title"] == "WebDeface Monitor API"
        assert "paths" in data

    def test_swagger_docs(self, test_client):
        """Test Swagger documentation endpoint."""
        response = test_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_docs(self, test_client):
        """Test ReDoc documentation endpoint."""
        response = test_client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAPIIntegration:
    """Test API integration scenarios."""

    def test_complete_website_lifecycle(
        self, test_client, mock_storage, mock_orchestrator
    ):
        """Test complete website lifecycle via API."""
        headers = {"Authorization": "Bearer test-token-123"}

        # Create website
        create_data = {"url": "https://example.com", "name": "Test Website"}
        response = test_client.post(
            "/api/v1/websites/", json=create_data, headers=headers
        )
        assert response.status_code == 201
        website_data = response.json()
        website_id = website_data["id"]

        # Start monitoring
        monitor_data = {"website_ids": [website_id]}
        response = test_client.post(
            "/api/v1/monitoring/start", json=monitor_data, headers=headers
        )
        assert response.status_code == 200

        # Trigger immediate check
        response = test_client.post(
            f"/api/v1/websites/{website_id}/check", headers=headers
        )
        assert response.status_code == 202

        # Check status
        response = test_client.get(
            f"/api/v1/websites/{website_id}/status", headers=headers
        )
        assert response.status_code == 200

        # Update website
        update_data = {"name": "Updated Website"}
        response = test_client.put(
            f"/api/v1/websites/{website_id}", json=update_data, headers=headers
        )
        assert response.status_code == 200

        # Stop monitoring
        response = test_client.post(
            "/api/v1/monitoring/stop", json=monitor_data, headers=headers
        )
        assert response.status_code == 200

        # Delete website
        response = test_client.delete(f"/api/v1/websites/{website_id}", headers=headers)
        assert response.status_code == 204

    def test_alert_management_workflow(self, test_client, mock_storage):
        """Test alert management workflow."""
        headers = {"Authorization": "Bearer test-token-123"}

        # List alerts
        response = test_client.get("/api/v1/alerts/", headers=headers)
        assert response.status_code == 200

        # Get alert details
        response = test_client.get("/api/v1/alerts/test-alert-123", headers=headers)
        assert response.status_code == 200

        # Acknowledge alert
        response = test_client.post(
            "/api/v1/alerts/test-alert-123/acknowledge", headers=headers
        )
        assert response.status_code == 200

        # Resolve alert
        response = test_client.post(
            "/api/v1/alerts/test-alert-123/resolve", headers=headers
        )
        assert response.status_code == 200

        # Get alert statistics
        response = test_client.get("/api/v1/alerts/stats/summary", headers=headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestAsyncAPIComponents:
    """Test async components used by API."""

    async def test_lifespan_events(self, test_settings):
        """Test API lifespan events."""
        from src.webdeface.api.app import lifespan

        with patch("src.webdeface.api.app.get_storage_manager") as mock_storage, patch(
            "src.webdeface.api.app.get_scheduling_orchestrator"
        ) as mock_orchestrator:
            mock_storage.return_value = AsyncMock()
            mock_orchestrator.return_value = AsyncMock()

            app = MagicMock()
            app.state = MagicMock()

            # Test lifespan context manager
            async with lifespan(app):
                assert hasattr(app.state, "storage")
                assert hasattr(app.state, "orchestrator")
                assert hasattr(app.state, "settings")
