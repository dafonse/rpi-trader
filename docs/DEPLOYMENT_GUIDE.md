# RPI Trader Deployment Guide

This guide provides detailed instructions for deploying the RPI Trader platform on your Raspberry Pi 5, including the setup for the hybrid MetaTrader 5 integration using BVM (Botspot Virtual Machine).

## Table of Contents

1. [Initial System Setup](#initial-system-setup)
2. [RPI Trader Project Deployment](#rpi-trader-project-deployment)
3. [BVM and Windows 11 VM Setup](#bvm-and-windows-11-vm-setup)
4. [MetaTrader 5 and Bridge Service Setup in VM](#metatrader-5-and-bridge-service-setup-in-vm)
5. [RPI Trader Configuration](#rpi-trader-configuration)
6. [Starting and Monitoring Services](#starting-and-monitoring-services)
7. [Troubleshooting](#troubleshooting)

## 1. Initial System Setup

Ensure your Raspberry Pi 5 is running Raspberry Pi OS (64-bit, Bookworm or later) and is up to date.

```bash
sudo apt update && sudo apt upgrade -y
```

Install essential system dependencies:

```bash
sudo apt install -y python3-dev python3-pip git curl wget build-essential \
    libssl-dev libffi-dev sqlite3 systemd psmisc htop vim nano
```

## 2. RPI Trader Project Deployment

Clone the RPI Trader repository to your Raspberry Pi and run the automated deployment script.

```bash
# Navigate to your desired installation directory (e.g., /home/pi/)
cd /home/pi/

# Clone the repository (replace <repository-url> with the actual URL if you host it elsewhere)
git clone https://github.com/your-repo/rpi-trader.git rpi-trader # Assuming you'll host it on GitHub
cd rpi-trader

# Make deployment script executable
chmod +x scripts/deploy.sh

# Run full deployment
./scripts/deploy.sh deploy
```

This script will:
- Install Miniconda and create isolated Python environments for each service.
- Install all Python dependencies, including `pydantic-settings`, `yfinance`, and `aiohttp`.
- Set up the project directory structure.
- Install systemd service files for all RPI Trader components.
- Configure cron jobs for automated tasks.

## 3. BVM and Windows 11 VM Setup

This section guides you through setting up the Windows 11 Virtual Machine using `bvm` (Botspot Virtual Machine) on your Raspberry Pi 5. This VM will host MetaTrader 5.

```bash
# Ensure you are in the rpi-trader project directory
cd /home/pi/rpi-trader

# Make the BVM deployment script executable
chmod +x scripts/deploy_bvm.sh

# Run the BVM deployment script
# This will install BVM dependencies, clone the BVM repo, create the VM, 
# and start the Windows 11 installation process. This step is time-consuming.
./scripts/deploy_bvm.sh deploy
```

**Important Notes during Windows 11 Installation:**
- The Windows 11 installation process within the VM is largely automated by `bvm`.
- It will take a significant amount of time (30-60 minutes or more) for the first boot and installation to complete.
- **DO NOT interrupt the process.** Let it run until it indicates completion.

## 4. MetaTrader 5 and Bridge Service Setup in VM

Once Windows 11 is installed in your BVM, you need to set up MetaTrader 5 and the custom bridge service.

**1. Start the Windows VM (if not already running):**

```bash
cd /home/pi/rpi-trader
./scripts/deploy_bvm.sh start_vm
```

**2. Connect to the Windows VM via RDP:**

```bash
cd /home/pi/rpi-trader
./scripts/deploy_bvm.sh connect_vm
```

**3. Install MetaTrader 5 in the Windows VM:**
   - Inside the Windows VM, open a web browser.
   - Download the MetaTrader 5 installer from your broker's website or from `www.metatrader5.com`.
   - Run the installer and follow the on-screen instructions to install MT5.

**4. Install Python and Dependencies in Windows VM:**
   - Download and install Python for Windows (e.g., from `python.org`) within the Windows VM.
   - **Crucially, ensure you select the option to 


     `Add Python to PATH` during installation.
   - Open PowerShell or Command Prompt in the VM and install required Python packages:
     ```powershell
     pip install MetaTrader5 flask flask-cors
     ```

**5. Deploy and Run MT5 Bridge Service in Windows VM:**
   - The `MT5_BRIDGE_SERVICE.py` file is located in the root of your `rpi-trader` project on the Raspberry Pi.
   - You can access the `rpi-trader` project directory from within your Windows VM via the shared folder you configured in BVM (default: `Z:\shared` if you used the `deploy_bvm.sh` script).
   - Copy `MT5_BRIDGE_SERVICE.py` from the shared folder to a dedicated directory in your Windows VM (e.g., `C:\mt5_bridge\`).
   - Open PowerShell or Command Prompt in the VM, navigate to `C:\mt5_bridge\` and run the service:
     ```powershell
     python MT5_BRIDGE_SERVICE.py
     ```
   - **For Production**: It is highly recommended to set up `MT5_BRIDGE_SERVICE.py` as a Windows service so it starts automatically with the VM and runs in the background. You can use tools like NSSM (Non-Sucking Service Manager) for this.

## 5. RPI Trader Configuration

On your Raspberry Pi, you need to configure the `.env` file to enable the BVM MT5 integration and provide your MT5 credentials.

```bash
cd /home/pi/rpi-trader
cp .env.example .env
chmod 600 .env
nano .env
```

Edit the `.env` file with your specific settings. Pay close attention to the `BVM MT5 Configuration` and `MT5 Credentials` sections:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_CHAT_ID=your_telegram_chat_id

# BVM MT5 Configuration
BVM_MT5_ENABLED=true
BVM_VM_IP=localhost  # If your VM is accessible via localhost from the Pi
BVM_VM_PORT=8080     # Port where MT5_BRIDGE_SERVICE.py is running in the VM

# MT5 Credentials (used by BVM MT5 client to connect to MT5 in VM)
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_broker_server

# Hybrid Mode Settings
USE_HYBRID_ANALYSIS=true  # Set to true to use API for analysis, MT5 for execution
MT5_FOR_EXECUTION_ONLY=true # Set to true if MT5 is only for execution, not data

# Security
SECRET_KEY=generate_a_secure_random_key
API_TOKEN=generate_a_secure_api_token

# Trading Configuration
MAX_DAILY_LOSS=1000.0
MAX_ORDER_SIZE=10000.0
DRY_RUN_MODE=true  # Set to false for live trading

# Service Ports (default values, change if needed)
BOT_GATEWAY_PORT=8001
SCHEDULER_PORT=8002
FINANCE_WORKER_PORT=8003
MARKET_WORKER_PORT=8004
EXECUTION_WORKER_PORT=8005

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 6. Starting and Monitoring Services

Once all configurations are in place, you can start the RPI Trader services.

**1. Ensure your Windows VM is running and the `MT5_BRIDGE_SERVICE.py` is active within it.**

**2. Start all RPI Trader services on your Raspberry Pi:**

```bash
cd /home/pi/rpi-trader
./scripts/deploy.sh start
```

**3. Verify service status:**

```bash
./scripts/deploy.sh status
```

You should see all RPI Trader services as `active`.

**4. Monitor logs for any issues:**

```bash
sudo journalctl -f -u rpi-trader-*
```

## 7. Troubleshooting

- **`status=203/EXEC` error**: This indicates a problem with the service executable path. Ensure the `ExecStart` lines in your `/etc/systemd/system/rpi-trader-*.service` files are correct and point to the right Python interpreter and script. Refer to `CORRECTED_FIX.md` if you encounter this.
- **`ImportError`**: If you see import errors, ensure all Python packages are installed in their respective Conda environments and that the project structure is correct. Refer to `PYDANTIC_FIX.md` and `IMPORT_FIX.md`.
- **MT5 Bridge Service Connection Issues**: Check the `BVM_VM_IP` and `BVM_VM_PORT` in your `.env` file. Ensure the `MT5_BRIDGE_SERVICE.py` is running in your Windows VM and is accessible on the specified IP and port. Check the firewall settings in your Windows VM.
- **MT5 Login/Connection Errors**: Verify your `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` in the `.env` file. Ensure MT5 is running in the VM and logged into your account.

This comprehensive guide should help you get your RPI Trader system up and running with the BVM-based MetaTrader 5 integration. If you encounter any further issues, please provide detailed error messages and logs.

