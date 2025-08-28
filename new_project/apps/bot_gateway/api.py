"""
FastAPI application for Bot Gateway
"""

import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.security import verify_api_token
from libs.core.logging import get_logger

logger = get_logger(__name__)


class AlertRequest(BaseModel):
    title: str
    message: str


class MessageRequest(BaseModel):
    message: str
    parse_mode: str = None


def create_app(telegram_bot) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="RPI Trader Bot Gateway API",
        description="Internal API for Telegram Bot Gateway",
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
            "service": "bot_gateway",
            "telegram_bot_active": telegram_bot.application is not None,
            "trading_enabled": telegram_bot.is_trading_enabled()
        }
    
    @app.post("/alert")
    async def send_alert(
        request: AlertRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Send alert via Telegram"""
        try:
            await telegram_bot.send_alert(request.title, request.message)
            logger.info("Alert sent", title=request.title)
            return {"status": "sent"}
        except Exception as e:
            logger.error("Failed to send alert", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/message")
    async def send_message(
        request: MessageRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Send message via Telegram"""
        try:
            await telegram_bot.send_message(request.message, request.parse_mode)
            logger.info("Message sent")
            return {"status": "sent"}
        except Exception as e:
            logger.error("Failed to send message", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/trading/status")
    async def get_trading_status(_: bool = Depends(verify_api_token)):
        """Get trading status"""
        return {
            "trading_enabled": telegram_bot.is_trading_enabled()
        }
    
    @app.post("/trading/enable")
    async def enable_trading(_: bool = Depends(verify_api_token)):
        """Enable trading"""
        telegram_bot.set_trading_enabled(True)
        logger.info("Trading enabled via API")
        return {"status": "enabled"}
    
    @app.post("/trading/disable")
    async def disable_trading(_: bool = Depends(verify_api_token)):
        """Disable trading"""
        telegram_bot.set_trading_enabled(False)
        logger.info("Trading disabled via API")
        return {"status": "disabled"}
    
    return app

