"""
FastAPI application for Market Worker Service
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.security import verify_api_token
from libs.core.logging import get_logger

logger = get_logger(__name__)


class SymbolRequest(BaseModel):
    symbol: str


def create_app(market_service) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="RPI Trader Market Worker API",
        description="Internal API for Market Worker Service",
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
            "service": "market_worker",
            "data_collection_active": market_service.collecting_data,
            "monitored_symbols": len(market_service.get_monitored_symbols())
        }
    
    # Market Data Endpoints
    
    @app.get("/market-data/{symbol}")
    async def get_market_data(
        symbol: str,
        _: bool = Depends(verify_api_token)
    ):
        """Get current market data for a symbol"""
        try:
            market_data = await market_service.get_current_market_data(symbol.upper())
            
            if not market_data:
                raise HTTPException(status_code=404, detail=f"No market data found for {symbol}")
            
            return market_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/market-data")
    async def get_all_market_data(_: bool = Depends(verify_api_token)):
        """Get current market data for all monitored symbols"""
        try:
            symbols = market_service.get_monitored_symbols()
            market_data = {}
            
            for symbol in symbols:
                data = await market_service.get_current_market_data(symbol)
                if data:
                    market_data[symbol] = data
            
            return market_data
            
        except Exception as e:
            logger.error("Failed to get all market data", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Signal Endpoints
    
    @app.get("/signals/{symbol}")
    async def get_signals_for_symbol(
        symbol: str,
        limit: int = Query(50, le=200),
        _: bool = Depends(verify_api_token)
    ):
        """Get recent signals for a specific symbol"""
        try:
            signals = await market_service.get_recent_signals(symbol.upper(), limit)
            return signals
        except Exception as e:
            logger.error("Failed to get signals for symbol", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/signals/recent")
    async def get_recent_signals(
        limit: int = Query(50, le=200),
        _: bool = Depends(verify_api_token)
    ):
        """Get recent signals for all symbols"""
        try:
            signals = await market_service.get_recent_signals(None, limit)
            return signals
        except Exception as e:
            logger.error("Failed to get recent signals", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/signal-stats")
    async def get_signal_stats(
        symbol: str = Query(...),
        hours: int = Query(24, le=168),  # Max 1 week
        _: bool = Depends(verify_api_token)
    ):
        """Get signal statistics for a symbol"""
        try:
            stats = await market_service.get_signal_statistics(symbol.upper(), hours)
            return stats
        except Exception as e:
            logger.error("Failed to get signal stats", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Price History Endpoints
    
    @app.get("/price-history/{symbol}")
    async def get_price_history(
        symbol: str,
        limit: int = Query(100, le=1000),
        _: bool = Depends(verify_api_token)
    ):
        """Get price history for a symbol"""
        try:
            history = await market_service.get_price_history(symbol.upper(), limit)
            return history
        except Exception as e:
            logger.error("Failed to get price history", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Symbol Management Endpoints
    
    @app.get("/symbols")
    async def get_monitored_symbols(_: bool = Depends(verify_api_token)):
        """Get list of monitored symbols"""
        try:
            symbols = market_service.get_monitored_symbols()
            return {"symbols": symbols}
        except Exception as e:
            logger.error("Failed to get monitored symbols", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/symbols")
    async def add_symbol(
        symbol_request: SymbolRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Add a symbol to monitoring"""
        try:
            market_service.add_symbol(symbol_request.symbol.upper())
            return {"status": "success", "message": f"Symbol {symbol_request.symbol} added to monitoring"}
        except Exception as e:
            logger.error("Failed to add symbol", symbol=symbol_request.symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/symbols/{symbol}")
    async def remove_symbol(
        symbol: str,
        _: bool = Depends(verify_api_token)
    ):
        """Remove a symbol from monitoring"""
        try:
            market_service.remove_symbol(symbol.upper())
            return {"status": "success", "message": f"Symbol {symbol} removed from monitoring"}
        except Exception as e:
            logger.error("Failed to remove symbol", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Service Control Endpoints
    
    @app.post("/data-collection/start")
    async def start_data_collection(_: bool = Depends(verify_api_token)):
        """Start data collection"""
        try:
            if not market_service.collecting_data:
                await market_service.start_data_collection()
                return {"status": "success", "message": "Data collection started"}
            else:
                return {"status": "info", "message": "Data collection already running"}
        except Exception as e:
            logger.error("Failed to start data collection", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/data-collection/stop")
    async def stop_data_collection(_: bool = Depends(verify_api_token)):
        """Stop data collection"""
        try:
            market_service.collecting_data = False
            return {"status": "success", "message": "Data collection stopped"}
        except Exception as e:
            logger.error("Failed to stop data collection", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/status")
    async def get_service_status(_: bool = Depends(verify_api_token)):
        """Get service status"""
        try:
            symbols = market_service.get_monitored_symbols()
            
            # Get recent signal count
            recent_signals = await market_service.get_recent_signals(None, 10)
            
            return {
                "service": "market_worker",
                "status": "running",
                "data_collection_active": market_service.collecting_data,
                "monitored_symbols": len(symbols),
                "symbols": symbols,
                "recent_signals_count": len(recent_signals),
                "last_signal_time": recent_signals[0]["timestamp"] if recent_signals else None
            }
        except Exception as e:
            logger.error("Failed to get service status", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

