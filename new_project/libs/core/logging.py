"""
Structured logging configuration using structlog
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.typing import FilteringBoundLogger

from .config import get_settings


def setup_logging(service_name: str) -> None:
    """Setup structured logging for a service"""
    settings = get_settings()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Add service name to context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def log_trade_decision(
    logger: FilteringBoundLogger,
    symbol: str,
    action: str,
    quantity: float,
    price: float,
    reason: str,
    metadata: Dict[str, Any] = None,
) -> None:
    """Log a trading decision with structured data for reproducibility"""
    logger.info(
        "trade_decision",
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        reason=reason,
        metadata=metadata or {},
    )

