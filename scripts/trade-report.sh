#!/bin/bash

# Trade Report Script for RPI Trader
# Runs daily at 7 PM via cron

set -e

# Configuration
PROJECT_DIR="/home/andrepi/rpi-trader"
LOG_FILE="$PROJECT_DIR/logs/trade-report.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

log "Generating daily trade report..."

# Check if finance worker is running
if ! systemctl is-active --quiet "rpi-trader-finance-worker"; then
    log "Finance worker is not running, skipping trade report"
    exit 0
fi

# Get API token
API_TOKEN=$(grep API_TOKEN $PROJECT_DIR/.env | cut -d'=' -f2)

# Get today's trades
TRADES_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8003/trades/today" \
    -H "Authorization: Bearer $API_TOKEN" || echo "")

# Get account balance
BALANCE_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8003/account" \
    -H "Authorization: Bearer $API_TOKEN" || echo "")

# Get positions
POSITIONS_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8003/positions" \
    -H "Authorization: Bearer $API_TOKEN" || echo "")

# Parse responses (simplified - in production you'd use jq)
if [ -n "$TRADES_RESPONSE" ] && [ "$TRADES_RESPONSE" != "[]" ]; then
    TRADE_COUNT=$(echo "$TRADES_RESPONSE" | grep -o '"id"' | wc -l)
    TRADES_SUMMARY="• Trades executed today: $TRADE_COUNT"
else
    TRADE_COUNT=0
    TRADES_SUMMARY="• No trades executed today"
fi

# Get balance info
if [ -n "$BALANCE_RESPONSE" ]; then
    BALANCE=$(echo "$BALANCE_RESPONSE" | grep -o '"balance":[0-9.]*' | cut -d':' -f2 || echo "N/A")
    EQUITY=$(echo "$BALANCE_RESPONSE" | grep -o '"equity":[0-9.]*' | cut -d':' -f2 || echo "N/A")
    BALANCE_SUMMARY="• Account Balance: \$${BALANCE}\\n• Account Equity: \$${EQUITY}"
else
    BALANCE_SUMMARY="• Balance information unavailable"
fi

# Get positions count
if [ -n "$POSITIONS_RESPONSE" ] && [ "$POSITIONS_RESPONSE" != "[]" ]; then
    POSITION_COUNT=$(echo "$POSITIONS_RESPONSE" | grep -o '"id"' | wc -l)
    POSITIONS_SUMMARY="• Open positions: $POSITION_COUNT"
else
    POSITION_COUNT=0
    POSITIONS_SUMMARY="• No open positions"
fi

# Determine trading day status
TRADING_STATUS="🟢 Active"
if [ $TRADE_COUNT -eq 0 ] && [ $POSITION_COUNT -eq 0 ]; then
    TRADING_STATUS="🟡 Quiet day"
fi

# Create trade report
REPORT="📊 *Daily Trading Report - $(date +'%Y-%m-%d')*

💹 *Trading Activity:*
$TRADES_SUMMARY
$POSITIONS_SUMMARY

💰 *Account Status:*
$BALANCE_SUMMARY

📈 *Day Summary:*
• Trading Status: $TRADING_STATUS
• Market Session: $(date +'%A')

$([ $TRADE_COUNT -gt 0 ] && echo "Great job today! 🎯" || echo "Patience is key in trading. 🧘‍♂️")

---
*Report generated at $(date +'%H:%M:%S')*"

# Send report via Telegram
log "Sending trade report via Telegram..."
curl -s -X POST "http://127.0.0.1:8001/message" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_TOKEN" \
    -d "{
        \"message\": \"$REPORT\",
        \"parse_mode\": \"Markdown\"
    }" && log "Trade report sent successfully" || log "Failed to send trade report"

# Archive daily data (optional)
DATE_STR=$(date +'%Y-%m-%d')
ARCHIVE_DIR="$PROJECT_DIR/data/archives/$DATE_STR"
mkdir -p "$ARCHIVE_DIR"

# Save raw data for historical analysis
echo "$TRADES_RESPONSE" > "$ARCHIVE_DIR/trades.json" 2>/dev/null || true
echo "$BALANCE_RESPONSE" > "$ARCHIVE_DIR/balance.json" 2>/dev/null || true
echo "$POSITIONS_RESPONSE" > "$ARCHIVE_DIR/positions.json" 2>/dev/null || true

log "Daily trade report generation completed"

