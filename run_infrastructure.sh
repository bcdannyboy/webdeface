#!/bin/bash

# WebDeface Monitor Infrastructure Management Script
# Provides comprehensive management for Docker-based WebDeface Monitor deployment

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_VERSION="1.0.0"
readonly PROJECT_NAME="WebDeface Monitor"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Container and service names
readonly MAIN_SERVICE="webdeface"
readonly MAIN_CONTAINER="webdeface-monitor"
readonly QDRANT_SERVICE="qdrant"
readonly QDRANT_CONTAINER="webdeface-qdrant"
readonly COMPOSE_FILE="docker-compose.yml"
readonly ENV_FILE=".env"
readonly ENV_EXAMPLE=".env.example"

# Directories
readonly DATA_DIR="./data"
readonly BACKUP_DIR="./backups"
readonly LOG_DIR="./logs"

# Required environment variables
readonly REQUIRED_ENV_VARS=(
    "SECRET_KEY"
    "CLAUDE_API_KEY"
    "SLACK_BOT_TOKEN"
    "SLACK_APP_TOKEN"
    "SLACK_SIGNING_SECRET"
)

# Logging
log_file="${LOG_DIR}/infrastructure-$(date +%Y%m%d).log"

# Utility functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}  ${PROJECT_NAME} Infrastructure Management${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Ensure log directory exists
    mkdir -p "${LOG_DIR}"
    
    # Write to log file
    echo "[${timestamp}] [${level}] ${message}" >> "${log_file}"
    
    # Print to console with colors
    case "${level}" in
        "INFO")  echo -e "${GREEN}[INFO]${NC} ${message}" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${message}" ;;
        "DEBUG") echo -e "${CYAN}[DEBUG]${NC} ${message}" ;;
        *)       echo -e "${WHITE}[${level}]${NC} ${message}" ;;
    esac
}

error_exit() {
    log "ERROR" "$1"
    exit "${2:-1}"
}

success() {
    log "INFO" "$1"
}

warning() {
    log "WARN" "$1"
}

debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        log "DEBUG" "$1"
    fi
}

# Validation functions
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker first."
    fi
    
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running. Please start Docker first."
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error_exit "Docker Compose is not available. Please install Docker Compose."
    fi
    
    # Check if compose file exists
    if [[ ! -f "${COMPOSE_FILE}" ]]; then
        error_exit "Docker Compose file '${COMPOSE_FILE}' not found."
    fi
    
    success "Prerequisites check passed"
}

validate_environment() {
    log "INFO" "Validating environment variables..."
    
    local missing_vars=()
    
    # Check if .env file exists
    if [[ ! -f "${ENV_FILE}" ]]; then
        warning "Environment file '${ENV_FILE}' not found."
        if [[ -f "${ENV_EXAMPLE}" ]]; then
            echo -e "${YELLOW}You can create it from the example:${NC}"
            echo -e "${CYAN}  cp ${ENV_EXAMPLE} ${ENV_FILE}${NC}"
            echo -e "${CYAN}  # Then edit ${ENV_FILE} with your actual values${NC}"
        fi
    fi
    
    # Source environment file if it exists
    if [[ -f "${ENV_FILE}" ]]; then
        set -a  # automatically export all variables
        source "${ENV_FILE}"
        set +a
    fi
    
    # Check required environment variables
    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("${var}")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error_exit "Missing required environment variables: ${missing_vars[*]}"
    fi
    
    success "Environment validation passed"
}

create_directories() {
    log "INFO" "Creating necessary directories..."
    
    local dirs=("${DATA_DIR}" "${BACKUP_DIR}" "${LOG_DIR}")
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "${dir}" ]]; then
            mkdir -p "${dir}"
            debug "Created directory: ${dir}"
        fi
    done
    
    success "Directories created"
}

# Docker Compose command wrapper
compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

