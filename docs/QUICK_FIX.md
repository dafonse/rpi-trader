# Quick Fix for Service Startup Error

## Problem
The systemd services are failing to start because they're trying to run Python modules using the `-m` flag, but the module paths are incorrect.

## Solution
The service files need to be updated to run the Python scripts directly instead of as modules.

## Fix Commands

Run these commands on your Raspberry Pi to fix the service files:

```bash
cd /home/pi/rpi-trader/services

# Fix all service files
sudo sed -i 's|python -m apps\.bot_gateway\.main|python apps/bot_gateway/main.py|g' rpi-trader-bot-gateway.service
sudo sed -i 's|python -m apps\.scheduler\.main|python apps/scheduler/main.py|g' rpi-trader-scheduler.service  
sudo sed -i 's|python -m apps\.finance_worker\.main|python apps/finance_worker/main.py|g' rpi-trader-finance-worker.service
sudo sed -i 's|python -m apps\.market_worker\.main|python apps/market_worker/main.py|g' rpi-trader-market-worker.service
sudo sed -i 's|python -m apps\.execution_worker\.main|python apps/execution_worker/main.py|g' rpi-trader-execution-worker.service

# Copy the fixed service files to systemd
sudo cp *.service /etc/systemd/system/

# Reload systemd and restart services
sudo systemctl daemon-reload

# Now try starting the services again
./scripts/deploy.sh start
```

## Alternative: Use the Updated Archive

I have also created an updated archive with the fixed service files. You can download the new `rpi-trader-complete.tar.gz` file and extract it to replace your current installation.

## Verification

After applying the fix, you should be able to start the services successfully:

```bash
./scripts/deploy.sh status
```

All services should show as "active (running)" in green.

