"""
Repository pattern for data access abstraction
"""

import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from .models import Trade, Position, MarketData, SystemHealth, SignalData, BacktestResult


class BaseRepository(ABC):
    """Base repository interface"""
    
    def __init__(self, db_path: str = "rpi_trader.db"):
        self.db_path = db_path
        self.init_db()
    
    @abstractmethod
    def init_db(self) -> None:
        """Initialize database tables"""
        pass


class TradeRepository(BaseRepository):
    """Repository for trade data"""
    
    def init_db(self) -> None:
        """Initialize trades table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity DECIMAL NOT NULL,
                    price DECIMAL,
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    filled_at TIMESTAMP,
                    broker_order_id TEXT,
                    commission DECIMAL,
                    pnl DECIMAL,
                    metadata TEXT
                )
            """)
            conn.commit()
    
    def create(self, trade: Trade) -> Trade:
        """Create a new trade"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trades (symbol, action, quantity, price, order_type, status, 
                                  created_at, filled_at, broker_order_id, commission, pnl, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol, trade.action.value, str(trade.quantity), 
                str(trade.price) if trade.price else None,
                trade.order_type.value, trade.status.value, trade.created_at,
                trade.filled_at, trade.broker_order_id, 
                str(trade.commission) if trade.commission else None,
                str(trade.pnl) if trade.pnl else None,
                str(trade.metadata) if trade.metadata else "{}"
            ))
            trade.id = cursor.lastrowid
            conn.commit()
        return trade
    
    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_trade(row)
        return None
    
    def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", 
                (limit,)
            )
            return [self._row_to_trade(row) for row in cursor.fetchall()]
    
    def get_trades_by_symbol(self, symbol: str, days: int = 30) -> List[Trade]:
        """Get trades for a symbol within specified days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM trades WHERE symbol = ? AND created_at >= ? ORDER BY created_at DESC",
                (symbol, start_date)
            )
            return [self._row_to_trade(row) for row in cursor.fetchall()]
    
    def update_status(self, trade_id: int, status: str, filled_at: Optional[datetime] = None) -> None:
        """Update trade status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE trades SET status = ?, filled_at = ? WHERE id = ?",
                (status, filled_at, trade_id)
            )
            conn.commit()
    
    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """Convert database row to Trade model"""
        return Trade(
            id=row["id"],
            symbol=row["symbol"],
            action=row["action"],
            quantity=Decimal(row["quantity"]),
            price=Decimal(row["price"]) if row["price"] else None,
            order_type=row["order_type"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            filled_at=datetime.fromisoformat(row["filled_at"]) if row["filled_at"] else None,
            broker_order_id=row["broker_order_id"],
            commission=Decimal(row["commission"]) if row["commission"] else None,
            pnl=Decimal(row["pnl"]) if row["pnl"] else None,
            metadata=eval(row["metadata"]) if row["metadata"] else {}
        )


class PositionRepository(BaseRepository):
    """Repository for position data"""
    
    def init_db(self) -> None:
        """Initialize positions table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    quantity DECIMAL NOT NULL,
                    average_price DECIMAL NOT NULL,
                    current_price DECIMAL,
                    unrealized_pnl DECIMAL,
                    realized_pnl DECIMAL DEFAULT 0.0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()
    
    def upsert(self, position: Position) -> Position:
        """Create or update position"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO positions 
                (symbol, quantity, average_price, current_price, unrealized_pnl, 
                 realized_pnl, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.symbol, str(position.quantity), str(position.average_price),
                str(position.current_price) if position.current_price else None,
                str(position.unrealized_pnl) if position.unrealized_pnl else None,
                str(position.realized_pnl), position.created_at, position.updated_at
            ))
            conn.commit()
        return position
    
    def get_all_positions(self) -> List[Position]:
        """Get all current positions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM positions WHERE quantity != 0")
            return [self._row_to_position(row) for row in cursor.fetchall()]
    
    def _row_to_position(self, row: sqlite3.Row) -> Position:
        """Convert database row to Position model"""
        return Position(
            id=row["id"],
            symbol=row["symbol"],
            quantity=Decimal(row["quantity"]),
            average_price=Decimal(row["average_price"]),
            current_price=Decimal(row["current_price"]) if row["current_price"] else None,
            unrealized_pnl=Decimal(row["unrealized_pnl"]) if row["unrealized_pnl"] else None,
            realized_pnl=Decimal(row["realized_pnl"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )


class MarketDataRepository(BaseRepository):
    """Repository for market data"""
    
    def init_db(self) -> None:
        """Initialize market_data table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    bid DECIMAL NOT NULL,
                    ask DECIMAL NOT NULL,
                    last DECIMAL,
                    volume DECIMAL,
                    high DECIMAL,
                    low DECIMAL,
                    open DECIMAL,
                    UNIQUE(symbol, timestamp)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)")
            conn.commit()
    
    def insert_tick(self, market_data: MarketData) -> MarketData:
        """Insert market data tick"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO market_data 
                (symbol, timestamp, bid, ask, last, volume, high, low, open)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol, market_data.timestamp, str(market_data.bid),
                str(market_data.ask), str(market_data.last) if market_data.last else None,
                str(market_data.volume) if market_data.volume else None,
                str(market_data.high) if market_data.high else None,
                str(market_data.low) if market_data.low else None,
                str(market_data.open) if market_data.open else None
            ))
            conn.commit()
        return market_data
    
    def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """Get latest price for symbol"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM market_data WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_market_data(row)
        return None
    
    def _row_to_market_data(self, row: sqlite3.Row) -> MarketData:
        """Convert database row to MarketData model"""
        return MarketData(
            id=row["id"],
            symbol=row["symbol"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            bid=Decimal(row["bid"]),
            ask=Decimal(row["ask"]),
            last=Decimal(row["last"]) if row["last"] else None,
            volume=Decimal(row["volume"]) if row["volume"] else None,
            high=Decimal(row["high"]) if row["high"] else None,
            low=Decimal(row["low"]) if row["low"] else None,
            open=Decimal(row["open"]) if row["open"] else None
        )

