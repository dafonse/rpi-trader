# Corrected Fix for Service Startup Error

## Problem
The previous `sed` command was incorrect and resulted in `python python` in the ExecStart line, which is why the services are still failing.

## Corrected Solution

**Step 1: Copy the corrected service files**

```bash
cd /home/pi/rpi-trader

# Copy the corrected service files to systemd
sudo cp services/*.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload
```

**Step 2: Verify the service files are correct**

Check that the ExecStart lines are correct:

```bash
grep "ExecStart" /etc/systemd/system/rpi-trader-*.service
```

You should see output like:
```
/etc/systemd/system/rpi-trader-bot-gateway.service:ExecStart=/home/pi/miniconda3/envs/env-bot/bin/python apps/bot_gateway/main.py
/etc/systemd/system/rpi-trader-scheduler.service:ExecStart=/home/pi/miniconda3/envs/env-scheduler/bin/python apps/scheduler/main.py
/etc/systemd/system/rpi-trader-finance-worker.service:ExecStart=/home/pi/miniconda3/envs/env-finance/bin/python apps/finance_worker/main.py
/etc/systemd/system/rpi-trader-market-worker.service:ExecStart=/home/pi/miniconda3/envs/env-market/bin/python apps/market_worker/main.py
/etc/systemd/system/rpi-trader-execution-worker.service:ExecStart=/home/pi/miniconda3/envs/env-execution/bin/python apps/execution_worker/main.py
```

**Step 3: Start the services**

```bash
./scripts/deploy.sh start
```

## Alternative: Manual Service File Fix

If you prefer to fix the files manually, edit each service file and ensure the ExecStart line looks like this:

For bot-gateway:
```
ExecStart=/home/pi/miniconda3/envs/env-bot/bin/python apps/bot_gateway/main.py
```

For scheduler:
```
ExecStart=/home/pi/miniconda3/envs/env-scheduler/bin/python apps/scheduler/main.py
```

For finance-worker:
```
ExecStart=/home/pi/miniconda3/envs/env-finance/bin/python apps/finance_worker/main.py
```

For market-worker:
```
ExecStart=/home/pi/miniconda3/envs/env-market/bin/python apps/market_worker/main.py
```

For execution-worker:
```
ExecStart=/home/pi/miniconda3/envs/env-execution/bin/python apps/execution_worker/main.py
```

## What Was Wrong

The previous fix accidentally created lines like:
```
ExecStart=/home/pi/miniconda3/envs/env-bot/bin/python python apps/bot_gateway/main.py
```

Notice the duplicate "python" - this is what was causing the 203/EXEC error.

The corrected version removes the duplicate and uses the proper path to the Python script.