# Service management functions
start_services() {
    local use_qdrant=false
    local detached=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --qdrant)
                use_qdrant=true
                shift
                ;;
            --foreground|-f)
                detached=false
                shift
                ;;
            *)
                warning "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    check_prerequisites
    validate_environment
    create_directories
    
    log "INFO" "Starting ${PROJECT_NAME} services..."
    
    local compose_args=()
    if [[ "${use_qdrant}" == "true" ]]; then
        compose_args+=(--profile qdrant)
        log "INFO" "Including Qdrant vector database"
    fi
    
    if [[ "${detached}" == "true" ]]; then
        compose_args+=(-d)
    fi
    
    if [[ "${use_qdrant}" == "true" ]]; then
        # Start both services when Qdrant is requested
        compose_cmd "${compose_args[@]}" up
    else
        # Start only the main service
        compose_cmd "${compose_args[@]}" up "${MAIN_SERVICE}"
    fi
    
    if [[ "${detached}" == "true" ]]; then
        # Wait for services to be healthy
        wait_for_health
        show_service_info
    fi
}

stop_services() {
    log "INFO" "Stopping ${PROJECT_NAME} services..."
    
    # Graceful shutdown
    compose_cmd down --timeout 30
    
    success "Services stopped"
}

restart_services() {
    local use_qdrant=false
    
    # Check if Qdrant was previously running to maintain same configuration
    if docker ps --format "table {{.Names}}" | grep -q "${QDRANT_CONTAINER}"; then
        use_qdrant=true
        log "INFO" "Detected running Qdrant container, will restart with Qdrant enabled"
    fi
    
    # Parse arguments for explicit qdrant flag
    while [[ $# -gt 0 ]]; do
        case $1 in
            --qdrant)
                use_qdrant=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    log "INFO" "Restarting ${PROJECT_NAME} services..."
    
    stop_services
    sleep 2
    
    if [[ "${use_qdrant}" == "true" ]]; then
        start_services --qdrant "$@"
    else
        start_services "$@"
    fi
}

show_status() {
    echo -e "\n${WHITE}Service Status:${NC}"
    compose_cmd ps
    
    echo -e "\n${WHITE}Container Health:${NC}"
    local containers=(${MAIN_CONTAINER})
    
    # Check if Qdrant is running
    if docker ps --format "table {{.Names}}" | grep -q "${QDRANT_CONTAINER}"; then
        containers+=(${QDRANT_CONTAINER})
    fi
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "${container}"; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "unknown")
            local status=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "not found")
            
            case "${health}" in
                "healthy")   echo -e "  ${GREEN}●${NC} ${container}: ${status} (${health})" ;;
                "unhealthy") echo -e "  ${RED}●${NC} ${container}: ${status} (${health})" ;;
                "starting")  echo -e "  ${YELLOW}●${NC} ${container}: ${status} (${health})" ;;
                *)           echo -e "  ${BLUE}●${NC} ${container}: ${status}" ;;
            esac
        else
            echo -e "  ${RED}○${NC} ${container}: not running"
        fi
    done
    
    echo -e "\n${WHITE}Network Information:${NC}"
    docker network ls | grep webdeface || echo "  No WebDeface networks found"
    
    echo -e "\n${WHITE}Volume Information:${NC}"
    docker volume ls | grep webdeface || echo "  No WebDeface volumes found"
}

show_logs() {
    local service="${1:-}"
    local follow=false
    local lines=100
    
    # Parse additional arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --follow|-f)
                follow=true
                shift
                ;;
            --lines|-n)
                lines="$2"
                shift 2
                ;;
            *)
                warning "Unknown log option: $1"
                shift
                ;;
        esac
    done
    
    local compose_args=(logs --timestamps)
    
    if [[ "${follow}" == "true" ]]; then
        compose_args+=(--follow)
    fi
    
    compose_args+=(--tail "${lines}")
    
    if [[ -n "${service}" ]]; then
        compose_args+=("${service}")
        log "INFO" "Showing logs for service: ${service}"
    else
        log "INFO" "Showing logs for all services"
    fi
    
    compose_cmd "${compose_args[@]}"
}

access_shell() {
    local service="${1:-${MAIN_SERVICE}}"
    local shell="${2:-bash}"
    
    log "INFO" "Accessing shell for service: ${service}"
    
    if ! compose_cmd exec "${service}" "${shell}"; then
        warning "Failed to access ${shell}, trying sh..."
        compose_cmd exec "${service}" sh
    fi
}

