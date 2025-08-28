# Troubleshooting 203/EXEC Error - Complete Guide

## Understanding the Error
The `status=203/EXEC` error means systemd cannot execute the command specified in `ExecStart`. This can happen for several reasons even when the path looks correct.

## Step-by-Step Troubleshooting

### Step 1: Verify File Permissions
```bash
cd /home/pi/rpi-trader

# Check if Python scripts are executable
ls -la apps/*/main.py

# Make Python scripts executable
chmod +x apps/*/main.py

# Verify the conda environment exists and Python is executable
ls -la /home/pi/miniconda3/envs/env-bot/bin/python
```

### Step 2: Test Manual Execution
Try running the service manually to see the actual error:

```bash
cd /home/pi/rpi-trader

# Test bot gateway manually
/home/pi/miniconda3/envs/env-bot/bin/python apps/bot_gateway/main.py
```

If this fails, you'll see the actual Python error that systemd can't show you.

### Step 3: Check Python Path and Dependencies
```bash
# Activate the environment and test
conda activate env-bot
cd /home/pi/rpi-trader
python apps/bot_gateway/main.py
```

### Step 4: Alternative Solution - Use Shell Wrapper Scripts

Create wrapper scripts that properly activate the conda environment:

```bash
# Create wrapper script for bot gateway
cat > /home/pi/rpi-trader/start_bot_gateway.sh << 'EOF'
#!/bin/bash
cd /home/pi/rpi-trader
source /home/pi/miniconda3/etc/profile.d/conda.sh
conda activate env-bot
exec python apps/bot_gateway/main.py
EOF

# Make it executable
chmod +x /home/pi/rpi-trader/start_bot_gateway.sh

# Test the wrapper
./start_bot_gateway.sh
```

### Step 5: Update Service Files to Use Wrapper Scripts

If the wrapper script works, update the service files:

```bash
# Edit the service file
sudo nano /etc/systemd/system/rpi-trader-bot-gateway.service
```

Change the ExecStart line to:
```
ExecStart=/home/pi/rpi-trader/start_bot_gateway.sh
```

### Step 6: Check Environment File
Ensure your `.env` file exists and has correct permissions:

```bash
ls -la /home/pi/rpi-trader/.env
chmod 600 /home/pi/rpi-trader/.env
```

### Step 7: Check Systemd Logs for More Details
```bash
# Get detailed logs
sudo journalctl -u rpi-trader-bot-gateway.service -f

# Or check recent logs
sudo journalctl -u rpi-trader-bot-gateway.service --since "5 minutes ago"
```

## Common Issues and Solutions

### Issue 1: Missing Shebang Line
Add shebang to Python files:
```bash
# Add to the top of each main.py file
#!/usr/bin/env python3
```

### Issue 2: Conda Environment Not Found
```bash
# Verify conda environments exist
conda env list

# Recreate if missing
conda create -n env-bot python=3.11 -y
```

### Issue 3: Permission Denied
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/rpi-trader

# Fix permissions
chmod -R 755 /home/pi/rpi-trader
chmod 600 /home/pi/rpi-trader/.env
```

### Issue 4: Missing Dependencies
```bash
# Reinstall dependencies
conda activate env-bot
cd /home/pi/rpi-trader
pip install -e .
cd apps/bot_gateway
pip install -e .
```

## Quick Test Commands

Run these to identify the exact issue:

```bash
# Test 1: Check if Python interpreter works
/home/pi/miniconda3/envs/env-bot/bin/python --version

# Test 2: Check if the script can be imported
/home/pi/miniconda3/envs/env-bot/bin/python -c "import sys; sys.path.insert(0, '/home/pi/rpi-trader'); import apps.bot_gateway.main"

# Test 3: Check if the script runs
cd /home/pi/rpi-trader
/home/pi/miniconda3/envs/env-bot/bin/python apps/bot_gateway/main.py

# Test 4: Check with conda activation
source /home/pi/miniconda3/etc/profile.d/conda.sh
conda activate env-bot
cd /home/pi/rpi-trader
python apps/bot_gateway/main.py
```

## If All Else Fails: Simple Service Approach

Create a simple service that just runs Python with conda:

```bash
cat > /etc/systemd/system/rpi-trader-bot-gateway.service << 'EOF'
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
```

This approach uses bash to properly activate conda before running Python.

