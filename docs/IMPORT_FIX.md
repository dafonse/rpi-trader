# Fix for Python Import Errors

## Problem
The error `ImportError: attempted relative import with no known parent package` occurs when running Python scripts directly that use relative imports (like `from .bot import TelegramBot`).

## Solution Applied

### What Was Fixed
1. **Relative imports changed to absolute imports**:
   - `from .bot import TelegramBot` → `from bot_gateway.bot import TelegramBot`
   - `from .api import create_app` → `from bot_gateway.api import create_app`

2. **Added apps directory to Python path** in all main.py files:
   ```python
   sys.path.insert(0, str(project_root / "apps"))
   ```

### Test the Fix

Now you should be able to run:

```bash
cd /home/pi/rpi-trader
conda activate env-bot

# Install pydantic-settings first
pip install pydantic-settings>=2.0.0

# Test the bot gateway
python apps/bot_gateway/main.py
```

### If You Still Get Import Errors

Try running as a module instead:

```bash
cd /home/pi/rpi-trader
conda activate env-bot

# Run as module (alternative method)
python -m apps.bot_gateway.main
```

### Complete Fix Commands

If you want to apply all fixes at once:

```bash
cd /home/pi/rpi-trader

# Install pydantic-settings in all environments
for env in env-bot env-scheduler env-finance env-market env-execution; do
  conda activate $env
  pip install pydantic-settings>=2.0.0
done

# Test each service
conda activate env-bot && python apps/bot_gateway/main.py &
sleep 2 && kill %1

conda activate env-scheduler && python apps/scheduler/main.py &
sleep 2 && kill %1

conda activate env-finance && python apps/finance_worker/main.py &
sleep 2 && kill %1

conda activate env-market && python apps/market_worker/main.py &
sleep 2 && kill %1

conda activate env-execution && python apps/execution_worker/main.py &
sleep 2 && kill %1
```

### What Each Fix Does

1. **Absolute imports**: Allows Python to find the modules when running scripts directly
2. **Path manipulation**: Ensures Python can find both the `libs` and `apps` directories
3. **pydantic-settings**: Fixes the BaseSettings import error

### Alternative: Use PYTHONPATH

You can also set the PYTHONPATH environment variable:

```bash
export PYTHONPATH="/home/pi/rpi-trader:/home/pi/rpi-trader/apps:$PYTHONPATH"
cd /home/pi/rpi-trader
conda activate env-bot
python apps/bot_gateway/main.py
```

This approach can be added to your shell profile or the systemd service files.

