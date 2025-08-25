"""
Main entry point for Telegram Bot Gateway
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import setup_logging, get_logger
from apps.bot_gateway.bot import TelegramBot
from apps.bot_gateway.api import create_app

logger = get_logger(__name__)


async def main():
    """Main entry point"""
    # Setup logging
    setup_logging("bot_gateway")
    
    settings = get_settings()
    logger.info("Starting Bot Gateway", port=settings.bot_gateway_port)
    
    # Create Telegram bot
    telegram_bot = TelegramBot()
    
    # Create FastAPI app
    app = create_app(telegram_bot)
    
    # Start both Telegram bot and FastAPI server
    import uvicorn
    
    # Start Telegram bot in background
    bot_task = asyncio.create_task(telegram_bot.start())
    
    # Start FastAPI server
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=settings.bot_gateway_port,
        log_config=None  # Use our custom logging
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down Bot Gateway")
    finally:
        # Stop Telegram bot
        await telegram_bot.stop()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())

