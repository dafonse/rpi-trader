"""
FastAPI application for Execution Worker Service
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.security import verify_api_token
from libs.core.logging import get_logger

logger = get_logger(__name__)


class SignalRequest(BaseModel):
    symbol: str
    action: str
    strength: float
    signal_type: str
    metadata: Dict[str, Any] = {}


class OrderRequest(BaseModel):
    symbol: str
    action: str
    quantity: float
    order_type: str = "MARKET"
    price: Optional[float] = None


def create_app(execution_service) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="RPI Trader Execution Worker API",
        description="Internal API for Execution Worker Service",
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
        status = execution_service.get_trading_status()
        return {
            "status": "healthy",
            "service": "execution_worker",
            "trading_enabled": status["trading_enabled"],
            "emergency_stop": status["emergency_stop"],
            "dry_run_mode": status["dry_run_mode"]
        }
    
    # Signal Processing Endpoints
    
    @app.post("/signals")
    async def process_signal(
        signal_request: SignalRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Process a trading signal"""
        try:
            signal_data = {
                "symbol": signal_request.symbol,
                "action": signal_request.action,
                "strength": signal_request.strength,
                "signal_type": signal_request.signal_type,
                "metadata": signal_request.metadata
            }
            
            result = await execution_service.process_signal(signal_data)
            return result
            
        except Exception as e:
            logger.error("Failed to process signal", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Order Management Endpoints
    
    @app.post("/orders")
    async def place_order(
        order_request: OrderRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Place a manual trading order"""
        try:
            # This would be used for manual order placement
            # For now, return a placeholder response
            logger.info("Manual order placement requested", 
                       symbol=order_request.symbol,
                       action=order_request.action,
                       quantity=order_request.quantity)
            
            return {
                "status": "received",
                "message": "Manual order placement not yet implemented"
            }
            
        except Exception as e:
            logger.error("Failed to place order", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Account Information Endpoints
    
    @app.get("/account")
    async def get_account_info(_: bool = Depends(verify_api_token)):
        """Get account information"""
        try:
            account_info = await execution_service._get_account_info()
            
            if not account_info:
                raise HTTPException(status_code=503, detail="Account information unavailable")
            
            return account_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/market-data/{symbol}")
    async def get_market_data(
        symbol: str,
        _: bool = Depends(verify_api_token)
    ):
        """Get current market data for a symbol"""
        try:
            market_data = await execution_service._get_market_data(symbol.upper())
            
            if not market_data:
                raise HTTPException(status_code=404, detail=f"No market data found for {symbol}")
            
            return {
                "symbol": symbol.upper(),
                "bid": market_data["bid"],
                "ask": market_data["ask"],
                "timestamp": "2024-01-01T00:00:00Z"  # Placeholder timestamp
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Trading Control Endpoints
    
    @app.post("/trading/enable")
    async def enable_trading(_: bool = Depends(verify_api_token)):
        """Enable trading"""
        try:
            result = await execution_service.enable_trading()
            
            if result["status"] == "success":
                return result
            else:
                raise HTTPException(status_code=400, detail=result["reason"])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to enable trading", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/trading/disable")
    async def disable_trading(_: bool = Depends(verify_api_token)):
        """Disable trading"""
        try:
            result = await execution_service.disable_trading()
            return result
        except Exception as e:
            logger.error("Failed to disable trading", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/emergency_stop")
    async def emergency_stop(_: bool = Depends(verify_api_token)):
        """Emergency stop - disable all trading immediately"""
        try:
            result = await execution_service.emergency_stop_trading()
            return result
        except Exception as e:
            logger.error("Failed to activate emergency stop", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/clear_emergency_stop")
    async def clear_emergency_stop(_: bool = Depends(verify_api_token)):
        """Clear emergency stop"""
        try:
            result = await execution_service.clear_emergency_stop()
            return result
        except Exception as e:
            logger.error("Failed to clear emergency stop", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/reset_daily_limits")
    async def reset_daily_limits(_: bool = Depends(verify_api_token)):
        """Reset daily trading limits"""
        try:
            result = await execution_service.reset_daily_limits()
            return result
        except Exception as e:
            logger.error("Failed to reset daily limits", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/trading/status")
    async def get_trading_status(_: bool = Depends(verify_api_token)):
        """Get current trading status"""
        try:
            status = execution_service.get_trading_status()
            return status
        except Exception as e:
            logger.error("Failed to get trading status", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Service Status Endpoints
    
    @app.get("/status")
    async def get_service_status(_: bool = Depends(verify_api_token)):
        """Get service status"""
        try:
            trading_status = execution_service.get_trading_status()
            
            return {
                "service": "execution_worker",
                "status": "running",
                "trading_enabled": trading_status["trading_enabled"],
                "emergency_stop": trading_status["emergency_stop"],
                "dry_run_mode": trading_status["dry_run_mode"],
                "daily_trades": trading_status["daily_trades_count"],
                "daily_pnl": trading_status["daily_pnl"]
            }
        except Exception as e:
            logger.error("Failed to get service status", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

