# RPI Trader - Deployment Guide for Raspberry Pi 5

## Quick Start Instructions

### 1. Transfer Files to Your Raspberry Pi

```bash
# On your Raspberry Pi 5, download and extract the project
wget <download-link>/rpi-trader-complete.tar.gz
tar -xzf rpi-trader-complete.tar.gz
sudo mv rpi-trader /home/andrepi/rpi-trader
sudo chown -R pi:pi /home/andrepi/rpi-trader
```

### 2. Run the Automated Deployment

```bash
cd /home/andrepi/rpi-trader
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Configure Your Settings

```bash
# Edit the environment file with your settings
nano /home/andrepi/rpi-trader/.env

# Required settings:
# - TELEGRAM_BOT_TOKEN (get from @BotFather)
# - ALLOWED_CHAT_ID (your Telegram chat ID)
# - MT5_* settings (your MetaTrader credentials)
# - Set DRY_RUN_MODE=false when ready for live trading
```

### 4. Start Trading

```bash
# Check system status
./scripts/deploy.sh status

# Send /start to your Telegram bot
# Use /help to see all available commands
```

## What's Included

### Complete Project Structure
- **5 Microservices**: Bot Gateway, Scheduler, Finance Worker, Market Worker, Execution Worker
- **Shared Libraries**: Core utilities, data models, signal processing, ML models, broker integration
- **Systemd Services**: Automatic startup and monitoring
- **Automated Scripts**: Deployment, health checks, daily reports
- **Comprehensive Documentation**: 50+ pages of detailed documentation

### Key Features
- **Telegram Bot Control**: Full system control via Telegram
- **MetaTrader Integration**: Support for MT5 direct or remote API
- **AI/ML Signals**: Technical analysis and machine learning models
- **Risk Management**: Daily loss limits, emergency stops, position sizing
- **Automated Monitoring**: Health checks, alerts, daily reports
- **Security**: Localhost-only APIs, token authentication, encrypted configs

### Safety Features
- **Dry Run Mode**: Test strategies without real money
- **Emergency Stop**: Instant trading halt via Telegram (/stop_trading)
- **Daily Loss Limits**: Automatic trading halt if losses exceed limits
- **Position Size Limits**: Maximum order size restrictions
- **Comprehensive Logging**: Full audit trail of all decisions

## Important Notes

### Before Live Trading
1. **Test Thoroughly**: Use DRY_RUN_MODE=true extensively
2. **Start Small**: Set conservative limits initially
3. **Monitor Closely**: Watch the system for the first few days
4. **Backup Regularly**: The system includes automated backups

### Security Reminders
- Keep your .env file secure (chmod 600)
- Use strong passwords and API tokens
- Monitor system logs regularly
- Update the system regularly via automated scripts

### Support
- Check the comprehensive README.md for detailed documentation
- Use the troubleshooting section for common issues
- Monitor logs: `sudo journalctl -f -u rpi-trader-*`
- System status: `./scripts/deploy.sh status`

## System Requirements Met
✅ Raspberry Pi 5 (8GB RAM) optimized  
✅ Multiple isolated Conda environments  
✅ Modern Python packaging (pyproject.toml)  
✅ Systemd service management  
✅ Comprehensive security implementation  
✅ Real-time trading capability  
✅ Complete audit trail and logging  
✅ Automated deployment and maintenance  

**Ready for production use with proper configuration and testing!**

