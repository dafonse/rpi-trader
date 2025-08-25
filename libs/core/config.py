"""
Configuration management using Pydantic settings
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    allowed_chat_id: str = Field(..., env="ALLOWED_CHAT_ID")
    
    # MetaTrader Configuration
    mt5_server: Optional[str] = Field(None, env="MT5_SERVER")
    mt5_login: Optional[str] = Field(None, env="MT5_LOGIN")
    mt5_password: Optional[str] = Field(None, env="MT5_PASSWORD")
    mt5_api_url: str = Field("http://localhost:8080/api/v1", env="MT5_API_URL")
    
    # Database Configuration
    database_url: str = Field("sqlite:///./rpi_trader.db", env="DATABASE_URL")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    api_token: str = Field(..., env="API_TOKEN")
    
    # Trading Configuration
    max_daily_loss: float = Field(1000.0, env="MAX_DAILY_LOSS")
    max_order_size: float = Field(10000.0, env="MAX_ORDER_SIZE")
    dry_run_mode: bool = Field(True, env="DRY_RUN_MODE")
    
    # Service Ports
    bot_gateway_port: int = Field(8001, env="BOT_GATEWAY_PORT")
    scheduler_port: int = Field(8002, env="SCHEDULER_PORT")
    finance_worker_port: int = Field(8003, env="FINANCE_WORKER_PORT")
    market_worker_port: int = Field(8004, env="MARKET_WORKER_PORT")
    execution_worker_port: int = Field(8005, env="EXECUTION_WORKER_PORT")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

