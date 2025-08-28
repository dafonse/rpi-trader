# BVM Integration Procedures for RPI Trader

## Overview

This guide provides step-by-step procedures to integrate your RPI Trader project with MetaTrader 5 running in a BVM (Botspot Virtual Machine) Windows 11 environment on Raspberry Pi 5.

## Architecture

```
Raspberry Pi 5 (Debian/Ubuntu Linux)
├── RPI Trader Bot (Python Services)
│   ├── Market Analysis (Free APIs)
│   ├── Signal Generation
│   ├── Telegram Bot Interface
│   └── BVM Integration Layer ←── NEW
└── BVM Windows 11 VM
    ├── MetaTrader 5
    ├── MT5 Bridge Service ←── NEW
    └── Shared Data Folder
```

## Phase 1: BVM Installation and Setup

### Step 1: Install BVM on Raspberry Pi 5

```bash
# Clone BVM repository
cd /home/pi
git clone https://github.com/Botspot/bvm
cd bvm

# Check system requirements
./bvm help

# Create Windows 11 VM
./bvm new-vm ~/mt5-vm

# Review and edit configuration
nano ~/mt5-vm/bvm-config
```

### Step 2: Configure BVM for Trading

Edit `~/mt5-vm/bvm-config`:
```bash
# Increase RAM allocation for trading
ram_gb=4

# Set up shared folder for data exchange
shared_folder="/home/pi/rpi-trader/shared"

# Enable RDP for better performance
enable_rdp=true

# Set timezone for trading hours
timezone="America/New_York"
```

### Step 3: Download and Install Windows 11

```bash
# Download Windows 11 ARM ISO
./bvm download ~/mt5-vm

# Prepare installation
./bvm prepare ~/mt5-vm

# Run first boot (automated Windows installation)
./bvm firstboot ~/mt5-vm
# This takes 30-60 minutes, let it complete automatically
```

## Phase 2: MetaTrader 5 Setup in BVM

### Step 4: Access Windows VM

```bash
# Start VM headless (recommended)
./bvm boot-nodisplay ~/mt5-vm

# Connect via RDP (in another terminal)
./bvm connect ~/mt5-vm
```

### Step 5: Install MetaTrader 5 in Windows

1. **Download MT5**: Visit your broker's website in Windows VM
2. **Install MT5**: Follow broker's installation instructions
3. **Configure Account**: Set up your trading account
4. **Test Connection**: Verify broker connectivity

### Step 6: Install Python in Windows VM

```powershell
# In Windows VM, download Python 3.11
# Install from python.org
# Add to PATH during installation

# Install required packages
pip install MetaTrader5 flask requests aiohttp
```

## Phase 3: Create MT5 Bridge Service

### Step 7: Create MT5 Bridge Service in Windows VM

Create `C:\mt5_bridge\mt5_bridge_service.py`:

