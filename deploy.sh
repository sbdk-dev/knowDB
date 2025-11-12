#!/bin/bash

# Semantic Layer Production Deployment Script
# This script provides easy commands for deploying and managing the semantic layer platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="backups"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    log_success "Requirements check passed"
}

setup_environment() {
    log_info "Setting up environment..."

    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found, copying from .env.example"
        cp .env.example .env
        log_warning "Please edit .env file with your configuration before deploying"
        return 1
    fi

    # Create required directories
    mkdir -p data logs semantic_models backups

    log_success "Environment setup complete"
}

build_images() {
    log_info "Building Docker images..."
    docker-compose build --no-cache
    log_success "Docker images built successfully"
}

start_services() {
    local profile="$1"
    log_info "Starting semantic layer services..."

    if [ -n "$profile" ]; then
        docker-compose --profile "$profile" up -d
    else
        docker-compose up -d
    fi

    log_success "Services started successfully"

    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 10
    docker-compose ps
}

stop_services() {
    log_info "Stopping semantic layer services..."
    docker-compose down
    log_success "Services stopped successfully"
}

restart_services() {
    log_info "Restarting semantic layer services..."
    docker-compose restart
    log_success "Services restarted successfully"
}

show_logs() {
    local service="$1"
    if [ -n "$service" ]; then
        docker-compose logs -f "$service"
    else
        docker-compose logs -f
    fi
}

show_status() {
    log_info "Service status:"
    docker-compose ps

    echo ""
    log_info "Health checks:"

    # Check API health
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Semantic Layer API: Healthy"
    else
        log_error "Semantic Layer API: Unhealthy"
    fi

    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis Cache: Healthy"
    else
        log_error "Redis Cache: Unhealthy"
    fi
}

backup_data() {
    log_info "Creating backup..."

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/semantic_layer_backup_$timestamp.tar.gz"

    mkdir -p "$BACKUP_DIR"

    # Backup semantic models and data
    tar -czf "$backup_file" \
        semantic_models/ \
        data/ \
        .env \
        2>/dev/null || log_warning "Some files may not exist"

    log_success "Backup created: $backup_file"
}

update_deployment() {
    log_info "Updating deployment..."

    # Create backup first
    backup_data

    # Pull latest changes
    git pull origin main

    # Rebuild and restart
    build_images
    restart_services

    log_success "Deployment updated successfully"
}

run_tests() {
    log_info "Running tests..."

    # Start test dependencies
    docker-compose up -d redis

    # Run tests in container
    docker-compose run --rm semantic-layer uv run pytest tests/

    log_success "Tests completed"
}

cleanup() {
    log_info "Cleaning up..."

    # Stop and remove containers
    docker-compose down -v

    # Remove unused images
    docker image prune -f

    # Remove unused volumes
    docker volume prune -f

    log_success "Cleanup completed"
}

show_help() {
    echo "Semantic Layer Deployment Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup                 Setup environment and configuration"
    echo "  build                 Build Docker images"
    echo "  start [profile]       Start services (optional profile: postgres, nginx, monitoring)"
    echo "  stop                  Stop all services"
    echo "  restart               Restart all services"
    echo "  status                Show service status and health"
    echo "  logs [service]        Show logs (optional: specify service)"
    echo "  backup                Create backup of data and configuration"
    echo "  update                Update deployment with latest code"
    echo "  test                  Run tests"
    echo "  cleanup               Stop services and clean up resources"
    echo "  help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup              # Initial setup"
    echo "  $0 start              # Start basic services"
    echo "  $0 start postgres     # Start with PostgreSQL"
    echo "  $0 start monitoring   # Start with monitoring stack"
    echo "  $0 logs semantic-layer # Show API logs"
    echo "  $0 status             # Check service health"
}

# Main command handler
case "$1" in
    setup)
        check_requirements
        setup_environment
        ;;
    build)
        check_requirements
        build_images
        ;;
    start)
        check_requirements
        setup_environment || exit 1
        start_services "$2"
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    backup)
        backup_data
        ;;
    update)
        update_deployment
        ;;
    test)
        run_tests
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac