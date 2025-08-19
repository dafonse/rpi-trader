# RPI Trader - Modular Automation and Day Trading Platform

**Version:** 0.1.0  
**Author:** dafonse 
**Target Platform:** Raspberry Pi 5 (8GB RAM, Raspberry Pi OS)  
**License:** Proprietary  

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [API Documentation](#api-documentation)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Development](#development)
12. [Security Considerations](#security-considerations)
13. [Contributing](#contributing)
14. [License](#license)

## Overview

RPI Trader is a comprehensive, modular automation and day trading platform specifically designed for Raspberry Pi 5. The system provides a robust, secure, and scalable solution for automated trading operations, controlled via Telegram, with multiple specialized worker services handling different aspects of the trading pipeline.

The platform is built with modern Python practices, utilizing isolated Conda environments, FastAPI for inter-service communication, and systemd for service management. It supports real-time trading with real money while maintaining strict security protocols and risk management features.

### Key Capabilities

- **Telegram Bot Control**: Complete system control and monitoring via Telegram bot interface
- **Modular Architecture**: Separate worker services for different functionalities
- **MetaTrader Integration**: Support for both direct MT5 integration and remote API connections
- **AI/ML Signal Generation**: Built-in technical analysis and machine learning models
- **Risk Management**: Comprehensive safeguards including daily loss limits and emergency stops
- **System Monitoring**: Automated health checks, alerts, and reporting
- **Secure Design**: Localhost-only APIs, environment-based configuration, and structured logging

## Architecture

The RPI Trader platform follows a microservices architecture with the following components:



### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        RPI Trader System                        │
├─────────────────────────────────────────────────────────────────┤
│  Telegram Bot Gateway (Port 8001)                              │
│  ├── Command Handlers                                          │
│  ├── Authentication & Authorization                            │
│  └── Alert & Notification System                               │
├─────────────────────────────────────────────────────────────────┤
│  Scheduler Service (Port 8002)                                 │
│  ├── APScheduler for Internal Jobs                             │
│  ├── Systemd Timer Integration                                 │
│  └── Task Orchestration                                        │
├─────────────────────────────────────────────────────────────────┤
│  Finance Worker (Port 8003)                                    │
│  ├── Trade Reporting & Analysis                                │
│  ├── P&L Calculations                                          │
│  ├── Database Management                                       │
│  └── Account Information                                       │
├─────────────────────────────────────────────────────────────────┤
│  Market Worker (Port 8004)                                     │
│  ├── Market Data Ingestion                                     │
│  ├── Real-time Price Feeds                                     │
│  ├── Technical Analysis                                        │
│  └── Signal Generation                                         │
├─────────────────────────────────────────────────────────────────┤
│  Execution Worker (Port 8005)                                  │
│  ├── Order Management                                          │
│  ├── Risk Control                                              │
│  ├── Broker Integration                                        │
│  └── Emergency Stop System                                     │
├─────────────────────────────────────────────────────────────────┤
│  Shared Libraries                                              │
│  ├── Core Utilities (Config, Logging, Security)               │
│  ├── Data Models & Repository Layer                            │
│  ├── Signal Processing & Technical Analysis                    │
│  ├── ML Models & Model Registry                                │
│  └── Broker Integration (MT5 Client)                           │
└─────────────────────────────────────────────────────────────────┘
```

### Service Communication

All services communicate via HTTP REST APIs over localhost (127.0.0.1) for security. Each service exposes a `/health` endpoint for monitoring and specific endpoints for its functionality. The communication flow follows this pattern:

1. **Telegram Bot Gateway** receives user commands and coordinates with other services
2. **Market Worker** continuously ingests market data and generates trading signals
3. **Execution Worker** receives signals and executes trades through broker integration
4. **Finance Worker** tracks all trades, positions, and account information
5. **Scheduler** manages automated tasks like daily reports and system maintenance

### Data Flow

The trading data flows through the system as follows:

```
Market Data → Signal Generation → Risk Assessment → Order Execution → Trade Recording
     ↓              ↓                    ↓               ↓              ↓
Market Worker → Market Worker → Execution Worker → Execution Worker → Finance Worker
```

### Environment Isolation

Each service runs in its own Conda environment to ensure dependency isolation:

- **env-bot**: Telegram bot dependencies (python-telegram-bot, FastAPI)
- **env-scheduler**: Scheduling dependencies (APScheduler, FastAPI)
- **env-finance**: Financial analysis dependencies (pandas, numpy, SQLAlchemy)
- **env-market**: Market data dependencies (websockets, technical analysis libraries)
- **env-execution**: Execution dependencies (broker APIs, risk management)

## Features

### Core Trading Features

**Automated Signal Generation**: The platform includes multiple signal generation strategies including moving average crossovers, RSI overbought/oversold conditions, MACD signals, and Bollinger Bands. These signals can be combined with configurable weights to create composite trading decisions.

**Risk Management System**: Comprehensive risk controls include daily loss limits, maximum order size restrictions, dry-run mode for testing, and an emergency stop mechanism accessible via Telegram. The system tracks daily P&L and automatically halts trading if limits are exceeded.

**MetaTrader Integration**: Flexible broker integration supporting both direct MetaTrader 5 installation on Raspberry Pi (via Wine) and remote API connections to a Windows VM running MT5. This provides reliability and performance optimization options.

**Machine Learning Models**: Built-in ML models for trend following and mean reversion strategies. The system includes a model registry for versioning and management, with support for training, backtesting, and live inference.

### System Management Features

**Telegram Bot Interface**: Complete system control via Telegram bot with commands for monitoring positions, trades, account balance, system health, and emergency controls. The bot includes authentication and supports multiple authorized users.

**Automated Monitoring**: Continuous health monitoring with alerts for high CPU usage, memory consumption, disk space, temperature, and service failures. The system automatically attempts to restart failed services and sends notifications via Telegram.

**Scheduled Reporting**: Automated daily reports including system health summaries, trading performance, and account status. Reports are delivered via Telegram at configurable times.

**Logging and Audit Trail**: Structured JSON logging with complete audit trails for all trading decisions. Logs are stored via systemd journal and include metadata for reproducibility of trading decisions.

### Security Features

**Environment-based Configuration**: All sensitive information stored in environment variables with proper file permissions (chmod 600). Configuration is isolated per service with shared global settings.

**API Security**: All inter-service communication secured with API tokens. Services bind only to localhost (127.0.0.1) to prevent external access. Telegram bot includes chat ID verification for authorized access only.

**Trading Safeguards**: Multiple layers of protection including notional caps per order, daily stop-loss limits, dry-run mode for testing, and Telegram-accessible kill switch for emergency stops.

## Prerequisites

### Hardware Requirements

- **Raspberry Pi 5** with 8GB RAM (minimum 4GB supported but 8GB recommended)
- **MicroSD Card**: 64GB or larger, Class 10 or better
- **Network Connection**: Ethernet or Wi-Fi with stable internet connectivity
- **Power Supply**: Official Raspberry Pi 5 power supply (5.1V, 5A)
- **Optional**: Cooling solution (fan or heatsink) for sustained operation

### Software Requirements

- **Raspberry Pi OS** (64-bit, Bookworm or later)
- **Python 3.9+** (included with Raspberry Pi OS)
- **Git** for version control
- **Systemd** for service management (included with Raspberry Pi OS)
- **SQLite3** for local database (included with Raspberry Pi OS)

### External Dependencies

- **Telegram Bot Token**: Create a bot via @BotFather on Telegram
- **MetaTrader 5 Account**: Trading account with API access
- **Optional**: Windows VM for MetaTrader 5 if not running directly on Pi

### Network Requirements

- **Outbound HTTPS (443)**: For Telegram API communication
- **Outbound HTTP/HTTPS**: For MetaTrader API communication
- **Optional**: Inbound SSH (22) for remote administration

## Installation

### Quick Start

The fastest way to get RPI Trader running is using the automated deployment script:

```bash
# Clone the repository
git clone <repository-url> /home/andrepi/rpi-trader
cd /home/andrepi/rpi-trader

# Make deployment script executable
chmod +x scripts/deploy.sh

# Run full deployment
./scripts/deploy.sh
```

The deployment script will automatically:
- Install system dependencies
- Set up Miniconda and create isolated environments
- Install Python packages in editable mode
- Configure systemd services
- Set up cron jobs for automated tasks
- Start all services

### Manual Installation

For more control over the installation process, follow these detailed steps:

#### Step 1: System Preparation

Update your Raspberry Pi system and install required packages:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-dev python3-pip git curl wget build-essential \
    libssl-dev libffi-dev sqlite3 systemd psmisc htop vim nano
```

#### Step 2: Install Miniconda

Download and install Miniconda for ARM64:

```bash
cd /tmp
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
bash Miniconda3-latest-Linux-aarch64.sh -b -p /home/andrepi/miniconda3
/home/andrepi/miniconda3/bin/conda init bash
source ~/.bashrc
```

#### Step 3: Create Conda Environments

Create isolated environments for each service:

```bash
# Bot Gateway environment
conda create -n env-bot -y python=3.11 python-telegram-bot fastapi uvicorn httpx psutil structlog python-dotenv

# Scheduler environment  
conda create -n env-scheduler -y python=3.11 apscheduler fastapi uvicorn httpx structlog python-dotenv

# Finance Worker environment
conda create -n env-finance -y python=3.11 fastapi uvicorn sqlalchemy pandas numpy structlog python-dotenv

# Market Worker environment
conda create -n env-market -y python=3.11 fastapi uvicorn pandas numpy websockets httpx structlog python-dotenv

# Execution Worker environment
conda create -n env-execution -y python=3.11 fastapi uvicorn pandas numpy httpx structlog python-dotenv
```

#### Step 4: Install Project Packages

Install the RPI Trader packages in editable mode:

```bash
cd /home/andrepi/rpi-trader

# Install shared libraries in all environments
for env in env-bot env-scheduler env-finance env-market env-execution; do
    conda activate $env
    pip install -e .
    conda deactivate
done

# Install individual app packages
conda activate env-bot && cd apps/bot_gateway && pip install -e . && cd ../..
conda activate env-scheduler && cd apps/scheduler && pip install -e . && cd ../..
conda activate env-finance && cd apps/finance_worker && pip install -e . && cd ../..
conda activate env-market && cd apps/market_worker && pip install -e . && cd ../..
conda activate env-execution && cd apps/execution_worker && pip install -e . && cd ../..
```

#### Step 5: Configure Services

Install systemd service files:

```bash
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable rpi-trader-bot-gateway
sudo systemctl enable rpi-trader-scheduler  
sudo systemctl enable rpi-trader-finance-worker
sudo systemctl enable rpi-trader-market-worker
sudo systemctl enable rpi-trader-execution-worker
```

#### Step 6: Set Up Cron Jobs

Install automated maintenance tasks:

```bash
# Add cron jobs (the deploy script handles this automatically)
./scripts/deploy.sh setup_cron_jobs
```

## Configuration

### Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

### Required Configuration

Edit the `.env` file with your specific settings:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_CHAT_ID=your_telegram_chat_id

# MetaTrader Configuration  
MT5_SERVER=your_mt5_server
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_API_URL=http://your-windows-vm:8080/api/v1

# Security
SECRET_KEY=generate_a_secure_random_key
API_TOKEN=generate_a_secure_api_token

# Trading Configuration
MAX_DAILY_LOSS=1000.0
MAX_ORDER_SIZE=10000.0
DRY_RUN_MODE=true  # Set to false for live trading
```

### Getting Your Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the provided token to your `.env` file

### Finding Your Telegram Chat ID

1. Send a message to your bot
2. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for the `chat.id` value in the response
4. Add this ID to your `.env` file

### MetaTrader Configuration

For **Direct Installation** on Raspberry Pi:
```bash
# Install Wine (if using direct MT5 installation)
sudo apt install wine
# Follow MetaTrader 5 installation guide for Linux
```

For **Remote API** (recommended):
Set up a Windows VM with MetaTrader 5 and configure the API endpoint in your `.env` file.

## Usage

### Starting the System

Start all services using the deployment script:

```bash
./scripts/deploy.sh start
```

Or start individual services:

```bash
sudo systemctl start rpi-trader-bot-gateway
sudo systemctl start rpi-trader-scheduler
sudo systemctl start rpi-trader-finance-worker  
sudo systemctl start rpi-trader-market-worker
sudo systemctl start rpi-trader-execution-worker
```

### Telegram Bot Commands

Once the system is running, interact with it via Telegram:

**Trading Commands:**
- `/positions` - Show current open positions
- `/trades` - Show recent trade history  
- `/balance` - Show account balance and equity
- `/stop_trading` - Emergency stop (kill switch)
- `/start_trading` - Resume trading operations

**System Commands:**
- `/status` - Quick system status overview
- `/health` - Detailed health metrics
- `/system` - System information (CPU, RAM, etc.)
- `/logs` - Show recent application logs
- `/reboot` - Reboot the Raspberry Pi

### Monitoring System Health

Check service status:

```bash
# View all service statuses
./scripts/deploy.sh status

# View live logs
sudo journalctl -f -u rpi-trader-*

# Check individual service
sudo systemctl status rpi-trader-bot-gateway
```

### Managing Trading

**Enable/Disable Trading:**
```bash
# Via Telegram
/stop_trading  # Emergency stop
/start_trading # Resume trading

# Via API (if needed)
curl -X POST http://127.0.0.1:8001/trading/disable \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

**Monitor Trading Activity:**
```bash
# View recent trades via Telegram
/trades 10  # Show last 10 trades

# View positions
/positions

# Check account balance
/balance
```


## API Documentation

### Service Endpoints

Each service exposes REST API endpoints for inter-service communication. All APIs require authentication via Bearer token.

#### Bot Gateway API (Port 8001)

**Health Check**
```http
GET /health
Response: {"status": "healthy", "service": "bot_gateway", "telegram_bot_active": true}
```

**Send Alert**
```http
POST /alert
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "title": "Alert Title",
  "message": "Alert message content"
}
```

**Send Message**
```http
POST /message
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "message": "Message content",
  "parse_mode": "Markdown"
}
```

**Trading Control**
```http
GET /trading/status
POST /trading/enable
POST /trading/disable
Authorization: Bearer <API_TOKEN>
```

#### Finance Worker API (Port 8003)

**Account Information**
```http
GET /account
Authorization: Bearer <API_TOKEN>
Response: {
  "balance": 10000.00,
  "equity": 10500.00,
  "margin": 500.00,
  "free_margin": 9500.00,
  "currency": "USD",
  "leverage": 100
}
```

**Current Positions**
```http
GET /positions
Authorization: Bearer <API_TOKEN>
Response: [
  {
    "symbol": "EURUSD",
    "quantity": 0.1,
    "average_price": 1.0850,
    "current_price": 1.0865,
    "unrealized_pnl": 15.00
  }
]
```

**Trade History**
```http
GET /trades?limit=50
GET /trades/today
Authorization: Bearer <API_TOKEN>
```

**Daily Statistics**
```http
GET /daily-stats
Authorization: Bearer <API_TOKEN>
Response: {
  "total_trades": 5,
  "winning_trades": 3,
  "losing_trades": 2,
  "total_pnl": 150.00,
  "win_rate": 0.6
}
```

#### Market Worker API (Port 8004)

**Current Market Data**
```http
GET /market-data/{symbol}
Authorization: Bearer <API_TOKEN>
Response: {
  "symbol": "EURUSD",
  "bid": 1.0850,
  "ask": 1.0852,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Trading Signals**
```http
GET /signals/{symbol}
GET /signals/recent?limit=10
Authorization: Bearer <API_TOKEN>
```

**Signal Statistics**
```http
GET /signal-stats?symbol=EURUSD&hours=24
Authorization: Bearer <API_TOKEN>
```

#### Execution Worker API (Port 8005)

**Place Order**
```http
POST /orders
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "symbol": "EURUSD",
  "action": "BUY",
  "quantity": 0.1,
  "order_type": "MARKET"
}
```

**Emergency Stop**
```http
POST /emergency_stop
Authorization: Bearer <API_TOKEN>
```

**Resume Trading**
```http
POST /resume_trading
Authorization: Bearer <API_TOKEN>
```

### Authentication

All API endpoints require authentication using Bearer tokens. Include the token in the Authorization header:

```http
Authorization: Bearer <YOUR_API_TOKEN>
```

The API token is configured in the `.env` file and should be kept secure.

## Monitoring and Maintenance

### Automated Monitoring

The system includes comprehensive automated monitoring through scheduled scripts:

**Health Checks (Every 15 minutes)**
- CPU usage monitoring (threshold: 90%)
- Memory usage monitoring (threshold: 85%)  
- Disk space monitoring (threshold: 90%)
- Temperature monitoring (threshold: 75°C)
- Service status verification
- Network connectivity checks
- Automatic service restart attempts

**Daily System Updates (3:00 AM)**
- Package updates via apt
- Conda environment updates
- Security patches
- Disk cleanup and maintenance
- Reboot notifications if required

**Daily Summary Reports (8:00 AM)**
- System health overview
- Service status summary
- Trading performance metrics
- Resource utilization statistics

**Daily Trade Reports (7:00 PM)**
- Trading activity summary
- Account balance updates
- Position status
- Performance analysis

### Manual Monitoring Commands

**System Status**
```bash
# Overall system status
./scripts/deploy.sh status

# Individual service status
sudo systemctl status rpi-trader-bot-gateway

# Live log monitoring
sudo journalctl -f -u rpi-trader-*

# Resource usage
htop
df -h
free -h
```

**Trading Monitoring**
```bash
# Via Telegram bot
/status    # Quick overview
/health    # Detailed metrics
/positions # Current positions
/trades    # Recent trades
/balance   # Account information
```

### Log Management

Logs are managed through systemd journal and local files:

**Viewing Logs**
```bash
# All services
sudo journalctl -u rpi-trader-* --since "1 hour ago"

# Specific service
sudo journalctl -u rpi-trader-bot-gateway -f

# Application logs
tail -f /home/andrepi/rpi-trader/logs/*.log
```

**Log Rotation**
Logs are automatically rotated by systemd journal. Additional cleanup is performed by the health check script, keeping logs for 7 days.

### Backup and Recovery

**Database Backup**
```bash
# Manual backup
sqlite3 /home/andrepi/rpi-trader/rpi_trader.db ".backup /home/andrepi/rpi-trader/backups/backup_$(date +%Y%m%d).db"

# Automated backup (add to cron)
0 2 * * * sqlite3 /home/andrepi/rpi-trader/rpi_trader.db ".backup /home/andrepi/rpi-trader/backups/backup_$(date +\%Y\%m\%d).db"
```

**Configuration Backup**
```bash
# Backup configuration
cp /home/andrepi/rpi-trader/.env /home/andrepi/rpi-trader/backups/env_backup_$(date +%Y%m%d)
```

**Full System Backup**
```bash
# Create system image (from another machine)
sudo dd if=/dev/sdX of=rpi_trader_backup.img bs=4M status=progress
```

### Performance Optimization

**Memory Optimization**
```bash
# Increase swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**CPU Optimization**
```bash
# Monitor CPU frequency
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# Set performance governor if needed
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**Database Optimization**
```bash
# Vacuum SQLite database
sqlite3 /home/andrepi/rpi-trader/rpi_trader.db "VACUUM;"

# Analyze database
sqlite3 /home/andrepi/rpi-trader/rpi_trader.db "ANALYZE;"
```

## Troubleshooting

### Common Issues and Solutions

**Service Won't Start**

1. Check service status:
```bash
sudo systemctl status rpi-trader-bot-gateway
```

2. Check logs for errors:
```bash
sudo journalctl -u rpi-trader-bot-gateway -n 50
```

3. Verify environment configuration:
```bash
# Check if .env file exists and has correct permissions
ls -la /home/andrepi/rpi-trader/.env

# Verify conda environment
conda activate env-bot
python -c "import telegram; print('OK')"
```

4. Restart service:
```bash
sudo systemctl restart rpi-trader-bot-gateway
```

**Telegram Bot Not Responding**

1. Verify bot token:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

2. Check network connectivity:
```bash
ping api.telegram.org
```

3. Verify chat ID authorization:
```bash
# Send a message to your bot, then check:
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

**MetaTrader Connection Issues**

1. For direct MT5 installation:
```bash
# Check if MT5 is running
ps aux | grep terminal64.exe

# Check Wine configuration
winecfg
```

2. For remote API:
```bash
# Test API connectivity
curl http://your-windows-vm:8080/api/v1/status
```

3. Verify credentials in `.env` file

**High Resource Usage**

1. Identify resource-heavy processes:
```bash
htop
iotop  # For disk I/O
```

2. Check for memory leaks:
```bash
# Monitor memory usage over time
watch -n 5 'free -h && ps aux --sort=-%mem | head -10'
```

3. Restart services if needed:
```bash
sudo systemctl restart rpi-trader-*
```

**Database Issues**

1. Check database integrity:
```bash
sqlite3 /home/andrepi/rpi-trader/rpi_trader.db "PRAGMA integrity_check;"
```

2. Repair database if corrupted:
```bash
sqlite3 /home/andrepi/rpi-trader/rpi_trader.db ".recover" | sqlite3 recovered.db
```

3. Check disk space:
```bash
df -h /home/andrepi/rpi-trader/
```

### Error Codes and Messages

**Common Error Patterns**

| Error Pattern | Cause | Solution |
|---------------|-------|----------|
| `ModuleNotFoundError` | Missing Python dependencies | Reinstall packages in correct conda environment |
| `Permission denied` | Incorrect file permissions | Check ownership and permissions of files |
| `Connection refused` | Service not running or wrong port | Verify service status and port configuration |
| `Unauthorized` | Invalid API token or chat ID | Check authentication configuration |
| `Database locked` | Concurrent database access | Restart services, check for hung processes |

**Service-Specific Errors**

**Bot Gateway Errors:**
- `TelegramError`: Network issues or invalid bot token
- `HTTPException 401`: Invalid API token for internal calls
- `ConnectionError`: Unable to reach other services

**Market Worker Errors:**
- `BrokerError`: MetaTrader connection issues
- `SignalError`: Technical analysis calculation failures
- `DataError`: Market data feed problems

**Execution Worker Errors:**
- `OrderError`: Trade execution failures
- `RiskError`: Risk management violations
- `BrokerConnectionError`: Broker API connectivity issues

### Debug Mode

Enable debug logging for troubleshooting:

1. Edit `.env` file:
```bash
LOG_LEVEL=DEBUG
```

2. Restart services:
```bash
sudo systemctl restart rpi-trader-*
```

3. Monitor debug logs:
```bash
sudo journalctl -u rpi-trader-* -f | grep DEBUG
```

### Getting Help

**Log Collection for Support**
```bash
# Collect system information
./scripts/collect-debug-info.sh > debug_info.txt

# Collect recent logs
sudo journalctl -u rpi-trader-* --since "1 hour ago" > recent_logs.txt
```

**Community Support**
- GitHub Issues: Report bugs and feature requests
- Documentation: Check the latest documentation updates
- Telegram Group: Join the community discussion (if available)

## Development

### Development Environment Setup

**Setting Up for Development**

1. Clone the repository:
```bash
git clone <repository-url> /home/andrepi/rpi-trader-dev
cd /home/andrepi/rpi-trader-dev
```

2. Create development conda environment:
```bash
conda create -n rpi-trader-dev python=3.11 -y
conda activate rpi-trader-dev
pip install -e ".[dev]"
```

3. Install development tools:
```bash
pip install pytest pytest-asyncio black isort flake8 mypy
```

### Code Structure

**Project Layout**
```
rpi-trader/
├── apps/                    # Main applications
│   ├── bot_gateway/        # Telegram bot service
│   ├── scheduler/          # Task scheduling service
│   ├── finance_worker/     # Financial data service
│   ├── market_worker/      # Market data service
│   └── execution_worker/   # Trade execution service
├── libs/                   # Shared libraries
│   ├── core/              # Core utilities
│   ├── data/              # Data models and repositories
│   ├── signals/           # Signal generation
│   ├── models/            # ML models
│   └── broker/            # Broker integration
├── services/              # Systemd service files
├── scripts/               # Deployment and maintenance scripts
└── tests/                 # Test suite
```

**Coding Standards**

The project follows Python best practices:

- **PEP 8** compliance with Black formatting
- **Type hints** for all function signatures
- **Docstrings** for all public functions and classes
- **Async/await** for I/O operations
- **Structured logging** with contextual information
- **Error handling** with specific exception types

### Adding New Features

**Creating a New Signal**

1. Create signal class in `libs/signals/`:
```python
from .base import BaseSignal
from ..data.models import SignalData, TradeAction

class MyCustomSignal(BaseSignal):
    def __init__(self, parameter1: float = 1.0):
        super().__init__("MY_CUSTOM_SIGNAL", {"parameter1": parameter1})
        self.parameter1 = parameter1
    
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        # Implement your signal logic
        pass
    
    def get_required_periods(self) -> int:
        return 20  # Minimum data points needed
```

2. Register signal in market worker:
```python
from libs.signals import MyCustomSignal

# In market worker initialization
signal_processor.add_signal_generator(MyCustomSignal(parameter1=2.0), weight=1.5)
```

**Adding a New API Endpoint**

1. Add endpoint to appropriate service:
```python
@app.get("/my-endpoint")
async def my_endpoint(_: bool = Depends(verify_api_token)):
    """My custom endpoint"""
    return {"result": "success"}
```

2. Update API documentation in README.md

**Creating a New ML Model**

1. Inherit from BaseModel:
```python
from libs.models.base import BaseModel

class MyMLModel(BaseModel):
    def train(self, data: pd.DataFrame, target: pd.Series) -> None:
        # Implement training logic
        pass
    
    def predict(self, data: pd.DataFrame) -> Optional[SignalData]:
        # Implement prediction logic
        pass
```

2. Register model in model registry:
```python
from libs.models import ModelRegistry, MyMLModel

registry = ModelRegistry()
model = MyMLModel("my_model", "1.0")
registry.register_model(model)
```

### Testing

**Running Tests**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_signals.py

# Run with coverage
pytest --cov=libs --cov=apps

# Run async tests
pytest -v tests/test_async_functions.py
```

**Writing Tests**

Create test files in the `tests/` directory:

```python
import pytest
from libs.signals import MovingAverageSignal

@pytest.fixture
def sample_data():
    # Create sample market data
    pass

def test_moving_average_signal(sample_data):
    signal = MovingAverageSignal(fast_period=5, slow_period=10)
    result = signal.calculate(sample_data)
    assert result is not None
    assert result.signal_type == "MA_CROSSOVER"
```

### Code Quality

**Formatting and Linting**

```bash
# Format code with Black
black libs/ apps/

# Sort imports with isort
isort libs/ apps/

# Lint with flake8
flake8 libs/ apps/

# Type checking with mypy
mypy libs/ apps/
```

**Pre-commit Hooks**

Set up pre-commit hooks for automatic code quality checks:

```bash
pip install pre-commit
pre-commit install
```

### Contributing Guidelines

**Pull Request Process**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Ensure code quality: `black`, `isort`, `flake8`, `mypy`
5. Run tests: `pytest`
6. Commit with descriptive messages
7. Push and create pull request

**Commit Message Format**
```
type(scope): description

feat(signals): add new RSI divergence signal
fix(broker): handle connection timeout errors
docs(readme): update installation instructions
test(models): add unit tests for trend following model
```

## Security Considerations

### Security Architecture

The RPI Trader platform implements multiple layers of security to protect both the system and trading operations:

**Network Security**
- All inter-service communication restricted to localhost (127.0.0.1)
- No external network access to internal APIs
- Telegram bot as the only external interface
- Optional VPN setup for remote administration

**Authentication and Authorization**
- API token-based authentication for all internal services
- Telegram chat ID verification for bot access
- Environment-based credential storage
- No hardcoded secrets in source code

**Data Protection**
- Environment files with restricted permissions (chmod 600)
- Structured logging without sensitive data exposure
- Database encryption options for sensitive trading data
- Secure backup procedures with encryption

### Trading Security

**Risk Management**
- Daily loss limits with automatic trading halt
- Maximum order size restrictions
- Dry-run mode for strategy testing
- Emergency stop mechanism via Telegram
- Position size validation before execution

**Audit Trail**
- Complete logging of all trading decisions
- Reproducible trade execution with saved parameters
- Immutable trade records in database
- Regular backup of trading history

**Broker Security**
- Secure API key management
- Connection encryption for broker communication
- Account balance verification before trades
- Automatic reconnection with authentication

### System Hardening

**File System Security**
```bash
# Set proper ownership
sudo chown -R pi:pi /home/andrepi/rpi-trader

# Restrict sensitive file permissions
chmod 600 /home/andrepi/rpi-trader/.env
chmod 700 /home/andrepi/rpi-trader/scripts/
chmod 644 /home/andrepi/rpi-trader/services/*.service
```

**Service Security**
- Services run as non-root user (pi)
- Systemd security features enabled (NoNewPrivileges, PrivateTmp)
- Resource limits configured in service files
- Automatic restart on failure with rate limiting

**Network Hardening**
```bash
# Configure firewall (optional)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow out 443  # HTTPS for Telegram
sudo ufw deny in 8001:8005  # Block internal service ports
```

### Security Monitoring

**Automated Security Checks**
- Failed authentication attempt logging
- Unusual trading activity detection
- System resource abuse monitoring
- Network connection anomaly detection

**Security Alerts**
- Telegram notifications for security events
- Failed login attempt alerts
- Unusual system behavior warnings
- Trading limit violation notifications

### Best Practices

**Credential Management**
- Use strong, unique passwords for all accounts
- Rotate API tokens regularly
- Store backups securely with encryption
- Never commit credentials to version control

**System Maintenance**
- Regular security updates via automated scripts
- Monitor system logs for suspicious activity
- Regular backup verification
- Periodic security audit of configurations

**Trading Security**
- Start with small position sizes
- Use dry-run mode extensively before live trading
- Monitor trading performance closely
- Set conservative risk limits initially

## Contributing

We welcome contributions to the RPI Trader project! Whether you're fixing bugs, adding features, improving documentation, or sharing trading strategies, your contributions help make the platform better for everyone.

### How to Contribute

**Reporting Issues**
- Use GitHub Issues to report bugs or request features
- Provide detailed information including system specs, error messages, and steps to reproduce
- Include relevant log excerpts (remove sensitive information)

**Code Contributions**
- Fork the repository and create a feature branch
- Follow the coding standards and include tests
- Update documentation for new features
- Submit a pull request with a clear description

**Documentation Improvements**
- Fix typos, clarify instructions, or add examples
- Update API documentation for new endpoints
- Add troubleshooting guides for common issues
- Translate documentation to other languages

**Community Support**
- Help other users in GitHub Discussions
- Share trading strategies and configurations
- Contribute to the knowledge base
- Provide feedback on new features

### Development Roadmap

**Planned Features**
- Web-based dashboard for system monitoring
- Additional broker integrations (Interactive Brokers, etc.)
- Advanced ML models with deep learning support
- Portfolio optimization and risk management tools
- Mobile app for iOS and Android
- Cloud deployment options (AWS, Azure, GCP)

**Community Requests**
- Multi-timeframe analysis support
- Cryptocurrency trading integration
- Social trading features
- Advanced backtesting framework
- Real-time strategy optimization

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

**Disclaimer**: This software is for educational and research purposes. Trading financial instruments involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Use at your own risk and never trade with money you cannot afford to lose.

**Support**: For support, please open an issue on GitHub or contact the development team. Commercial support and custom development services may be available upon request.

**Version**: 0.1.0  
**Last Updated**: January 2024  
**Maintainer**: Manus AI

