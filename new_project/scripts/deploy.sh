#!/bin/bash

# RPI Trader Deployment Script
# This script sets up the complete RPI Trader system on Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/pi/rpi-trader"
USER="pi"
GROUP="pi"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as user 'pi'."
        exit 1
    fi
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        warning "This doesn't appear to be a Raspberry Pi. Continuing anyway..."
    fi
}

# Install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    
    sudo apt update
    sudo apt install -y \
        python3-dev \
        python3-pip \
        git \
        curl \
        wget \
        build-essential \
        libssl-dev \
        libffi-dev \
        sqlite3 \
        systemd \
        psmisc \
        htop \
        vim \
        nano
    
    success "System dependencies installed"
}

# Install Miniconda
install_miniconda() {
    log "Checking for Miniconda installation..."
    
    if [ -d "/home/pi/miniconda3" ]; then
        log "Miniconda already installed"
        return
    fi
    
    log "Installing Miniconda..."
    cd /tmp
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O miniconda.sh
    bash miniconda.sh -b -p /home/pi/miniconda3
    rm miniconda.sh
    
    # Initialize conda
    /home/pi/miniconda3/bin/conda init bash
    source ~/.bashrc
    
    success "Miniconda installed"
}

# Create conda environments
create_conda_environments() {
    log "Creating conda environments..."
    
    # Source conda
    source /home/pi/miniconda3/etc/profile.d/conda.sh
    
    # Environment configurations
    declare -A envs=(
        ["env-bot"]="python=3.11 python-telegram-bot fastapi uvicorn httpx psutil structlog python-dotenv pydantic-settings aiohttp"
        ["env-scheduler"]="python=3.11 apscheduler fastapi uvicorn httpx structlog python-dotenv pydantic-settings"
        ["env-finance"]="python=3.11 fastapi uvicorn sqlalchemy pandas numpy structlog python-dotenv pydantic-settings"
        ["env-market"]="python=3.11 fastapi uvicorn pandas numpy websockets httpx structlog python-dotenv pydantic-settings yfinance aiohttp"
        ["env-execution"]="python=3.11 fastapi uvicorn pandas numpy httpx structlog python-dotenv pydantic-settings aiohttp"
    )
    
    for env_name in "${!envs[@]}"; do
        log "Creating environment: $env_name"
        
        if conda env list | grep -q "^$env_name "; then
            log "Environment $env_name already exists, updating..."
            conda env update -n "$env_name" --file /dev/stdin <<< "dependencies: [${envs[$env_name]}]"
        else
            conda create -n "$env_name" -y ${envs[$env_name]}
        fi
    done
    
    success "Conda environments created"
}

# Setup project directory
setup_project_directory() {
    log "Setting up project directory..."
    
    # Ensure correct ownership
    sudo chown -R $USER:$GROUP $PROJECT_DIR
    chmod -R 755 $PROJECT_DIR
    
    # Create necessary directories
    mkdir -p $PROJECT_DIR/{logs,data,models,backups}
    
    # Set up environment file
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log "Creating .env file from template..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        chmod 600 "$PROJECT_DIR/.env"
        warning "Please edit $PROJECT_DIR/.env with your actual configuration values"
    fi
    
    success "Project directory setup complete"
}

# Install Python packages in editable mode
install_python_packages() {
    log "Installing Python packages in editable mode..."
    
    source /home/pi/miniconda3/etc/profile.d/conda.sh
    
    # Install main libs package in all environments
    for env in env-bot env-scheduler env-finance env-market env-execution; do
        log "Installing libs package in $env..."
        conda activate $env
        cd $PROJECT_DIR
        pip install -e .
        conda deactivate
    done
    
    # Install individual app packages
    declare -A app_envs=(
        ["apps/bot_gateway"]="env-bot"
        ["apps/scheduler"]="env-scheduler"
        ["apps/finance_worker"]="env-finance"
        ["apps/market_worker"]="env-market"
        ["apps/execution_worker"]="env-execution"
    )
    
    for app_dir in "${!app_envs[@]}"; do
        env_name="${app_envs[$app_dir]}"
        if [ -f "$PROJECT_DIR/$app_dir/pyproject.toml" ]; then
            log "Installing $app_dir in $env_name..."
            conda activate $env_name
            cd "$PROJECT_DIR/$app_dir"
            pip install -e .
            conda deactivate
        fi
    done
    
    success "Python packages installed"
}

