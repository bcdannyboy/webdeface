# Web Defacement Monitor

**AI-Powered Web Defacement Detection and Alerting System**

A sophisticated monitoring system that detects, classifies, and alerts on website content modifications using advanced AI classification, vector similarity analysis, and real-time Slack-based team collaboration.

## 🚀 Features

### Core Capabilities
- **🤖 AI-Powered Detection** - Claude AI classifies changes as benign, malicious, or suspicious
- **🕷️ JavaScript-Aware Scraping** - Playwright renders dynamic content for accurate monitoring
- **⚡ Real-Time Alerts** - Instant Slack notifications with detailed change analysis
- **🔍 Vector Similarity Analysis** - Qdrant-powered semantic change detection
- **📊 Comprehensive Monitoring** - Multi-site monitoring with customizable intervals
- **🐳 Container-Ready** - Docker deployment with production-grade configuration

### Advanced Features
- **📱 Slack-First Interface** - Native slash commands for team collaboration
- **🎛️ Multiple Interfaces** - Slack commands, REST API, and legacy CLI
- **🔐 Enterprise Security** - Role-based permissions and audit logging
- **📈 Rich Analytics** - Metrics, health monitoring, and performance insights
- **🔄 Intelligent Scheduling** - Cron-based monitoring with smart retry logic
- **🎯 Smart Filtering** - Volatility detection ignores dynamic content

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Slack Commands](#-slack-commands)
- [CLI Reference](#-cli-reference)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Architecture](#-architecture)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

## ⚡ Quick Start

### Slack Commands (Recommended)

If WebDeface Monitor is already deployed in your Slack workspace:

```slack
# Check system status
/webdeface system status

# Add your first website
/webdeface website add https://example.com name:"Example Site"

# List monitored websites
/webdeface website list

# Start monitoring
/webdeface monitoring start
```

### Docker Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/webdeface-monitor.git
cd webdeface-monitor

# Configure environment
cp .env.example .env
cp config.example.yaml config.yaml

# Edit configuration files with your API keys and settings
# .env - API tokens and secrets (including Slack bot tokens)
# config.yaml - monitoring configuration

# Start with Docker Compose
docker-compose up -d

# Add your first website via Slack
/webdeface website add https://example.com name:"Example Site"

# Or use the API/CLI for initial setup
docker exec webdeface-monitor webdeface-monitor website add https://example.com
```

### Local Development

```bash
# Install dependencies
pip install -e .

# Install browser dependencies
playwright install --with-deps

# Configure environment
cp .env.example .env
cp config.example.yaml config.yaml

# Start the API server (enables Slack commands)
webdeface-api

# Or use the legacy CLI
webdeface-monitor --help
```

### Slack Bot Setup

If you're setting up the bot for your team:

```bash
# Install dependencies
pip install -e .

# Install browser dependencies
playwright install --with-deps

# Configure environment with Slack tokens
cp .env.example .env
cp config.example.yaml config.yaml

# Edit .env with your Slack bot tokens:
# SLACK_BOT_TOKEN=xoxb-your-bot-token
# SLACK_APP_TOKEN=xapp-your-app-token
# SLACK_SIGNING_SECRET=your-signing-secret

# Start the API server (enables Slack commands)
webdeface-api

# Test in Slack
# /webdeface system status
```

## 🛠️ Installation

### Prerequisites

- **Python 3.11+** - Modern Python with asyncio support
- **System Dependencies** - For Playwright browser automation
- **API Keys** - Anthropic Claude, Slack Bot Token, Qdrant (optional)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    libnss3 libatk-bridge2.0-0 libdrm2 \
    libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libxss1 libasound2
```

**macOS:**
```bash
brew install python@3.11
# Playwright dependencies installed automatically
```

**Docker (Recommended):**
```bash
# Use our pre-built image with all dependencies
docker pull ghcr.io/your-org/webdeface-monitor:latest
```

### Python Installation

**From PyPI (Stable):**
```bash
pip install webdeface-monitor
playwright install --with-deps
```

**From Source (Development):**
```bash
git clone https://github.com/your-org/webdeface-monitor.git
cd webdeface-monitor
pip install -e ".[dev]"
playwright install --with-deps
pre-commit install
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file with required API credentials:

```bash
# Anthropic Claude API (Required)
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# Slack Integration (Required for Slack commands)
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_APP_TOKEN=xapp-xxxxx
SLACK_SIGNING_SECRET=xxxxx

# Qdrant Vector Database (optional - uses in-memory if not specified)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=xxxxx

# Application Settings
WEBDEFACE_ENV=production
WEBDEFACE_LOG_LEVEL=INFO
WEBDEFACE_DATA_DIR=./data

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Configuration File

Create `config.yaml` with monitoring settings:

```yaml
global:
  default_interval: "*/15 * * * *"  # Every 15 minutes
  keep_scans: 50                     # Retention history
  max_concurrent_jobs: 4             # Parallel monitoring

  alert:
    site_down: ["#ops-alerts"]
    benign_change: []                # No alerts for benign changes
    defacement: ["#security-alerts", "#ops-alerts"]
    suspicious: ["#security-review"]

monitoring:
  timeout_seconds: 30
  retry_attempts: 3
  retry_delay_seconds: 5
  user_agents:
    - "Mozilla/5.0 (compatible; WebdefaceBot/1.0)"
    - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

classification:
  confidence_threshold: 0.7
  max_tokens: 8000
  context_chunks: 5

storage:
  sqlite_path: "./data/webdeface.db"
  vector_collection: "website_content"
  backup_enabled: true
  backup_interval_hours: 24

sites:
  - url: "https://example.com"
    name: "Example Site"
    interval: "0,30 * * * *"  # Every 30 minutes
    max_depth: 2
    priority: "high"

  - url: "https://important-site.com"
    name: "Critical Infrastructure"
    interval: "*/5 * * * *"   # Every 5 minutes
    max_depth: 1
    priority: "critical"
```

See [Configuration Reference](docs/CONFIGURATION.md) for all available options.

## 🎯 Usage

### Slack Commands (Primary Interface)

**Add a website for monitoring:**
```slack
/webdeface website add https://example.com name:"Example Site" interval:900 max-depth:2
```

**List monitored websites:**
```slack
/webdeface website list status:active
```

**Check website status:**
```slack
/webdeface website status abc123
```

**Remove website:**
```slack
/webdeface website remove abc123
```

**Start monitoring system:**
```slack
/webdeface monitoring start
```

**Run immediate check:**
```slack
/webdeface monitoring check abc123
```

**Check system status:**
```slack
/webdeface system status
```

**View health metrics:**
```slack
/webdeface system health
```

**Monitor system logs:**
```slack
/webdeface system logs level:warning limit:20 since:1h
```

### Legacy CLI Interface

**Add a website for monitoring:**
```bash
webdeface-monitor website add https://example.com \
    --name "Example Site" \
    --interval 900 \
    --max-depth 2
```

**List monitored websites:**
```bash
webdeface-monitor website list --status active
```

**Check system status:**
```bash
webdeface-monitor system status
```

> **Note:** The CLI interface is deprecated. Please migrate to Slack commands for improved team collaboration.

### API Server

**Start the API server:**
```bash
webdeface-api
# Server available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Using the REST API:**
```bash
# Health check
curl http://localhost:8000/health

# List websites
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/websites

# Add website via API
curl -X POST \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "name": "Example"}' \
     http://localhost:8000/api/v1/websites
```

## 📱 Slack Commands

The primary interface for WebDeface Monitor is through Slack slash commands, providing real-time team collaboration and monitoring.

### Command Categories

**Website Management (4 commands):**
- `/webdeface website add URL` - Add website for monitoring
- `/webdeface website remove ID` - Remove website from monitoring
- `/webdeface website list` - List all monitored websites
- `/webdeface website status ID` - Show detailed website status

**Monitoring Operations (5 commands):**
- `/webdeface monitoring start` - Start monitoring system
- `/webdeface monitoring stop` - Stop monitoring operations
- `/webdeface monitoring pause ID` - Pause monitoring for website
- `/webdeface monitoring resume ID` - Resume monitoring for website
- `/webdeface monitoring check ID` - Run immediate check

**System Management (4 commands):**
- `/webdeface system status` - Show overall system status
- `/webdeface system health` - Display health metrics
- `/webdeface system metrics` - Show performance metrics
- `/webdeface system logs` - View system logs with filtering

### Permission System

- **VIEWER** - Read-only access to view commands
- **OPERATOR** - View + monitoring control (pause/resume/check)
- **ADMIN** - View + control + site management (add/remove sites)
- **SUPER_ADMIN** - All permissions including user management

### Flag Syntax

Slack commands use `name:value` syntax instead of CLI `--name value`:

```slack
# Add website with custom settings
/webdeface website add https://example.com name:"My Site" interval:300

# Filter lists
/webdeface website list status:active

# View specific log levels
/webdeface system logs level:error since:1h
```

See [Slack Commands Documentation](docs/SLACK_COMMANDS.md) for complete reference.

## � CLI Reference

> **⚠️ DEPRECATED:** The CLI interface is being phased out in favor of Slack commands. Use for legacy automation only.

### Global Options
- `--verbose, -v` - Enable verbose output
- `--debug` - Enable debug mode with detailed error info
- `--config PATH` - Use custom configuration file

### Website Commands
- `website add URL` - Add website for monitoring
- `website remove ID` - Remove website from monitoring
- `website list` - List all monitored websites
- `website status ID` - Show detailed website status

### Monitoring Commands
- `monitoring start` - Start the monitoring system
- `monitoring stop` - Stop all monitoring
- `monitoring pause` - Pause monitoring operations
- `monitoring resume` - Resume paused monitoring
- `monitoring check ID` - Run immediate check for website

### System Commands
- `system status` - Show overall system status
- `system health` - Display health metrics and checks
- `system metrics` - Show performance and usage metrics
- `system logs` - View system logs with filtering

See [CLI Documentation](docs/CLI.md) for complete command reference and migration guide.

## 🌐 API Documentation

The Web Defacement Monitor provides a comprehensive REST API for integration and automation.

### Authentication
```bash
# Obtain access token
curl -X POST http://localhost:8000/api/v1/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=secret"

# Use token in requests
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8000/api/v1/websites
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/v1/websites` | GET, POST | Website management |
| `/api/v1/websites/{id}` | GET, PUT, DELETE | Individual website operations |
| `/api/v1/monitoring/start` | POST | Start monitoring |
| `/api/v1/monitoring/check/{id}` | POST | Immediate check |
| `/api/v1/system/status` | GET | System status |
| `/api/v1/alerts` | GET | Alert history |
| `/api/v1/metrics` | GET | Performance metrics |

### Interactive Documentation
- **OpenAPI/Swagger UI**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

See [API Documentation](docs/API.md) for complete reference.

## 🐳 Deployment

### Docker Deployment

**Single Container:**
```bash
docker run -d \
  --name webdeface-monitor \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/.env:/app/.env \
  -v webdeface-data:/app/data \
  ghcr.io/your-org/webdeface-monitor:latest
```

**Docker Compose (Recommended):**
```yaml
version: '3.8'
services:
  webdeface:
    image: ghcr.io/your-org/webdeface-monitor:latest
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./.env:/app/.env
      - webdeface-data:/app/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    restart: unless-stopped

volumes:
  webdeface-data:
  qdrant-data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webdeface-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webdeface-monitor
  template:
    metadata:
      labels:
        app: webdeface-monitor
    spec:
      containers:
      - name: webdeface
        image: ghcr.io/your-org/webdeface-monitor:latest
        ports:
        - containerPort: 8000
        env:
        - name: CLAUDE_API_KEY
          valueFrom:
            secretKeyRef:
              name: webdeface-secrets
              key: claude-api-key
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
      volumes:
      - name: config
        configMap:
          name: webdeface-config
```

### Production Considerations

**Security:**
- Use secrets management for API keys
- Enable HTTPS with proper certificates
- Configure firewall rules
- Use non-root containers

**Monitoring:**
- Set up health checks and liveness probes
- Configure log aggregation
- Monitor resource usage
- Set up alerting for system failures

**Scaling:**
- Use multiple replicas for high availability
- Configure load balancing
- Optimize database connections
- Monitor queue depths

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

## 🏗️ Architecture

### System Overview

```mermaid
graph TB
    subgraph "External Services"
        SL[Slack Workspace]
        CL[Claude AI API]
        WS[Monitored Websites]
    end

    subgraph "Web Defacement Monitor"
        subgraph "Interface Layer"
            API[REST API<br/>FastAPI]
            CLI[CLI Interface<br/>Rich/Click]
            SLK[Slack Bot<br/>Bolt Framework]
        end

        subgraph "Core Services"
            SCH[Scheduler<br/>APScheduler]
            SCR[Scraper Engine<br/>Playwright]
            CLS[AI Classifier<br/>Claude API]
            NOT[Notifier<br/>Slack/Email]
        end

        subgraph "Storage Layer"
            SQL[SQLite Database<br/>Metadata & History]
            QDR[Qdrant Vector DB<br/>Content Embeddings]
        end
    end

    SL <--> SLK
    SLK --> SCH
    API --> SCH
    CLI --> SCH

    SCH --> SCR
    SCR --> WS
    SCR --> CLS
    CLS --> CL
    CLS --> NOT
    NOT --> SL

    SCR --> SQL
    SCR --> QDR
    CLS --> SQL
```

### Key Components

- **🕷️ Scraper Engine** - Playwright-based web scraping with JavaScript support
- **🤖 AI Classifier** - Claude-powered content change classification
- **📊 Storage Layer** - Dual storage: SQLite + Qdrant vector database
- **⚡ Scheduler** - APScheduler-based job management
- **🔔 Notification System** - Multi-channel alerting (Slack, email, webhooks)
- **🎛️ Interface Layer** - CLI, REST API, and Slack bot interfaces

### Data Flow

1. **Scheduler** triggers monitoring jobs at configured intervals
2. **Scraper** fetches and renders website content via Playwright
3. **Change Engine** compares new content against stored baselines
4. **AI Classifier** analyzes significant changes using Claude AI
5. **Notifier** sends alerts through configured channels
6. **Storage** persists scan results and content vectors

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed design.

## 🤝 Contributing

We welcome contributions! Please follow our development guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-org/webdeface-monitor.git
cd webdeface-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev]"
playwright install --with-deps

# Setup pre-commit hooks
pre-commit install

# Run tests
pytest

# Check code quality
ruff check src/
mypy src/
black --check src/
```

### Code Standards

- **Python 3.11+** with type hints
- **Black** code formatting
- **Ruff** linting and import sorting
- **MyPy** static type checking
- **Pytest** testing framework
- **Pre-commit** hooks for quality control

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all checks pass (`pre-commit run --all-files`)
5. Update documentation as needed
6. Submit a pull request

See [Development Guide](docs/DEVELOPMENT.md) for detailed guidelines.

## 🔍 Troubleshooting

### Common Issues

**Playwright Installation Issues:**
```bash
# Reinstall browser dependencies
playwright install --with-deps chromium

# On Linux, install system dependencies
sudo apt-get install libnss3 libatk-bridge2.0-0
```

**API Connection Errors:**
```bash
# Check API key configuration
webdeface-monitor system health

# Verify network connectivity
curl -I https://api.anthropic.com
```

**Monitoring Not Starting:**
```bash
# Check configuration
webdeface-monitor system status

# View detailed logs
webdeface-monitor system logs --level debug
```

**Database Issues:**
```bash
# Check database permissions
ls -la ./data/

# Reset database (WARNING: destroys data)
rm ./data/webdeface.db
webdeface-monitor system status
```
See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for comprehensive help.
