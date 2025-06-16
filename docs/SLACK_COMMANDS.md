# WebDeface Monitor Slack Commands Documentation

**Command Prefix:** `/webdeface`
**Version:** 1.0.0

This document provides comprehensive documentation for the WebDeface Monitor Slack slash commands interface, including all commands, usage syntax, permissions, and examples.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Command Syntax](#command-syntax)
- [Permission System](#permission-system)
- [Website Management](#website-management)
- [Monitoring Operations](#monitoring-operations)
- [System Management](#system-management)
- [Help System](#help-system)
- [Examples & Workflows](#examples--workflows)
- [Troubleshooting](#troubleshooting)
- [Migration from CLI](#migration-from-cli)

## 🚀 Getting Started

### Prerequisites

- Access to the Slack workspace where the WebDeface Monitor bot is installed
- Appropriate user permissions (contact your administrator for access)
- The bot must be invited to channels where you want to use commands

### Quick Start

```slack
# Get help
/webdeface help

# Check system status
/webdeface system status

# List monitored websites
/webdeface website list

# Add a new website
/webdeface website add https://example.com name:"Example Site"
```

## 🔧 Command Syntax

All Slack commands use the `/webdeface` prefix followed by command groups and subcommands:

```
/webdeface <GROUP> <SUBCOMMAND> [ARGUMENTS] [FLAGS]
```

### Flag Format

Slack commands use `name:value` syntax instead of CLI-style `--name value`:

| CLI Format | Slack Format |
|------------|--------------|
| `--name "Example Site"` | `name:"Example Site"` |
| `--interval 900` | `interval:900` |
| `--status active` | `status:active` |
| `--force` | `force:true` |

### Examples

```slack
# Add website with custom name and interval
/webdeface website add https://example.com name:"My Website" interval:300

# List active websites
/webdeface website list status:active

# Get system metrics for last 24 hours
/webdeface system metrics range:24h

# View error logs from last hour
/webdeface system logs level:error since:1h
```

## 🔐 Permission System

The Slack bot implements a role-based permission system to control access to commands.

### User Roles

| Role | Description | Command Access |
|------|-------------|----------------|
| **VIEWER** | Read-only access | View commands only |
| **OPERATOR** | Operational control | View + monitoring control |
| **ADMIN** | Full management | View + control + site management |
| **SUPER_ADMIN** | System administration | All commands |

### Role Permissions

#### VIEWER Role
- `website list`, `website status`
- `system status`, `system health`, `system metrics`, `system logs`

#### OPERATOR Role
- All VIEWER permissions plus:
- `monitoring pause`, `monitoring resume`, `monitoring check`

#### ADMIN Role
- All OPERATOR permissions plus:
- `website add`, `website remove`
- `monitoring start`, `monitoring stop`

#### SUPER_ADMIN Role
- All permissions including user management

### Permission Errors

If you lack permissions for a command, you'll see:
```
❌ Insufficient permissions for this command
Required: <permission_name>
Your role: <current_role>
Contact your administrator for access.
```

## 🌐 Website Management

Manage websites for defacement monitoring.

### Add Website

Add a new website to the monitoring system.

**Syntax:**
```
/webdeface website add <URL> [FLAGS]
```

**Arguments:**
- `URL` (required) - Website URL to monitor

**Flags:**
- `name:TEXT` - Custom website name (defaults to domain)
- `interval:NUMBER` - Check interval in seconds (default: 900)
- `max-depth:NUMBER` - Maximum crawl depth (default: 2)

**Required Permission:** `ADD_SITES` (Admin+)

**Examples:**
```slack
# Basic website addition
/webdeface website add https://example.com

# With custom name and interval
/webdeface website add https://example.com name:"Example Website" interval:300

# High-frequency monitoring
/webdeface website add https://critical-site.com name:"Critical Infrastructure" interval:60 max-depth:1
```

**Response:**
```
✅ Website added successfully: Example Website (https://example.com)
Website ID: abc123
Execution ID: exec_xyz789
Interval: 300 seconds
```

### Remove Website

Remove a website from monitoring.

**Syntax:**
```
/webdeface website remove <WEBSITE_ID> [FLAGS]
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to remove

**Flags:**
- `force:true` - Skip confirmation (always applied in Slack)

**Required Permission:** `REMOVE_SITES` (Admin+)

**Examples:**
```slack
# Remove website
/webdeface website remove abc123

# Force removal (same behavior in Slack)
/webdeface website remove abc123 force:true
```

**Response:**
```
✅ Website removed successfully: Example Website
Website ID: abc123
```

### List Websites

List all monitored websites.

**Syntax:**
```
/webdeface website list [FLAGS]
```

**Flags:**
- `status:CHOICE` - Filter by status (`active`, `inactive`, `all`) (default: `all`)
- `format:CHOICE` - Output format (`table`, `json`) (default: `table`)

**Required Permission:** `VIEW_SITES` (Viewer+)

**Examples:**
```slack
# List all websites
/webdeface website list

# List only active websites
/webdeface website list status:active

# JSON output for integrations
/webdeface website list format:json
```

**Response:**
```
📊 Monitored Websites (3 total)

ID       Name              Status     Last Checked
abc123   Example Website   🟢 Active  2024-01-01 12:15
def456   Test Site         🔴 Inactive Never
ghi789   Important Site    🟢 Active  2024-01-01 12:10
```

### Website Status

Show detailed status for a specific website.

**Syntax:**
```
/webdeface website status <WEBSITE_ID>
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to check

**Required Permission:** `VIEW_SITES` (Viewer+)

**Examples:**
```slack
# Get website status
/webdeface website status abc123
```

**Response:**
```
📊 Website Status: Example Website

🔗 URL: https://example.com
🆔 ID: abc123
⏰ Created: 2024-01-01 10:00:00
🔄 Last Checked: 2024-01-01 12:15:00
📸 Total Snapshots: 48
🚨 Active Alerts: 0
✅ Status: Active
```

## 🔄 Monitoring Operations

Control monitoring operations for websites.

### Start Monitoring

Start monitoring operations.

**Syntax:**
```
/webdeface monitoring start [WEBSITE_ID]
```

**Arguments:**
- `WEBSITE_ID` (optional) - Start monitoring for specific website only

**Required Permission:** `CONTROL_MONITORING` (Admin+)

**Examples:**
```slack
# Start all monitoring
/webdeface monitoring start

# Start monitoring for specific website
/webdeface monitoring start abc123
```

**Response:**
```
✅ Started monitoring for 3 websites
Started: Example Website, Test Site, Important Site
```

### Stop Monitoring

Stop monitoring operations.

**Syntax:**
```
/webdeface monitoring stop [WEBSITE_ID]
```

**Arguments:**
- `WEBSITE_ID` (optional) - Stop monitoring for specific website only

**Required Permission:** `CONTROL_MONITORING` (Admin+)

**Examples:**
```slack
# Stop all monitoring
/webdeface monitoring stop

# Stop monitoring for specific website
/webdeface monitoring stop abc123
```

**Response:**
```
✅ Stopped monitoring for 3 websites
Stopped: Example Website, Test Site, Important Site
```

### Pause Monitoring

Temporarily pause monitoring for a website.

**Syntax:**
```
/webdeface monitoring pause <WEBSITE_ID> [FLAGS]
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to pause

**Flags:**
- `duration:NUMBER` - Pause duration in seconds (default: 3600)

**Required Permission:** `PAUSE_MONITORING` (Operator+)

**Examples:**
```slack
# Pause for 1 hour (default)
/webdeface monitoring pause abc123

# Pause for 30 minutes
/webdeface monitoring pause abc123 duration:1800
```

**Response:**
```
⏸️ Paused monitoring for Example Website for 3600 seconds
Resume time: 2024-01-01 13:15:00
```

### Resume Monitoring

Resume paused monitoring for a website.

**Syntax:**
```
/webdeface monitoring resume <WEBSITE_ID>
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to resume

**Required Permission:** `PAUSE_MONITORING` (Operator+)

**Examples:**
```slack
# Resume monitoring
/webdeface monitoring resume abc123
```

**Response:**
```
▶️ Resumed monitoring for Example Website
Status: Active
```

### Immediate Check

Trigger an immediate check for a website.

**Syntax:**
```
/webdeface monitoring check <WEBSITE_ID>
```

**Arguments:**
- `WEBSITE_ID` (required) - Website ID to check

**Required Permission:** `TRIGGER_CHECKS` (Operator+)

**Examples:**
```slack
# Run immediate check
/webdeface monitoring check abc123
```

**Response:**
```
🔍 Triggered immediate check for Example Website
Execution ID: exec_immediate_xyz789
Check initiated at: 2024-01-01 12:30:00
```

## 🖥️ System Management

Monitor and manage system status and health.

### System Status

Show overall system status.

**Syntax:**
```
/webdeface system status
```

**Required Permission:** `VIEW_SYSTEM` (Viewer+)

**Examples:**
```slack
# Get system status
/webdeface system status
```

**Response:**
```
🖥️ System Status

📊 Websites: 25 total (23 active, 2 inactive)
📈 Activity (24h): 1,156 checks (1,142 successful)
⚙️ Scheduler: Running (3 active jobs)
💾 Storage: Connected
⏱️ Uptime: 5d 12h 30m
```

### System Health

Show detailed health information.

**Syntax:**
```
/webdeface system health
```

**Required Permission:** `VIEW_SYSTEM` (Viewer+)

**Examples:**
```slack
# Check system health
/webdeface system health
```

**Response:**
```
🏥 System Health Score: 9.8/10

Component Status:
✅ Storage: Healthy (All operations normal)
✅ Scheduler: Healthy (All jobs running)
✅ Claude API: Healthy (Response time: 245ms)
✅ Qdrant: Healthy (Vector operations normal)

Overall Status: 🟢 Healthy
```

### System Metrics

Show system metrics and statistics.

**Syntax:**
```
/webdeface system metrics [FLAGS]
```

**Flags:**
- `range:TEXT` - Time range (`1h`, `24h`, `7d`, `30d`) (default: `24h`)
- `type:TEXT` - Metric type (`all`, `performance`, `monitoring`, `alerts`, `system`) (default: `all`)

**Required Permission:** `VIEW_METRICS` (Viewer+)

**Examples:**
```slack
# Get 24h metrics
/webdeface system metrics

# Get performance metrics for last hour
/webdeface system metrics range:1h type:performance

# Get monitoring metrics for last week
/webdeface system metrics range:7d type:monitoring
```

**Response:**
```
📊 System Metrics (24h)

🌐 Monitoring:
• Active monitors: 23/25
• Checks completed: 1,156
• Success rate: 98.5%

⚡ Performance:
• Avg response time: 2.3s
• Error rate: 0.02%
• Throughput: 2.5 checks/min

🚨 Alerts:
• Total alerts: 12
• Open alerts: 2
• Resolved: 10
```

### System Logs

View system logs with filtering.

**Syntax:**
```
/webdeface system logs [FLAGS]
```

**Flags:**
- `level:TEXT` - Filter by log level (`debug`, `info`, `warning`, `error`) (default: `info`)
- `component:TEXT` - Filter by component (`scheduler`, `scraper`, `notification`, etc.)
- `limit:NUMBER` - Number of entries to show (default: 20, max: 100)
- `since:TEXT` - Time filter (`1h`, `6h`, `1d`, `3d`) (default: `1h`)

**Required Permission:** `VIEW_LOGS` (Viewer+)

**Examples:**
```slack
# Recent logs
/webdeface system logs

# Error logs only
/webdeface system logs level:error

# Scheduler logs from last 6 hours
/webdeface system logs component:scheduler since:6h limit:50
```

**Response:**
```
📋 System Logs (last 20 entries, level: info)

2024-01-01 12:00:00 INFO [scheduler] Monitoring task scheduled
2024-01-01 12:01:00 INFO [scraper] Website check completed
2024-01-01 12:02:00 WARN [classifier] Low confidence score
2024-01-01 12:03:00 ERROR [notification] Slack rate limit hit
```

## ❓ Help System

Get help and command information.

### General Help

**Syntax:**
```
/webdeface help [COMMAND_GROUP]
```

**Examples:**
```slack
# General help
/webdeface help

# Website commands help
/webdeface help website

# Monitoring commands help
/webdeface help monitoring

# System commands help
/webdeface help system
```

### Command Listing

Get a quick reference of all available commands:

```slack
/webdeface commands
```

## 🔧 Examples & Workflows

### Initial Setup Workflow

```slack
# Check system status
/webdeface system status

# Add critical websites
/webdeface website add https://company.com name:"Company Main Site" interval:300

/webdeface website add https://blog.company.com name:"Company Blog" interval:900

/webdeface website add https://api.company.com name:"API Endpoint" interval:120

# Start monitoring
/webdeface monitoring start

# Verify everything is running
/webdeface website list status:active
```

### Daily Operations Workflow

```slack
# Morning health check
/webdeface system health

# Check active websites
/webdeface website list status:active

# Review any recent errors
/webdeface system logs level:error since:24h

# Check system metrics
/webdeface system metrics range:24h
```

### Incident Response Workflow

```slack
# Check system status during incident
/webdeface system status

# View recent error logs
/webdeface system logs level:error since:1h limit:50

# Pause monitoring if needed
/webdeface monitoring pause abc123 duration:1800

# Resume after incident resolution
/webdeface monitoring resume abc123

# Trigger immediate check to verify
/webdeface monitoring check abc123
```

### Website Management Workflow

```slack
# Add new website
/webdeface website add https://newsite.com name:"New Site" interval:600

# Check its status
/webdeface website status <new_website_id>

# List all websites to verify
/webdeface website list

# Remove website if no longer needed
/webdeface website remove <website_id>
```

## 🔍 Troubleshooting

### Common Issues

#### Command Not Recognized

**Error:** `Unknown command: <command>`
**Solution:**
- Check command spelling
- Use `/webdeface help` to see available commands
- Ensure you have the correct permissions

#### Permission Denied

**Error:** `❌ Insufficient permissions for this command`
**Solution:**
- Contact your Slack administrator to adjust your role
- Check which permissions you need using `/webdeface help <command>`

#### Website Not Found

**Error:** `Website not found: <website_id>`
**Solution:**
- Use `/webdeface website list` to get correct website IDs
- Ensure the website hasn't been removed

#### Bot Not Responding

**Issues:**
- Bot not responding in channel
- Commands timing out

**Solutions:**
1. Ensure bot is invited to the channel
2. Check bot status with administrator
3. Try commands in direct message with bot
4. Verify Slack workspace connectivity

### Getting Help

```slack
# Get command help
/webdeface help

# Check system status
/webdeface system status

# Contact administrator if issues persist
```

## 🔄 Migration from CLI

### Command Mapping

| CLI Command | Slack Command | Notes |
|-------------|---------------|-------|
| `webdeface-monitor website add URL --name "Site"` | `/webdeface website add URL name:"Site"` | Flag syntax change |
| `webdeface-monitor website list --status active` | `/webdeface website list status:active` | Same functionality |
| `webdeface-monitor monitoring start` | `/webdeface monitoring start` | Identical |
| `webdeface-monitor system status` | `/webdeface system status` | Identical |

### Flag Conversion

| CLI Format | Slack Format | Example |
|------------|--------------|---------|
| `--name "value"` | `name:"value"` | `name:"My Site"` |
| `--interval 300` | `interval:300` | `interval:300` |
| `--status active` | `status:active` | `status:active` |
| `--force` | `force:true` | `force:true` |
| `--verbose` | Not needed | Slack responses are verbose by default |

### Migration Tips

1. **Flag Syntax**: Replace `--flag value` with `flag:value`
2. **Quoted Values**: Keep quotes for multi-word values: `name:"My Website"`
3. **Boolean Flags**: Use `flag:true` instead of just `--flag`
4. **Help Commands**: Use `/webdeface help` instead of `--help`
5. **Output Format**: Slack commands automatically format output appropriately

### Example Migrations

**CLI:**
```bash
webdeface-monitor website add https://example.com --name "Example Site" --interval 300
```

**Slack:**
```slack
/webdeface website add https://example.com name:"Example Site" interval:300
```

**CLI:**
```bash
webdeface-monitor website list --status active --format json
```

**Slack:**
```slack
/webdeface website list status:active format:json
```

## 📞 Support

### Quick Reference

- **Help Command:** `/webdeface help`
- **System Status:** `/webdeface system status`
- **Command List:** `/webdeface commands`

### Contact Information

- **Slack Channel:** #webdeface-support
- **Administrator:** Contact your Slack workspace admin
- **Documentation:** This guide and `/webdeface help`

### Resources

- **Command Reference:** Use `/webdeface help <command>` for specific command help
- **Permission Issues:** Contact your administrator for role adjustments
- **System Issues:** Use `/webdeface system health` to diagnose problems

---

**Quick Help:**
```slack
/webdeface help
/webdeface help <command_group>
/webdeface system status