wait_for_health() {
    log "INFO" "Waiting for services to become healthy..."
    
    local max_attempts=60
    local attempt=1
    local services_to_check=()
    
    # Determine which services to wait for
    if docker ps --format "table {{.Names}}" | grep -q "${MAIN_CONTAINER}"; then
        services_to_check+=("${MAIN_CONTAINER}")
    fi
    
    if docker ps --format "table {{.Names}}" | grep -q "${QDRANT_CONTAINER}"; then
        services_to_check+=("${QDRANT_CONTAINER}")
    fi
    
    if [[ ${#services_to_check[@]} -eq 0 ]]; then
        warning "No services found to check health"
        return 1
    fi
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        local all_healthy=true
        local status_text=""
        
        for container in "${services_to_check[@]}"; do
            local health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "unknown")
            local status=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "not found")
            
            case "${health}" in
                "healthy")
                    status_text="${status_text} ✓${container}"
                    ;;
                "unhealthy")
                    all_healthy=false
                    status_text="${status_text} ✗${container}"
                    ;;
                "starting")
                    all_healthy=false
                    status_text="${status_text} ⏳${container}"
                    ;;
                *)
                    if [[ "${status}" == "running" ]]; then
                        status_text="${status_text} ⏳${container}(no-hc)"
                    else
                        all_healthy=false
                        status_text="${status_text} ✗${container}(${status})"
                    fi
                    ;;
            esac
        done
        
        if [[ "${all_healthy}" == "true" ]]; then
            echo -e "\r${GREEN}All services are healthy:${status_text}${NC}"
            return 0
        fi
        
        echo -ne "\r${YELLOW}Health check (${attempt}/${max_attempts}):${status_text}${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo # New line
    warning "Health check timeout reached. Some services may not be healthy."
    show_status
    return 1
}

show_service_info() {
    echo -e "\n${GREEN}✓ Services started successfully!${NC}\n"
    
    echo -e "${WHITE}Access Information:${NC}"
    echo -e "  🌐 Web Interface: ${CYAN}http://localhost:8000${NC}"
    echo -e "  📚 API Docs: ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  ❤️  Health Check: ${CYAN}http://localhost:8000/health${NC}"
    
    if docker ps --format "table {{.Names}}" | grep -q "${QDRANT_CONTAINER}"; then
        echo -e "  🔍 Qdrant API: ${CYAN}http://localhost:6333${NC}"
        echo -e "  📊 Qdrant Dashboard: ${CYAN}http://localhost:6333/dashboard${NC}"
    fi
    
    echo -e "\n${WHITE}Useful Commands:${NC}"
    echo -e "  📊 Check status: ${CYAN}./${SCRIPT_NAME} status${NC}"
    echo -e "  📝 View logs: ${CYAN}./${SCRIPT_NAME} logs${NC}"
    echo -e "  🐚 Access shell: ${CYAN}./${SCRIPT_NAME} shell${NC}"
    echo -e "  🛑 Stop services: ${CYAN}./${SCRIPT_NAME} stop${NC}"
}

# Maintenance functions
build_images() {
    local no_cache=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cache)
                no_cache=true
                shift
                ;;
            *)
                warning "Unknown build option: $1"
                shift
                ;;
        esac
    done
    
    log "INFO" "Building Docker images..."
    
    local build_args=(build)
    if [[ "${no_cache}" == "true" ]]; then
        build_args+=(--no-cache)
    fi
    
    compose_cmd "${build_args[@]}"
    success "Images built successfully"
}

update_services() {
    log "INFO" "Updating ${PROJECT_NAME} services..."
    
    # Pull latest images
    compose_cmd pull
    
    # Rebuild and restart
    build_images
    restart_services
    
    success "Services updated successfully"
}

backup_data() {
    local backup_name="webdeface-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    log "INFO" "Creating backup: ${backup_name}"
    
    mkdir -p "${backup_path}"
    
    # Backup SQLite database if it exists
    if [[ -f "${DATA_DIR}/webdeface.db" ]]; then
        cp "${DATA_DIR}/webdeface.db" "${backup_path}/"
        success "Database backed up"
    fi
    
    # Backup data directory
    if [[ -d "${DATA_DIR}" ]]; then
        cp -r "${DATA_DIR}" "${backup_path}/"
        success "Data directory backed up"
    fi
    
    # Backup configuration
    if [[ -f "${ENV_FILE}" ]]; then
        cp "${ENV_FILE}" "${backup_path}/"
    fi
    
    if [[ -f "config.yaml" ]]; then
        cp "config.yaml" "${backup_path}/"
    fi
    
    # Create archive
    tar -czf "${backup_path}.tar.gz" -C "${BACKUP_DIR}" "${backup_name}"
    rm -rf "${backup_path}"
    
    success "Backup created: ${backup_path}.tar.gz"
}

