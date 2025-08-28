"""
Data repository layer for RPI Trader
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from decimal import Decimal

from .models import MarketData, SignalData, Trade, TradeAction, TradeStatus


class BaseRepository:
    """Base repository class with common database operations"""
    
    def __init__(self, db_path: str = "data/rpi_trader.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.Connection(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self) -> None:
        """Initialize database tables"""
        pass  # Override in subclasses


class MarketDataRepository(BaseRepository):
    """Repository for market data storage and retrieval"""
    
    def init_db(self) -> None:
        """Initialize market data table"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    bid DECIMAL(10, 5) NOT NULL,
                    ask DECIMAL(10, 5) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    volume INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)")
    
    def create(self, market_data: MarketData) -> MarketData:
        """Create new market data entry"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO market_data (symbol, bid, ask, timestamp, volume, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol,
                str(market_data.bid),
                str(market_data.ask),
                market_data.timestamp,
                market_data.volume or 0,
                json.dumps(market_data.metadata) if market_data.metadata else None
            ))
            
            market_data.id = cursor.lastrowid
            return market_data
    
    def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """Get latest price for a symbol"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (symbol,)).fetchone()
            
            if row:
                return self._row_to_market_data(row)
            return None
    
    def get_recent_data(self, symbol: str, limit: int = 100) -> List[MarketData]:
        """Get recent market data for a symbol"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (symbol, limit)).fetchall()
            
            return [self._row_to_market_data(row) for row in rows]
    
    def get_data_since(self, symbol: str, since: datetime) -> List[MarketData]:
        """Get market data since a specific datetime"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM market_data 
                WHERE symbol = ? AND timestamp >= ? 
                ORDER BY timestamp ASC
            """, (symbol, since)).fetchall()
            
            return [self._row_to_market_data(row) for row in rows]
    
    def get_daily_data(self, symbol: str, date: datetime) -> List[MarketData]:
        """Get all market data for a specific day"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM market_data 
                WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            """, (symbol, start_of_day, end_of_day)).fetchall()
            
            return [self._row_to_market_data(row) for row in rows]
    
    def delete_old_data(self, days_to_keep: int = 30) -> int:
        """Delete market data older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM market_data 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            return cursor.rowcount
    
    def _row_to_market_data(self, row: sqlite3.Row) -> MarketData:
        """Convert database row to MarketData object"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return MarketData(
            id=row['id'],
            symbol=row['symbol'],
            bid=Decimal(str(row['bid'])),
            ask=Decimal(str(row['ask'])),
            timestamp=datetime.fromisoformat(row['timestamp']),
            volume=row['volume'],
            metadata=metadata
        )


class SignalRepository(BaseRepository):
    """Repository for trading signals storage and retrieval"""
    
    def init_db(self) -> None:
        """Initialize signals table"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    strength REAL NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals(symbol, timestamp)")
    
    def create(self, signal: SignalData) -> SignalData:
        """Create new signal entry"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO signals (symbol, signal_type, action, strength, confidence, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.symbol,
                signal.signal_type,
                signal.action.value,
                signal.strength,
                signal.confidence,
                signal.timestamp,
                json.dumps(signal.metadata) if signal.metadata else None
            ))
            
            signal.id = cursor.lastrowid
            return signal
    
    def get_recent_signals(self, symbol: str = None, limit: int = 50) -> List[SignalData]:
        """Get recent signals, optionally filtered by symbol"""
        with self.get_connection() as conn:
            if symbol:
                rows = conn.execute("""
                    SELECT * FROM signals 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (symbol, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM signals 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
            
            return [self._row_to_signal(row) for row in rows]
    
    def get_signals_since(self, symbol: str, since: datetime) -> List[SignalData]:
        """Get signals since a specific datetime"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM signals 
                WHERE symbol = ? AND timestamp >= ? 
                ORDER BY timestamp ASC
            """, (symbol, since)).fetchall()
            
            return [self._row_to_signal(row) for row in rows]
    
    def get_daily_signals(self, symbol: str, date: datetime) -> List[SignalData]:
        """Get all signals for a specific day"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM signals 
                WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            """, (symbol, start_of_day, end_of_day)).fetchall()
            
            return [self._row_to_signal(row) for row in rows]
    
    def delete_old_signals(self, days_to_keep: int = 90) -> int:
        """Delete signals older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM signals 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            return cursor.rowcount
    
    def _row_to_signal(self, row: sqlite3.Row) -> SignalData:
        """Convert database row to SignalData object"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return SignalData(
            id=row['id'],
            symbol=row['symbol'],
            signal_type=row['signal_type'],
            action=TradeAction(row['action']),
            strength=row['strength'],
            confidence=row['confidence'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            metadata=metadata
        )


