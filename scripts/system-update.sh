#!/bin/bash

# System Update Script for RPI Trader
# Runs daily at 3 AM via cron

set -e

# Configuration
PROJECT_DIR="/home/andrepi/rpi-trader"
LOG_FILE="$PROJECT_DIR/logs/system-update.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

log "Starting system update..."

# Update package lists
log "Updating package lists..."
sudo apt update

# Check for available upgrades
UPGRADES=$(apt list --upgradable 2>/dev/null | grep -c upgradable || true)

if [ "$UPGRADES" -gt 1 ]; then  # -gt 1 because header line is counted
    log "Found $((UPGRADES-1)) packages to upgrade"
    
    # Perform upgrade (non-interactive)
    sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y
    
    log "System packages upgraded successfully"
    
    # Check if reboot is required
    if [ -f /var/run/reboot-required ]; then
        log "Reboot required after updates"
        
        # Send notification via Telegram bot
        curl -s -X POST "http://127.0.0.1:8001/alert" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)" \
            -d '{
                "title": "System Update Complete",
                "message": "System packages have been updated. A reboot is required and will be performed at the next maintenance window."
            }' || log "Failed to send Telegram notification"
    fi
else
    log "No package updates available"
fi

# Clean up package cache
log "Cleaning package cache..."
sudo apt autoremove -y
sudo apt autoclean

# Update conda environments
log "Updating conda environments..."
source /home/andrepi/miniconda3/etc/profile.d/conda.sh

for env in env-bot env-scheduler env-finance env-market env-execution; do
    log "Updating conda environment: $env"
    conda activate "$env"
    conda update --all -y || log "Failed to update $env"
    conda deactivate
done

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "WARNING: Disk usage is at ${DISK_USAGE}%"
    
    # Send alert
    curl -s -X POST "http://127.0.0.1:8001/alert" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)" \
        -d "{
            \"title\": \"High Disk Usage Warning\",
            \"message\": \"Disk usage is at ${DISK_USAGE}%. Please check and clean up disk space.\"
        }" || log "Failed to send disk usage alert"
fi

log "System update completed successfully"

