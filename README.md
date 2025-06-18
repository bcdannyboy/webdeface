# WebDeface Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Tests-100%25_Pass-brightgreen.svg)](#-testing)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Slack](https://img.shields.io/badge/Slack-4A154B?style=flat&logo=slack&logoColor=white)](https://slack.com/)
[![Claude AI](https://img.shields.io/badge/Claude_AI-FF6B35?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/)

**Enterprise-Grade AI-Powered Web Defacement Detection and Monitoring System**

WebDeface Monitor is a web defacement detection system that combines advanced AI classification, intelligent orchestration, and Slack-based team collaboration to provide comprehensive website security monitoring. Built with Docker-first deployment and designed for high-availability production environments.

## 📋 Table of Contents

- [🚀 Overview & Features](#-overview--features)
- [⚡ Quick Start](#-quick-start)
- [🛠️ Prerequisites & Setup](#-prerequisites--setup)
- [🚀 Deployment](#-deployment)
- [⚙️ Configuration](#-configuration)
- [🎯 Usage](#-usage)
- [🏗️ Architecture](#-architecture)
- [🔍 Troubleshooting](#-troubleshooting)
- [📚 Documentation Links](#-documentation-links)


## 🚀 Overview & Features

### Core Capabilities
- **🤖 AI-Powered Classification** - Claude AI analyzes content changes with confidence scoring and sophisticated threat detection.
- **🕷️ JavaScript-Aware Scraping** - Playwright engine renders dynamic content for accurate monitoring of modern web applications.
- **💬 Slack-First Interface** - Native team collaboration with slash commands, interactive components, and role-based permissions.
- **🎯 Vector Similarity Detection** - Optional Qdrant-powered semantic analysis for advanced pattern recognition and anomaly detection.
- **⚙️ Intelligent Orchestration** - Three-tier orchestration system: Scheduling, Scraping, and Classification with unified data management.
- **🐳 Production Infrastructure** - Docker containerization with multi-stage builds, health monitoring, and automated lifecycle management.

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

### Required API Keys
- **Anthropic Claude API**: For AI-powered content classification and threat analysis.
- **Slack Bot Tokens**: For team integration, notifications, and primary interface.

### Slack Bot Setup
A Slack App is required for the primary interface. Here is a summary of the setup process:
1.  **Create a Slack App** in your workspace.
2.  **Enable Socket Mode** and generate an app-level token (`xapp-...`).
3.  **Add OAuth Scopes** for the bot (e.g., `chat:write`, `commands`, `users:read`).
4.  **Create a Slash Command**: `/webdeface`.
5.  **Install the App** to your workspace and get the Bot User OAuth Token (`xoxb-...`).

For a complete, step-by-step walkthrough, refer to the dedicated guide in **[`docs/SLACK_INTEGRATION.md`](docs/SLACK_INTEGRATION.md)**.

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
The `run_infrastructure.sh` script provides a simple interface for managing the application stack.
```bash
# Standard deployment
./run_infrastructure.sh start

# Production deployment with vector database
./run_infrastructure.sh start --qdrant

# Development mode with hot-reload
./run_infrastructure.sh dev
```

**Option 2: Docker Compose**
For more granular control, you can use `docker-compose` directly.
```bash
# Basic deployment
docker-compose up -d

# With Qdrant vector database
docker-compose --profile qdrant up -d
```

## ⚙️ Configuration

Configuration is managed through environment variables and a `config.yaml` file. Environment variables always override settings in the YAML file.

### Environment Variables
| Variable | Description | Default |
|---|---|---|
| `DEBUG` | Enable debug mode. | `False` |
| `LOG_LEVEL` | The log level to use (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `KEEP_SCANS` | The number of scans to keep for each website. | `20` |
| `API_TOKENS` | A comma-separated list of API tokens for the REST API. | `dev-token-12345` |
| `DATABASE_URL` | The URL of the database. | `sqlite:///./data/webdeface.db` |
| `QDRANT_URL` | The URL of the Qdrant vector database. | `http://localhost:6333` |
| `SLACK_BOT_TOKEN` | The Slack bot token (`xoxb-...`). | `""` |
| `SLACK_APP_TOKEN` | The Slack app token (`xapp-...`). | `""` |
| `SLACK_SIGNING_SECRET` | The Slack signing secret. | `""` |
| `CLAUDE_API_KEY` | The Claude API key. | `""` |

### YAML Configuration
The `config.yaml` file is used for static configuration.

**Example `config.yaml`:**
```yaml
global:
  default_interval: "*/15 * * * *"   # Every 15 minutes
  keep_scans: 20
  alert:
    site_down:
      channels: ["#noc"]
    defacement:
      channels: ["#sec-ops"]
      users: ["@security-team"]

sites:
  - url: "https://example.com"
    name: "Example Site"
    interval: "0,30 * * * *"  # Every 30 minutes
    depth: 2
    enabled: true

scraping:
  default_timeout: 10000  # 10 seconds
  max_retries: 3
```
For more details, see **[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)**.

## 🎯 Usage

### Primary Interface: Slack Commands
The primary operational interface is Slack-based.

**Website Management:**
```slack
# Add website for monitoring
/webdeface website add https://example.com name:"Production Site"

# List all monitored websites
/webdeface website list

# Get detailed website status
/webdeface website status <website_id>

# Remove website from monitoring
/webdeface website remove <website_id>
```

**Monitoring Operations:**
```slack
# Start monitoring system
/webdeface monitoring start

# Stop all monitoring
/webdeface monitoring stop

# Run immediate check
/webdeface monitoring check <website_id>
```

**System Management:**
```slack
# Check overall system health
/webdeface system status

# View system metrics
/webdeface system health
```

### Secondary Interface: REST API
The system also provides a REST API for programmatic access.

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
```

## 🏗️ Architecture

The system is composed of several layers, including an interface layer (Slack, REST API), an orchestration layer (Scheduling, Scraping, Classification), a service layer, and a storage layer (SQLite, Qdrant).

For a detailed breakdown of the architecture, see **[`docs/SITE_CHANGE_ANALYSIS_ARCHITECTURE.md`](docs/SITE_CHANGE_ANALYSIS_ARCHITECTURE.md)**.

## 🔍 Troubleshooting

### Service Won't Start
- **Port already in use:** Check if another application is using port 8000.
- **Missing environment variables:** Ensure all required variables in `.env` are set.

### Slack Notifications Not Working
- **Invalid bot token:** Double-check your `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`.
- **Missing bot permissions:** Ensure the bot has the required OAuth scopes in the Slack App configuration.
- **Channel access:** Make sure the bot is invited to the channels you want to receive notifications in.

For more help, see the **[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)** guide.

## 📚 Documentation Links

For deeper usage and advanced topics, refer to the documentation in the `docs/` directory:

- **[API Documentation](docs/API.md)** - Complete REST API reference and examples.
- **[CLI Reference](docs/CLI.md)** - Guide for the command-line interface.
- **[Configuration Guide](docs/CONFIGURATION.md)** - Detailed configuration options and best practices.
- **[Data Models](docs/DATA_MODELS.md)** - Overview of the database schema.
- **[Site Change Analysis Architecture](docs/SITE_CHANGE_ANALYSIS_ARCHITECTURE.md)** - Detailed system and algorithm architecture.
- **[Slack Integration Guide](docs/SLACK_INTEGRATION.md)** - In-depth Slack application configuration instructions.
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions.

---

**Version**: 1.0.0