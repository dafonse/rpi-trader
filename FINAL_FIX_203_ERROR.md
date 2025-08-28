# FINAL FIX for 203/EXEC Error

The 203/EXEC error is likely caused by conda environment activation issues. Here's the definitive solution:

## Solution: Use Wrapper Scripts

### Step 1: Create Wrapper Scripts
```bash
cd /home/pi/rpi-trader
./create_wrapper_scripts.sh
```

This creates 5 wrapper scripts that properly activate conda environments before running Python.

### Step 2: Test Wrapper Scripts Manually
Before updating services, test each wrapper script:

```bash
cd /home/pi/rpi-trader

# Test each service manually
./start_bot_gateway.sh &
# Press Ctrl+C to stop, then test the next one

./start_scheduler.sh &
# Press Ctrl+C to stop, then test the next one

./start_finance_worker.sh &
# Press Ctrl+C to stop, then test the next one

./start_market_worker.sh &
# Press Ctrl+C to stop, then test the next one

./start_execution_worker.sh &
# Press Ctrl+C to stop
```

### Step 3: Update Service Files (Only if wrapper scripts work)
```bash
# Copy the wrapper-based service files
sudo cp services_with_wrappers/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Start services
./scripts/deploy.sh start
```

## Alternative: Simple Bash-Based Services

If wrapper scripts still don't work, use this simpler approach:

```bash
# Create a simple service file that uses bash directly
sudo tee /etc/systemd/system/rpi-trader-bot-gateway.service > /dev/null << 'EOF'
[Unit]
Description=RPI Trader Bot Gateway
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/rpi-trader
ExecStart=/bin/bash -c 'source /home/pi/miniconda3/etc/profile.d/conda.sh && conda activate env-bot && python apps/bot_gateway/main.py'
Restart=always
RestartSec=10
EnvironmentFile=/home/pi/rpi-trader/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start rpi-trader-bot-gateway
sudo systemctl status rpi-trader-bot-gateway
```

## Debugging Steps

If you're still getting errors, run these diagnostic commands:

```bash
# 1. Check if conda is properly installed
which conda
conda --version

# 2. Check if environments exist
conda env list

# 3. Test manual activation
source /home/pi/miniconda3/etc/profile.d/conda.sh
conda activate env-bot
which python
python --version

# 4. Test the actual Python script
cd /home/pi/rpi-trader
python apps/bot_gateway/main.py

# 5. Check file permissions
ls -la apps/bot_gateway/main.py
ls -la start_bot_gateway.sh

# 6. Check systemd logs
sudo journalctl -u rpi-trader-bot-gateway.service -f
```

## What Each Wrapper Script Does

Each wrapper script:
1. Changes to the correct directory
2. Sources conda initialization
3. Activates the specific conda environment
4. Runs the Python application with `exec` (replaces the shell process)

This ensures that:
- The conda environment is properly activated
- All dependencies are available
- The Python path is correct
- Environment variables are loaded

## If Nothing Works: Manual Start

As a last resort, you can start services manually:

```bash
# Terminal 1
cd /home/pi/rpi-trader
source /home/pi/miniconda3/etc/profile.d/conda.sh
conda activate env-bot
python apps/bot_gateway/main.py

# Terminal 2  
cd /home/pi/rpi-trader
source /home/pi/miniconda3/etc/profile.d/conda.sh
conda activate env-scheduler
python apps/scheduler/main.py

# And so on for each service...
```

This will at least get the system running while we debug the systemd integration.

