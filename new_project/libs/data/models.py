"""
Data models for RPI Trader
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class TradeAction(Enum):
    """Trade action enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(Enum):
    """Trade status enumeration"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class MarketData:
    """Market data model"""
    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime
    volume: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    
    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price"""
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> Decimal:
        """Calculate spread"""
        return self.ask - self.bid


@dataclass
class SignalData:
    """Trading signal model"""
    symbol: str
    signal_type: str
    action: TradeAction
    strength: float  # -1.0 to 1.0
    timestamp: datetime
    confidence: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None


@dataclass
class Trade:
    """Trade model"""
    symbol: str
    action: TradeAction
    quantity: Decimal
    order_type: OrderType
    status: TradeStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    price: Optional[Decimal] = None
    broker_order_id: Optional[str] = None
    commission: Decimal = Decimal('0.0')
    pnl: Decimal = Decimal('0.0')
    filled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None


@dataclass
class DailyAnalysis:
    """Daily market analysis model"""
    symbol: str
    analysis_date: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    signals: Dict[str, Any] = field(default_factory=dict)
    next_day_prediction: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None


@dataclass
class MarketSummary:
    """Market summary for end-of-day analysis"""
    symbol: str
    date: datetime
    ohlcv: Dict[str, float]  # Open, High, Low, Close, Volume
    technical_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    news_impact: Dict[str, Any]
    next_day_signals: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
