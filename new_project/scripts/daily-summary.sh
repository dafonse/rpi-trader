#!/bin/bash

# Daily Summary Script for RPI Trader
# Runs daily at 8 AM via cron

set -e

# Configuration
PROJECT_DIR="/home/pi/rpi-trader"
LOG_FILE="$PROJECT_DIR/logs/daily-summary.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

log "Generating daily summary..."

# Get system metrics
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
UPTIME=$(uptime -p)

# Get temperature (Raspberry Pi specific)
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    TEMP=$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
else
    TEMP="N/A"
fi

# Check service status
SERVICES=("rpi-trader-bot-gateway" "rpi-trader-scheduler" "rpi-trader-finance-worker" "rpi-trader-market-worker" "rpi-trader-execution-worker")
ACTIVE_SERVICES=0
TOTAL_SERVICES=${#SERVICES[@]}

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        ((ACTIVE_SERVICES++))
    fi
done

# Get trading statistics (if finance worker is available)
TRADING_STATS=""
if systemctl is-active --quiet "rpi-trader-finance-worker"; then
    TRADING_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8003/daily-stats" \
        -H "Authorization: Bearer $(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)" || echo "")
    
    if [ -n "$TRADING_RESPONSE" ]; then
        TRADING_STATS="\\n📊 *Trading Summary:*\\n$TRADING_RESPONSE"
    fi
fi

# Create summary message
SUMMARY="🌅 *Daily System Summary - $(date +'%Y-%m-%d')*

🖥️ *System Health:*
• CPU Usage: ${CPU_USAGE}%
• Memory Usage: ${MEMORY_USAGE}%
• Disk Usage: ${DISK_USAGE}%
• Temperature: ${TEMP}°C
• Uptime: ${UPTIME}

🔧 *Services:*
• Active: ${ACTIVE_SERVICES}/${TOTAL_SERVICES}
• Status: $([ $ACTIVE_SERVICES -eq $TOTAL_SERVICES ] && echo "🟢 All services running" || echo "🟡 Some services down")
${TRADING_STATS}

📈 *System Status:* $([ $ACTIVE_SERVICES -eq $TOTAL_SERVICES ] && [ ${DISK_USAGE} -lt 80 ] && [ ${TEMP%.*} -lt 70 ] && echo "🟢 Healthy" || echo "🟡 Needs attention")

Have a great trading day! 📊"

# Send summary via Telegram
log "Sending daily summary via Telegram..."
curl -s -X POST "http://127.0.0.1:8001/message" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)" \
    -d "{
        \"message\": \"$SUMMARY\",
        \"parse_mode\": \"Markdown\"
    }" && log "Daily summary sent successfully" || log "Failed to send daily summary"

log "Daily summary generation completed"

