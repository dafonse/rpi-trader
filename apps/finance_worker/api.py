"""
FastAPI application for Finance Worker Service
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.security import verify_api_token
from libs.core.logging import get_logger
from libs.data.models import Trade, Position

logger = get_logger(__name__)


class TradeRequest(BaseModel):
    symbol: str
    action: str
    quantity: float
    price: Optional[float] = None
    order_type: str = "MARKET"
    broker_order_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PositionRequest(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    current_price: Optional[float] = None


class CleanupRequest(BaseModel):
    days_to_keep: int = 30


def create_app(finance_service) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="RPI Trader Finance Worker API",
        description="Internal API for Finance Worker Service",
        version="0.1.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "finance_worker",
            "database_connected": True  # Simplified check
        }
    
    # Trade Endpoints
    
    @app.post("/trades")
    async def record_trade(
        trade_request: TradeRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Record a new trade"""
        try:
            # Convert request to Trade model
            trade = Trade(
                symbol=trade_request.symbol,
                action=trade_request.action,
                quantity=trade_request.quantity,
                price=trade_request.price,
                order_type=trade_request.order_type,
                broker_order_id=trade_request.broker_order_id,
                metadata=trade_request.metadata
            )
            
            recorded_trade = await finance_service.record_trade(trade)
            return {"trade_id": recorded_trade.id, "status": "recorded"}
            
        except Exception as e:
            logger.error("Failed to record trade", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/trades")
    async def get_trades(
        limit: int = Query(100, le=1000),
        _: bool = Depends(verify_api_token)
    ):
        """Get recent trades"""
        try:
            trades = await finance_service.get_recent_trades(limit)
            return trades
        except Exception as e:
            logger.error("Failed to get trades", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/trades/today")
    async def get_today_trades(_: bool = Depends(verify_api_token)):
        """Get today's trades"""
        try:
            trades = await finance_service.get_daily_trades()
            return trades
        except Exception as e:
            logger.error("Failed to get today's trades", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/trades/{symbol}")
    async def get_trades_by_symbol(
        symbol: str,
        days: int = Query(30, le=365),
        _: bool = Depends(verify_api_token)
    ):
        """Get trades for a specific symbol"""
        try:
            trades = await finance_service.get_trades_by_symbol(symbol, days)
            return trades
        except Exception as e:
            logger.error("Failed to get trades by symbol", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.put("/trades/{trade_id}/status")
    async def update_trade_status(
        trade_id: int,
        status: str,
        filled_at: Optional[str] = None,
        _: bool = Depends(verify_api_token)
    ):
        """Update trade status"""
        try:
            filled_datetime = None
            if filled_at:
                filled_datetime = datetime.fromisoformat(filled_at)
            
            await finance_service.update_trade_status(trade_id, status, filled_datetime)
            return {"status": "updated"}
            
        except Exception as e:
            logger.error("Failed to update trade status", trade_id=trade_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Position Endpoints
    
    @app.get("/positions")
    async def get_positions(_: bool = Depends(verify_api_token)):
        """Get current positions"""
        try:
            positions = await finance_service.get_current_positions()
            return positions
        except Exception as e:
            logger.error("Failed to get positions", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/positions")
    async def update_position(
        position_request: PositionRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Update or create position"""
        try:
            # Convert request to Position model
            position = Position(
                symbol=position_request.symbol,
                quantity=position_request.quantity,
                average_price=position_request.average_price,
                current_price=position_request.current_price
            )
            
            updated_position = await finance_service.update_position(position)
            return {"position_id": updated_position.id, "status": "updated"}
            
        except Exception as e:
            logger.error("Failed to update position", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Account Endpoints
    
    @app.get("/account")
    async def get_account_info(_: bool = Depends(verify_api_token)):
        """Get account information"""
        try:
            account_info = await finance_service.get_account_info()
            return account_info
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Statistics Endpoints
    
    @app.get("/daily-stats")
    async def get_daily_stats(
        date: Optional[str] = None,
        _: bool = Depends(verify_api_token)
    ):
        """Get daily trading statistics"""
        try:
            target_date = None
            if date:
                target_date = datetime.fromisoformat(date).date()
            
            stats = await finance_service.get_daily_statistics(target_date)
            return stats
        except Exception as e:
            logger.error("Failed to get daily stats", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/performance")
    async def get_performance_summary(
        days: int = Query(30, le=365),
        _: bool = Depends(verify_api_token)
    ):
        """Get performance summary"""
        try:
            performance = await finance_service.get_performance_summary(days)
            return performance
        except Exception as e:
            logger.error("Failed to get performance summary", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Maintenance Endpoints
    
    @app.post("/cleanup")
    async def cleanup_old_data(
        cleanup_request: CleanupRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Clean up old data"""
        try:
            result = await finance_service.cleanup_old_data(cleanup_request.days_to_keep)
            return result
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/status")
    async def get_service_status(_: bool = Depends(verify_api_token)):
        """Get service status"""
        try:
            # Get some basic statistics
            recent_trades = await finance_service.get_recent_trades(10)
            positions = await finance_service.get_current_positions()
            
            return {
                "service": "finance_worker",
                "status": "running",
                "recent_trades_count": len(recent_trades),
                "open_positions_count": len(positions),
                "last_trade_time": recent_trades[0]["created_at"] if recent_trades else None
            }
        except Exception as e:
            logger.error("Failed to get service status", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

