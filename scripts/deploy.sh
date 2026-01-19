#!/bin/bash

# Budget Survey Application Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environment: dev, prod (default: dev)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
PROJECT_NAME="budget-survey"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get the correct docker compose command
get_docker_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command_exists docker-compose; then
        echo "docker-compose"
    else
        print_error "Neither 'docker compose' nor 'docker-compose' is available"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check for Docker Compose (v2 plugin or standalone)
    if ! docker compose version >/dev/null 2>&1 && ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running or you don't have permission to access it."
        print_error "Try: sudo usermod -aG docker $USER && newgrp docker"
        exit 1
    fi
    
    # Check for port conflicts
    check_port_conflicts
    
    print_success "Prerequisites check passed"
}

# Check for port conflicts
check_port_conflicts() {
    local ports_to_check=("5000" "5001" "3306" "8080" "8025")
    local conflicted_ports=()
    
    for port in "${ports_to_check[@]}"; do
        if command_exists lsof; then
            if lsof -i :$port >/dev/null 2>&1; then
                conflicted_ports+=($port)
            fi
        elif command_exists netstat; then
            if netstat -tuln 2>/dev/null | grep -q ":$port "; then
                conflicted_ports+=($port)
            fi
        fi
    done
    
    if [ ${#conflicted_ports[@]} -gt 0 ]; then
        print_warning "Port conflicts detected:"
        for port in "${conflicted_ports[@]}"; do
            print_warning "  Port $port is already in use"
        done
        print_warning "You can:"
        print_warning "  1. Stop the conflicting services"
        print_warning "  2. Change ports in .env file (APP_PORT, MYSQL_PORT, etc.)"
        print_warning "  3. Use: lsof -i :PORT to find the process"
        echo
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Enable BuildKit for better caching and performance
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            print_warning "Created .env from .env.example. Please review and update the configuration."
            print_warning "Edit $PROJECT_ROOT/.env with your specific settings before continuing."
            
            if [ "$ENVIRONMENT" = "prod" ]; then
                print_warning "For production deployment, make sure to:"
                print_warning "  1. Set FLASK_ENV=production"
                print_warning "  2. Generate a secure FLASK_SECRET_KEY"
                print_warning "  3. Set strong database passwords"
                print_warning "  4. Configure SURVEY_BASE_URL with your domain"
                read -p "Press Enter after updating .env file to continue..."
            fi
        else
            print_error ".env.example file not found. Cannot create environment configuration."
            exit 1
        fi
    else
        print_success "Environment file already exists"
    fi
}

# Generate secure secret key
generate_secret_key() {
    print_status "Generating secure secret key..."
    
    if command_exists python3; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        print_success "Generated secret key: $SECRET_KEY"
        print_warning "Add this to your .env file: FLASK_SECRET_KEY=$SECRET_KEY"
    elif command_exists openssl; then
        SECRET_KEY=$(openssl rand -hex 32)
        print_success "Generated secret key: $SECRET_KEY"
        print_warning "Add this to your .env file: FLASK_SECRET_KEY=$SECRET_KEY"
    else
        print_warning "Cannot generate secret key automatically. Please generate one manually."
        print_warning "Use: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    fi
}

# Setup SSL certificates for production
setup_ssl() {
    if [ "$ENVIRONMENT" = "prod" ]; then
        print_status "Setting up SSL certificates..."
        
        mkdir -p "$PROJECT_ROOT/ssl"
        
        if [ ! -f "$PROJECT_ROOT/ssl/cert.pem" ] || [ ! -f "$PROJECT_ROOT/ssl/key.pem" ]; then
            print_warning "SSL certificates not found in ssl/ directory"
            print_warning "For production deployment, you need SSL certificates:"
            print_warning "  1. Copy your certificate to ssl/cert.pem"
            print_warning "  2. Copy your private key to ssl/key.pem"
            print_warning ""
            print_warning "Or use Let's Encrypt:"
            print_warning "  sudo apt install certbot"
            print_warning "  sudo certbot certonly --standalone -d your-domain.com"
            print_warning "  sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem"
            print_warning "  sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem"
            print_warning "  sudo chown \$USER:\$USER ssl/*"
            
            read -p "Press Enter after setting up SSL certificates to continue..."
        else
            print_success "SSL certificates found"
        fi
    fi
}

# Deploy development environment
deploy_dev() {
    print_status "Deploying development environment..."
    
    cd "$PROJECT_ROOT"
    
    local COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Stop existing containers
    $COMPOSE_CMD -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Build and start services
    $COMPOSE_CMD -f docker-compose.dev.yml up -d --build
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 10
    
    # Check service status
    if $COMPOSE_CMD -f docker-compose.dev.yml ps | grep -q "healthy\|Up"; then
        print_success "Development environment deployed successfully!"
        print_success "Application: http://localhost:5001"
        print_success "phpMyAdmin: http://localhost:8080"
        print_success ""
        print_status "Useful commands:"
        print_status "  View logs: $COMPOSE_CMD -f docker-compose.dev.yml logs -f"
        print_status "  Stop: $COMPOSE_CMD -f docker-compose.dev.yml down"
        print_status "  Shell: $COMPOSE_CMD -f docker-compose.dev.yml exec app bash"
    else
        print_error "Deployment failed. Check logs with:"
        print_error "$COMPOSE_CMD -f docker-compose.dev.yml logs"
        exit 1
    fi
}

# Deploy production environment
deploy_prod() {
    print_status "Deploying production environment..."
    
    cd "$PROJECT_ROOT"
    
    local COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Stop existing containers
    $COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Build and start services
    $COMPOSE_CMD -f docker-compose.prod.yml up -d --build
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 20
    
    # Run tests before completing deployment
    print_status "Running tests to verify deployment..."
    if ! $COMPOSE_CMD -f docker-compose.prod.yml exec -T app pytest --maxfail=1 -q; then
        print_error "Tests failed! Rolling back deployment..."
        $COMPOSE_CMD -f docker-compose.prod.yml down
        print_error "Deployment aborted. Previous version (if any) is still running."
        exit 1
    fi
    print_success "All tests passed!"
    
    # Check service status
    if $COMPOSE_CMD -f docker-compose.prod.yml ps | grep -q "healthy\|Up"; then
        print_success "Production environment deployed successfully!"
        print_success "Application: https://your-domain.com"
        print_success "Health check: curl -f http://localhost/health"
        print_success ""
        print_status "Useful commands:"
        print_status "  View logs: $COMPOSE_CMD -f docker-compose.prod.yml logs -f"
        print_status "  Stop: $COMPOSE_CMD -f docker-compose.prod.yml down"
        print_status "  Update: git pull && $COMPOSE_CMD -f docker-compose.prod.yml up -d --build"
        print_status "  Backup DB: $COMPOSE_CMD -f docker-compose.prod.yml exec db mysqldump -u root -p survey > backup.sql"
    else
        print_error "Deployment failed. Check logs with:"
        print_error "$COMPOSE_CMD -f docker-compose.prod.yml logs"
        exit 1
    fi
}

# Setup log rotation for production
setup_log_rotation() {
    if [ "$ENVIRONMENT" = "prod" ]; then
        print_status "Setting up log rotation..."
        
        local COMPOSE_CMD=$(get_docker_compose_cmd)
        cat > /tmp/budget-survey-logrotate << EOF
/home/*/budget-survey/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $(whoami) $(whoami)
    postrotate
        cd /home/$(whoami)/budget-survey && $COMPOSE_CMD restart nginx 2>/dev/null || true
    endscript
}
EOF
        
        if sudo mv /tmp/budget-survey-logrotate /etc/logrotate.d/budget-survey; then
            print_success "Log rotation configured"
        else
            print_warning "Could not configure log rotation (requires sudo)"
        fi
    fi
}

# Main deployment function
main() {
    echo "=================================================="
    echo "Budget Survey Application Deployment Script"
    echo "Environment: $ENVIRONMENT"
    echo "=================================================="
    
    check_prerequisites
    setup_environment
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        generate_secret_key
        setup_ssl
        deploy_prod
        setup_log_rotation
    else
        deploy_dev
    fi
    
    print_success "Deployment completed!"
}

# Show usage if no valid environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Usage: $0 [environment]"
    echo "Environment options:"
    echo "  dev  - Development environment (default)"
    echo "  prod - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 dev   # Deploy development environment"
    echo "  $0 prod  # Deploy production environment"
    exit 1
fi

# Run main function
main 