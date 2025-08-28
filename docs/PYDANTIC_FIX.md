# Fix for Pydantic BaseSettings Import Error

## Problem
The error `pydantic.errors.PydanticImportError: BaseSettings has been moved to the pydantic-settings package` occurs because Pydantic v2 moved `BaseSettings` to a separate package.

## Solution

### Step 1: Install pydantic-settings in all environments

```bash
# For each conda environment, install pydantic-settings
conda activate env-bot
pip install pydantic-settings>=2.0.0

conda activate env-scheduler  
pip install pydantic-settings>=2.0.0

conda activate env-finance
pip install pydantic-settings>=2.0.0

conda activate env-market
pip install pydantic-settings>=2.0.0

conda activate env-execution
pip install pydantic-settings>=2.0.0
```

### Step 2: Reinstall the project dependencies

```bash
cd /home/pi/rpi-trader

# Install main project dependencies
conda activate env-bot
pip install -e .

# Install each app's dependencies
cd apps/bot_gateway && pip install -e . && cd ../..
cd apps/scheduler && conda activate env-scheduler && pip install -e . && cd ../..
cd apps/finance_worker && conda activate env-finance && pip install -e . && cd ../..
cd apps/market_worker && conda activate env-market && pip install -e . && cd ../..
cd apps/execution_worker && conda activate env-execution && pip install -e . && cd ../..
```

### Step 3: Test the fix

```bash
cd /home/pi/rpi-trader
conda activate env-bot
python apps/bot_gateway/main.py
```

If this runs without the Pydantic error, the fix is successful!

## What Was Fixed

1. **Import statement**: Changed from `from pydantic import BaseSettings, Field` to:
   ```python
   from pydantic_settings import BaseSettings
   from pydantic import Field
   ```

2. **Dependencies**: Added `pydantic-settings>=2.0.0` to all `pyproject.toml` files

## Quick Install Command

If you want to install pydantic-settings in all environments at once:

```bash
cd /home/pi/rpi-trader

# Install in all environments
for env in env-bot env-scheduler env-finance env-market env-execution; do
  conda activate $env
  pip install pydantic-settings>=2.0.0
done
```

## Verification

After applying the fix, you should be able to run:

```bash
conda activate env-bot
cd /home/pi/rpi-trader
python -c "from libs.core.config import get_settings; print('Config import successful!')"
```

This should print "Config import successful!" without any errors.

