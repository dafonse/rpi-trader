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

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "mt5_connected": mt5_connected,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/connect", methods=["POST"])
def connect_mt5():
    """Connect to MT5 with credentials"""
    try:
        data = request.json
        login = data.get("login")
        password = data.get("password")
        server = data.get("server")
        
        # Initialize MT5
        if not mt5.initialize():
            return jsonify({"success": False, "error": "MT5 initialization failed"}), 500
        
        # Login
        authorized = mt5.login(login, password=password, server=server)
        if not authorized:
            return jsonify({"success": False, "error": "Login failed"}), 401
        
        global mt5_connected, mt5_account_info
        mt5_connected = True
        mt5_account_info = mt5.account_info()._asdict()
        
        return jsonify({
            "success": True,
            "account_info": mt5_account_info
        })
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/account_info", methods=["GET"])
def get_account_info():
    """Get account information"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return jsonify({"error": "Failed to get account info"}), 500
        
        return jsonify(account_info._asdict())
        
    except Exception as e:
        logger.error(f"Account info error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/symbol_info/<symbol>", methods=["GET"])
def get_symbol_info(symbol):
    """Get symbol information"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return jsonify({"error": f"Symbol {symbol} not found"}), 404
        
        return jsonify(symbol_info._asdict())
        
    except Exception as e:
        logger.error(f"Symbol info error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/tick/<symbol>", methods=["GET"])
def get_tick(symbol):
    """Get current tick for symbol"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return jsonify({"error": f"No tick data for {symbol}"}), 404
        
        return jsonify({
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": tick.time,
            "flags": tick.flags,
            "volume_real": tick.volume_real
        })
        
    except Exception as e:
        logger.error(f"Tick error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/rates/<symbol>", methods=["GET"])
def get_rates(symbol):
    """Get historical rates"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
    try:
        # Get query parameters
        timeframe = request.args.get("timeframe", "M1")
        count = int(request.args.get("count", 100))
        
        # Convert timeframe string to MT5 constant
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
        
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return jsonify({"error": f"No rates data for {symbol}"}), 404
        
        # Convert numpy array to list of dicts
        rates_list = []
        for rate in rates:
            rates_list.append({
                "time": int(rate[0]),
                "open": float(rate[1]),
                "high": float(rate[2]),
                "low": float(rate[3]),
                "close": float(rate[4]),
                "tick_volume": int(rate[5]),
                "spread": int(rate[6]),
                "real_volume": int(rate[7])
            })
        
        return jsonify({
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(rates_list),
            "rates": rates_list
        })
        
    except Exception as e:
        logger.error(f"Rates error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/order_send", methods=["POST"])
def send_order():
    """Send trading order"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
    try:
        data = request.json
        
        # Build order request
        request_dict = {
            "action": data.get("action", mt5.TRADE_ACTION_DEAL),
            "symbol": data["symbol"],
            "volume": float(data["volume"]),
            "type": data.get("type", mt5.ORDER_TYPE_BUY),
            "price": float(data.get("price", 0)),
            "sl": float(data.get("sl", 0)),
            "tp": float(data.get("tp", 0)),
            "deviation": int(data.get("deviation", 20)),
            "magic": int(data.get("magic", 234000)),
            "comment": data.get("comment", "RPI Trader"),
            "type_time": data.get("type_time", mt5.ORDER_TIME_GTC),
            "type_filling": data.get("type_filling", mt5.ORDER_FILLING_IOC)
        }
        
        # Send order
        result = mt5.order_send(request_dict)
        
        if result is None:
            return jsonify({"success": False, "error": "Order send failed"}), 500
        
        return jsonify({
            "success": True,
            "order_result": result._asdict()
        })
        
    except Exception as e:
        logger.error(f"Order send error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/positions", methods=["GET"])
def get_positions():
    """Get open positions"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
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
        return jsonify({"error": str(e)}), 500

@app.route("/orders", methods=["GET"])
def get_orders():
    """Get pending orders"""
    if not mt5_connected:
        return jsonify({"error": "MT5 not connected"}), 400
    
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
        return jsonify({"error": str(e)}), 500

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

if __name__ == "__main__":
    # Initialize MT5 on startup
    initialize_mt5()
    
    # Start connection monitor thread
    monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
    monitor_thread.start()
    
    # Start Flask server
    logger.info("Starting MT5 Bridge Service on port 8080")
    app.run(host="0.0.0.0", port=8080, debug=False)


