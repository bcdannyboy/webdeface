# Data Models

This document outlines the database schema used in the web defacement monitoring system. The schema is defined using SQLAlchemy ORM, and the models are located in `src/webdeface/storage/sqlite/models.py`.

## Table of Contents

- [Website](#website)
- [WebsiteSnapshot](#websitesnapshot)
- [DefacementAlert](#defacementalert)
- [ScheduledJob](#scheduledjob)
- [JobExecution](#jobexecution)
- [WorkflowDefinition](#workflowdefinition)
- [WorkflowExecution](#workflowexecution)

## Website

The `Website` table stores information about the websites being monitored.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `url` | String(2048) | The URL of the website. |
| `name` | String(255) | A human-readable name for the website. |
| `description` | Text | A description of the website. |
| `check_interval_seconds` | Integer | The interval in seconds at which to check the website. |
| `is_active` | Boolean | Whether the website is currently being monitored. |
| `created_at` | DateTime | The timestamp when the website was added. |
| `updated_at` | DateTime | The timestamp when the website was last updated. |
| `last_checked_at` | DateTime | The timestamp when the website was last checked. |

**Relationships:**

*   Has many `WebsiteSnapshot`s.
*   Has many `DefacementAlert`s.

## WebsiteSnapshot

The `WebsiteSnapshot` table stores a snapshot of a website's content at a particular point in time.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `website_id` | String(36) | Foreign key to the `websites` table. |
| `content_hash` | String(64) | The SHA-256 hash of the website's content. |
| `content_text` | Text | The text content of the website. |
| `raw_html` | LargeBinary | The raw HTML of the website. |
| `status_code` | Integer | The HTTP status code of the response. |
| `response_time_ms` | Float | The response time in milliseconds. |
| `content_length` | Integer | The length of the content in bytes. |
| `content_type` | String(255) | The content type of the response. |
| `vector_id` | String(255) | The ID of the vector in the vector database. |
| `similarity_score` | Float | The similarity score between this snapshot and the previous one. |
| `is_defaced` | Boolean | Whether the website is considered defaced. |
| `confidence_score` | Float | The confidence score of the defacement classification. |
| `captured_at` | DateTime | The timestamp when the snapshot was captured. |
| `analyzed_at` | DateTime | The timestamp when the snapshot was analyzed. |

**Relationships:**

*   Belongs to a `Website`.

## DefacementAlert

The `DefacementAlert` table stores information about detected defacements.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `website_id` | String(36) | Foreign key to the `websites` table. |
| `snapshot_id` | String(36) | Foreign key to the `website_snapshots` table. |
| `alert_type` | String(50) | The type of alert (e.g., "defacement", "site_down"). |
| `severity` | String(20) | The severity of the alert (e.g., "low", "medium", "high", "critical"). |
| `title` | String(255) | The title of the alert. |
| `description` | Text | A description of the alert. |
| `classification_label` | String(100) | The label of the classification. |
| `confidence_score` | Float | The confidence score of the classification. |
| `similarity_score` | Float | The similarity score of the content. |
| `status` | String(20) | The status of the alert (e.g., "open", "acknowledged", "resolved"). |
| `acknowledged_by` | String(255) | The user who acknowledged the alert. |
| `acknowledged_at` | DateTime | The timestamp when the alert was acknowledged. |
| `resolved_at` | DateTime | The timestamp when the alert was resolved. |
| `notifications_sent` | Integer | The number of notifications sent for this alert. |
| `last_notification_at` | DateTime | The timestamp when the last notification was sent. |
| `created_at` | DateTime | The timestamp when the alert was created. |
| `updated_at` | DateTime | The timestamp when the alert was last updated. |

**Relationships:**

*   Belongs to a `Website`.

## ScheduledJob

The `ScheduledJob` table stores information about scheduled jobs.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `job_id` | String(255) | The ID of the job. |
| `website_id` | String(36) | Foreign key to the `websites` table. |
| `job_type` | String(50) | The type of job. |
| `interval_expression` | String(255) | The interval expression for the job. |
| `priority` | Integer | The priority of the job. |
| `enabled` | Boolean | Whether the job is enabled. |
| `max_retries` | Integer | The maximum number of retries for the job. |
| `retry_delay` | Float | The delay in seconds between retries. |
| `status` | String(20) | The status of the job. |
| `next_run_at` | DateTime | The timestamp of the next run. |
| `last_run_at` | DateTime | The timestamp of the last run. |
| `last_success_at` | DateTime | The timestamp of the last successful run. |
| `job_metadata` | Text | JSON metadata for the job. |
| `created_at` | DateTime | The timestamp when the job was created. |
| `updated_at` | DateTime | The timestamp when the job was last updated. |

**Relationships:**

*   Belongs to a `Website`.
*   Has many `JobExecution`s.

## JobExecution

The `JobExecution` table stores information about individual job executions.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `execution_id` | String(255) | The ID of the execution. |
| `job_id` | String(36) | Foreign key to the `scheduled_jobs` table. |
| `website_id` | String(36) | Foreign key to the `websites` table. |
| `job_type` | String(50) | The type of job. |
| `status` | String(20) | The status of the execution. |
| `priority` | Integer | The priority of the execution. |
| `attempt_number` | Integer | The attempt number of the execution. |
| `started_at` | DateTime | The timestamp when the execution started. |
| `completed_at` | DateTime | The timestamp when the execution completed. |
| `duration_seconds` | Float | The duration of the execution in seconds. |
| `error_message` | Text | The error message if the execution failed. |
| `result_data` | Text | JSON data for the result. |
| `created_at` | DateTime | The timestamp when the execution was created. |

**Relationships:**

*   Belongs to a `ScheduledJob`.
*   Belongs to a `Website`.

## WorkflowDefinition

The `WorkflowDefinition` table stores information about workflow definitions.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `workflow_id` | String(255) | The ID of the workflow. |
| `name` | String(255) | The name of the workflow. |
| `description` | Text | A description of the workflow. |
| `priority` | Integer | The priority of the workflow. |
| `timeout_seconds` | Integer | The timeout in seconds for the workflow. |
| `workflow_steps` | Text | JSON data for the workflow steps. |
| `enabled` | Boolean | Whether the workflow is enabled. |
| `created_at` | DateTime | The timestamp when the workflow was created. |
| `updated_at` | DateTime | The timestamp when the workflow was last updated. |

**Relationships:**

*   Has many `WorkflowExecution`s.

## WorkflowExecution

The `WorkflowExecution` table stores information about individual workflow executions.

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | Primary key, a UUID. |
| `execution_id` | String(255) | The ID of the execution. |
| `workflow_id` | String(36) | Foreign key to the `workflow_definitions` table. |
| `website_id` | String(36) | Foreign key to the `websites` table. |
| `status` | String(20) | The status of the execution. |
| `priority` | Integer | The priority of the execution. |
| `started_at` | DateTime | The timestamp when the execution started. |
| `completed_at` | DateTime | The timestamp when the execution completed. |
| `duration_seconds` | Float | The duration of the execution in seconds. |
| `step_executions` | Text | JSON data for the step executions. |
| `error_message` | Text | The error message if the execution failed. |
| `result_data` | Text | JSON data for the result. |
| `created_at` | DateTime | The timestamp when the execution was created. |

**Relationships:**

*   Belongs to a `WorkflowDefinition`.
*   Belongs to a `Website`.