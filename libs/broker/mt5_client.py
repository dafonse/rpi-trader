"""
MetaTrader 5 client implementations
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

import httpx
from structlog import get_logger

from .base import BaseBroker, BrokerError, ConnectionError, OrderError
from ..data.models import Trade, Position, MarketData, TradeAction, TradeStatus, OrderType
from ..core.config import get_settings

logger = get_logger(__name__)


class MT5Client(BaseBroker):
    """Direct MetaTrader 5 client (requires MT5 installed locally)"""
    
    def __init__(self):
        self.settings = get_settings()
        self._connected = False
        
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
        except ImportError:
            raise BrokerError("MetaTrader5 package not installed. Use MT5APIClient instead.")
    
    async def connect(self) -> bool:
        """Connect to MT5 terminal"""
        try:
            if not self.mt5.initialize():
                error = self.mt5.last_error()
                logger.error("MT5 initialization failed", error=error)
                return False
            
            if self.settings.mt5_login and self.settings.mt5_password and self.settings.mt5_server:
                if not self.mt5.login(
                    login=int(self.settings.mt5_login),
                    password=self.settings.mt5_password,
                    server=self.settings.mt5_server
                ):
                    error = self.mt5.last_error()
                    logger.error("MT5 login failed", error=error)
                    return False
            
            self._connected = True
            logger.info("Connected to MT5")
            return True
            
        except Exception as e:
            logger.error("MT5 connection error", error=str(e))
            raise ConnectionError(f"Failed to connect to MT5: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from MT5"""
        if self._connected:
            self.mt5.shutdown()
            self._connected = False
            logger.info("Disconnected from MT5")
    
    async def is_connected(self) -> bool:
        """Check MT5 connection status"""
        return self._connected and self.mt5.terminal_info() is not None
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5")
        
        account_info = self.mt5.account_info()
        if account_info is None:
            raise BrokerError("Failed to get account info")
        
        return {
            "login": account_info.login,
            "balance": float(account_info.balance),
            "equity": float(account_info.equity),
            "margin": float(account_info.margin),
            "free_margin": float(account_info.margin_free),
            "currency": account_info.currency,
            "leverage": account_info.leverage,
        }
    
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5")
        
        positions = self.mt5.positions_get()
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            position = Position(
                symbol=pos.symbol,
                quantity=Decimal(str(pos.volume)),
                average_price=Decimal(str(pos.price_open)),
                current_price=Decimal(str(pos.price_current)),
                unrealized_pnl=Decimal(str(pos.profit)),
                created_at=datetime.fromtimestamp(pos.time)
            )
            result.append(position)
        
        return result
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5")
        
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return MarketData(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(tick.time),
            bid=Decimal(str(tick.bid)),
            ask=Decimal(str(tick.ask)),
            last=Decimal(str(tick.last)),
            volume=Decimal(str(tick.volume))
        )
    
    async def place_order(self, trade: Trade) -> str:
        """Place an order"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5")
        
        # Convert trade to MT5 order request
        order_type_map = {
            (TradeAction.BUY, OrderType.MARKET): self.mt5.ORDER_TYPE_BUY,
            (TradeAction.SELL, OrderType.MARKET): self.mt5.ORDER_TYPE_SELL,
            (TradeAction.BUY, OrderType.LIMIT): self.mt5.ORDER_TYPE_BUY_LIMIT,
            (TradeAction.SELL, OrderType.LIMIT): self.mt5.ORDER_TYPE_SELL_LIMIT,
        }
        
        mt5_order_type = order_type_map.get((trade.action, trade.order_type))
        if mt5_order_type is None:
            raise OrderError(f"Unsupported order type: {trade.action} {trade.order_type}")
        
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": trade.symbol,
            "volume": float(trade.quantity),
            "type": mt5_order_type,
            "deviation": 20,
            "magic": 234000,
            "comment": "RPI Trader",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        
        if trade.price:
            request["price"] = float(trade.price)
        
        result = self.mt5.order_send(request)
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise OrderError(f"Order failed: {result.comment}")
        
        return str(result.order)
    
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order"""
        # Implementation depends on MT5 API for pending orders
        return True
    
    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        """Get order status"""
        # Implementation depends on MT5 API
        return {"status": "unknown"}
    
    async def get_trade_history(self, days: int = 30) -> List[Trade]:
        """Get trade history"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5")
        
        start_date = datetime.now() - timedelta(days=days)
        deals = self.mt5.history_deals_get(start_date, datetime.now())
        
        if deals is None:
            return []
        
        trades = []
        for deal in deals:
            trade = Trade(
                symbol=deal.symbol,
                action=TradeAction.BUY if deal.type == 0 else TradeAction.SELL,
                quantity=Decimal(str(deal.volume)),
                price=Decimal(str(deal.price)),
                status=TradeStatus.FILLED,
                created_at=datetime.fromtimestamp(deal.time),
                filled_at=datetime.fromtimestamp(deal.time),
                broker_order_id=str(deal.order),
                commission=Decimal(str(deal.commission)),
                pnl=Decimal(str(deal.profit))
            )
            trades.append(trade)
        
        return trades


class MT5APIClient(BaseBroker):
    """MetaTrader 5 API client (connects to remote MT5 via HTTP API)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.mt5_api_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to MT5 API"""
        try:
            response = await self.client.post(f"{self.base_url}/connect", json={
                "login": self.settings.mt5_login,
                "password": self.settings.mt5_password,
                "server": self.settings.mt5_server
            })
            
            if response.status_code == 200:
                result = response.json()
                self._connected = result.get("success", False)
                if self._connected:
                    logger.info("Connected to MT5 API")
                else:
                    logger.error("MT5 API connection failed", error=result.get("error"))
                return self._connected
            else:
                logger.error("MT5 API connection failed", status_code=response.status_code)
                return False
                
        except Exception as e:
            logger.error("MT5 API connection error", error=str(e))
            raise ConnectionError(f"Failed to connect to MT5 API: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from MT5 API"""
        if self._connected:
            try:
                await self.client.post(f"{self.base_url}/disconnect")
            except Exception:
                pass
            finally:
                self._connected = False
                await self.client.aclose()
                logger.info("Disconnected from MT5 API")
    
    async def is_connected(self) -> bool:
        """Check connection status"""
        if not self._connected:
            return False
        
        try:
            response = await self.client.get(f"{self.base_url}/status")
            return response.status_code == 200 and response.json().get("connected", False)
        except Exception:
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5 API")
        
        response = await self.client.get(f"{self.base_url}/account")
        if response.status_code != 200:
            raise BrokerError("Failed to get account info")
        
        return response.json()
    
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5 API")
        
        response = await self.client.get(f"{self.base_url}/positions")
        if response.status_code != 200:
            return []
        
        positions_data = response.json()
        positions = []
        
        for pos_data in positions_data:
            position = Position(
                symbol=pos_data["symbol"],
                quantity=Decimal(str(pos_data["volume"])),
                average_price=Decimal(str(pos_data["price_open"])),
                current_price=Decimal(str(pos_data["price_current"])),
                unrealized_pnl=Decimal(str(pos_data["profit"])),
                created_at=datetime.fromisoformat(pos_data["time"])
            )
            positions.append(position)
        
        return positions
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5 API")
        
        response = await self.client.get(f"{self.base_url}/tick/{symbol}")
        if response.status_code != 200:
            return None
        
        tick_data = response.json()
        return MarketData(
            symbol=symbol,
            timestamp=datetime.fromisoformat(tick_data["time"]),
            bid=Decimal(str(tick_data["bid"])),
            ask=Decimal(str(tick_data["ask"])),
            last=Decimal(str(tick_data["last"])),
            volume=Decimal(str(tick_data["volume"]))
        )
    
    async def place_order(self, trade: Trade) -> str:
        """Place an order"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5 API")
        
        order_data = {
            "symbol": trade.symbol,
            "action": trade.action.value,
            "volume": float(trade.quantity),
            "order_type": trade.order_type.value,
            "price": float(trade.price) if trade.price else None
        }
        
        response = await self.client.post(f"{self.base_url}/order", json=order_data)
        if response.status_code != 200:
            result = response.json()
            raise OrderError(f"Order failed: {result.get('error', 'Unknown error')}")
        
        result = response.json()
        return str(result["order_id"])
    
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order"""
        response = await self.client.delete(f"{self.base_url}/order/{broker_order_id}")
        return response.status_code == 200
    
    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        """Get order status"""
        response = await self.client.get(f"{self.base_url}/order/{broker_order_id}")
        if response.status_code == 200:
            return response.json()
        return {"status": "unknown"}
    
    async def get_trade_history(self, days: int = 30) -> List[Trade]:
        """Get trade history"""
        if not await self.is_connected():
            raise ConnectionError("Not connected to MT5 API")
        
        response = await self.client.get(f"{self.base_url}/history?days={days}")
        if response.status_code != 200:
            return []
        
        history_data = response.json()
        trades = []
        
        for trade_data in history_data:
            trade = Trade(
                symbol=trade_data["symbol"],
                action=TradeAction(trade_data["action"]),
                quantity=Decimal(str(trade_data["volume"])),
                price=Decimal(str(trade_data["price"])),
                status=TradeStatus.FILLED,
                created_at=datetime.fromisoformat(trade_data["time"]),
                filled_at=datetime.fromisoformat(trade_data["time"]),
                broker_order_id=str(trade_data["order_id"]),
                commission=Decimal(str(trade_data.get("commission", 0))),
                pnl=Decimal(str(trade_data.get("profit", 0)))
            )
            trades.append(trade)
        
        return trades

