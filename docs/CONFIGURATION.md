# WebDeface Monitor Configuration

This document provides a reference for configuring the WebDeface Monitor.

## Configuration Methods

The application can be configured in two ways:

1.  **Environment Variables:** For sensitive data and settings that change between environments.
2.  **YAML Configuration File:** For static configuration that is shared across environments.

Environment variables always override the values in the configuration file.

## Environment Variables

The following environment variables are used to configure the application:

| Variable | Description | Default |
|---|---|---|
| `DEBUG` | Enable debug mode. | `False` |
| `LOG_LEVEL` | The log level to use. | `INFO` |
| `KEEP_SCANS` | The number of scans to keep for each website. | `20` |
| `API_TOKENS` | A comma-separated list of API tokens. | `dev-token-12345` |
| `DATABASE_URL` | The URL of the database. | `sqlite:///./data/webdeface.db` |
| `QDRANT_URL` | The URL of the Qdrant vector database. | `http://localhost:6333` |
| `SLACK_BOT_TOKEN` | The Slack bot token. | `""` |
| `SLACK_APP_TOKEN` | The Slack app token. | `""` |
| `SLACK_SIGNING_SECRET` | The Slack signing secret. | `""` |
| `CLAUDE_API_KEY` | The Claude API key. | `""` |

## YAML Configuration

The `config.yaml` file is used to configure the application's static settings.

### Example `config.yaml`

```yaml
global:
  default_interval: "*/15 * * * *"   # Every 15 minutes
  keep_scans: 20
  alert:
    site_down:
      channels: ["#noc"]
      users: []
    benign_change:
      channels: []
      users: []
    defacement:
      channels: ["#sec-ops"]
      users: ["@security-team"]

sites:
  - url: "https://example.com"
    name: "Example Site"
    interval: "0,30 * * * *"  # Every 30 minutes
    depth: 2
    enabled: true
  - url: "https://critical-site.com"
    name: "Critical Site"
    interval: "*/5 * * * *"   # Every 5 minutes
    depth: 1
    enabled: true

scraping:
  default_timeout: 10000  # 10 seconds
  max_retries: 3
  max_depth: 3
  user_agents:
    - "Mozilla/5.0 (compatible; WebDefaceMonitor/1.0)"
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### Top-Level Sections

*   **`global`**: Global settings for the application.
*   **`sites`**: A list of websites to monitor.
*   **`scraping`**: Settings for the web scraper.

## Support

If you have any questions or issues with the configuration, please open an issue on our [GitHub repository](https://github.com/bcdannyboy/webdeface/issues).