class TradeRepository(BaseRepository):
    """Repository for trade records storage and retrieval"""
    
    def init_db(self) -> None:
        """Initialize trades table"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity DECIMAL(10, 5) NOT NULL,
                    price DECIMAL(10, 5),
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    broker_order_id TEXT,
                    commission DECIMAL(10, 5) DEFAULT 0.0,
                    pnl DECIMAL(10, 5) DEFAULT 0.0,
                    created_at DATETIME NOT NULL,
                    filled_at DATETIME,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at)")
    
    def create(self, trade: Trade) -> Trade:
        """Create new trade record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (symbol, action, quantity, price, order_type, status, 
                                  broker_order_id, commission, pnl, created_at, filled_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol,
                trade.action.value,
                str(trade.quantity),
                str(trade.price) if trade.price else None,
                trade.order_type.value,
                trade.status.value,
                trade.broker_order_id,
                str(trade.commission),
                str(trade.pnl),
                trade.created_at,
                trade.filled_at,
                json.dumps(trade.metadata) if trade.metadata else None
            ))
            
            trade.id = cursor.lastrowid
            return trade
    
    def update(self, trade: Trade) -> Trade:
        """Update existing trade record"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE trades 
                SET price = ?, status = ?, broker_order_id = ?, commission = ?, 
                    pnl = ?, filled_at = ?, metadata = ?
                WHERE id = ?
            """, (
                str(trade.price) if trade.price else None,
                trade.status.value,
                trade.broker_order_id,
                str(trade.commission),
                str(trade.pnl),
                trade.filled_at,
                json.dumps(trade.metadata) if trade.metadata else None,
                trade.id
            ))
            
            return trade
    
    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM trades WHERE id = ?
            """, (trade_id,)).fetchone()
            
            if row:
                return self._row_to_trade(row)
            return None
    
    def get_recent_trades(self, symbol: str = None, limit: int = 100) -> List[Trade]:
        """Get recent trades, optionally filtered by symbol"""
        with self.get_connection() as conn:
            if symbol:
                rows = conn.execute("""
                    SELECT * FROM trades 
                    WHERE symbol = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (symbol, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM trades 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
            
            return [self._row_to_trade(row) for row in rows]
    
    def get_trades_by_status(self, status: TradeStatus) -> List[Trade]:
        """Get trades by status"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM trades 
                WHERE status = ? 
                ORDER BY created_at DESC
            """, (status.value,)).fetchall()
            
            return [self._row_to_trade(row) for row in rows]
    
    def get_daily_trades(self, date: datetime) -> List[Trade]:
        """Get all trades for a specific day"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM trades 
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC
            """, (start_of_day, end_of_day)).fetchall()
            
            return [self._row_to_trade(row) for row in rows]
    
    def get_pnl_summary(self, symbol: str = None, days: int = 30) -> Dict[str, Any]:
        """Get P&L summary for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.get_connection() as conn:
            if symbol:
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as trade_count,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        MIN(pnl) as min_pnl,
                        MAX(pnl) as max_pnl
                    FROM trades 
                    WHERE symbol = ? AND created_at >= ? AND status = 'FILLED'
                """, (symbol, cutoff_date)).fetchone()
            else:
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as trade_count,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        MIN(pnl) as min_pnl,
                        MAX(pnl) as max_pnl
                    FROM trades 
                    WHERE created_at >= ? AND status = 'FILLED'
                """, (cutoff_date,)).fetchone()
            
            return {
                "trade_count": row['trade_count'] or 0,
                "total_pnl": float(row['total_pnl'] or 0),
                "avg_pnl": float(row['avg_pnl'] or 0),
                "min_pnl": float(row['min_pnl'] or 0),
                "max_pnl": float(row['max_pnl'] or 0),
                "period_days": days
            }
    
    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """Convert database row to Trade object"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return Trade(
            id=row['id'],
            symbol=row['symbol'],
            action=TradeAction(row['action']),
            quantity=Decimal(str(row['quantity'])),
            price=Decimal(str(row['price'])) if row['price'] else None,
            order_type=row['order_type'],
            status=TradeStatus(row['status']),
            broker_order_id=row['broker_order_id'],
            commission=Decimal(str(row['commission'])),
            pnl=Decimal(str(row['pnl'])),
            created_at=datetime.fromisoformat(row['created_at']),
            filled_at=datetime.fromisoformat(row['filled_at']) if row['filled_at'] else None,
            metadata=metadata
        )


class AnalysisRepository(BaseRepository):
    """Repository for storing analysis results and insights"""
    
    def init_db(self) -> None:
        """Initialize analysis table"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    analysis_date DATE NOT NULL,
                    results TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_symbol ON analysis(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_date ON analysis(analysis_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_type ON analysis(analysis_type)")
    
    def save_analysis(self, symbol: str, analysis_type: str, analysis_date: datetime, 
                     results: Dict[str, Any], confidence: float = 0.0, 
                     metadata: Dict[str, Any] = None) -> int:
        """Save analysis results"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO analysis (symbol, analysis_type, analysis_date, results, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                analysis_type,
                analysis_date.date(),
                json.dumps(results),
                confidence,
                json.dumps(metadata) if metadata else None
            ))
            
            return cursor.lastrowid
    
    def get_latest_analysis(self, symbol: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Get latest analysis for symbol and type"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM analysis 
                WHERE symbol = ? AND analysis_type = ?
                ORDER BY analysis_date DESC, created_at DESC
                LIMIT 1
            """, (symbol, analysis_type)).fetchone()
            
            if row:
                return {
                    "id": row['id'],
                    "symbol": row['symbol'],
                    "analysis_type": row['analysis_type'],
                    "analysis_date": row['analysis_date'],
                    "results": json.loads(row['results']),
                    "confidence": row['confidence'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {},
                    "created_at": row['created_at']
                }
            return None
    
    def get_analysis_history(self, symbol: str, analysis_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get analysis history for the last N days"""
        cutoff_date = datetime.utcnow().date() - timedelta(days=days)
        
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM analysis 
                WHERE symbol = ? AND analysis_type = ? AND analysis_date >= ?
                ORDER BY analysis_date DESC, created_at DESC
            """, (symbol, analysis_type, cutoff_date)).fetchall()
            
            return [
                {
                    "id": row['id'],
                    "symbol": row['symbol'],
                    "analysis_type": row['analysis_type'],
                    "analysis_date": row['analysis_date'],
                    "results": json.loads(row['results']),
                    "confidence": row['confidence'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {},
                    "created_at": row['created_at']
                }
                for row in rows
            ]

