"""
Finance Service Implementation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

import pandas as pd
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import get_logger
from libs.data.repository import TradeRepository, PositionRepository, MarketDataRepository
from libs.data.models import Trade, Position, TradeStatus, TradeAction

logger = get_logger(__name__)


class FinanceService:
    """Finance service for managing trading data and reporting"""
    
    def __init__(self):
        self.settings = get_settings()
        self.trade_repo = TradeRepository()
        self.position_repo = PositionRepository()
        self.market_data_repo = MarketDataRepository()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self) -> None:
        """Initialize the finance service"""
        try:
            logger.info("Initializing Finance Service")
            
            # Initialize database repositories
            self.trade_repo.init_db()
            self.position_repo.init_db()
            self.market_data_repo.init_db()
            
            logger.info("Finance Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Finance Service", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            await self.http_client.aclose()
            logger.info("Finance Service cleanup completed")
        except Exception as e:
            logger.error("Error during Finance Service cleanup", error=str(e))
    
    # Trade Management
    
    async def record_trade(self, trade: Trade) -> Trade:
        """Record a new trade"""
        try:
            recorded_trade = self.trade_repo.create(trade)
            logger.info("Trade recorded", trade_id=recorded_trade.id, symbol=trade.symbol, action=trade.action.value)
            return recorded_trade
        except Exception as e:
            logger.error("Failed to record trade", error=str(e))
            raise
    
    async def update_trade_status(self, trade_id: int, status: TradeStatus, filled_at: Optional[datetime] = None) -> None:
        """Update trade status"""
        try:
            self.trade_repo.update_status(trade_id, status.value, filled_at)
            logger.info("Trade status updated", trade_id=trade_id, status=status.value)
        except Exception as e:
            logger.error("Failed to update trade status", trade_id=trade_id, error=str(e))
            raise
    
    async def get_recent_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            trades = self.trade_repo.get_recent_trades(limit)
            return [self._trade_to_dict(trade) for trade in trades]
        except Exception as e:
            logger.error("Failed to get recent trades", error=str(e))
            raise
    
    async def get_trades_by_symbol(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get trades for a specific symbol"""
        try:
            trades = self.trade_repo.get_trades_by_symbol(symbol, days)
            return [self._trade_to_dict(trade) for trade in trades]
        except Exception as e:
            logger.error("Failed to get trades by symbol", symbol=symbol, error=str(e))
            raise
    
    async def get_daily_trades(self, date: datetime = None) -> List[Dict[str, Any]]:
        """Get trades for a specific day"""
        if date is None:
            date = datetime.utcnow().date()
        
        try:
            # Get all recent trades and filter by date
            trades = self.trade_repo.get_recent_trades(1000)  # Get more to ensure we have the day's trades
            daily_trades = [
                trade for trade in trades 
                if trade.created_at.date() == date
            ]
            return [self._trade_to_dict(trade) for trade in daily_trades]
        except Exception as e:
            logger.error("Failed to get daily trades", date=str(date), error=str(e))
            raise
    
    # Position Management
    
    async def update_position(self, position: Position) -> Position:
        """Update or create position"""
        try:
            updated_position = self.position_repo.upsert(position)
            logger.info("Position updated", symbol=position.symbol, quantity=position.quantity)
            return updated_position
        except Exception as e:
            logger.error("Failed to update position", symbol=position.symbol, error=str(e))
            raise
    
    async def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get all current positions"""
        try:
            positions = self.position_repo.get_all_positions()
            
            # Update current prices for positions
            updated_positions = []
            for position in positions:
                position_dict = self._position_to_dict(position)
                
                # Get current market price
                current_price = await self._get_current_price(position.symbol)
                if current_price:
                    position_dict['current_price'] = float(current_price)
                    
                    # Calculate unrealized P&L
                    price_diff = current_price - position.average_price
                    unrealized_pnl = price_diff * position.quantity
                    position_dict['unrealized_pnl'] = float(unrealized_pnl)
                
                updated_positions.append(position_dict)
            
            return updated_positions
        except Exception as e:
            logger.error("Failed to get current positions", error=str(e))
            raise
    
    # Account Information
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from broker"""
        try:
            # Try to get account info from execution worker
            response = await self.http_client.get(
                f"http://127.0.0.1:{self.settings.execution_worker_port}/account",
                headers={"Authorization": f"Bearer {self.settings.api_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Failed to get account info from execution worker")
                return {
                    "balance": 0.0,
                    "equity": 0.0,
                    "margin": 0.0,
                    "free_margin": 0.0,
                    "currency": "USD",
                    "leverage": 1
                }
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            return {
                "balance": 0.0,
                "equity": 0.0,
                "margin": 0.0,
                "free_margin": 0.0,
                "currency": "USD",
                "leverage": 1
            }
    
    # Statistics and Reporting
    
    async def get_daily_statistics(self, date: datetime = None) -> Dict[str, Any]:
        """Get daily trading statistics"""
        if date is None:
            date = datetime.utcnow().date()
        
        try:
            daily_trades = await self.get_daily_trades(date)
            
            if not daily_trades:
                return {
                    "date": str(date),
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0
                }
            
            # Calculate statistics
            total_trades = len(daily_trades)
            filled_trades = [t for t in daily_trades if t['status'] == 'FILLED' and t.get('pnl') is not None]
            
            if not filled_trades:
                return {
                    "date": str(date),
                    "total_trades": total_trades,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0
                }
            
            winning_trades = [t for t in filled_trades if float(t['pnl']) > 0]
            losing_trades = [t for t in filled_trades if float(t['pnl']) < 0]
            
            total_pnl = sum(float(t['pnl']) for t in filled_trades)
            win_rate = len(winning_trades) / len(filled_trades) if filled_trades else 0.0
            
            avg_win = sum(float(t['pnl']) for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
            avg_loss = sum(float(t['pnl']) for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
            
            return {
                "date": str(date),
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 3),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2)
            }
            
        except Exception as e:
            logger.error("Failed to get daily statistics", error=str(e))
            raise
    
    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for specified period"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # Get all trades in the period
            all_trades = self.trade_repo.get_recent_trades(1000)
            period_trades = [
                trade for trade in all_trades
                if start_date <= trade.created_at.date() <= end_date
            ]
            
            if not period_trades:
                return {
                    "period_days": days,
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": None
                }
            
            filled_trades = [t for t in period_trades if t.status == TradeStatus.FILLED and t.pnl is not None]
            
            if not filled_trades:
                return {
                    "period_days": days,
                    "total_trades": len(period_trades),
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": None
                }
            
            # Calculate metrics
            total_pnl = sum(float(t.pnl) for t in filled_trades)
            winning_trades = [t for t in filled_trades if float(t.pnl) > 0]
            win_rate = len(winning_trades) / len(filled_trades)
            
            # Calculate drawdown (simplified)
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            
            for trade in sorted(filled_trades, key=lambda x: x.created_at):
                cumulative_pnl += float(trade.pnl)
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = peak - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return {
                "period_days": days,
                "total_trades": len(period_trades),
                "filled_trades": len(filled_trades),
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 3),
                "max_drawdown": round(max_drawdown, 2),
                "avg_trade_pnl": round(total_pnl / len(filled_trades), 2) if filled_trades else 0.0
            }
            
        except Exception as e:
            logger.error("Failed to get performance summary", error=str(e))
            raise
    
    # Data Cleanup
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # This is a simplified cleanup - in a full implementation,
            # you'd implement proper database cleanup methods
            logger.info("Data cleanup requested", days_to_keep=days_to_keep, cutoff_date=cutoff_date)
            
            return {
                "trades_cleaned": 0,
                "market_data_cleaned": 0,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
            raise
    
    # Helper Methods
    
    def _trade_to_dict(self, trade: Trade) -> Dict[str, Any]:
        """Convert Trade model to dictionary"""
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "action": trade.action.value,
            "quantity": str(trade.quantity),
            "price": str(trade.price) if trade.price else None,
            "order_type": trade.order_type.value,
            "status": trade.status.value,
            "created_at": trade.created_at.isoformat(),
            "filled_at": trade.filled_at.isoformat() if trade.filled_at else None,
            "broker_order_id": trade.broker_order_id,
            "commission": str(trade.commission) if trade.commission else None,
            "pnl": str(trade.pnl) if trade.pnl else None,
            "metadata": trade.metadata
        }
    
    def _position_to_dict(self, position: Position) -> Dict[str, Any]:
        """Convert Position model to dictionary"""
        return {
            "id": position.id,
            "symbol": position.symbol,
            "quantity": str(position.quantity),
            "average_price": str(position.average_price),
            "current_price": str(position.current_price) if position.current_price else None,
            "unrealized_pnl": str(position.unrealized_pnl) if position.unrealized_pnl else None,
            "realized_pnl": str(position.realized_pnl),
            "created_at": position.created_at.isoformat(),
            "updated_at": position.updated_at.isoformat()
        }
    
    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol"""
        try:
            # Try to get current price from market worker
            response = await self.http_client.get(
                f"http://127.0.0.1:{self.settings.market_worker_port}/market-data/{symbol}",
                headers={"Authorization": f"Bearer {self.settings.api_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Use mid price (average of bid and ask)
                bid = Decimal(str(data.get('bid', 0)))
                ask = Decimal(str(data.get('ask', 0)))
                return (bid + ask) / 2 if bid and ask else None
            
            # Fallback to database
            market_data = self.market_data_repo.get_latest_price(symbol)
            if market_data:
                return (market_data.bid + market_data.ask) / 2
            
            return None
            
        except Exception as e:
            logger.error("Failed to get current price", symbol=symbol, error=str(e))
            return None

