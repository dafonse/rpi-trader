"""
Security utilities for API authentication and authorization
"""

import secrets
import hashlib
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings

security = HTTPBearer()


def generate_api_token() -> str:
    """Generate a secure API token"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_api_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify API token from request headers"""
    settings = get_settings()
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if credentials.credentials != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")
    
    return True


def verify_telegram_chat_id(chat_id: str) -> bool:
    """Verify if chat ID is allowed to use the bot"""
    settings = get_settings()
    allowed_ids = [id.strip() for id in settings.allowed_chat_id.split(",")]
    return str(chat_id) in allowed_ids


class TradingSafeguards:
    """Trading safety checks and limits"""
    
    def __init__(self):
        self.settings = get_settings()
        self.daily_loss = 0.0
        self.emergency_stop = False
    
    def check_order_size(self, size: float) -> bool:
        """Check if order size is within limits"""
        return size <= self.settings.max_order_size
    
    def check_daily_loss(self, potential_loss: float) -> bool:
        """Check if potential loss would exceed daily limit"""
        return (self.daily_loss + potential_loss) <= self.settings.max_daily_loss
    
    def add_loss(self, loss: float) -> None:
        """Add to daily loss tracking"""
        self.daily_loss += loss
    
    def reset_daily_loss(self) -> None:
        """Reset daily loss counter (called at start of new trading day)"""
        self.daily_loss = 0.0
    
    def trigger_emergency_stop(self) -> None:
        """Trigger emergency stop for all trading"""
        self.emergency_stop = True
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed"""
        if self.settings.dry_run_mode:
            return True  # Always allow in dry run mode
        
        return not self.emergency_stop and self.daily_loss < self.settings.max_daily_loss

