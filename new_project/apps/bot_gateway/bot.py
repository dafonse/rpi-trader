"""
Telegram Bot implementation
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.security import verify_telegram_chat_id
from libs.core.logging import get_logger
from .handlers import (
    start_handler, help_handler, status_handler, health_handler,
    positions_handler, trades_handler, balance_handler,
    reboot_handler, stop_trading_handler, start_trading_handler,
    system_info_handler, logs_handler
)

logger = get_logger(__name__)


class TelegramBot:
    """Telegram Bot for RPI Trader control"""
    
    def __init__(self):
        self.settings = get_settings()
        self.application = None
        self.trading_enabled = True
        
    async def start(self) -> None:
        """Start the Telegram bot"""
        try:
            # Create application
            self.application = Application.builder().token(self.settings.telegram_bot_token).build()
            
            # Register handlers
            self._register_handlers()
            
            # Set bot commands
            await self._set_bot_commands()
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error("Failed to start Telegram bot", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the Telegram bot"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error("Error stopping Telegram bot", error=str(e))
    
    def _register_handlers(self) -> None:
        """Register command handlers"""
        handlers = [
            CommandHandler("start", self._auth_wrapper(start_handler)),
            CommandHandler("help", self._auth_wrapper(help_handler)),
            CommandHandler("status", self._auth_wrapper(status_handler)),
            CommandHandler("health", self._auth_wrapper(health_handler)),
            CommandHandler("positions", self._auth_wrapper(positions_handler)),
            CommandHandler("trades", self._auth_wrapper(trades_handler)),
            CommandHandler("balance", self._auth_wrapper(balance_handler)),
            CommandHandler("mt5_account", self._auth_wrapper(mt5_account_handler)),
            CommandHandler("mt5_positions", self._auth_wrapper(mt5_positions_handler)),
            CommandHandler("mt5_orders", self._auth_wrapper(mt5_orders_handler)),
            CommandHandler("system", self._auth_wrapper(system_info_handler)),
            CommandHandler("logs", self._auth_wrapper(logs_handler)),
            CommandHandler("reboot", self._auth_wrapper(reboot_handler)),
            CommandHandler("stop_trading", self._auth_wrapper(stop_trading_handler)),
            CommandHandler("start_trading", self._auth_wrapper(start_trading_handler)),
            
            # Message handler for unknown commands
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._auth_wrapper(self._unknown_message))
        ]
        
        for handler in handlers:
            self.application.add_handler(handler)
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    def _auth_wrapper(self, handler_func):
        """Wrapper to check authorization before executing handlers"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = str(update.effective_chat.id)
            
            if not verify_telegram_chat_id(chat_id):
                await update.message.reply_text(
                    "❌ Unauthorized access. Your chat ID is not allowed to use this bot."
                )
                logger.warning("Unauthorized access attempt", chat_id=chat_id)
                return
            
            try:
                await handler_func(update, context, self)
            except Exception as e:
                logger.error("Handler error", handler=handler_func.__name__, error=str(e))
                await update.message.reply_text(
                    f"❌ An error occurred: {str(e)}"
                )
        
        return wrapper
    
    async def _unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
        """Handle unknown messages"""
        await update.message.reply_text(
            "❓ Unknown command. Use /help to see available commands."
        )
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error("Telegram bot error", error=str(context.error))
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )
    
    async def _set_bot_commands(self) -> None:
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("status", "Show system status"),
            BotCommand("health", "Show health metrics"),
            BotCommand("positions", "Show current positions"),
            BotCommand("trades", "Show recent trades"),
            BotCommand("balance", "Show account balance"),
            BotCommand("mt5_account", "Show MT5 account details"),
            BotCommand("mt5_positions", "Show MT5 open positions"),
            BotCommand("mt5_orders", "Show MT5 pending orders"),
            BotCommand("system", "Show system information"),
            BotCommand("logs", "Show recent logs"),
            BotCommand("stop_trading", "Stop all trading"),
            BotCommand("start_trading", "Resume trading"),
            BotCommand("reboot", "Reboot system"),
        ]
        
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except TelegramError as e:
            logger.error("Failed to set bot commands", error=str(e))
    
    async def send_message(self, message: str, parse_mode: str = None) -> None:
        """Send message to authorized chat"""
        if not self.application:
            return
        
        try:
            chat_ids = [id.strip() for id in self.settings.allowed_chat_id.split(",")]
            for chat_id in chat_ids:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
        except TelegramError as e:
            logger.error("Failed to send message", error=str(e))
    
    async def send_alert(self, title: str, message: str) -> None:
        """Send alert message"""
        alert_text = f"🚨 *{title}*\n\n{message}"
        await self.send_message(alert_text, parse_mode="Markdown")
    
    def set_trading_enabled(self, enabled: bool) -> None:
        """Set trading enabled/disabled state"""
        self.trading_enabled = enabled
        logger.info("Trading state changed", enabled=enabled)
    
    def is_trading_enabled(self) -> bool:
        """Check if trading is enabled"""
        return self.trading_enabled

