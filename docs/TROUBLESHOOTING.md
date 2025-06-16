# WebDeface Monitor Troubleshooting Guide

**Version:** 1.0.0

This guide provides comprehensive troubleshooting information for common issues, error codes, diagnostic procedures, and solutions for the WebDeface Monitor system.

## 📋 Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Error Codes](#error-codes)
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Monitoring Issues](#monitoring-issues)
- [API Problems](#api-problems)
- [Integration Issues](#integration-issues)
- [Performance Problems](#performance-problems)
- [Logging & Debugging](#logging--debugging)
- [Recovery Procedures](#recovery-procedures)
- [Support & Escalation](#support--escalation)

## 🔍 Quick Diagnostics

### System Health Check

```bash
# Quick system status
webdeface-monitor system health

# Detailed system information
webdeface-monitor system status --verbose

# Check configuration
webdeface-monitor system validate-config

# Test connections
webdeface-monitor system test-connections
```

### Essential Diagnostic Commands

```bash
# Check if service is running
curl -f http://localhost:8000/health || echo "Service not responding"

# Verify environment variables
env | grep WEBDEFACE

# Check log files
tail -f ./data/webdeface.log

# Test database connection
webdeface-monitor db health

# Verify API access
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/websites
```

### Quick Status Dashboard

```bash
#!/bin/bash
echo "=== WebDeface Monitor Status ==="
echo "Service: $(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null || echo 'DOWN')"
echo "Database: $(webdeface-monitor db health --json | jq -r .status 2>/dev/null || echo 'UNKNOWN')"
echo "Active Jobs: $(webdeface-monitor monitor status --json | jq '.active_jobs // 0' 2>/dev/null || echo 'UNKNOWN')"
echo "Last Check: $(webdeface-monitor monitor status --json | jq -r '.last_check // "Never"' 2>/dev/null || echo 'UNKNOWN')"
```

## 🚨 Common Issues

### Issue: Service Won't Start

**Symptoms:**
- `webdeface-monitor api start` fails
- Connection refused errors
- Process exits immediately

**Diagnosis:**
```bash
# Check port availability
netstat -tulpn | grep :8000
lsof -i :8000

# Check configuration
webdeface-monitor system validate-config

# Check logs for startup errors
webdeface-monitor api start --debug
```

**Solutions:**
1. **Port already in use:**
   ```bash
   # Kill existing process
   kill $(lsof -t -i:8000)

   # Or use different port
   export WEBDEFACE_PORT=8001
   webdeface-monitor api start
   ```

2. **Missing environment variables:**
   ```bash
   # Check required variables
   echo $SECRET_KEY
   echo $CLAUDE_API_KEY

   # Set missing variables
   export SECRET_KEY="your-secret-key-here"
   export CLAUDE_API_KEY="your-claude-key"
   ```

3. **Database issues:**
   ```bash
   # Check database file permissions
   ls -la ./data/webdeface.db

   # Recreate database
   rm ./data/webdeface.db
   webdeface-monitor db init
   ```

### Issue: Monitoring Jobs Not Running

**Symptoms:**
- Websites not being checked
- No new scan results
- Scheduler appears inactive

**Diagnosis:**
```bash
# Check scheduler status
webdeface-monitor monitor status

# List active jobs
webdeface-monitor monitor jobs --active

# Check for errors in logs
grep -i "error\|exception" ./data/webdeface.log | tail -20
```

**Solutions:**
1. **Scheduler not started:**
   ```bash
   # Start monitoring
   webdeface-monitor monitor start

   # Verify status
   webdeface-monitor monitor status
   ```

2. **Invalid cron expressions:**
   ```bash
   # Test cron expression
   webdeface-monitor website list --json | jq '.[].interval'

   # Fix invalid intervals
   webdeface-monitor website update https://example.com --interval "*/15 * * * *"
   ```

3. **Jobs failing silently:**
   ```bash
   # Enable debug logging
   export WEBDEFACE_LOG_LEVEL=DEBUG
   webdeface-monitor monitor start

   # Check specific website
   webdeface-monitor website check https://example.com --verbose
   ```

### Issue: Classification Not Working

**Symptoms:**
- All changes classified as "unknown"
- Claude API errors
- Classification timeouts

**Diagnosis:**
```bash
# Test Claude API connection
curl -H "Authorization: Bearer $CLAUDE_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.anthropic.com/v1/messages \
     -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'

# Check classification logs
grep -i "classif" ./data/webdeface.log | tail -10

# Test manual classification
webdeface-monitor classify --text "test content" --previous "old content"
```

**Solutions:**
1. **Invalid API key:**
   ```bash
   # Verify API key format
   echo $CLAUDE_API_KEY | grep -E "^sk-ant-api03-"

   # Test with new key
   export CLAUDE_API_KEY="your-new-key"
   ```

2. **Rate limiting:**
   ```bash
   # Check rate limit status
   grep -i "rate.limit\|429" ./data/webdeface.log

   # Reduce classification frequency
   webdeface-monitor config set classification.max_requests_per_hour 100
   ```

3. **Content too large:**
   ```bash
   # Check content size limits
   webdeface-monitor config get classification.max_tokens

   # Adjust token limits
   webdeface-monitor config set classification.max_tokens 4000
   ```

### Issue: Slack Notifications Not Working

**Symptoms:**
- No Slack messages received
- Slack API errors
- Authentication failures

**Diagnosis:**
```bash
# Test Slack connection
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
     https://slack.com/api/auth.test

# Check notification logs
grep -i "slack\|notification" ./data/webdeface.log | tail -10

# Test manual notification
webdeface-monitor notify --channel "#test" --message "Test message"
```

**Solutions:**
1. **Invalid bot token:**
   ```bash
   # Verify token format
   echo $SLACK_BOT_TOKEN | grep -E "^xoxb-"

   # Test token validity
   curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        https://slack.com/api/auth.test
   ```

2. **Missing bot permissions:**
   - Go to Slack App settings
   - Add required scopes: `chat:write`, `channels:read`
   - Reinstall app to workspace

3. **Channel access issues:**
   ```bash
   # List available channels
   webdeface-monitor slack channels

   # Test specific channel
   webdeface-monitor notify --channel "#monitoring" --message "Test"
   ```

## 📝 Error Codes

### HTTP API Errors

| Code | Error | Cause | Solution |
|------|-------|-------|----------|
| 401 | Unauthorized | Missing/invalid API token | Check `Authorization: Bearer <token>` header |
| 403 | Forbidden | Insufficient permissions | Verify user role and permissions |
| 404 | Not Found | Website/resource doesn't exist | Check URL and resource ID |
| 422 | Validation Error | Invalid request data | Review request payload against API docs |
| 429 | Rate Limited | Too many requests | Implement backoff and retry logic |
| 500 | Internal Error | Server-side error | Check logs and report if persistent |

### Application Error Codes

| Code | Category | Description | Solution |
|------|----------|-------------|----------|
| WDF-001 | Configuration | Missing required environment variable | Set required environment variables |
| WDF-002 | Configuration | Invalid configuration format | Validate YAML syntax and structure |
| WDF-003 | Database | Database connection failed | Check database file and permissions |
| WDF-004 | Database | Database migration failed | Run `webdeface-monitor db migrate` |
| WDF-005 | Scraping | Website unreachable | Check URL and network connectivity |
| WDF-006 | Scraping | Request timeout | Increase timeout or check website performance |
| WDF-007 | Classification | Claude API error | Check API key and service status |
| WDF-008 | Classification | Classification timeout | Reduce content size or increase timeout |
| WDF-009 | Notification | Slack API error | Verify bot token and permissions |
| WDF-010 | Notification | Channel not found | Check channel name and bot access |
| WDF-011 | Scheduler | Job execution failed | Check job configuration and logs |
| WDF-012 | Scheduler | Concurrent job limit reached | Reduce concurrent jobs or increase limit |

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | No action needed |
| 1 | General error | Check error message and logs |
| 2 | Configuration error | Review configuration files |
| 3 | Database error | Check database connectivity |
| 4 | Network error | Verify network connectivity |
| 5 | Permission error | Check file/directory permissions |
| 6 | Resource exhaustion | Check system resources |

## 🛠️ Installation Issues

### Issue: Python Dependencies

**Problem:** Package installation failures

```bash
# Common dependency issues
pip install --verbose webdeface-monitor

# For compilation issues
sudo apt-get install build-essential python3-dev

# For cryptography issues
sudo apt-get install libffi-dev libssl-dev

# Clean install
pip uninstall webdeface-monitor
pip cache purge
pip install --no-cache-dir webdeface-monitor
```

### Issue: Docker Problems

**Problem:** Container won't start or build

```bash
# Check Docker logs
docker logs webdeface-monitor

# Rebuild with verbose output
docker build --no-cache --progress=plain -t webdeface-monitor .

# Check permissions
docker run --rm -it webdeface-monitor ls -la /app/data

# Volume mounting issues
docker run -v $(pwd)/data:/app/data webdeface-monitor system health
```

### Issue: Permission Problems

**Problem:** File/directory permission errors

```bash
# Check data directory permissions
ls -la ./data

# Fix permissions
chmod 755 ./data
chmod 644 ./data/webdeface.db

# For Docker
sudo chown -R $(id -u):$(id -g) ./data
```

## ⚙️ Configuration Problems

### Issue: Environment Variables Not Loaded

**Diagnosis:**
```bash
# Check current environment
env | grep WEBDEFACE
printenv | grep -E "(SECRET_KEY|CLAUDE_API_KEY|SLACK_)"

# Check .env file loading
cat .env
webdeface-monitor config show --env
```

**Solutions:**
```bash
# Source .env file manually
set -a && source .env && set +a

# Use explicit environment file
webdeface-monitor --env-file .env.production api start

# Set variables directly
export SECRET_KEY="your-secret-key"
export CLAUDE_API_KEY="your-claude-key"
```

### Issue: YAML Configuration Errors

**Diagnosis:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check configuration loading
webdeface-monitor config validate --config config.yaml

# Show parsed configuration
webdeface-monitor config show --config config.yaml
```

**Common YAML Issues:**
1. **Indentation errors:** Use spaces, not tabs
2. **Quotes in strings:** Quote strings with special characters
3. **Environment variable substitution:** Use `${VAR_NAME}` format
4. **Boolean values:** Use `true`/`false`, not `True`/`False`

### Issue: Configuration Precedence

**Understanding Priority:**
1. Command line arguments (highest)
2. Environment variables
3. Configuration files
4. Default values (lowest)

**Debugging:**
```bash
# Show final merged configuration
webdeface-monitor config show --merged

# Show configuration sources
webdeface-monitor config show --sources

# Override for testing
webdeface-monitor --config /dev/null api start  # Env vars and defaults only
```

## 🔍 Monitoring Issues

### Issue: Websites Not Being Monitored

**Diagnosis:**
```bash
# Check website list
webdeface-monitor website list

# Check scheduler status
webdeface-monitor monitor status

# Check individual website
webdeface-monitor website status https://example.com
```

**Solutions:**
```bash
# Add website if missing
webdeface-monitor website add https://example.com

# Fix cron expression
webdeface-monitor website update https://example.com --interval "*/15 * * * *"

# Force immediate check
webdeface-monitor website check https://example.com
```

### Issue: False Positive Alerts

**Diagnosis:**
```bash
# Check recent changes
webdeface-monitor website changes https://example.com --limit 10

# Review classification
webdeface-monitor changes list --classification suspicious --limit 5

# Check volatility settings
webdeface-monitor config get monitoring.detection.volatility_threshold
```

**Solutions:**
```bash
# Adjust similarity threshold
webdeface-monitor config set monitoring.detection.similarity_threshold 0.9

# Mark content as volatile
webdeface-monitor website update https://example.com --volatile-patterns "timestamp,date"

# Adjust classification confidence
webdeface-monitor config set classification.confidence_threshold 0.8
```

### Issue: Missing Real Defacements

**Diagnosis:**
```bash
# Check detection sensitivity
webdeface-monitor config get monitoring.detection.similarity_threshold

# Review recent scans
webdeface-monitor scans list --website https://example.com --limit 5

# Check classification accuracy
webdeface-monitor changes list --manual-review
```

**Solutions:**
```bash
# Increase sensitivity
webdeface-monitor config set monitoring.detection.similarity_threshold 0.7

# Reduce minimum change size
webdeface-monitor config set monitoring.detection.min_change_size 20

# Enable aggressive detection
webdeface-monitor website update https://example.com --sensitivity high
```

## 🌐 API Problems

### Issue: API Authentication Failures

**Diagnosis:**
```bash
# Test API endpoint
curl http://localhost:8000/health

# Test authentication
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/websites

# Check token validity
webdeface-monitor auth verify-token YOUR_TOKEN
```

**Solutions:**
```bash
# Generate new token
webdeface-monitor auth create-token --user admin

# Check token format
echo "YOUR_TOKEN" | base64 -d | jq .

# Update secret key
export SECRET_KEY="new-secret-key"
webdeface-monitor api restart
```

### Issue: API Performance Problems

**Diagnosis:**
```bash
# Check response times
time curl http://localhost:8000/api/v1/websites

# Monitor resource usage
top -p $(pgrep -f webdeface-monitor)

# Check database performance
webdeface-monitor db stats
```

**Solutions:**
```bash
# Enable caching
webdeface-monitor config set performance.caching.enabled true

# Increase workers
webdeface-monitor api start --workers 4

# Optimize database
webdeface-monitor db vacuum
webdeface-monitor db analyze
```

### Issue: CORS Problems

**Problem:** Browser requests blocked by CORS

**Solution:**
```yaml
# config.yaml
api:
  cors:
    allow_origins: ["https://your-frontend-domain.com"]
    allow_credentials: true
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["*"]
```

## 🔗 Integration Issues

### Issue: Slack Integration Problems

**Diagnosis:**
```bash
# Test Slack API
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
     https://slack.com/api/auth.test

# Check bot permissions
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
     https://slack.com/api/users.info?user=@me

# Test channel access
webdeface-monitor slack test-channel "#monitoring"
```

**Solutions:**
1. **Bot not in channel:**
   - Invite bot to channel: `/invite @webdeface-bot`
   - Or use public channels

2. **Missing scopes:**
   - Add required OAuth scopes in Slack app settings
   - Reinstall app to workspace

3. **Socket mode issues:**
   ```yaml
   notifications:
     slack:
       socket_mode: false  # Use HTTP mode instead
   ```

### Issue: Qdrant Vector Database Problems

**Diagnosis:**
```bash
# Test Qdrant connection
curl $QDRANT_URL/collections

# Check collection status
webdeface-monitor vector status

# Test vector operations
webdeface-monitor vector search "test query"
```

**Solutions:**
```bash
# Recreate collection
webdeface-monitor vector recreate-collection

# Check Qdrant service
docker logs qdrant

# Use local fallback
webdeface-monitor config set storage.qdrant.enabled false
```

## ⚡ Performance Problems

### Issue: High Memory Usage

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep webdeface-monitor
free -h

# Monitor memory over time
watch -n 5 'ps aux | grep webdeface-monitor'

# Check for memory leaks
webdeface-monitor system memory-profile
```

**Solutions:**
```bash
# Limit memory usage
webdeface-monitor config set performance.resources.max_memory_mb 512

# Reduce concurrent jobs
webdeface-monitor config set global.max_concurrent_jobs 2

# Enable garbage collection
webdeface-monitor config set performance.gc_threshold 100
```

### Issue: Slow Website Checks

**Diagnosis:**
```bash
# Time individual check
time webdeface-monitor website check https://example.com

# Check network latency
ping example.com
curl -w "@curl-format.txt" -o /dev/null https://example.com

# Profile check operation
webdeface-monitor website check https://example.com --profile
```

**Solutions:**
```bash
# Increase timeout
webdeface-monitor website update https://example.com --timeout 60

# Disable images/JS for static sites
webdeface-monitor website update https://example.com --disable-images --disable-js

# Use multiple workers
webdeface-monitor config set performance.concurrency.max_workers 6
```

### Issue: Database Performance

**Diagnosis:**
```bash
# Check database size
ls -lh ./data/webdeface.db

# Check query performance
webdeface-monitor db analyze --verbose

# Monitor database operations
webdeface-monitor db monitor
```

**Solutions:**
```bash
# Vacuum database
webdeface-monitor db vacuum

# Clean old data
webdeface-monitor db cleanup --older-than 30d

# Optimize settings
webdeface-monitor config set storage.sqlite.cache_size 20000
```

## 📊 Logging & Debugging

### Enable Debug Logging

```bash
# Temporary debug mode
export WEBDEFACE_LOG_LEVEL=DEBUG
webdeface-monitor api start

# Persistent debug configuration
webdeface-monitor config set logging.level DEBUG
```

### Structured Logging Analysis

```bash
# Filter logs by component
grep '"logger_name":"webdeface.scraper"' ./data/webdeface.log | jq .

# Find errors
grep '"level":"ERROR"' ./data/webdeface.log | jq .

# Track specific website
grep '"website":"https://example.com"' ./data/webdeface.log | jq .

# Performance analysis
grep '"duration_ms"' ./data/webdeface.log | jq .duration_ms | sort -n
```

### Log Analysis Tools

```bash
# Real-time log monitoring
tail -f ./data/webdeface.log | jq .

# Error summary
grep ERROR ./data/webdeface.log | cut -d'"' -f8 | sort | uniq -c

# Performance trends
grep duration_ms ./data/webdeface.log | jq .duration_ms | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "ms"}'
```

### Debug Mode Features

```bash
# Start with debug mode
webdeface-monitor --debug api start

# Enable profiling
webdeface-monitor --profile website check https://example.com

# Verbose output
webdeface-monitor --verbose monitor status
```

## 🔄 Recovery Procedures

### Database Recovery

```bash
# Backup current database
cp ./data/webdeface.db ./data/webdeface.db.backup

# Check database integrity
webdeface-monitor db check

# Repair database if needed
webdeface-monitor db repair

# Recreate from scratch if corrupted
rm ./data/webdeface.db
webdeface-monitor db init
```

### Configuration Recovery

```bash
# Reset to defaults
webdeface-monitor config reset

# Restore from backup
cp config.yaml.backup config.yaml

# Validate after restore
webdeface-monitor config validate
```

### Service Recovery

```bash
# Graceful restart
webdeface-monitor api restart

# Force restart
pkill -f webdeface-monitor
webdeface-monitor api start

# Reset state
webdeface-monitor monitor stop
webdeface-monitor monitor reset
webdeface-monitor monitor start
```

### Data Recovery

```bash
# Restore from backup
webdeface-monitor backup restore --file ./data/backups/latest.tar.gz

# Export data
webdeface-monitor export --format json --output backup.json

# Import data
webdeface-monitor import --file backup.json
```

## 📞 Support & Escalation

### Before Contacting Support

1. **Gather diagnostic information:**
   ```bash
   webdeface-monitor system diagnostic-report > diagnostic.txt
   ```

2. **Check logs for errors:**
   ```bash
   grep -i "error\|exception\|failed" ./data/webdeface.log | tail -20
   ```

3. **Verify configuration:**
   ```bash
   webdeface-monitor config validate
   webdeface-monitor system health
   ```

### Support Channels

- **GitHub Issues:** [webdeface-monitor/issues](https://github.com/your-org/webdeface-monitor/issues)
- **Email:** support@your-org.com
- **Slack Community:** #webdeface-support
- **Documentation:** [docs.webdeface-monitor.com](https://docs.webdeface-monitor.com)

### Information to Include

When reporting issues, please include:

1. **System information:**
   ```bash
   webdeface-monitor system info
   ```

2. **Error logs:**
   ```bash
   tail -50 ./data/webdeface.log
   ```

3. **Configuration (sanitized):**
   ```bash
   webdeface-monitor config show --sanitize
   ```

4. **Steps to reproduce the issue**

5. **Expected vs actual behavior**

### Emergency Procedures

**Service Down:**
1. Check service status: `webdeface-monitor system health`
2. Review recent logs: `tail -100 ./data/webdeface.log`
3. Restart service: `webdeface-monitor api restart`
4. If persistent, contact support with diagnostic report

**Security Incident:**
1. Stop monitoring: `webdeface-monitor monitor stop`
2. Preserve logs: `cp ./data/webdeface.log incident-$(date +%s).log`
3. Contact security team immediately
4. Follow incident response procedures

**Data Corruption:**
1. Stop all operations: `webdeface-monitor stop`
2. Backup current state: `cp -r ./data ./data-corrupted-$(date +%s)`
3. Restore from backup: `webdeface-monitor backup restore --latest`
4. Validate restoration: `webdeface-monitor db check`

---

## 🔧 Quick Reference

### Essential Commands
```bash
# Health check
webdeface-monitor system health

# View logs
tail -f ./data/webdeface.log

# Restart service
webdeface-monitor api restart

# Check configuration
webdeface-monitor config validate

# Manual website check
webdeface-monitor website check https://example.com
```

### Emergency Contacts
- **Technical Support:** support@your-org.com
- **Security Team:** security@your-org.com
- **On-call Engineer:** +1-555-ONCALL

**Remember:** When in doubt, check the logs first!
