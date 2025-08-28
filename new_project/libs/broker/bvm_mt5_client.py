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

from libs.core.logging import get_logger
from libs.core.config import get_settings

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


