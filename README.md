# WebDeface Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Slack](https://img.shields.io/badge/Slack-4A154B?style=flat&logo=slack&logoColor=white)](https://slack.com/)
[![Claude AI](https://img.shields.io/badge/Claude_AI-FF6B35?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/)

**Enterprise-Grade AI-Powered Web Defacement Detection and Monitoring System**

WebDeface Monitor is a production-ready, enterprise-grade web defacement detection system that combines advanced AI classification, intelligent orchestration, and Slack-based team collaboration to provide comprehensive website security monitoring. Built with Docker-first deployment and designed for high-availability production environments.

## 🚀 Overview & Features

### Core Capabilities
- **🤖 AI-Powered Classification** - Claude AI analyzes content changes with confidence scoring and sophisticated threat detection
- **🕷️ JavaScript-Aware Scraping** - Playwright engine renders dynamic content for accurate monitoring of modern web applications
- **💬 Slack-First Interface** - Native team collaboration with slash commands, interactive components, and role-based permissions
- **🎯 Vector Similarity Detection** - Optional Qdrant-powered semantic analysis for advanced pattern recognition and anomaly detection
- **⚙️ Intelligent Orchestration** - Three-tier orchestration system: Scheduling, Scraping, and Classification with unified data management
- **🐳 Production Infrastructure** - Docker containerization with multi-stage builds, health monitoring, and automated lifecycle management

### Enterprise Features
- **🏗️ Infrastructure Management** - Comprehensive [`run_infrastructure.sh`](run_infrastructure.sh) script for complete operational control
- **🔐 Security & Authentication** - API key-based authentication with role-based access control and secure credential management
- **📊 Monitoring & Observability** - Health checks, performance metrics, structured logging, and comprehensive system insights
- **🔄 High Availability** - Multi-container deployment, graceful shutdowns, automatic restarts, and load balancing support
- **💾 Data Management** - Automated backups, restore capabilities, persistent storage with volume management and data retention policies
- **⚙️ Flexible Configuration** - Environment-based configuration with YAML overrides, runtime validation, and hot-reload capabilities

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Prerequisites & Setup](#-prerequisites--setup)
- [Deployment](#-deployment)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Infrastructure Management](#-infrastructure-management)
- [Development](#-development)
- [Production Considerations](#-production-considerations)
- [Documentation Links](#-documentation-links)

## ⚡ Quick Start

Deploy WebDeface Monitor in 3 simple steps:

### 1. Clone & Configure
```bash
git clone https://github.com/your-org/webdeface-monitor.git
cd webdeface-monitor

# Setup environment with API keys
cp .env.example .env
# Edit .env: Add CLAUDE_API_KEY and Slack credentials
```

### 2. Deploy Infrastructure
```bash
chmod +x run_infrastructure.sh
./run_infrastructure.sh start
```

### 3. Start Monitoring via Slack
```slack
/webdeface system status
/webdeface website add https://example.com name:"Production Site"
/webdeface monitoring start
```

**Access Points:**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Qdrant Dashboard**: http://localhost:6333/dashboard (optional)

## 🛠️ Prerequisites & Setup

### System Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- **Memory**: 2GB RAM minimum, 4GB recommended for production
- **Storage**: 1GB free space minimum, 5GB recommended
- **Network**: Internet access for API calls and web monitoring

### Required Dependencies
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

### Required API Keys
- **Anthropic Claude API**: For AI-powered content classification and threat analysis
- **Slack Bot Tokens**: For team integration, notifications, and primary interface

### Docker Installation

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
```bash
brew install --cask docker
# Or download from https://docker.com/products/docker-desktop
```

### Slack Bot Setup

1. **Create Slack App** at https://api.slack.com/apps
   - Name: "WebDeface Monitor"
   - Development Slack workspace selection

2. **Configure Bot Permissions** (OAuth & Permissions):
   ```
   - chat:write (send messages and notifications)
   - commands (slash command support)
   - channels:read (channel access)
   - users:read (user information)
   ```

3. **Enable Socket Mode**:
   ```
   - Generate App-Level Token with connections:write scope
   - Copy as SLACK_APP_TOKEN
   ```

4. **Add Slash Command**:
   ```
   Command: /webdeface
   Description: WebDeface Monitor controls
   Usage Hint: [action] [parameters]
   ```

5. **Install to Workspace**:
   ```
   - Copy Bot User OAuth Token (SLACK_BOT_TOKEN)
   - Copy Signing Secret (SLACK_SIGNING_SECRET)
   ```

## 🚀 Deployment

### Environment Configuration

**1. API Keys Setup:**
```bash
cp .env.example .env
# Edit .env with your credentials:
```

**Required Environment Variables:**
```bash
# Claude AI Configuration (Required)
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# Slack Integration (Required for primary interface)
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_APP_TOKEN=xapp-xxxxx
SLACK_SIGNING_SECRET=xxxxx

# Optional: Restrict Slack access
SLACK_ALLOWED_USERS=user1,user2,user3

# Application Security
SECRET_KEY=your-secret-key-here
DEBUG=false
LOG_LEVEL=INFO
```

### Deployment Options

**Option 1: Infrastructure Script (Recommended)**
```bash
# Standard deployment
./run_infrastructure.sh start

# Production deployment with vector database
./run_infrastructure.sh start --qdrant

# Development mode with hot-reload
./run_infrastructure.sh dev --qdrant
```

**Option 2: Docker Compose**
```bash
# Basic deployment
docker-compose up -d

# With Qdrant vector database
docker-compose --profile qdrant up -d

# View logs
docker-compose logs -f webdeface
```

**Option 3: Production Scaling**
```bash
# High availability deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale webdeface=3
```

## ⚙️ Configuration

### Environment Variables

**Core Application:**
```bash
# Security & Authentication
SECRET_KEY=your-secret-key-here           # Application secret
DEBUG=false                               # Production mode
LOG_LEVEL=INFO                           # Logging verbosity

# Data Management
KEEP_SCANS=20                            # Scan history retention
DATABASE__URL=sqlite:///./data/webdeface.db
```

**External Service Integration:**
```bash
# Claude AI Configuration
CLAUDE_API_KEY=sk-ant-xxxxx              # Required for AI classification
CLAUDE_MODEL=claude-3-sonnet-20240229    # AI model selection
CLAUDE_MAX_TOKENS=4000                   # Response length limit
CLAUDE_TEMPERATURE=0.1                   # Response consistency

# Slack Integration (Primary Interface)
SLACK_BOT_TOKEN=xoxb-xxxxx               # Required
SLACK_APP_TOKEN=xapp-xxxxx               # Required for socket mode
SLACK_SIGNING_SECRET=xxxxx               # Required for verification

# Qdrant Vector Database (Optional)
QDRANT__URL=http://qdrant:6333           # Service URL
QDRANT__COLLECTION_NAME=webdeface        # Collection name
QDRANT__VECTOR_SIZE=384                  # Embedding dimensions
```

### YAML Configuration

**Monitoring Configuration ([`config.yaml`](config.yaml)):**
```yaml
global:
  default_interval: "*/15 * * * *"        # Default monitoring frequency
  keep_scans: 20                          # Scan history retention
  max_concurrent_jobs: 4                  # Parallel monitoring limit
  
  # Alert routing configuration
  alert:
    site_down:
      channels: ["#ops-alerts"]
      users: ["@oncall-engineer"]
    defacement:
      channels: ["#security-alerts", "#ops-alerts"]
      users: ["@security-team"]
    suspicious:
      channels: ["#security-review"]

# Website monitoring definitions
sites:
  - url: "https://example.com"
    name: "Production Site"
    interval: "*/5 * * * *"               # Every 5 minutes
    max_depth: 2
    priority: "critical"
    enabled: true

# Scraping behavior
scraping:
  default_timeout: 10000
  max_retries: 3
  max_depth: 3
  user_agents:
    - "Mozilla/5.0 (compatible; WebDefaceMonitor/1.0)"

# AI classification settings
classification:
  confidence_threshold: 0.7
  max_tokens: 8000
  context_chunks: 5
```

## 🎯 Usage

### Primary Interface: Slack Commands

WebDeface Monitor's primary operational interface is Slack-based, designed for real-time team collaboration and response:

**Website Management:**
```slack
# Add website for monitoring
/webdeface website add https://example.com name:"Production Site" interval:300

# List all monitored websites
/webdeface website list status:active

# Get detailed website status
/webdeface website status abc123

# Remove website from monitoring
/webdeface website remove abc123

# Update website configuration
/webdeface website update abc123 interval:600 priority:high
```

**Monitoring Operations:**
```slack
# Start monitoring system
/webdeface monitoring start

# Stop all monitoring
/webdeface monitoring stop

# Pause specific website
/webdeface monitoring pause abc123

# Resume monitoring
/webdeface monitoring resume abc123

# Run immediate check
/webdeface monitoring check abc123

# View monitoring status
/webdeface monitoring status
```

**System Management:**
```slack
# Check overall system health
/webdeface system status

# View system metrics
/webdeface system health

# Monitor logs with filtering
/webdeface system logs level:warning since:1h limit:50

# View system configuration
/webdeface system config

# Performance insights
/webdeface system metrics
```

### Secondary Interface: REST API

**Authentication:**
```bash
# API uses simple API key authentication
export API_KEY="your-api-key-here"
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/websites
```

**Core Operations:**
```bash
# Health check
curl http://localhost:8000/health

# List websites
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/websites

# Add website
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "name": "Example"}' \
     http://localhost:8000/api/v1/websites

# Start monitoring
curl -X POST -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/v1/monitoring/start

# Get system metrics
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/v1/metrics
```

### Health Monitoring

**System Health Endpoints:**
- **Application Health**: `GET /health`
- **Detailed Status**: `GET /api/v1/system/status`
- **Performance Metrics**: `GET /api/v1/metrics`
- **Qdrant Health**: `GET http://localhost:6333/health` (if enabled)

**Infrastructure Monitoring:**
```bash
# Service status
./run_infrastructure.sh status

# Live log monitoring
./run_infrastructure.sh logs --follow

# Resource usage
docker stats webdeface-monitor
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     WebDeface Monitor                          │
│                   Enterprise Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                      Interface Layer                           │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ Slack Bot   │ │  REST API    │ │    Health Monitors      │  │
│  │ (Primary)   │ │ (Secondary)  │ │    (Observability)      │  │
│  │ Bolt + Socket│ │  FastAPI     │ │    Prometheus Ready     │  │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                   Orchestration Layer                          │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ Scheduling  │ │   Scraping   │ │    Classification       │  │
│  │Orchestrator │ │ Orchestrator │ │    Orchestrator         │  │
│  │(APScheduler)│ │ (Playwright) │ │    (Claude AI)          │  │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                             │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │   Browser   │ │ AI Classifier │ │     Notification        │  │
│  │ (Playwright)│ │ (Claude API)  │ │   (Slack Integration)   │  │
│  │ JS-Aware    │ │ Content Anal. │ │   Multi-Channel         │  │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      Storage Layer                             │
│  ┌─────────────┐ ┌──────────────┐                             │
│  │   SQLite    │ │    Qdrant    │                             │
│  │ (Metadata   │ │  (Vectors &  │                             │
│  │  & State)   │ │  Similarity) │                             │
│  └─────────────┘ └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

**Interface Layer:**
- **Slack Bot** (Primary): Bolt framework with Socket Mode, slash commands, interactive components
- **REST API** (Secondary): FastAPI with OpenAPI documentation and API key authentication
- **Health Monitors**: Comprehensive observability with Prometheus metrics support

**Orchestration Layer:**
- **Scheduling Orchestrator**: APScheduler with cron-based monitoring and job management
- **Scraping Orchestrator**: Playwright coordination with JavaScript rendering and dynamic content support
- **Classification Orchestrator**: Claude AI pipeline with confidence scoring and threat analysis

**Service Layer:**
- **Browser Engine**: Playwright with Chromium for JavaScript-aware content extraction
- **AI Classifier**: Claude API integration with sophisticated content analysis and threat detection
- **Notification System**: Multi-channel alerting with Slack integration and configurable routing

**Storage Layer:**
- **SQLite Database**: Persistent metadata, scan history, configuration, and application state
- **Qdrant Vector DB**: Optional semantic similarity analysis and advanced pattern recognition

### Data Flow

1. **Schedule Activation** → Scheduling Orchestrator triggers monitoring jobs based on cron expressions
2. **Content Acquisition** → Scraping Orchestrator extracts content using Playwright browser engine
3. **Change Detection** → Compare extracted content against stored baselines with hash-based detection
4. **AI Analysis** → Classification Orchestrator processes changes through Claude AI for threat assessment
5. **Alert Generation** → Notification system routes alerts through configured Slack channels and users
6. **Data Persistence** → Results stored in SQLite with optional vector embeddings in Qdrant

### Security Architecture

- **Authentication**: Simple API key-based authentication with role-based access control
- **Secrets Management**: Environment-based credential storage with container secrets support
- **Network Security**: Container isolation with minimal port exposure and internal service communication
- **Data Protection**: Encrypted storage support with automated backup capabilities

## 🛠️ Infrastructure Management

The [`run_infrastructure.sh`](run_infrastructure.sh) script provides comprehensive lifecycle management:

### Service Management

**Start Services:**
```bash
# Basic deployment
./run_infrastructure.sh start

# Production with vector database
./run_infrastructure.sh start --qdrant

# Foreground mode for debugging
./run_infrastructure.sh start --foreground
```

**Control Operations:**
```bash
# Graceful shutdown
./run_infrastructure.sh stop

# Restart with configuration
./run_infrastructure.sh restart --qdrant

# Service status and health
./run_infrastructure.sh status
```

**Monitoring & Logs:**
```bash
# Monitor all services
./run_infrastructure.sh logs

# Follow specific service
./run_infrastructure.sh logs webdeface --follow

# Container shell access
./run_infrastructure.sh shell webdeface
```

### Maintenance Operations

**Image Management:**
```bash
# Rebuild images
./run_infrastructure.sh build

# Force rebuild without cache
./run_infrastructure.sh build --no-cache

# Update to latest images
./run_infrastructure.sh update
```

**Data Management:**
```bash
# Create timestamped backup
./run_infrastructure.sh backup

# Restore from backup
./run_infrastructure.sh restore /path/to/backup.tar.gz

# Cleanup Docker resources
./run_infrastructure.sh cleanup
```

**Development Support:**
```bash
# Development mode with hot-reload
./run_infrastructure.sh dev --qdrant

# Run comprehensive test suite
./run_infrastructure.sh test

# Development with debugging
./run_infrastructure.sh dev --debug
```

## 👨‍💻 Development

### Development Environment

**Setup:**
```bash
git clone https://github.com/your-org/webdeface-monitor.git
cd webdeface-monitor

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Development installation
pip install -e ".[dev]"
playwright install --with-deps chromium

# Pre-commit hooks
pre-commit install
```

**Development Server:**
```bash
# Infrastructure script (recommended)
./run_infrastructure.sh dev --qdrant

# Manual API server
uvicorn src.webdeface.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality

**Testing:**
```bash
# Full test suite
pytest

# With coverage
pytest --cov=src/webdeface --cov-report=html

# Test categories
pytest -m "unit"          # Unit tests
pytest -m "integration"   # Integration tests
```

**Linting & Formatting:**
```bash
# Format code
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/

# All quality checks
pre-commit run --all-files
```

### Project Structure

```
webdeface-monitor/
├── src/webdeface/           # Application source code
│   ├── api/                 # FastAPI application and routes
│   ├── notification/        # Slack integration and alerting
│   │   └── slack/          # Slack Bot implementation
│   ├── classifier/          # AI classification pipeline
│   ├── scheduler/           # Job scheduling and orchestration
│   ├── scraper/             # Web scraping and browser automation
│   ├── storage/             # Database and storage interfaces
│   ├── config/              # Configuration management
│   └── utils/               # Shared utilities and helpers
├── tests/                   # Comprehensive test suite
├── docs/                    # Additional documentation
├── docker-compose.yml       # Container orchestration
├── Dockerfile               # Multi-stage container build
├── run_infrastructure.sh    # Infrastructure management script
└── pyproject.toml          # Python project configuration
```

## 🚀 Production Considerations

### Scaling & Performance

**High Availability:**
```yaml
# docker-compose.prod.yml
services:
  webdeface:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Resource Optimization:**
```yaml
services:
  webdeface:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Security Hardening

**Container Security:**
```bash
# Non-root user in container
USER app

# Read-only filesystem
docker run --read-only --tmpfs /tmp webdeface-monitor

# Network restrictions
networks:
  internal:
    internal: true
```

**Secrets Management:**
```bash
# Docker secrets
echo "sk-ant-your-key" | docker secret create claude_api_key -
docker service update --secret-add claude_api_key webdeface
```

### Backup & Recovery

**Automated Backups:**
```bash
# Scheduled backups
crontab -e
0 2 * * * /path/to/webdeface/run_infrastructure.sh backup

# Remote backup storage
./run_infrastructure.sh backup
aws s3 cp ./backups/latest.tar.gz s3://webdeface-backups/
```

**Disaster Recovery:**
```bash
# Restore from backup
./run_infrastructure.sh restore ./backups/webdeface-backup-20241201.tar.gz

# Verify restoration
./run_infrastructure.sh status
curl http://localhost:8000/health
```

### Monitoring & Observability

**Metrics & Logging:**
```bash
# Prometheus metrics
curl http://localhost:8000/api/v1/metrics/prometheus

# Structured logging
./run_infrastructure.sh logs | jq '.level, .message'

# Performance monitoring
docker stats webdeface-monitor
```

## 📚 Documentation Links

**Core Documentation:**
- **[API Documentation](docs/API.md)** - Complete REST API reference and examples
- **[Configuration Guide](docs/CONFIGURATION.md)** - Detailed configuration options and best practices
- **[Slack Commands](docs/SLACK_COMMANDS.md)** - Comprehensive Slack interface documentation
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions

**Online Resources:**
- **API Documentation**: http://localhost:8000/docs (Interactive OpenAPI)
- **Health Dashboard**: http://localhost:8000/health
- **Qdrant Dashboard**: http://localhost:6333/dashboard (if enabled)

---

**Version**: 1.0.0  