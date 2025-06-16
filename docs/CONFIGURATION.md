# WebDeface Monitor Configuration Reference

**Version:** 1.0.0

This document provides comprehensive configuration documentation for the WebDeface Monitor, including all available settings, environment variables, and configuration examples for different deployment scenarios.

## 📋 Table of Contents

- [Configuration Overview](#configuration-overview)
- [Environment Variables](#environment-variables)
- [YAML Configuration](#yaml-configuration)
- [Security Settings](#security-settings)
- [Monitoring Configuration](#monitoring-configuration)
- [Integration Settings](#integration-settings)
- [Performance Tuning](#performance-tuning)
- [Logging Configuration](#logging-configuration)
- [Deployment Configurations](#deployment-configurations)
- [Validation & Testing](#validation--testing)

## 📖 Configuration Overview

WebDeface Monitor uses a multi-layered configuration system:

1. **Default Values** - Built-in defaults
2. **Configuration Files** - YAML files with structured settings
3. **Environment Variables** - Override any configuration value
4. **Command Line Options** - Runtime overrides

### Configuration Priority

Higher priority overrides lower priority:

```
CLI Options > Environment Variables > Config Files > Defaults
```

### Configuration Files

**Search Order:**
1. `--config` parameter path
2. `WEBDEFACE_CONFIG` environment variable
3. `./config.yaml` (current directory)
4. `~/.webdeface/config.yaml` (user directory)
5. `/etc/webdeface/config.yaml` (system directory)

## 🔧 Environment Variables

### Core Application Settings

```bash
# Application Environment
WEBDEFACE_ENV=production                    # Environment (development, production)
WEBDEFACE_DEBUG=false                       # Enable debug mode
WEBDEFACE_LOG_LEVEL=INFO                    # Log level (DEBUG, INFO, WARNING, ERROR)
WEBDEFACE_DATA_DIR=./data                   # Data storage directory
WEBDEFACE_CONFIG=/path/to/config.yaml      # Configuration file path

# API Server Settings
WEBDEFACE_HOST=0.0.0.0                      # API server host
WEBDEFACE_PORT=8000                         # API server port
WEBDEFACE_WORKERS=1                         # Number of worker processes
```

### Authentication & Security

```bash
# API Authentication
SECRET_KEY=your-secret-key-here             # JWT signing secret (REQUIRED)
ACCESS_TOKEN_EXPIRE_MINUTES=30              # Token expiration time
ALGORITHM=HS256                             # JWT algorithm

# API Keys (REQUIRED)
CLAUDE_API_KEY=sk-ant-api03-xxxxx          # Anthropic Claude API key
SLACK_BOT_TOKEN=xoxb-xxxxx                 # Slack bot token
SLACK_APP_TOKEN=xapp-xxxxx                 # Slack app token (for Socket Mode)
SLACK_SIGNING_SECRET=xxxxx                 # Slack signing secret

# Optional Integrations
QDRANT_URL=http://localhost:6333           # Qdrant vector database URL
QDRANT_API_KEY=xxxxx                       # Qdrant API key (if required)
QDRANT_TIMEOUT=30                          # Qdrant request timeout
```

### Database & Storage

```bash
# SQLite Configuration
DATABASE_URL=sqlite:///./data/webdeface.db  # Database URL
DATABASE_POOL_SIZE=5                        # Connection pool size
DATABASE_TIMEOUT=30                         # Query timeout seconds

# File Storage
BACKUP_ENABLED=true                         # Enable automatic backups
BACKUP_INTERVAL_HOURS=24                    # Backup interval
BACKUP_RETENTION_DAYS=30                    # Backup retention period
```

### Monitoring & Alerting

```bash
# Monitoring Defaults
DEFAULT_CHECK_INTERVAL=900                  # Default check interval (seconds)
MAX_CONCURRENT_JOBS=4                       # Maximum parallel monitoring jobs
JOB_TIMEOUT=120                            # Job execution timeout (seconds)
RETRY_ATTEMPTS=3                           # Number of retry attempts
RETRY_DELAY=5                              # Delay between retries (seconds)

# Alert Configuration
ALERT_COOLDOWN_MINUTES=60                  # Minimum time between duplicate alerts
MAX_ALERTS_PER_HOUR=10                     # Rate limiting for alerts
```

### Performance & Scaling

```bash
# Resource Limits
MAX_MEMORY_MB=512                          # Maximum memory usage
MAX_CPU_PERCENT=80                         # CPU usage threshold
MAX_DISK_USAGE_PERCENT=85                  # Disk usage threshold

# Browser Configuration
BROWSER_POOL_SIZE=2                        # Number of browser instances
BROWSER_TIMEOUT=30                         # Browser operation timeout
BROWSER_WAIT_TIMEOUT=10                    # Page load timeout
```

## 📝 YAML Configuration

### Complete Configuration Example

```yaml
# Global application settings
global:
  environment: "production"
  debug: false
  data_dir: "./data"
  timezone: "UTC"

  # Default monitoring settings
  default_interval: "*/15 * * * *"         # Every 15 minutes
  keep_scans: 50                           # Number of scans to retain
  max_concurrent_jobs: 4                   # Parallel job limit
  job_timeout_seconds: 120                 # Job execution timeout

  # Alert routing configuration
  alert:
    site_down: ["#ops-alerts", "#monitoring"]
    benign_change: []                      # No alerts for benign changes
    defacement: ["#security-alerts", "#ops-alerts", "@security-team"]
    suspicious: ["#security-review"]

    # Alert rate limiting
    cooldown_minutes: 60                   # Minimum time between duplicate alerts
    max_per_hour: 10                       # Rate limit for alerts

    # Notification preferences
    include_diff: true                     # Include content diff in alerts
    include_screenshot: false              # Include screenshots (requires storage)
    max_diff_length: 500                   # Maximum diff characters to include

# API server configuration
api:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  reload: false                            # Auto-reload on code changes (dev only)

  # Security settings
  cors:
    allow_origins: ["*"]                   # CORS allowed origins
    allow_credentials: true
    allow_methods: ["*"]
    allow_headers: ["*"]

  # Rate limiting
  rate_limit:
    requests_per_minute: 60
    requests_per_hour: 1000
    burst_size: 10

# Authentication configuration
auth:
  secret_key: "${SECRET_KEY}"              # Use environment variable
  algorithm: "HS256"
  access_token_expire_minutes: 30

  # User management (simple token-based)
  users:
    - id: "admin"
      username: "admin"
      role: "admin"
      permissions: ["read", "write", "admin"]
      token: "${ADMIN_API_TOKEN}"
    - id: "readonly"
      username: "readonly"
      role: "user"
      permissions: ["read"]
      token: "${READONLY_API_TOKEN}"

# Monitoring engine configuration
monitoring:
  # Scraping settings
  scraping:
    timeout_seconds: 30                    # HTTP request timeout
    retry_attempts: 3                      # Number of retries
    retry_delay_seconds: 5                 # Delay between retries
    max_content_size_mb: 10               # Maximum page size to process

    # User agent rotation
    user_agents:
      - "Mozilla/5.0 (compatible; WebdefaceBot/1.0; +https://example.com/bot)"
      - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Content filtering
    ignore_patterns:
      - "<!--.*?-->"                       # HTML comments
      - "\\s+"                             # Multiple whitespace
      - "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}" # Timestamps

    # Browser settings
    browser:
      headless: true
      disable_images: false                # Set to true to improve performance
      disable_javascript: false           # Set to true for static sites only
      viewport:
        width: 1280
        height: 720

  # Change detection settings
  detection:
    similarity_threshold: 0.8              # Minimum similarity to consider unchanged
    volatility_threshold: 0.7              # Mark chunks as volatile if they change this often
    min_change_size: 50                    # Minimum change size (characters) to trigger alert

    # Hash algorithm settings
    hash_algorithm: "blake3"               # blake3, sha256, md5
    chunk_size: 1000                       # Text chunk size for hashing

  # Classification settings
  classification:
    provider: "claude"                     # claude, openai, local
    model: "claude-3-haiku-20240307"      # Model to use
    confidence_threshold: 0.7              # Minimum confidence for classification
    max_tokens: 8000                       # Maximum tokens to send to classifier
    context_chunks: 5                      # Number of context chunks to include

    # Claude-specific settings
    claude:
      api_key: "${CLAUDE_API_KEY}"
      base_url: "https://api.anthropic.com"
      timeout_seconds: 60
      max_retries: 3

    # Classification prompts
    prompts:
      system: |
        You are a security classifier that analyzes website changes to detect defacement.
        Classify changes as: benign, suspicious, or defacement.
        Consider context, content type, and severity when classifying.

      user_template: |
        Website: {website_url}

        Previous content context:
        {context_chunks}

        Changed content:
        {changed_content}

        Classify this change and explain your reasoning.

# Storage configuration
storage:
  # SQLite settings
  sqlite:
    path: "./data/webdeface.db"
    timeout: 30
    check_same_thread: false
    pool_size: 5

    # Database maintenance
    vacuum_interval_hours: 24              # Regular database optimization
    analyze_interval_hours: 6              # Update statistics

  # Qdrant vector database
  qdrant:
    url: "${QDRANT_URL:-http://localhost:6333}"
    api_key: "${QDRANT_API_KEY:-}"
    timeout: 30
    collection: "website_content"
    vector_size: 384                       # Depends on embedding model
    distance: "Cosine"                     # Cosine, Dot, Euclid

    # Collection settings
    replication_factor: 1
    write_consistency_factor: 1

  # Backup configuration
  backup:
    enabled: true
    interval_hours: 24
    retention_days: 30
    compression: true
    location: "./data/backups"

# Notification configuration
notifications:
  # Slack integration
  slack:
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
    signing_secret: "${SLACK_SIGNING_SECRET}"
    socket_mode: false                     # Use HTTP mode by default

    # Message formatting
    formatting:
      use_blocks: true                     # Use rich Block Kit formatting
      include_images: false                # Include screenshots in messages
      max_message_length: 3000             # Maximum message length

    # Channel mapping
    channels:
      default: "#monitoring"
      alerts: "#alerts"
      system: "#system-alerts"

  # Email notifications (optional)
  email:
    enabled: false
    smtp_host: "smtp.example.com"
    smtp_port: 587
    username: "${EMAIL_USERNAME}"
    password: "${EMAIL_PASSWORD}"
    from_email: "monitoring@example.com"

    # Email templates
    templates:
      defacement: "templates/defacement_alert.html"
      site_down: "templates/site_down_alert.html"

  # Webhook notifications
  webhooks:
    enabled: false
    endpoints:
      - url: "https://api.example.com/webhooks/alerts"
        events: ["defacement", "site_down"]
        headers:
          Authorization: "Bearer ${WEBHOOK_TOKEN}"
        timeout: 10
        retry_attempts: 3

# Logging configuration
logging:
  level: "INFO"                           # DEBUG, INFO, WARNING, ERROR
  format: "structured"                    # structured, plain
  output: "console"                       # console, file, both

  # File logging
  file:
    path: "./data/webdeface.log"
    max_size_mb: 100
    backup_count: 5
    rotation: "time"                      # time, size

  # Structured logging
  structured:
    include_timestamp: true
    include_level: true
    include_caller: true
    json_format: true

  # Component-specific log levels
  components:
    "webdeface.scraper": "INFO"
    "webdeface.classifier": "INFO"
    "webdeface.scheduler": "INFO"
    "webdeface.api": "WARNING"

# Scheduler configuration
scheduler:
  type: "asyncio"                         # asyncio, background
  timezone: "UTC"

  # Job settings
  job_defaults:
    misfire_grace_time: 30                # Seconds to allow late execution
    coalesce: true                        # Skip overlapping executions
    max_instances: 1                      # Maximum concurrent instances

  # Thread pool settings
  thread_pool:
    max_workers: 4                        # Maximum worker threads

  # Job store settings
  job_store:
    type: "memory"                        # memory, sqlalchemy
    url: "${DATABASE_URL}"                # For SQLAlchemy job store

# Website-specific configurations
sites:
  - url: "https://example.com"
    name: "Example Website"
    description: "Main company website"

    # Monitoring settings
    interval: "*/10 * * * *"              # Every 10 minutes
    timeout: 30
    max_depth: 2
    priority: "high"                      # high, medium, low

    # Site-specific settings
    settings:
      ignore_dynamic_content: true
      custom_headers:
        User-Agent: "Custom Bot 1.0"
      cookies:
        session: "abc123"

    # Alert overrides
    alerts:
      defacement: ["#critical-alerts", "@security-lead"]
      site_down: ["#ops-alerts"]

  - url: "https://blog.example.com"
    name: "Company Blog"
    interval: "0 */2 * * *"               # Every 2 hours
    max_depth: 1
    priority: "medium"

    settings:
      ignore_dynamic_content: false      # Blog content changes frequently

  - url: "https://api.example.com/health"
    name: "API Health Check"
    interval: "*/5 * * * *"               # Every 5 minutes
    max_depth: 0                          # Single page only
    priority: "critical"

    settings:
      response_type: "json"               # Expect JSON response
      check_json_keys: ["status", "timestamp"]

# Development and testing settings
development:
  # Mock external services
  mock_claude: false                      # Use mock responses instead of real API
  mock_slack: false                       # Use mock Slack client
  mock_qdrant: false                      # Use in-memory vector store

  # Development tools
  hot_reload: true                        # Auto-reload on code changes
  debug_toolbar: true                     # Enable debug toolbar
  profiling: false                        # Enable performance profiling

  # Test data
  create_test_websites: false             # Create test websites on startup
  test_website_count: 5                   # Number of test websites to create

# Production optimizations
production:
  # Performance settings
  enable_compression: true                # Enable response compression
  enable_caching: true                    # Enable caching where appropriate
  preload_models: true                    # Preload ML models on startup

  # Security hardening
  hide_error_details: true                # Hide detailed error messages
  enable_csrf_protection: true            # Enable CSRF protection
  enforce_https: true                     # Redirect HTTP to HTTPS

  # Monitoring
  health_check_interval: 60               # Health check interval (seconds)
  metrics_collection: true                # Enable metrics collection
  performance_monitoring: true            # Enable performance monitoring
```

## 🔒 Security Settings

### Essential Security Configuration

```yaml
# Minimal security configuration
auth:
  secret_key: "${SECRET_KEY}"             # MUST be set and strong
  algorithm: "HS256"
  access_token_expire_minutes: 30

api:
  cors:
    allow_origins: ["https://your-domain.com"]  # Restrict origins in production
    allow_credentials: true

production:
  hide_error_details: true                # Don't expose stack traces
  enforce_https: true                     # Require HTTPS
  enable_csrf_protection: true            # Enable CSRF protection
```

### Advanced Security Configuration

```yaml
security:
  # Rate limiting
  rate_limiting:
    global:
      requests_per_minute: 100
      requests_per_hour: 1000
    api:
      requests_per_minute: 60
      burst_size: 10
    alerts:
      max_per_hour: 20

  # Content security
  content_security:
    max_request_size_mb: 10
    allowed_file_types: [".yaml", ".json", ".txt"]
    scan_uploads: true

  # Access control
  access_control:
    require_api_key: true
    allow_anonymous_health_check: true
    session_timeout_minutes: 60

    # IP restrictions
    allowed_ips: ["10.0.0.0/8", "192.168.0.0/16"]
    blocked_ips: []

  # Audit logging
  audit:
    enabled: true
    log_level: "INFO"
    include_request_body: false           # For privacy
    include_response_body: false
    retention_days: 90
```

## 📊 Monitoring Configuration

### Basic Monitoring Setup

```yaml
monitoring:
  # Global defaults
  default_interval: "*/15 * * * *"
  timeout_seconds: 30
  retry_attempts: 3

  # Detection settings
  detection:
    similarity_threshold: 0.8
    min_change_size: 50

  # Classification
  classification:
    confidence_threshold: 0.7
    max_tokens: 4000
```

### Advanced Monitoring Configuration

```yaml
monitoring:
  # Performance optimizations
  performance:
    concurrent_jobs: 4
    job_timeout: 120
    batch_size: 10

  # Content analysis
  content_analysis:
    extract_text: true
    extract_links: true
    extract_images: false
    analyze_structure: true

    # Content filtering
    filters:
      min_content_length: 100
      max_content_length: 1000000
      ignore_binary: true
      ignore_scripts: true

  # Change detection algorithms
  change_detection:
    algorithms: ["hash", "similarity", "structure"]
    hash_algorithm: "blake3"
    similarity_algorithm: "cosine"

    # Thresholds
    thresholds:
      minor_change: 0.1
      major_change: 0.3
      critical_change: 0.5

  # Site-specific overrides
  site_overrides:
    "example.com":
      interval: "*/5 * * * *"
      sensitivity: "high"
    "blog.example.com":
      ignore_dynamic_content: true
      check_frequency: "low"
```

## 🔗 Integration Settings

### Slack Integration

```yaml
notifications:
  slack:
    # Authentication
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
    signing_secret: "${SLACK_SIGNING_SECRET}"

    # Connection settings
    socket_mode: false
    timeout: 30
    retry_attempts: 3

    # Message formatting
    formatting:
      use_blocks: true
      include_diff: true
      max_diff_length: 500
      use_threads: true

    # Channel routing
    routing:
      default_channel: "#monitoring"
      alert_channels:
        defacement: ["#security", "#ops"]
        site_down: ["#ops"]
        suspicious: ["#security-review"]

    # Mention settings
    mentions:
      on_critical: ["@security-team", "@ops-lead"]
      on_site_down: ["@ops-team"]

    # Rate limiting
    rate_limit:
      messages_per_minute: 10
      burst_size: 5
```

### Claude AI Integration

```yaml
classification:
  claude:
    # API settings
    api_key: "${CLAUDE_API_KEY}"
    base_url: "https://api.anthropic.com"
    model: "claude-3-haiku-20240307"

    # Request settings
    timeout: 60
    max_retries: 3
    retry_delay: 2

    # Usage limits
    max_tokens_per_request: 8000
    max_requests_per_hour: 1000

    # Custom prompts
    prompts:
      system_prompt: |
        You are an expert security analyst specializing in web defacement detection.
        Analyze website changes and classify them as benign, suspicious, or defacement.

      classification_prompt: |
        Website: {url}
        Previous content: {previous_content}
        Current content: {current_content}

        Classify this change and provide reasoning.
```

### Qdrant Vector Database

```yaml
storage:
  qdrant:
    # Connection
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    timeout: 30

    # Collection settings
    collection: "website_embeddings"
    vector_size: 384
    distance: "Cosine"

    # Performance settings
    shard_number: 1
    replication_factor: 1
    write_consistency_factor: 1

    # Indexing
    hnsw_config:
      m: 16
      ef_construct: 100
      full_scan_threshold: 10000

    # Optimization
    optimizer_config:
      deleted_threshold: 0.2
      vacuum_min_vector_number: 1000
      default_segment_number: 2
```

## ⚡ Performance Tuning

### Resource Optimization

```yaml
performance:
  # CPU and memory limits
  resources:
    max_memory_mb: 1024
    max_cpu_percent: 80

  # Concurrency settings
  concurrency:
    max_workers: 4
    max_concurrent_requests: 20
    queue_size: 100

  # Caching
  caching:
    enabled: true
    ttl_seconds: 300
    max_size_mb: 100

    # Cache strategies
    strategies:
      content_hash: 3600        # Cache content hashes for 1 hour
      classification: 1800      # Cache classifications for 30 minutes
      website_metadata: 600     # Cache metadata for 10 minutes

  # Database optimization
  database:
    connection_pool_size: 5
    query_timeout: 30
    batch_size: 100

    # SQLite specific
    sqlite:
      journal_mode: "WAL"
      synchronous: "NORMAL"
      cache_size: 10000
      temp_store: "MEMORY"
```

### Network Optimization

```yaml
network:
  # Connection settings
  connection:
    timeout: 30
    connect_timeout: 10
    read_timeout: 30
    pool_connections: 10
    pool_maxsize: 20

  # Retry configuration
  retry:
    total: 3
    backoff_factor: 0.3
    status_forcelist: [500, 502, 503, 504]

  # Compression
  compression:
    enabled: true
    level: 6
    min_size: 1024
```

## 📊 Logging Configuration

### Basic Logging Setup

```yaml
logging:
  level: "INFO"
  format: "structured"
  output: "console"

  components:
    "webdeface.api": "WARNING"
    "webdeface.scraper": "INFO"
    "webdeface.classifier": "INFO"
```

### Advanced Logging Configuration

```yaml
logging:
  # Global settings
  level: "INFO"
  format: "structured"
  output: "both"

  # Console logging
  console:
    enabled: true
    format: "colored"
    level: "INFO"

  # File logging
  file:
    enabled: true
    path: "./data/logs/webdeface.log"
    level: "DEBUG"
    max_size_mb: 100
    backup_count: 10
    rotation: "time"
    when: "midnight"

  # Structured logging
  structured:
    format: "json"
    include_fields:
      - timestamp
      - level
      - logger_name
      - message
      - module
      - function
      - line_number

  # Component-specific settings
  components:
    "webdeface.api": "WARNING"
    "webdeface.scraper": "INFO"
    "webdeface.classifier": "INFO"
    "webdeface.scheduler": "INFO"
    "webdeface.storage": "WARNING"
    "webdeface.notifications": "INFO"
    "httpx": "WARNING"
    "uvicorn": "INFO"

  # Log filtering
  filters:
    - name: "sensitive_data"
      pattern: "(password|token|key).*=.*"
      replacement: "$1=***"
    - name: "urls"
      pattern: "https?://[\\w.-]+/[\\w.-]*"
      replacement: "https://***"

  # External log shipping
  shipping:
    enabled: false
    endpoint: "https://logs.example.com/api/logs"
    api_key: "${LOG_SHIPPING_API_KEY}"
    batch_size: 100
    flush_interval: 10
```

## 🚀 Deployment Configurations

### Development Configuration

```yaml
global:
  environment: "development"
  debug: true

api:
  host: "127.0.0.1"
  port: 8000
  reload: true

logging:
  level: "DEBUG"
  output: "console"

development:
  hot_reload: true
  debug_toolbar: true
  create_test_websites: true
```

### Production Configuration

```yaml
global:
  environment: "production"
  debug: false

api:
  host: "0.0.0.0"
  port: 8000
  workers: 2

security:
  rate_limiting:
    enabled: true
  access_control:
    require_api_key: true

production:
  hide_error_details: true
  enforce_https: true
  enable_compression: true
  metrics_collection: true

logging:
  level: "INFO"
  output: "file"
  file:
    path: "/var/log/webdeface/app.log"
```

### Docker Configuration

```yaml
# Docker-optimized configuration
global:
  data_dir: "/app/data"

storage:
  sqlite:
    path: "/app/data/webdeface.db"

logging:
  output: "console"
  structured:
    json_format: true

# Health check settings
health:
  enabled: true
  endpoint: "/health"
  timeout: 5
```

### High Availability Configuration

```yaml
# HA configuration
global:
  max_concurrent_jobs: 8

api:
  workers: 4

storage:
  qdrant:
    replication_factor: 2

scheduler:
  job_store:
    type: "sqlalchemy"
    url: "postgresql://user:pass@db:5432/webdeface"

notifications:
  slack:
    retry_attempts: 5
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout: 60
```

## ✅ Validation & Testing

### Configuration Validation

```bash
# Validate configuration
webdeface-monitor --config config.yaml system health

# Test configuration syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check environment variables
webdeface-monitor --debug system status
```

### Environment Variable Testing

```bash
#!/bin/bash
# Test essential environment variables

required_vars=(
    "SECRET_KEY"
    "CLAUDE_API_KEY"
    "SLACK_BOT_TOKEN"
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

echo "✅ All required environment variables are set"
```

### Configuration Templates

**Minimal Production Config:**
```yaml
global:
  environment: "production"
  default_interval: "*/15 * * * *"
  alert:
    defacement: ["#security-alerts"]
    site_down: ["#ops-alerts"]

api:
  host: "0.0.0.0"
  port: 8000

auth:
  secret_key: "${SECRET_KEY}"

monitoring:
  classification:
    claude:
      api_key: "${CLAUDE_API_KEY}"

notifications:
  slack:
    bot_token: "${SLACK_BOT_TOKEN}"
    signing_secret: "${SLACK_SIGNING_SECRET}"

logging:
  level: "INFO"
  output: "file"
```

**Development Config:**
```yaml
global:
  environment: "development"
  debug: true

api:
  reload: true

logging:
  level: "DEBUG"
  output: "console"

development:
  hot_reload: true
  create_test_websites: true
```

---

## 📞 Support

- **Configuration Issues:** [GitHub Issues](https://github.com/your-org/webdeface-monitor/issues)
- **Documentation:** [Configuration Guide](docs/CONFIGURATION.md)
- **Email:** config-support@your-org.com

**Quick Validation:**
```bash
webdeface-monitor --config your-config.yaml system health