restore_data() {
    local backup_file="$1"
    
    if [[ -z "${backup_file}" ]]; then
        echo -e "${WHITE}Available backups:${NC}"
        ls -la "${BACKUP_DIR}"/*.tar.gz 2>/dev/null || echo "No backups found"
        error_exit "Please specify a backup file to restore"
    fi
    
    if [[ ! -f "${backup_file}" ]]; then
        error_exit "Backup file not found: ${backup_file}"
    fi
    
    log "INFO" "Restoring from backup: $(basename "${backup_file}")"
    
    # Stop services first
    stop_services
    
    # Extract backup
    local temp_dir=$(mktemp -d)
    tar -xzf "${backup_file}" -C "${temp_dir}"
    
    # Restore data
    local backup_dir_name=$(basename "${backup_file}" .tar.gz)
    if [[ -d "${temp_dir}/${backup_dir_name}/data" ]]; then
        rm -rf "${DATA_DIR}"
        cp -r "${temp_dir}/${backup_dir_name}/data" "${DATA_DIR}"
        success "Data restored"
    fi
    
    # Restore configuration
    if [[ -f "${temp_dir}/${backup_dir_name}/.env" ]]; then
        cp "${temp_dir}/${backup_dir_name}/.env" "${ENV_FILE}"
        success "Environment configuration restored"
    fi
    
    if [[ -f "${temp_dir}/${backup_dir_name}/config.yaml" ]]; then
        cp "${temp_dir}/${backup_dir_name}/config.yaml" "config.yaml"
        success "YAML configuration restored"
    fi
    
    # Cleanup
    rm -rf "${temp_dir}"
    
    success "Restore completed. You can now start the services."
}

cleanup_docker() {
    log "INFO" "Cleaning up Docker resources..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this)
    echo -e "${YELLOW}Warning: This will remove ALL unused Docker volumes.${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Remove unused networks
    docker network prune -f
    
    success "Docker cleanup completed"
}

# Development functions
start_dev_mode() {
    local use_qdrant=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --qdrant)
                use_qdrant=true
                shift
                ;;
            *)
                warning "Unknown dev option: $1"
                shift
                ;;
        esac
    done
    
    log "INFO" "Starting development mode..."
    
    check_prerequisites
    validate_environment
    create_directories
    
    # Create development override
    cat > docker-compose.dev.yml << EOF
version: '3.8'
services:
  webdeface:
    volumes:
      - ./src:/app/src:ro
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: ["webdeface-api", "--reload"]
EOF
    
    local compose_args=(-f "${COMPOSE_FILE}" -f docker-compose.dev.yml)
    
    if [[ "${use_qdrant}" == "true" ]]; then
        compose_args+=(--profile qdrant)
        log "INFO" "Including Qdrant in development mode"
    fi
    
    compose_args+=(up -d)
    
    compose_cmd "${compose_args[@]}"
    
    # Wait for services to be healthy
    wait_for_health
    
    success "Development mode started with code hot-reloading"
    show_service_info
    
    # Cleanup dev override file
    rm -f docker-compose.dev.yml
}

run_tests() {
    log "INFO" "Running test suite..."
    
    # Build test image if needed
    if ! docker images | grep -q "webdeface.*test"; then
        log "INFO" "Building test image..."
        docker build -t webdeface:test --target base .
    fi
    
    # Run tests in container
    docker run --rm \
        -v "$(pwd):/app" \
        -w /app \
        webdeface:test \
        python -m pytest tests/ -v
    
    success "Tests completed"
}

# Help function
show_help() {
    print_header
    echo -e "\n${WHITE}USAGE:${NC}"
    echo -e "  ${SCRIPT_NAME} [COMMAND] [OPTIONS]"
    
    echo -e "\n${WHITE}SERVICE MANAGEMENT:${NC}"
    echo -e "  ${CYAN}start${NC} [--qdrant] [--foreground]  Start services"
    echo -e "  ${CYAN}stop${NC}                             Stop all services gracefully"
    echo -e "  ${CYAN}restart${NC} [--qdrant]              Restart services"
    echo -e "  ${CYAN}status${NC}                           Show service status and health"
    echo -e "  ${CYAN}logs${NC} [service] [--follow] [-n N] Display service logs"
    echo -e "  ${CYAN}shell${NC} [service] [shell]         Access container shell"
    
    echo -e "\n${WHITE}MAINTENANCE:${NC}"
    echo -e "  ${CYAN}build${NC} [--no-cache]              Rebuild Docker images"
    echo -e "  ${CYAN}update${NC}                           Pull latest images and restart"
    echo -e "  ${CYAN}backup${NC}                           Backup SQLite database and data"
    echo -e "  ${CYAN}restore${NC} <backup-file>            Restore from backup"
    echo -e "  ${CYAN}cleanup${NC}                          Remove unused Docker resources"
    
    echo -e "\n${WHITE}DEVELOPMENT:${NC}"
    echo -e "  ${CYAN}dev${NC}                              Start in development mode"
    echo -e "  ${CYAN}test${NC}                             Run test suite in container"
    
    echo -e "\n${WHITE}OPTIONS:${NC}"
    echo -e "  ${CYAN}--qdrant${NC}                         Include Qdrant vector database"
    echo -e "  ${CYAN}--foreground, -f${NC}                 Run in foreground (don't detach)"
    echo -e "  ${CYAN}--follow, -f${NC}                     Follow log output"
    echo -e "  ${CYAN}--lines, -n N${NC}                    Number of log lines to show"
    echo -e "  ${CYAN}--no-cache${NC}                       Build without using cache"
    echo -e "  ${CYAN}--help, -h${NC}                       Show this help message"
    echo -e "  ${CYAN}--version, -v${NC}                    Show version information"
    
    echo -e "\n${WHITE}EXAMPLES:${NC}"
    echo -e "  ${CYAN}${SCRIPT_NAME} start --qdrant${NC}              Start with Qdrant database"
    echo -e "  ${CYAN}${SCRIPT_NAME} logs webdeface --follow${NC}     Follow main service logs"
    echo -e "  ${CYAN}${SCRIPT_NAME} shell webdeface${NC}             Access main container shell"
    echo -e "  ${CYAN}${SCRIPT_NAME} backup${NC}                      Create data backup"
    echo -e "  ${CYAN}${SCRIPT_NAME} dev${NC}                         Start development mode"
    
    echo -e "\n${WHITE}ENVIRONMENT:${NC}"
    echo -e "  Configuration is loaded from ${CYAN}${ENV_FILE}${NC} file"
    echo -e "  Copy ${CYAN}${ENV_EXAMPLE}${NC} to ${CYAN}${ENV_FILE}${NC} and customize"
    
    echo -e "\n${WHITE}LOGS:${NC}"
    echo -e "  Script logs: ${CYAN}${log_file}${NC}"
    echo -e "  Service logs: ${CYAN}${SCRIPT_NAME} logs${NC}"
    
    echo
}

show_version() {
    echo -e "${WHITE}${PROJECT_NAME} Infrastructure Management${NC}"
    echo -e "Version: ${CYAN}${SCRIPT_VERSION}${NC}"
    echo -e "Docker Compose: ${CYAN}$(compose_cmd version --short 2>/dev/null || echo 'unknown')${NC}"
    echo -e "Docker: ${CYAN}$(docker --version | cut -d' ' -f3 | tr -d ',')${NC}"
}

# Signal handlers
cleanup_on_exit() {
    debug "Cleanup on exit"
}

trap cleanup_on_exit EXIT

# Main command dispatcher
main() {
    # Handle global options first
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                show_version
                exit 0
                ;;
            --debug)
                export DEBUG=true
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Show help if no command provided
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    local command="$1"
    shift
    
    # Dispatch to command functions
    case "${command}" in
        "start")
            start_services "$@"
            ;;
        "stop")
            stop_services "$@"
            ;;
        "restart")
            restart_services "$@"
            ;;
        "status")
            show_status "$@"
            ;;
        "logs")
            show_logs "$@"
            ;;
        "shell")
            access_shell "$@"
            ;;
        "build")
            build_images "$@"
            ;;
        "update")
            update_services "$@"
            ;;
        "backup")
            backup_data "$@"
            ;;
        "restore")
            restore_data "$@"
            ;;
        "cleanup")
            cleanup_docker "$@"
            ;;
        "dev")
            start_dev_mode "$@"
            ;;
        "test")
            run_tests "$@"
            ;;
        *)
            error_exit "Unknown command: ${command}. Use --help for usage information."
            ;;
    esac
}

# Run main function with all arguments
main "$@"