```python
"""
MetaTrader 5 Bridge Service
Runs in Windows VM, exposes MT5 functionality via HTTP API
"""

import MetaTrader5 as mt5
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import logging
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MT5 connection status
mt5_connected = False
mt5_account_info = None

def initialize_mt5():
    """Initialize MT5 connection"""
    global mt5_connected, mt5_account_info
    
    try:
        if not mt5.initialize():
            logger.error("MT5 initialization failed")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False
        
        mt5_connected = True
        mt5_account_info = account_info._asdict()
        logger.info(f"MT5 connected successfully. Account: {account_info.login}")
        return True
        
    except Exception as e:
        logger.error(f"MT5 initialization error: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'mt5_connected': mt5_connected,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/connect', methods=['POST'])
def connect_mt5():
    """Connect to MT5 with credentials"""
    try:
        data = request.json
        login = data.get('login')
        password = data.get('password')
        server = data.get('server')
        
        # Initialize MT5
        if not mt5.initialize():
            return jsonify({'success': False, 'error': 'MT5 initialization failed'}), 500
        
        # Login
        authorized = mt5.login(login, password=password, server=server)
        if not authorized:
            return jsonify({'success': False, 'error': 'Login failed'}), 401
        
        global mt5_connected, mt5_account_info
        mt5_connected = True
        mt5_account_info = mt5.account_info()._asdict()
        
        return jsonify({
            'success': True,
            'account_info': mt5_account_info
        })
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/account_info', methods=['GET'])
def get_account_info():
    """Get account information"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return jsonify({'error': 'Failed to get account info'}), 500
        
        return jsonify(account_info._asdict())
        
    except Exception as e:
        logger.error(f"Account info error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/symbol_info/<symbol>', methods=['GET'])
def get_symbol_info(symbol):
    """Get symbol information"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return jsonify({'error': f'Symbol {symbol} not found'}), 404
        
        return jsonify(symbol_info._asdict())
        
    except Exception as e:
        logger.error(f"Symbol info error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/tick/<symbol>', methods=['GET'])
def get_tick(symbol):
    """Get current tick for symbol"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return jsonify({'error': f'No tick data for {symbol}'}), 404
        
        return jsonify({
            'symbol': symbol,
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'time': tick.time,
            'flags': tick.flags,
            'volume_real': tick.volume_real
        })
        
    except Exception as e:
        logger.error(f"Tick error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/rates/<symbol>', methods=['GET'])
def get_rates(symbol):
    """Get historical rates"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        # Get query parameters
        timeframe = request.args.get('timeframe', 'M1')
        count = int(request.args.get('count', 100))
        
        # Convert timeframe string to MT5 constant
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        
        tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
        
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return jsonify({'error': f'No rates data for {symbol}'}), 404
        
        # Convert numpy array to list of dicts
        rates_list = []
        for rate in rates:
            rates_list.append({
                'time': int(rate[0]),
                'open': float(rate[1]),
                'high': float(rate[2]),
                'low': float(rate[3]),
                'close': float(rate[4]),
                'tick_volume': int(rate[5]),
                'spread': int(rate[6]),
                'real_volume': int(rate[7])
            })
        
        return jsonify({
            'symbol': symbol,
            'timeframe': timeframe,
            'count': len(rates_list),
            'rates': rates_list
        })
        
    except Exception as e:
        logger.error(f"Rates error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/order_send', methods=['POST'])
def send_order():
    """Send trading order"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        data = request.json
        
        # Build order request
        request_dict = {
            "action": data.get('action', mt5.TRADE_ACTION_DEAL),
            "symbol": data['symbol'],
            "volume": float(data['volume']),
            "type": data.get('type', mt5.ORDER_TYPE_BUY),
            "price": float(data.get('price', 0)),
            "sl": float(data.get('sl', 0)),
            "tp": float(data.get('tp', 0)),
            "deviation": int(data.get('deviation', 20)),
            "magic": int(data.get('magic', 234000)),
            "comment": data.get('comment', 'RPI Trader'),
            "type_time": data.get('type_time', mt5.ORDER_TIME_GTC),
            "type_filling": data.get('type_filling', mt5.ORDER_FILLING_IOC)
        }
        
        # Send order
        result = mt5.order_send(request_dict)
        
        if result is None:
            return jsonify({'success': False, 'error': 'Order send failed'}), 500
        
        return jsonify({
            'success': True,
            'order_result': result._asdict()
        })
        
    except Exception as e:
        logger.error(f"Order send error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/positions', methods=['GET'])
def get_positions():
    """Get open positions"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        positions = mt5.positions_get()
        if positions is None:
            return jsonify([])
        
        positions_list = []
        for pos in positions:
            positions_list.append(pos._asdict())
        
        return jsonify(positions_list)
        
    except Exception as e:
        logger.error(f"Positions error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    """Get pending orders"""
    if not mt5_connected:
        return jsonify({'error': 'MT5 not connected'}), 400
    
    try:
        orders = mt5.orders_get()
        if orders is None:
            return jsonify([])
        
        orders_list = []
        for order in orders:
            orders_list.append(order._asdict())
        
        return jsonify(orders_list)
        
    except Exception as e:
        logger.error(f"Orders error: {e}")
        return jsonify({'error': str(e)}), 500

def monitor_connection():
    """Monitor MT5 connection in background"""
    global mt5_connected
    
    while True:
        try:
            if mt5_connected:
                # Test connection
                account_info = mt5.account_info()
                if account_info is None:
                    logger.warning("MT5 connection lost")
                    mt5_connected = False
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Connection monitor error: {e}")
            mt5_connected = False
            time.sleep(30)

if __name__ == '__main__':
    # Initialize MT5 on startup
    initialize_mt5()
    
    # Start connection monitor thread
    monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
    monitor_thread.start()
    
    # Start Flask server
    logger.info("Starting MT5 Bridge Service on port 8080")
    app.run(host='0.0.0.0', port=8080, debug=False)
```

### Step 8: Create Windows Service Wrapper

Create `C:\mt5_bridge\start_service.bat`:
```batch
@echo off
cd C:\mt5_bridge
python mt5_bridge_service.py
pause
```

Create `C:\mt5_bridge\install_service.py`:
```python
"""
Install MT5 Bridge as Windows Service
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess

class MT5BridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MT5BridgeService"
    _svc_display_name_ = "MetaTrader 5 Bridge Service"
    _svc_description_ = "HTTP API bridge for MetaTrader 5"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        # Start the MT5 bridge service
        script_path = r"C:\mt5_bridge\mt5_bridge_service.py"
        self.process = subprocess.Popen([sys.executable, script_path])
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(MT5BridgeService)
```