# Install systemd services
install_systemd_services() {
    log "Installing systemd services..."
    
    # Copy service files
    for service_file in $PROJECT_DIR/services/*.service; do
        if [ -f "$service_file" ]; then
            service_name=$(basename "$service_file")
            log "Installing service: $service_name"
            sudo cp "$service_file" /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable "$service_name"
        fi
    done
    
    success "Systemd services installed"
}

# Setup cron jobs
setup_cron_jobs() {
    log "Setting up cron jobs..."
    
    # Create cron script
    cat > /tmp/rpi-trader-cron << 'EOF'
# RPI Trader Cron Jobs
# System updates at 3 AM
0 3 * * * /home/pi/rpi-trader/scripts/system-update.sh >> /home/pi/rpi-trader/logs/cron.log 2>&1

# Daily summary at 8 AM
0 8 * * * /home/pi/rpi-trader/scripts/daily-summary.sh >> /home/pi/rpi-trader/logs/cron.log 2>&1

# Trade reports at 7 PM
0 19 * * * /home/pi/rpi-trader/scripts/trade-report.sh >> /home/pi/rpi-trader/logs/cron.log 2>&1

# Health check every 15 minutes
*/15 * * * * /home/pi/rpi-trader/scripts/health-check.sh >> /home/pi/rpi-trader/logs/cron.log 2>&1
EOF
    
    # Install cron jobs (avoid duplicates)
    if ! crontab -l 2>/dev/null | grep -q "RPI Trader Cron Jobs"; then
        (crontab -l 2>/dev/null; cat /tmp/rpi-trader-cron) | crontab -
        log "Cron jobs installed"
    else
        log "Cron jobs already installed"
    fi
    
    rm /tmp/rpi-trader-cron
    success "Cron jobs setup complete"
}

# Create helper scripts
create_helper_scripts() {
    log "Creating helper scripts..."
    
    # Make all scripts executable
    chmod +x $PROJECT_DIR/scripts/*.sh
    
    success "Helper scripts created"
}

# Start services
start_services() {
    log "Starting RPI Trader services..."
    
    services=(
        "rpi-trader-bot-gateway"
        "rpi-trader-scheduler"
        "rpi-trader-finance-worker"
        "rpi-trader-market-worker"
        "rpi-trader-execution-worker"
    )
    
    for service in "${services[@]}"; do
        log "Starting $service..."
        sudo systemctl start "$service"
        
        # Wait a moment and check status
        sleep 2
        if sudo systemctl is-active --quiet "$service"; then
            success "$service started successfully"
        else
            error "$service failed to start"
            sudo systemctl status "$service" --no-pager -l
        fi
    done
}

# Show status
show_status() {
    log "RPI Trader System Status:"
    echo
    
    services=(
        "rpi-trader-bot-gateway"
        "rpi-trader-scheduler"
        "rpi-trader-finance-worker"
        "rpi-trader-market-worker"
        "rpi-trader-execution-worker"
    )
    
    for service in "${services[@]}"; do
        if sudo systemctl is-active --quiet "$service"; then
            echo -e "  ${GREEN}●${NC} $service: ${GREEN}active${NC}"
        else
            echo -e "  ${RED}●${NC} $service: ${RED}inactive${NC}"
        fi
    done
    
    echo
    log "Deployment complete!"
    echo
    echo "Next steps:"
    echo "1. Edit $PROJECT_DIR/.env with your configuration"
    echo "2. Test the Telegram bot by sending /start"
    echo "3. Monitor logs: sudo journalctl -f -u rpi-trader-*"
    echo "4. Check status: sudo systemctl status rpi-trader-*"
}

# Main deployment function
main() {
    log "Starting RPI Trader deployment..."
    
    check_root
    check_raspberry_pi
    
    install_system_dependencies
    install_miniconda
    create_conda_environments
    setup_project_directory
    install_python_packages
    install_systemd_services
    setup_cron_jobs
    create_helper_scripts
    start_services
    show_status
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "update")
        log "Updating RPI Trader..."
        install_python_packages
        sudo systemctl daemon-reload
        for service in rpi-trader-*; do
            sudo systemctl restart "$service" 2>/dev/null || true
        done
        show_status
        ;;
    "start")
        start_services
        ;;
    "stop")
        log "Stopping RPI Trader services..."
        for service in rpi-trader-*; do
            sudo systemctl stop "$service" 2>/dev/null || true
        done
        ;;
    "status")
        show_status
        ;;
    "logs")
        sudo journalctl -f -u rpi-trader-*
        ;;
    *)
        echo "Usage: $0 {deploy|update|start|stop|status|logs}"
        echo
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  update  - Update and restart services"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  status  - Show service status"
        echo "  logs    - Show live logs"
        exit 1
        ;;
esac

