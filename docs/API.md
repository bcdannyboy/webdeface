# WebDeface Monitor API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000/api/v1`
**Authentication:** Bearer Token

This document provides comprehensive documentation for the WebDeface Monitor REST API, including all endpoints, request/response schemas, authentication, and integration examples.

## 📋 Table of Contents

- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Website Management](#website-management)
- [Monitoring Control](#monitoring-control)
- [Alert Management](#alert-management)
- [System Status](#system-status)
- [Metrics & Analytics](#metrics--analytics)
- [Integration Examples](#integration-examples)
- [Rate Limiting](#rate-limiting)
- [Webhooks](#webhooks)

## 🔐 Authentication

The API uses Bearer token authentication. Include your API token in the Authorization header for all requests.

### Getting Started

**Contact your administrator to obtain an API token.**

```bash
# Include in all requests
Authorization: Bearer <your-api-token>
```

### Verify Token

**Endpoint:** `GET /auth/token/verify`

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/auth/token/verify
```

**Response:**
```json
{
  "valid": true,
  "user_id": "user123",
  "role": "admin",
  "permissions": ["read", "write", "admin"]
}
```

### Token Information

**Endpoint:** `GET /auth/token/info`

```bash
curl http://localhost:8000/api/v1/auth/token/info
```

**Response:**
```json
{
  "message": "API uses Bearer token authentication",
  "header": "Authorization: Bearer <your-api-token>",
  "note": "Contact administrator for API token"
}
```

## 📤 Response Format

All API responses follow a consistent JSON format:

### Success Response
```json
{
  "id": "abc123",
  "name": "Example Website",
  "url": "https://example.com",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Error Response
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid website URL format",
  "details": {
    "field": "url",
    "code": "INVALID_URL"
  }
}
```

### List Response
```json
{
  "websites": [...],
  "total": 25,
  "page": 1,
  "page_size": 50
}
```

## ⚠️ Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `204` | No Content | Resource deleted successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `409` | Conflict | Resource already exists |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |

### Error Response Schema

```json
{
  "error": "string",           // Error code
  "message": "string",         // Human-readable message
  "details": {                 // Additional error details
    "field": "string",
    "code": "string",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## 🌐 Website Management

Manage websites for defacement monitoring.

### Create Website

**Endpoint:** `POST /websites`
**Permissions:** `write`

**Request Body:**
```json
{
  "url": "https://example.com",
  "name": "Example Website",
  "description": "Main company website",
  "check_interval_seconds": 900,
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": "abc123",
  "url": "https://example.com",
  "name": "Example Website",
  "description": "Main company website",
  "check_interval_seconds": 900,
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "last_checked_at": null
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "name": "Example Website",
    "check_interval_seconds": 600
  }' \
  http://localhost:8000/api/v1/websites
```

### List Websites

**Endpoint:** `GET /websites`
**Permissions:** `read`

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 50, max: 100) - Items per page
- `is_active` (bool, optional) - Filter by active status

**Response:** `200 OK`
```json
{
  "websites": [
    {
      "id": "abc123",
      "url": "https://example.com",
      "name": "Example Website",
      "description": "Main company website",
      "check_interval_seconds": 900,
      "is_active": true,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "last_checked_at": "2024-01-01T12:15:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

**Example:**
```bash
# List all websites
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/websites

# List only active websites
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/websites?is_active=true"

# Paginated list
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/websites?page=2&page_size=10"
```

### Get Website

**Endpoint:** `GET /websites/{website_id}`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "id": "abc123",
  "url": "https://example.com",
  "name": "Example Website",
  "description": "Main company website",
  "check_interval_seconds": 900,
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "last_checked_at": "2024-01-01T12:15:00Z"
}
```

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/websites/abc123
```

### Update Website

**Endpoint:** `PUT /websites/{website_id}`
**Permissions:** `write`

**Request Body:**
```json
{
  "name": "Updated Website Name",
  "description": "Updated description",
  "check_interval_seconds": 600,
  "is_active": false
}
```

**Response:** `200 OK`
```json
{
  "id": "abc123",
  "url": "https://example.com",
  "name": "Updated Website Name",
  "description": "Updated description",
  "check_interval_seconds": 600,
  "is_active": false,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z",
  "last_checked_at": "2024-01-01T12:15:00Z"
}
```

**Example:**
```bash
curl -X PUT \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name", "is_active": false}' \
  http://localhost:8000/api/v1/websites/abc123
```

### Delete Website

**Endpoint:** `DELETE /websites/{website_id}`
**Permissions:** `write`

**Response:** `204 No Content`

**Example:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/websites/abc123
```

### Get Website Status

**Endpoint:** `GET /websites/{website_id}/status`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "id": "abc123",
  "name": "Example Website",
  "url": "https://example.com",
  "is_active": true,
  "last_checked_at": "2024-01-01T12:15:00Z",
  "monitoring_status": "active",
  "recent_snapshots_count": 48,
  "active_alerts_count": 0,
  "health_score": 9.8
}
```

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/websites/abc123/status
```

### Trigger Immediate Check

**Endpoint:** `POST /websites/{website_id}/check`
**Permissions:** `write`

**Response:** `202 Accepted`
```json
{
  "message": "Immediate check triggered",
  "website_id": "abc123",
  "execution_id": "exec_xyz789"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/websites/abc123/check
```

## 🔄 Monitoring Control

Control monitoring operations for websites.

### Start Monitoring

**Endpoint:** `POST /monitoring/start`
**Permissions:** `write`

**Request Body:**
```json
{
  "website_ids": ["abc123", "def456"],
  "priority": "high"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Monitoring started for 2 websites",
  "website_ids": ["abc123", "def456"],
  "execution_ids": ["exec_1", "exec_2"]
}
```

**Example:**
```bash
# Start monitoring for specific websites
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"website_ids": ["abc123"]}' \
  http://localhost:8000/api/v1/monitoring/start

# Start monitoring for all active websites
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/api/v1/monitoring/start
```

### Stop Monitoring

**Endpoint:** `POST /monitoring/stop`
**Permissions:** `write`

**Request Body:**
```json
{
  "website_ids": ["abc123", "def456"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Monitoring stopped for 2 websites",
  "website_ids": ["abc123", "def456"],
  "execution_ids": []
}
```

### Pause Monitoring

**Endpoint:** `POST /monitoring/pause`
**Permissions:** `write`

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "All monitoring jobs paused",
  "paused_jobs_count": 5
}
```

### Resume Monitoring

**Endpoint:** `POST /monitoring/resume`
**Permissions:** `write`

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "All monitoring jobs resumed",
  "resumed_jobs_count": 5
}
```

### Get Monitoring Status

**Endpoint:** `GET /monitoring/status`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "overall_status": "running",
  "active_websites": 12,
  "total_jobs_scheduled": 12,
  "total_workflows_executed": 1543,
  "uptime_seconds": 86400.5,
  "components": {
    "scheduler": true,
    "orchestrator": true,
    "workflow_engine": true
  }
}
```

### Execute Workflow

**Endpoint:** `POST /monitoring/workflows/{workflow_id}/execute`
**Permissions:** `write`

**Query Parameters:**
- `website_id` (required) - Target website ID
- `priority` (optional, default: "normal") - Execution priority

**Response:** `200 OK`
```json
{
  "execution_id": "exec_abc123",
  "workflow_id": "website_monitoring",
  "website_id": "abc123",
  "status": "initiated",
  "started_at": null,
  "completed_at": null,
  "duration_seconds": null
}
```

### List Active Workflows

**Endpoint:** `GET /monitoring/workflows/active`
**Permissions:** `read`

**Response:** `200 OK`
```json
[
  {
    "execution_id": "exec_abc123",
    "workflow_id": "website_monitoring",
    "website_id": "abc123",
    "status": "running",
    "started_at": "2024-01-01T12:00:00Z",
    "completed_at": null,
    "duration_seconds": null
  }
]
```

## 🚨 Alert Management

Manage defacement and monitoring alerts.

### List Alerts

**Endpoint:** `GET /alerts`
**Permissions:** `read`

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 50, max: 100) - Items per page
- `status` (string, optional) - Filter by status (open, acknowledged, resolved)
- `severity` (string, optional) - Filter by severity (critical, high, medium, low)
- `website_id` (string, optional) - Filter by website
- `alert_type` (string, optional) - Filter by alert type

**Response:** `200 OK`
```json
{
  "alerts": [
    {
      "id": "alert_123",
      "website_id": "abc123",
      "website_name": "Example Website",
      "website_url": "https://example.com",
      "alert_type": "defacement",
      "severity": "high",
      "title": "Potential defacement detected",
      "description": "Claude classifier detected malicious content changes",
      "classification_label": "deface",
      "confidence_score": 0.92,
      "similarity_score": 0.15,
      "status": "open",
      "acknowledged_by": null,
      "acknowledged_at": null,
      "resolved_at": null,
      "notifications_sent": 3,
      "last_notification_at": "2024-01-01T12:05:00Z",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

**Example:**
```bash
# List all alerts
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/alerts

# Filter by status and severity
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/alerts?status=open&severity=high"

# Filter by website
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/alerts?website_id=abc123"
```

### Get Alert

**Endpoint:** `GET /alerts/{alert_id}`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "id": "alert_123",
  "website_id": "abc123",
  "website_name": "Example Website",
  "website_url": "https://example.com",
  "alert_type": "defacement",
  "severity": "high",
  "title": "Potential defacement detected",
  "description": "Claude classifier detected malicious content changes",
  "classification_label": "deface",
  "confidence_score": 0.92,
  "similarity_score": 0.15,
  "status": "open",
  "acknowledged_by": null,
  "acknowledged_at": null,
  "resolved_at": null,
  "notifications_sent": 3,
  "last_notification_at": "2024-01-01T12:05:00Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Update Alert

**Endpoint:** `PUT /alerts/{alert_id}`
**Permissions:** `write`

**Request Body:**
```json
{
  "status": "acknowledged",
  "acknowledged_by": "security-team"
}
```

**Response:** `200 OK` - Returns updated alert object

### Acknowledge Alert

**Endpoint:** `POST /alerts/{alert_id}/acknowledge`
**Permissions:** `write`

**Response:** `200 OK` - Returns updated alert object

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/alerts/alert_123/acknowledge
```

### Resolve Alert

**Endpoint:** `POST /alerts/{alert_id}/resolve`
**Permissions:** `write`

**Response:** `200 OK` - Returns updated alert object

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/alerts/alert_123/resolve
```

### Alert Statistics

**Endpoint:** `GET /alerts/stats/summary`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "total_alerts": 156,
  "open_alerts": 12,
  "acknowledged_alerts": 8,
  "resolved_alerts": 136,
  "critical_alerts": 3,
  "high_alerts": 15,
  "medium_alerts": 45,
  "low_alerts": 93,
  "alerts_today": 5,
  "alerts_this_week": 23,
  "avg_resolution_time_hours": 4.2
}
```

### Bulk Acknowledge

**Endpoint:** `POST /alerts/bulk/acknowledge`
**Permissions:** `write`

**Request Body:**
```json
["alert_123", "alert_456", "alert_789"]
```

**Response:** `200 OK`
```json
{
  "message": "Acknowledged 3 alerts",
  "successful_updates": ["alert_123", "alert_456", "alert_789"],
  "failed_updates": [],
  "total_requested": 3
}
```

## 🖥️ System Status

Monitor system health and operational status.

### Health Check

**Endpoint:** `GET /system/health`
**Authentication:** Optional

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "0.1.0",
  "uptime_seconds": 86400.5,
  "checks": {
    "orchestrator": true,
    "storage": true,
    "scheduler": true
  },
  "message": "All systems operational"
}
```

**Example:**
```bash
# Public health check
curl http://localhost:8000/api/v1/system/health

# Authenticated health check (more details)
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/system/health
```

### System Status

**Endpoint:** `GET /system/status`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "overall_status": "healthy",
  "uptime_seconds": 86400.5,
  "start_time": "2024-01-01T00:00:00Z",
  "components": [
    {
      "component": "scheduler_orchestrator",
      "status": "running",
      "healthy": true,
      "message": "Scheduling orchestrator status",
      "last_check": "2024-01-01T12:00:00Z",
      "details": {
        "scheduler": true,
        "workflow_engine": true
      }
    },
    {
      "component": "storage",
      "status": "running",
      "healthy": true,
      "message": "Storage operational with 25 websites",
      "last_check": "2024-01-01T12:00:00Z",
      "details": {
        "website_count": 25
      }
    }
  ],
  "scheduler_stats": {
    "total_jobs": 25,
    "active_jobs": 25,
    "completed_workflows": 1543
  },
  "health_score": 9.8
}
```

### System Information

**Endpoint:** `GET /system/info`
**Permissions:** `read`

**Response:** `200 OK`
```json
{
  "application": "WebDeface Monitor",
  "version": "0.1.0",
  "environment": "production",
  "started_at": "2024-01-01T00:00:00Z",
  "configuration": {
    "logging_level": "INFO",
    "development_mode": false,
    "api_version": "v1"
  }
}
```

### System Logs

**Endpoint:** `GET /system/logs`
**Permissions:** `read`

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 50, max: 500) - Items per page
- `level` (string, optional) - Filter by log level (debug, info, warning, error)
- `component` (string, optional) - Filter by component

**Response:** `200 OK`
```json
{
  "entries": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "INFO",
      "component": "scheduler",
      "message": "Website monitoring job completed successfully",
      "details": {
        "website_id": "abc123",
        "duration": 2.5
      }
    },
    {
      "timestamp": "2024-01-01T11:58:00Z",
      "level": "WARNING",
      "component": "classifier",
      "message": "Low confidence score detected",
      "details": {
        "confidence": 0.3,
        "website_id": "xyz789"
      }
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 50
}
```

### Restart System

**Endpoint:** `POST /system/restart`
**Permissions:** `write`

**Response:** `200 OK`
```json
{
  "message": "System restart completed successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Run Maintenance

**Endpoint:** `POST /system/maintenance`
**Permissions:** `write`

**Response:** `200 OK`
```json
{
  "message": "Maintenance tasks initiated",
  "execution_id": "maint_abc123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 📊 Metrics & Analytics

**Note:** The metrics router exists in the codebase but endpoints would be implemented based on monitoring requirements.

Common metrics endpoints would include:
- `GET /metrics/prometheus` - Prometheus-formatted metrics
- `GET /metrics/performance` - Performance statistics
- `GET /metrics/usage` - Usage analytics

## 🔗 Integration Examples

### Python Integration

```python
import requests
import json

class WebDefaceClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def add_website(self, url, name=None, interval=900):
        """Add a website for monitoring."""
        data = {
            'url': url,
            'name': name,
            'check_interval_seconds': interval
        }
        response = requests.post(
            f'{self.base_url}/websites',
            headers=self.headers,
            json=data
        )
        return response.json()

    def get_alerts(self, status=None, severity=None):
        """Get alerts with optional filtering."""
        params = {}
        if status:
            params['status'] = status
        if severity:
            params['severity'] = severity

        response = requests.get(
            f'{self.base_url}/alerts',
            headers=self.headers,
            params=params
        )
        return response.json()

    def acknowledge_alert(self, alert_id):
        """Acknowledge an alert."""
        response = requests.post(
            f'{self.base_url}/alerts/{alert_id}/acknowledge',
            headers=self.headers
        )
        return response.json()

# Usage
client = WebDefaceClient('http://localhost:8000/api/v1', 'your-token')

# Add website
website = client.add_website('https://example.com', 'Example Site')
print(f"Added website: {website['id']}")

# Check alerts
alerts = client.get_alerts(status='open', severity='high')
print(f"Found {len(alerts['alerts'])} high-priority open alerts")

# Acknowledge alerts
for alert in alerts['alerts']:
    client.acknowledge_alert(alert['id'])
    print(f"Acknowledged alert: {alert['id']}")
```

### JavaScript/Node.js Integration

```javascript
class WebDefaceAPI {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: { ...this.headers, ...options.headers }
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        return response.json();
    }

    async addWebsite(url, name, interval = 900) {
        return this.request('/websites', {
            method: 'POST',
            body: JSON.stringify({
                url,
                name,
                check_interval_seconds: interval
            })
        });
    }

    async getWebsites(isActive = null) {
        const params = new URLSearchParams();
        if (isActive !== null) {
            params.append('is_active', isActive);
        }

        return this.request(`/websites?${params}`);
    }

    async startMonitoring(websiteIds = null) {
        return this.request('/monitoring/start', {
            method: 'POST',
            body: JSON.stringify({
                website_ids: websiteIds
            })
        });
    }

    async getSystemStatus() {
        return this.request('/system/status');
    }
}

// Usage
const api = new WebDefaceAPI('http://localhost:8000/api/v1', 'your-token');

// Add and start monitoring
(async () => {
    try {
        const website = await api.addWebsite('https://example.com', 'Example');
        console.log('Website added:', website.id);

        await api.startMonitoring([website.id]);
        console.log('Monitoring started');

        const status = await api.getSystemStatus();
        console.log('System status:', status.overall_status);
    } catch (error) {
        console.error('API error:', error.message);
    }
})();
```

### Shell/Bash Integration

```bash
#!/bin/bash

# Configuration
API_BASE="http://localhost:8000/api/v1"
API_TOKEN="your-api-token"
AUTH_HEADER="Authorization: Bearer $API_TOKEN"

# Add website
add_website() {
    local url=$1
    local name=$2

    curl -s -X POST \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$url\", \"name\": \"$name\"}" \
        "$API_BASE/websites" | jq -r '.id'
}

# Get system health
check_health() {
    curl -s -H "$AUTH_HEADER" \
        "$API_BASE/system/health" | jq '.status'
}

# List open alerts
list_open_alerts() {
    curl -s -H "$AUTH_HEADER" \
        "$API_BASE/alerts?status=open" | jq '.alerts'
}

# Start monitoring
start_monitoring() {
    curl -s -X POST \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d '{}' \
        "$API_BASE/monitoring/start"
}

# Usage examples
echo "Adding website..."
WEBSITE_ID=$(add_website "https://example.com" "Example Site")
echo "Website ID: $WEBSITE_ID"

echo "Checking system health..."
HEALTH=$(check_health)
echo "System status: $HEALTH"

echo "Starting monitoring..."
start_monitoring

echo "Checking for open alerts..."
list_open_alerts
```

## 🚦 Rate Limiting

- **Default Limits:** 1000 requests per hour per API token
- **Burst Allowance:** 100 requests per minute
- **Headers:** Rate limit information included in response headers

**Response Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 945
X-RateLimit-Reset: 1640995200
```

**Rate Limit Exceeded Response:**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Limit: 1000 per hour",
  "details": {
    "limit": 1000,
    "remaining": 0,
    "reset_time": "2024-01-01T13:00:00Z"
  }
}
```

## 📡 Webhooks

Configure webhooks to receive real-time notifications about alerts and system events.

**Webhook Configuration:** Contact your administrator to configure webhook endpoints.

**Webhook Payload Example:**
```json
{
  "event": "alert.created",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "alert_id": "alert_123",
    "website_id": "abc123",
    "website_url": "https://example.com",
    "alert_type": "defacement",
    "severity": "high",
    "classification_label": "deface",
    "confidence_score": 0.92
  }
}
```

**Event Types:**
- `alert.created` - New alert generated
- `alert.acknowledged` - Alert acknowledged
- `alert.resolved` - Alert resolved
- `website.created` - Website added
- `website.updated` - Website modified
- `monitoring.started` - Monitoring started
- `monitoring.stopped` - Monitoring stopped
- `system.error` - System error occurred

---

## 📞 Support

- **Documentation:** [Full API Documentation](http://localhost:8000/docs)
- **Issues:** [GitHub Issues](https://github.com/bcdannyboy/webdeface/issues)
- **Email:** api-support@your-org.com

**Interactive API Documentation available at:**
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