## Phase 4: Create Linux Integration Layer

### Step 9: Create BVM MT5 Client for Linux

Create `/home/pi/rpi-trader/libs/broker/bvm_mt5_client.py`:

```python
"""
BVM MetaTrader 5 Client
Communicates with MT5 running in BVM Windows VM
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import logging

from ..core.logging import get_logger
from ..core.config import get_settings

logger = get_logger(__name__)


class BVMMT5Client:
    """MetaTrader 5 client for BVM Windows VM"""
    
    def __init__(self, vm_ip: str = "localhost", vm_port: int = 8080):
        self.vm_ip = vm_ip
        self.vm_port = vm_port
        self.base_url = f"http://{vm_ip}:{vm_port}"
        self.session = None
        self.connected = False
        self.account_info = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to MT5 bridge service"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
            
            elif method.upper() == 'POST':
                async with self.session.post(url, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Connection error: {e}")
    
    async def health_check(self) -> bool:
        """Check if MT5 bridge service is running"""
        try:
            result = await self._make_request('GET', 'health')
            return result.get('status') == 'running'
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def connect(self, login: str, password: str, server: str) -> bool:
        """Connect to MetaTrader 5"""
        try:
            data = {
                'login': login,
                'password': password,
                'server': server
            }
            
            result = await self._make_request('POST', 'connect', data)
            
            if result.get('success'):
                self.connected = True
                self.account_info = result.get('account_info')
                logger.info("Successfully connected to MT5", account=login)
                return True
            else:
                logger.error("MT5 connection failed", error=result.get('error'))
                return False
                
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            return await self._make_request('GET', 'account_info')
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for symbol"""
        try:
            return await self._make_request('GET', f'tick/{symbol}')
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str = 'H1', count: int = 100) -> List[Dict[str, Any]]:
        """Get historical data"""
        try:
            endpoint = f'rates/{symbol}?timeframe={timeframe}&count={count}'
            result = await self._make_request('GET', endpoint)
            return result.get('rates', [])
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []
    
    async def place_order(self, symbol: str, order_type: str, volume: float, 
                         price: float = 0, sl: float = 0, tp: float = 0,
                         comment: str = "RPI Trader") -> Optional[Dict[str, Any]]:
        """Place trading order"""
        try:
            # Map order types
            type_map = {
                'BUY': 0,  # ORDER_TYPE_BUY
                'SELL': 1,  # ORDER_TYPE_SELL
                'BUY_LIMIT': 2,
                'SELL_LIMIT': 3,
                'BUY_STOP': 4,
                'SELL_STOP': 5
            }
            
            data = {
                'symbol': symbol,
                'type': type_map.get(order_type.upper(), 0),
                'volume': volume,
                'price': price,
                'sl': sl,
                'tp': tp,
                'comment': comment
            }
            
            result = await self._make_request('POST', 'order_send', data)
            
            if result.get('success'):
                logger.info("Order placed successfully", symbol=symbol, type=order_type, volume=volume)
                return result.get('order_result')
            else:
                logger.error("Order failed", error=result.get('error'))
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        try:
            return await self._make_request('GET', 'positions')
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        try:
            return await self._make_request('GET', 'orders')
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    def is_connected(self) -> bool:
        """Check if connected to MT5"""
        return self.connected
```

## Phase 5: Update RPI Trader Configuration

### Step 10: Update Environment Configuration

Add to `/home/pi/rpi-trader/.env`:
```bash
# BVM MT5 Configuration
BVM_MT5_ENABLED=true
BVM_VM_IP=localhost
BVM_VM_PORT=8080

# MT5 Credentials
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_broker_server

# Hybrid Mode Settings
USE_HYBRID_ANALYSIS=true
MT5_FOR_EXECUTION_ONLY=true
```

### Step 11: Update Core Configuration

Update `/home/pi/rpi-trader/libs/core/config.py`:
```python
# Add BVM MT5 settings
class Settings(BaseSettings):
    # ... existing settings ...
    
    # BVM MT5 Configuration
    bvm_mt5_enabled: bool = False
    bvm_vm_ip: str = "localhost"
    bvm_vm_port: int = 8080
    
    # MT5 Credentials
    mt5_login: str = ""
    mt5_password: str = ""
    mt5_server: str = ""
    
    # Hybrid Mode
    use_hybrid_analysis: bool = True
    mt5_for_execution_only: bool = True
```

This completes the integration framework. The next steps would involve updating the execution worker and creating the hybrid analysis system.

