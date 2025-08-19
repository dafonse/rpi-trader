"""
Pydantic models for data structures
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class Trade(BaseModel):
    """Trade model"""
    id: Optional[int] = None
    symbol: str
    action: TradeAction
    quantity: Decimal
    price: Optional[Decimal] = None
    order_type: OrderType = OrderType.MARKET
    status: TradeStatus = TradeStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    broker_order_id: Optional[str] = None
    commission: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Position(BaseModel):
    """Position model"""
    id: Optional[int] = None
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketData(BaseModel):
    """Market data model"""
    id: Optional[int] = None
    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None


class SystemHealth(BaseModel):
    """System health metrics"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float] = None
    uptime: int  # seconds
    active_services: int
    failed_services: int
    network_status: bool = True


class SignalData(BaseModel):
    """Trading signal data"""
    id: Optional[int] = None
    symbol: str
    signal_type: str  # e.g., "MA_CROSSOVER", "RSI_OVERSOLD"
    strength: float  # 0.0 to 1.0
    action: TradeAction
    confidence: float  # 0.0 to 1.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BacktestResult(BaseModel):
    """Backtest result model"""
    id: Optional[int] = None
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Optional[float] = None
    win_rate: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

