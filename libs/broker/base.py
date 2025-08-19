"""
Base broker interface and exceptions
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ..data.models import Trade, Position, MarketData


class BrokerError(Exception):
    """Base exception for broker-related errors"""
    pass


class ConnectionError(BrokerError):
    """Broker connection error"""
    pass


class OrderError(BrokerError):
    """Order execution error"""
    pass


class BaseBroker(ABC):
    """Abstract base class for broker implementations"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to broker"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data for symbol"""
        pass
    
    @abstractmethod
    async def place_order(self, trade: Trade) -> str:
        """Place an order and return broker order ID"""
        pass
    
    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_trade_history(self, days: int = 30) -> List[Trade]:
        """Get trade history"""
        pass

