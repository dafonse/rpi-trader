# MetaTrader 5 Virtual Machine Integration Guide

## Your Setup: Windows 11 VM on Raspberry Pi 5

Running MetaTrader 5 in a Windows 11 virtual machine on your Raspberry Pi 5 is actually a clever workaround for the ARM compatibility issue. Here are the integration options:

## Current Code Status

**The original MT5 code I wrote was designed for direct local access**, but it can be adapted for your VM setup. Here's what needs to be configured:

### Option 1: MetaTrader 5 Python API (Recommended)

The MT5 Python library (`MetaTrader5`) can connect to MT5 running in a VM, but requires specific configuration:

#### Requirements:
1. **MT5 Terminal** running in Windows 11 VM
2. **Python with MetaTrader5 library** installed in the VM
3. **Network bridge** between VM and Raspberry Pi host
4. **Remote API service** to expose MT5 data

#### Architecture:
```
Raspberry Pi (Linux) → Network → Windows 11 VM → MetaTrader 5
     ↑                                              ↑
RPI Trader Bot                              MT5 Python API
```

### Option 2: MetaTrader 5 Web API (Alternative)

Some brokers provide REST APIs that can be used alongside MT5:

#### Supported Brokers with APIs:
- **OANDA** - REST API
- **Interactive Brokers** - TWS API
- **Alpaca** - REST API (US stocks only)
- **Dukascopy** - REST API

## Implementation Options

### Option A: Hybrid System (Recommended)

Keep the new API-based system for analysis and add MT5 for actual trading:

```python
# Use new APIs for analysis
analysis_result = await data_collector.collect_end_of_day_data(symbols)

# Use MT5 VM for actual trading
if should_execute_trade(analysis_result):
    await mt5_vm_client.place_order(symbol, action, volume)
```

### Option B: Pure MT5 VM Integration

Restore the original MT5 client but configure it for remote access.

## Detailed Implementation

### 1. MT5 VM Bridge Service

Create a bridge service that runs in the Windows VM and exposes MT5 functionality via HTTP API:

#### In Windows VM (`mt5_bridge_service.py`):
```python
import MetaTrader5 as mt5
from flask import Flask, jsonify, request
import json

app = Flask(__name__)

@app.route('/connect', methods=['POST'])
def connect_mt5():
    data = request.json
    result = mt5.initialize(
        login=data['login'],
        password=data['password'],
        server=data['server']
    )
    return jsonify({'success': result})

@app.route('/get_price/<symbol>')
def get_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return jsonify({
            'symbol': symbol,
            'bid': tick.bid,
            'ask': tick.ask,
            'time': tick.time
        })
    return jsonify({'error': 'Symbol not found'}), 404

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    # Implement order placement logic
    # Return order result
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)  # Accessible from host
```

#### On Raspberry Pi (`mt5_vm_client.py`):
```python
import aiohttp
import asyncio
from typing import Dict, Any, Optional

class MT5VMClient:
    def __init__(self, vm_ip: str, vm_port: int = 8080):
        self.base_url = f"http://{vm_ip}:{vm_port}"
        self.session = None
    
    async def connect(self, login: str, password: str, server: str) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/connect", json={
                'login': login,
                'password': password,
                'server': server
            }) as response:
                result = await response.json()
                return result.get('success', False)
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/get_price/{symbol}") as response:
                if response.status == 200:
                    return await response.json()
                return None
```

### 2. Network Configuration

#### VM Network Setup:
1. **Bridge Network Mode**: Configure VM with bridged networking
2. **Static IP**: Assign static IP to VM (e.g., 192.168.1.100)
3. **Firewall**: Open port 8080 in Windows firewall

#### Raspberry Pi Configuration:
```bash
# Test connectivity to VM
ping 192.168.1.100

# Test MT5 bridge service
curl http://192.168.1.100:8080/get_price/EURUSD
```

### 3. Updated Configuration

#### `.env` file:
```bash
# MT5 VM Configuration
MT5_VM_IP=192.168.1.100
MT5_VM_PORT=8080
MT5_SERVER=your_broker_server
MT5_LOGIN=your_login
MT5_PASSWORD=your_password

# Keep API keys for analysis
ALPHA_VANTAGE_API_KEY=optional
FINNHUB_API_KEY=optional
```

## Code Integration

### Restore MT5 Client with VM Support

I can restore the original MT5 client code and modify it to work with your VM setup:

```python
# libs/broker/mt5_vm_client.py
class MT5VMClient:
    def __init__(self, vm_ip: str, vm_port: int = 8080):
        self.vm_ip = vm_ip
        self.vm_port = vm_port
        self.base_url = f"http://{vm_ip}:{vm_port}"
        self.connected = False
    
    async def connect(self) -> bool:
        # Connect to MT5 via VM bridge
        pass
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        # Get price from MT5 via VM
        pass
    
    async def place_order(self, symbol: str, action: str, volume: float) -> Dict[str, Any]:
        # Place order via MT5 VM
        pass
```

### Hybrid Market Service

Combine both approaches:

```python
class HybridMarketService:
    def __init__(self):
        # Initialize both systems
        self.data_collector = DataCollector()  # For analysis
        self.mt5_client = MT5VMClient()        # For trading
    
    async def run_analysis_and_trade(self):
        # 1. Run comprehensive analysis using APIs
        analysis = await self.data_collector.collect_end_of_day_data(symbols)
        
        # 2. Generate signals
        signals = self.generate_signals(analysis)
        
        # 3. Execute trades via MT5 VM
        for signal in signals:
            if signal['confidence'] > 0.7:
                await self.mt5_client.place_order(
                    symbol=signal['symbol'],
                    action=signal['action'],
                    volume=signal['volume']
                )
```

## Performance Considerations

### VM Resource Requirements:
- **RAM**: 4-8GB for Windows 11 + MT5
- **CPU**: 2-4 cores allocated to VM
- **Storage**: 50-100GB for Windows + MT5
- **Network**: Stable connection between host and VM

### Latency Considerations:
- **VM Overhead**: ~10-50ms additional latency
- **Network Latency**: ~1-5ms between host and VM
- **Total Impact**: Acceptable for end-of-day trading, not for scalping

## Advantages of This Approach

1. **Full MT5 Functionality**: Access to all MT5 features and indicators
2. **Broker Compatibility**: Works with any MT5-compatible broker
3. **Real Trading**: Actual order execution through MT5
4. **Hybrid Analysis**: Combine free APIs with MT5 data
5. **Flexibility**: Can switch between API-only and MT5 modes

## Disadvantages

1. **Resource Intensive**: VM requires significant RAM/CPU
2. **Complexity**: More moving parts to maintain
3. **Single Point of Failure**: VM issues affect trading
4. **Licensing**: Windows 11 licensing requirements

## Recommendation

**I recommend the Hybrid approach**:
1. Use the new API system for market analysis (free, reliable)
2. Add MT5 VM integration for actual trading execution
3. This gives you the best of both worlds

Would you like me to:
1. **Restore and adapt the original MT5 client** for VM integration?
2. **Create the VM bridge service** for Windows 11?
3. **Implement the hybrid system** combining both approaches?

Let me know which approach interests you most!

