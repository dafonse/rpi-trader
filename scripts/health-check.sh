#!/bin/bash

# Health Check Script for RPI Trader
# Runs every 15 minutes via cron

set -e

# Configuration
PROJECT_DIR="/home/andrepi/rpi-trader"
LOG_FILE="$PROJECT_DIR/logs/health-check.log"
ALERT_THRESHOLD_FILE="$PROJECT_DIR/data/last_alert.txt"

# Thresholds
CPU_THRESHOLD=90
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
TEMP_THRESHOLD=75

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$ALERT_THRESHOLD_FILE")"

# Function to send alert (with rate limiting)
send_alert() {
    local title="$1"
    local message="$2"
    local alert_key="$3"
    
    # Check if we've sent this alert recently (within 1 hour)
    local last_alert_time=0
    if [ -f "$ALERT_THRESHOLD_FILE" ]; then
        last_alert_time=$(grep "^$alert_key:" "$ALERT_THRESHOLD_FILE" 2>/dev/null | cut -d':' -f2 || echo 0)
    fi
    
    local current_time=$(date +%s)
    local time_diff=$((current_time - last_alert_time))
    
    # Only send alert if more than 1 hour has passed
    if [ $time_diff -gt 3600 ]; then
        curl -s -X POST "http://127.0.0.1:8001/alert" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)" \
            -d "{
                \"title\": \"$title\",
                \"message\": \"$message\"
            }" && {
                log "Alert sent: $title"
                # Update last alert time
                grep -v "^$alert_key:" "$ALERT_THRESHOLD_FILE" 2>/dev/null > "${ALERT_THRESHOLD_FILE}.tmp" || true
                echo "$alert_key:$current_time" >> "${ALERT_THRESHOLD_FILE}.tmp"
                mv "${ALERT_THRESHOLD_FILE}.tmp" "$ALERT_THRESHOLD_FILE"
            } || log "Failed to send alert: $title"
    fi
}

# Check CPU usage
check_cpu() {
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | cut -d'.' -f1)
    
    if [ "$cpu_usage" -gt "$CPU_THRESHOLD" ]; then
        log "HIGH CPU USAGE: ${cpu_usage}%"
        send_alert "High CPU Usage" "CPU usage is at ${cpu_usage}%, which exceeds the threshold of ${CPU_THRESHOLD}%." "high_cpu"
    fi
}

# Check memory usage
check_memory() {
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [ "$memory_usage" -gt "$MEMORY_THRESHOLD" ]; then
        log "HIGH MEMORY USAGE: ${memory_usage}%"
        send_alert "High Memory Usage" "Memory usage is at ${memory_usage}%, which exceeds the threshold of ${MEMORY_THRESHOLD}%." "high_memory"
    fi
}

# Check disk usage
check_disk() {
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        log "HIGH DISK USAGE: ${disk_usage}%"
        send_alert "High Disk Usage" "Disk usage is at ${disk_usage}%, which exceeds the threshold of ${DISK_THRESHOLD}%." "high_disk"
    fi
}

# Check temperature (Raspberry Pi specific)
check_temperature() {
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        local temp=$(awk '{printf "%.0f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
        
        if [ "$temp" -gt "$TEMP_THRESHOLD" ]; then
            log "HIGH TEMPERATURE: ${temp}°C"
            send_alert "High Temperature Warning" "CPU temperature is at ${temp}°C, which exceeds the threshold of ${TEMP_THRESHOLD}°C." "high_temp"
        fi
    fi
}

# Check service status
check_services() {
    local services=("rpi-trader-bot-gateway" "rpi-trader-scheduler" "rpi-trader-finance-worker" "rpi-trader-market-worker" "rpi-trader-execution-worker")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            failed_services+=("$service")
            log "SERVICE DOWN: $service"
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        local failed_list=$(IFS=', '; echo "${failed_services[*]}")
        send_alert "Service Failure" "The following services are not running: $failed_list" "service_failure"
        
        # Attempt to restart failed services
        for service in "${failed_services[@]}"; do
            log "Attempting to restart $service"
            sudo systemctl restart "$service" && log "Successfully restarted $service" || log "Failed to restart $service"
        done
    fi
}

# Check network connectivity
check_network() {
    if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log "NETWORK CONNECTIVITY ISSUE"
        send_alert "Network Connectivity Issue" "Unable to reach external network. Internet connection may be down." "network_down"
    fi
}

# Check database connectivity (if using external database)
check_database() {
    # This is a placeholder - implement based on your database setup
    # For SQLite, we can check if the file exists and is readable
    local db_file="$PROJECT_DIR/rpi_trader.db"
    if [ -f "$db_file" ]; then
        if ! sqlite3 "$db_file" "SELECT 1;" >/dev/null 2>&1; then
            log "DATABASE CONNECTIVITY ISSUE"
            send_alert "Database Issue" "Unable to connect to the trading database." "database_error"
        fi
    fi
}

# Main health check function
main() {
    log "Starting health check..."
    
    check_cpu
    check_memory
    check_disk
    check_temperature
    check_services
    check_network
    check_database
    
    log "Health check completed"
}

# Run health check
main

# Clean up old log files (keep last 7 days)
find "$PROJECT_DIR/logs" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true

# Clean up old alert threshold data (keep last 30 days)
if [ -f "$ALERT_THRESHOLD_FILE" ]; then
    local cutoff_time=$(($(date +%s) - 2592000))  # 30 days ago
    awk -F: -v cutoff="$cutoff_time" '$2 > cutoff' "$ALERT_THRESHOLD_FILE" > "${ALERT_THRESHOLD_FILE}.tmp" || true
    mv "${ALERT_THRESHOLD_FILE}.tmp" "$ALERT_THRESHOLD_FILE" 2>/dev/null || true
fi

