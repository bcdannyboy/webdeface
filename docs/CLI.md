# WebDeface Monitor CLI Documentation

**Command:** `webdeface-monitor`
**Version:** 1.0.0

> **⚠️ DEPRECATION NOTICE:** The CLI is deprecated and will be removed in a future version. Please migrate to the Slack slash commands for all operations. The Slack interface provides a better user experience, real-time collaboration, and more features. See the [Migration Guide](#migration-to-slack-commands) and [Slack Commands Documentation](SLACK_COMMANDS.md) for details.

This document provides comprehensive documentation for the WebDeface Monitor command-line interface, including all commands, options, usage examples, and advanced scenarios.

## 📋 Table of Contents

- [Installation](#installation)
- [Global Options](#global-options)
- [Command Overview](#command-overview)
- [Website Management](#website-management)
- [Monitoring Control](#monitoring-control)
- [System Management](#system-management)
- [Configuration](#configuration)
- [Output Formats](#output-formats)
- [Examples & Workflows](#examples--workflows)
- [Troubleshooting](#troubleshooting)

## 🛠️ Installation

### Via Package Manager
```bash
pip install webdeface-monitor
```

### From Source
```bash
git clone https://github.com/bcdannyboy/webdeface.git
cd webdeface-monitor
pip install -e .
```

### Verify Installation
```bash
webdeface-monitor --help
```

## 🌐 Global Options

Available for all commands:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--verbose` | `-v` | Enable verbose output | `false` |
| `--debug` | | Enable debug output | `false` |
| `--config PATH` | | Use custom configuration file | `config.yaml` |
| `--help` | `-h` | Show help message | |

**Examples:**
```bash
# Verbose output
webdeface-monitor --verbose website list

# Debug mode
webdeface-monitor --debug system status

# Custom config
webdeface-monitor --config /path/to/config.yaml website add https://example.com
```

## 📚 Command Overview

```bash
webdeface-monitor [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

### Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| `website` | `add`, `remove`, `list`, `status` | Website management |
| `monitoring` | `start`, `stop`, `pause`, `resume`, `check` | Monitoring control |
| `system` | `status`, `health`, `metrics`, `logs` | System management |

### Quick Reference

```bash
# Get help for any command
webdeface-monitor COMMAND --help

# Common operations
webdeface-monitor website add https://example.com
webdeface-monitor monitoring start
webdeface-monitor system status
```

## 🌐 Website Management

Manage websites for defacement monitoring.

### Add Website

Add a new website to the monitoring system.

**Syntax:**
```bash
webdeface-monitor website add URL [OPTIONS]
```

**Arguments:**
- `URL` (required) - Website URL to monitor

**Options:**
- `--name TEXT` - Website name (defaults to domain)
- `--interval TEXT` - Monitoring interval (cron expression, default: `*/15 * * * *`). Note: Currently, the interval is fixed at 15 minutes.
- `--max-depth INTEGER` - Maximum crawl depth (default: 2)

**Examples:**
```bash
# Basic website addition
webdeface-monitor website add https://example.com

# With custom name and interval
webdeface-monitor website add https://example.com \
    --name "Example Website" \
    --interval "*/5 * * * *"

# High-frequency monitoring
webdeface-monitor website add https://critical-site.com \
    --name "Critical Infrastructure" \
    --interval "* * * * *" \
    --max-depth 1

# Multiple websites (script)
for site in example.com important.org; do
    webdeface-monitor website add "https://$site" --name "$site"
done
```

**Output:**
```
✅ Website added successfully: Example Website (https://example.com)
   Website ID: abc123
   Execution ID: exec_xyz789
   Interval: */15 * * * *
```

### Remove Website

Remove a website from monitoring.

**Syntax:**
```bash
webdeface-monitor website remove WEBSITE_ID [OPTIONS]
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to remove

**Options:**
- `--force` - Force removal without confirmation

**Examples:**
```bash
# Interactive removal
webdeface-monitor website remove abc123

# Force removal
webdeface-monitor website remove abc123 --force

# Remove multiple websites
for id in abc123 def456 ghi789; do
    webdeface-monitor website remove $id --force
done
```

**Output:**
```
Remove website 'Example Website' (https://example.com)? [y/N]: y
✅ Website removed successfully: Example Website
   Website ID: abc123
```

### List Websites

List all monitored websites.

**Syntax:**
```bash
webdeface-monitor website list [OPTIONS]
```

**Options:**
- `--status CHOICE` - Filter by status (`active`, `inactive`, `all`, default: `all`)
- `--format CHOICE` - Output format (`table`, `json`, default: `table`)

**Examples:**
```bash
# List all websites
webdeface-monitor website list

# List only active websites
webdeface-monitor website list --status active

# JSON output
webdeface-monitor website list --format json

# Verbose output with details
webdeface-monitor --verbose website list
```

**Table Output:**
```
ID       Name              URL                    Status     Last Checked
abc123   Example Website   https://example.com    🟢 Active  2024-01-01 12:15
def456   Test Site         https://test.com       🔴 Inactive Never
ghi789   Important Site    https://important.org  🟢 Active  2024-01-01 12:10

Found 3 websites
```

**JSON Output:**
```json
[
  {
    "id": "abc123",
    "name": "Example Website",
    "url": "https://example.com",
    "status": "active",
    "last_checked": "2024-01-01T12:15:00Z",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

### Website Status

Show detailed status for a specific website.

**Syntax:**
```bash
webdeface-monitor website status WEBSITE_ID
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to check

**Examples:**
```bash
# Basic status
webdeface-monitor website status abc123

# Verbose status
webdeface-monitor --verbose website status abc123
```

**Output:**
```
Website Status: Example Website
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value                                                        ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ID               │ abc123                                                       │
│ Name             │ Example Website                                              │
│ URL              │ https://example.com                                          │
│ Status           │ 🟢 Active                                                    │
│ Created          │ 2024-01-01 10:00:00                                         │
│ Last Checked     │ 2024-01-01 12:15:00                                         │
│ Total Snapshots  │ 48                                                           │
│ Active Alerts    │ 0                                                            │
└──────────────────┴──────────────────────────────────────────────────────────────┘
```

## 🔄 Monitoring Control

Control monitoring operations.

### Start Monitoring

Start monitoring operations.

**Syntax:**
```bash
webdeface-monitor monitoring start [OPTIONS]
```

**Options:**
- `--website-id TEXT` - Start monitoring for specific website

**Examples:**
```bash
# Start all monitoring
webdeface-monitor monitoring start

# Start monitoring for specific website
webdeface-monitor monitoring start --website-id abc123

# Verbose start
webdeface-monitor --verbose monitoring start
```

**Output:**
```
✅ Monitoring system started
   Status: running
```

### Stop Monitoring

Stop monitoring operations.

**Syntax:**
```bash
webdeface-monitor monitoring stop [OPTIONS]
```

**Options:**
- `--website-id TEXT` - Stop monitoring for specific website

**Examples:**
```bash
# Stop all monitoring
webdeface-monitor monitoring stop

# Stop monitoring for specific website
webdeface-monitor monitoring stop --website-id abc123
```

**Output:**
```
✅ Monitoring system stopped
   Status: stopped
```

### Pause Monitoring

Temporarily pause monitoring operations.

**Syntax:**
```bash
webdeface-monitor monitoring pause [OPTIONS]
```

**Options:**
- `--website-id TEXT` - Pause monitoring for specific website

**Examples:**
```bash
# Pause all monitoring
webdeface-monitor monitoring pause

# Pause monitoring for specific website
webdeface-monitor monitoring pause --website-id abc123
```

### Resume Monitoring

Resume paused monitoring operations.

**Syntax:**
```bash
webdeface-monitor monitoring resume [OPTIONS]
```

**Options:**
- `--website-id TEXT` - Resume monitoring for specific website

**Examples:**
```bash
# Resume all monitoring
webdeface-monitor monitoring resume

# Resume monitoring for specific website
webdeface-monitor monitoring resume --website-id abc123
```

### Immediate Check

Run immediate check for a website.

**Syntax:**
```bash
webdeface-monitor monitoring check WEBSITE_ID
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to check

**Examples:**
```bash
# Run immediate check
webdeface-monitor monitoring check abc123

# Verbose check
webdeface-monitor --verbose monitoring check abc123
```

**Output:**
```
✅ Immediate check initiated for website: abc123
   Website ID: abc123
   Execution ID: exec_immediate_xyz789
```

## 🖥️ System Management

Monitor and manage system status.

### System Status

Show overall system status.

**Syntax:**
```bash
webdeface-monitor system status
```

**Examples:**
```bash
# Basic status
webdeface-monitor system status

# Verbose status
webdeface-monitor --verbose system status
```

**Output:**
```
System Status
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component            ┃ Status           ┃ Details              ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Overall              │ 🟢 Running       │ Uptime: 86400.5s     │
│ Scheduler Orchestrator │ 🟢 Running       │                      │
│ Workflow Engine      │ 🟢 Running       │                      │
│ Storage              │ 🟢 Running       │                      │
│ Jobs Scheduled       │ 25               │                      │
│ Workflows Executed   │ 1543             │                      │
│ Active Workflows     │ 3                │                      │
└──────────────────────┴──────────────────┴──────────────────────┘
```

### System Health

Show system health information.

**Syntax:**
```bash
webdeface-monitor system health
```

**Examples:**
```bash
# Basic health check
webdeface-monitor system health

# Verbose health check
webdeface-monitor --verbose system health
```

**Output:**
```
System Health
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                     ┃ Status                                                       ┃ Score                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Overall Health            │ 9.8/10                                                      │                          │
│ Scheduler                 │ 🟢 Healthy                                                   │ All jobs running         │
│ Storage                   │ 🟢 Healthy                                                   │ All operations normal    │
│ Claude API                │ 🟢 Healthy                                                   │ Response time: 245ms     │
│ Qdrant                    │ 🟢 Healthy                                                   │ Vector operations normal │
└───────────────────────────┴──────────────────────────────────────────────────────────────┴──────────────────────────┘
```

### System Metrics

Show system metrics and statistics.

**Syntax:**
```bash
webdeface-monitor system metrics
```

**Examples:**
```bash
# Basic metrics
webdeface-monitor system metrics

# Verbose metrics
webdeface-monitor --verbose system metrics
```

**Output:**
```
System Metrics
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value                                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Total Websites            │ 25                                                           │
│ Active Websites           │ 23                                                           │
│ Inactive Websites         │ 2                                                            │
│ Total Checks Today        │ 1,156                                                        │
│ Successful Checks         │ 1,142                                                        │
│ Failed Checks             │ 14                                                           │
│ Average Response Time     │ 2.3s                                                         │
└───────────────────────────┴──────────────────────────────────────────────────────────────┘
```

### System Logs

View system logs with filtering.

**Syntax:**
```bash
webdeface-monitor system logs [OPTIONS]
```

**Options:**
- `--level CHOICE` - Filter by log level (`debug`, `info`, `warning`, `error`)
- `--component TEXT` - Filter logs by component
- `--lines INTEGER` - Number of lines to show (default: 50)

**Examples:**
```bash
# Recent logs
webdeface-monitor system logs

# Error logs only
webdeface-monitor system logs --level error

# Logs from specific component
webdeface-monitor system logs --component scheduler

# Last 100 lines
webdeface-monitor system logs --lines 100

# Debug logs with more lines
webdeface-monitor system logs --level debug --lines 200
```

**Output:**
```
📋 Showing last 50 log entries (level: info)

2024-01-01 12:00:00 INFO [scheduler] Starting monitoring for website abc123
2024-01-01 12:01:00 INFO [scraper] Successfully scraped website xyz789
2024-01-01 12:02:00 WARNING [classifier] Low confidence score for detection
2024-01-01 12:03:00 ERROR [notification] Failed to send Slack alert
2024-01-01 12:04:00 INFO [api] Website created via API
```

## ⚙️ Configuration

### Configuration File

The CLI uses configuration files for default settings.

**Default Locations:**
- `./config.yaml` (current directory)
- `~/.webdeface/config.yaml` (user directory)
- `/etc/webdeface/config.yaml` (system directory)

**Custom Configuration:**
```bash
# Use specific config file
webdeface-monitor --config /path/to/config.yaml website list

# Environment variable
export WEBDEFACE_CONFIG=/path/to/config.yaml
webdeface-monitor website list
```

### Environment Variables

Override configuration with environment variables:

```bash
# Debug mode
export WEBDEFACE_DEBUG=true

# Verbose output
export WEBDEFACE_VERBOSE=true

# Custom data directory
export WEBDEFACE_DATA_DIR=/custom/path

# Log level
export WEBDEFACE_LOG_LEVEL=DEBUG
```

## 📊 Output Formats

### Table Format (Default)

Rich, formatted tables with colors and styling:

```bash
webdeface-monitor website list
```

### JSON Format

Machine-readable JSON output:

```bash
webdeface-monitor website list --format json
```

**Benefits:**
- Scriptable output
- Integration with other tools
- Programmatic processing

### Verbose Mode

Detailed output with additional information:

```bash
webdeface-monitor --verbose website add https://example.com
```

**Shows:**
- Execution details
- Timing information
- Additional context
- Success/failure reasons

### Debug Mode

Maximum detail for troubleshooting:

```bash
webdeface-monitor --debug system status
```

**Shows:**
- Internal operation details
- Full error traces
- Configuration values
- API call details

## 🔧 Examples & Workflows

### Initial Setup Workflow

```bash
#!/bin/bash
# Initial setup script

echo "Setting up WebDeface Monitor..."

# Add critical websites
webdeface-monitor website add https://company.com \
    --name "Company Main Site" \
    --interval "*/5 * * * *"

webdeface-monitor website add https://blog.company.com \
    --name "Company Blog" \
    --interval "*/15 * * * *"

webdeface-monitor website add https://api.company.com \
    --name "API Endpoint" \
    --interval "*/2 * * * *"

# Start monitoring
webdeface-monitor monitoring start

# Check status
webdeface-monitor system status

echo "Setup complete!"
```

### Daily Operations Workflow

```bash
#!/bin/bash
# Daily operations check

echo "=== Daily WebDeface Monitor Check ==="

# System health
echo "Checking system health..."
webdeface-monitor system health

# Website status
echo "Checking website status..."
webdeface-monitor website list --status active

# Recent logs
echo "Recent errors..."
webdeface-monitor system logs --level error --lines 20

# Metrics
echo "System metrics..."
webdeface-monitor system metrics

echo "Daily check complete!"
```

### Bulk Website Management

```bash
#!/bin/bash
# Bulk add websites from file

WEBSITE_FILE="websites.txt"

if [[ ! -f "$WEBSITE_FILE" ]]; then
    echo "Error: $WEBSITE_FILE not found"
    exit 1
fi

echo "Adding websites from $WEBSITE_FILE..."

while IFS= read -r url; do
    # Skip empty lines and comments
    [[ -z "$url" || "$url" =~ ^#.* ]] && continue

    echo "Adding: $url"
    webdeface-monitor website add "$url" --name "$(basename "$url")"

    # Small delay to avoid overwhelming the system
    sleep 1
done < "$WEBSITE_FILE"

echo "Bulk addition complete!"
webdeface-monitor website list
```

### Monitoring Report Script

```bash
#!/bin/bash
# Generate monitoring report

OUTPUT_FILE="monitoring-report-$(date +%Y%m%d).json"

echo "Generating monitoring report..."

# Collect data
{
    echo "{"
    echo "  \"generated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"system_status\": $(webdeface-monitor system status --format json 2>/dev/null || echo 'null'),"
    echo "  \"websites\": $(webdeface-monitor website list --format json 2>/dev/null || echo '[]'),"
    echo "  \"health\": $(webdeface-monitor system health --format json 2>/dev/null || echo 'null'),"
    echo "  \"metrics\": $(webdeface-monitor system metrics --format json 2>/dev/null || echo 'null')"
    echo "}"
} > "$OUTPUT_FILE"

echo "Report saved to: $OUTPUT_FILE"
```

### Emergency Response Script

```bash
#!/bin/bash
# Emergency response - stop all monitoring

echo "🚨 EMERGENCY: Stopping all monitoring operations"

# Stop monitoring
webdeface-monitor monitoring stop

# Check system status
webdeface-monitor system status

# Show recent errors
echo "Recent errors:"
webdeface-monitor system logs --level error --lines 50

echo "Emergency stop complete!"
```

## 🔍 Troubleshooting

### Common Issues

#### Command Not Found
```bash
# Check installation
which webdeface-monitor

# Reinstall if needed
pip install --force-reinstall webdeface-monitor

# Check PATH
echo $PATH
```

#### Permission Errors
```bash
# Check file permissions
ls -la config.yaml

# Fix permissions
chmod 644 config.yaml

# Check directory permissions
ls -la ./data/
```

#### Configuration Issues
```bash
# Validate configuration
webdeface-monitor --debug system status

# Check configuration file
cat config.yaml

# Use default configuration
webdeface-monitor --config config.example.yaml system status
```

#### Connection Errors
```bash
# Test API connectivity
curl -I https://api.anthropic.com

# Check Slack connectivity
webdeface-monitor --debug system health

# Verify network settings
webdeface-monitor system status
```

### Debug Mode

Enable maximum debugging for troubleshooting:

```bash
# Debug mode with verbose output
webdeface-monitor --debug --verbose COMMAND

# Environment variable
export WEBDEFACE_DEBUG=true
webdeface-monitor COMMAND
```

### Log Files

Check log files for detailed error information:

```bash
# View logs through CLI
webdeface-monitor system logs --level debug --lines 200

# Direct log file access
tail -f ./data/webdeface.log

# Error logs only
grep ERROR ./data/webdeface.log
```

### Getting Help

```bash
# General help
webdeface-monitor --help

# Command-specific help
webdeface-monitor website --help
webdeface-monitor website add --help

# Version information
webdeface-monitor --version
```

---

## 📞 Support

- **Documentation:** [CLI Reference](docs/CLI.md)
- **Issues:** [GitHub Issues](https://github.com/bcdannyboy/webdeface/issues)
- **Email:** cli-support@your-org.com

**Quick Help:**
```bash
webdeface-monitor --help
```

## 🔄 Migration to Slack Commands

The WebDeface Monitor now provides a comprehensive Slack slash commands interface that offers better team collaboration and real-time monitoring capabilities.

### Why Migrate?

- **Team Collaboration:** Commands and results are visible to team members
- **Real-time Notifications:** Immediate alerts in Slack channels
- **Simplified Access:** No need for CLI installation or configuration
- **Permission Management:** Role-based access control
- **Interactive Responses:** Rich formatted output with actionable buttons

### Command Mapping

| CLI Command | Slack Command | Notes |
|-------------|---------------|-------|
| `webdeface-monitor website add URL --name "Site"` | `/webdeface website add URL name:"Site"` | Flag syntax changes |
| `webdeface-monitor website list --status active` | `/webdeface website list status:active` | Same functionality |
| `webdeface-monitor monitoring start` | `/webdeface monitoring start` | Identical |
| `webdeface-monitor system status` | `/webdeface system status` | Identical |
| `webdeface-monitor system health` | `/webdeface system health` | Identical |

### Key Differences

1. **Flag Syntax:** Replace `--flag value` with `flag:value`
2. **Command Prefix:** Use `/webdeface` instead of `webdeface-monitor`
3. **Output:** Automatically formatted for Slack with rich formatting
4. **Permissions:** Role-based access instead of system-level access

### Migration Steps

1. **Get Slack Access:** Contact your administrator for WebDeface bot access
2. **Learn New Syntax:** Review [Slack Commands Documentation](SLACK_COMMANDS.md)
3. **Update Scripts:** Convert any automation scripts to use Slack webhooks or API
4. **Test Commands:** Try equivalent Slack commands for your workflows

### Example Migration

**Old CLI command:**
```bash
webdeface-monitor website add https://example.com --name "Example Site" --interval 300
```

**New Slack command:**
```slack
/webdeface website add https://example.com name:"Example Site" interval:300
```

For complete migration guidance, see [Slack Commands Documentation](SLACK_COMMANDS.md).

---

## 📞 Support

- **New Interface:** [Slack Commands Documentation](SLACK_COMMANDS.md)
- **CLI Documentation:** [CLI Reference](docs/CLI.md) (legacy)
- **Issues:** [GitHub Issues](https://github.com/bcdannyboy/webdeface/issues)
- **Email:** support@your-org.com

**Quick Help:**
```bash
# CLI (legacy)
webdeface-monitor --help
webdeface-monitor COMMAND --help

# Slack (recommended)
/webdeface help
/webdeface help <command>
```
webdeface-monitor COMMAND --help
