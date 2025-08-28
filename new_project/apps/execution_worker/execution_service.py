"""
Execution Service Implementation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import get_logger
from libs.data.models import Trade, TradeAction, TradeStatus, OrderType, SignalData
from libs.broker.bvm_mt5_client import BVMMT5Client

logger = get_logger(__name__)


class ExecutionService:
    """Execution service for order management and trade execution"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize MT5 client based on BVM settings
        if self.settings.bvm_mt5_enabled:
            self.mt5_client = BVMMT5Client(
                vm_ip=self.settings.bvm_vm_ip,
                vm_port=self.settings.bvm_vm_port
            )
        else:
            # Fallback or placeholder if BVM MT5 is not enabled
            self.mt5_client = None # Or a mock client for testing
            logger.warning("BVM MT5 is not enabled. Execution service will operate in dry-run mode or require a direct MT5 connection.")

        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Trading state
        self.trading_enabled = not self.settings.dry_run_mode
        self.emergency_stop = False
        
        # Risk management
        self.daily_pnl = Decimal("0.0")
        self.daily_loss_limit = Decimal(str(self.settings.max_daily_loss))
        self.max_order_size = Decimal(str(self.settings.max_order_size))
        
        # Order tracking
        self.pending_orders = {}
        self.daily_trades_count = 0
        
        # Last reset date for daily limits
        self.last_reset_date = datetime.utcnow().date()
        
    async def initialize(self) -> None:
        """Initialize the execution service"""
        try:
            logger.info("Initializing Execution Service")
            
            # Initialize MT5 client
            if not self.settings.dry_run_mode and self.settings.bvm_mt5_enabled and self.mt5_client:
                # Connect to the BVM MT5 bridge service
                connected = await self.mt5_client.connect(
                    login=self.settings.mt5_login,
                    password=self.settings.mt5_password,
                    server=self.settings.mt5_server
                )
                if connected:
                    logger.info("BVM MT5 client initialized and connected")
                else:
                    logger.error("Failed to connect to BVM MT5 client. Trading will be disabled.")
                    self.trading_enabled = False
            elif not self.settings.dry_run_mode and not self.settings.bvm_mt5_enabled:
                logger.warning("Trading is enabled but BVM MT5 is not. Please ensure a direct MT5 connection is configured or enable BVM MT5.")
                self.trading_enabled = False # Disable trading if no MT5 connection is expected
            else:
                logger.info("Running in dry-run mode, BVM MT5 client not initialized")
            
            # Reset daily limits if new day
            await self._check_and_reset_daily_limits()
            
            logger.info("Execution Service initialized successfully", 
                       trading_enabled=self.trading_enabled,
                       dry_run_mode=self.settings.dry_run_mode)
            
        except Exception as e:
            logger.error("Failed to initialize Execution Service", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if not self.settings.dry_run_mode and self.mt5_client and self.mt5_client.is_connected():
                # No explicit disconnect for BVMMT5Client, just close session
                await self.mt5_client.__aexit__(None, None, None)
            
            await self.http_client.aclose()
            logger.info("Execution Service cleanup completed")
        except Exception as e:
            logger.error("Error during Execution Service cleanup", error=str(e))
    
    async def _check_and_reset_daily_limits(self) -> None:
        """Check and reset daily limits if new day"""
        current_date = datetime.utcnow().date()
        
        if current_date > self.last_reset_date:
            logger.info("Resetting daily limits for new trading day", date=current_date)
            self.daily_pnl = Decimal("0.0")
            self.daily_trades_count = 0
            self.last_reset_date = current_date
            
            # Re-enable trading if it was disabled due to daily limits
            if not self.emergency_stop:
                self.trading_enabled = not self.settings.dry_run_mode
    
    # Signal Processing
    
    async def process_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a trading signal"""
        try:
            logger.info("Processing trading signal", 
                       symbol=signal_data["symbol"], 
                       action=signal_data["action"],
                       strength=signal_data["strength"])
            
            # Check if trading is enabled
            if not self.trading_enabled or self.emergency_stop:
                return {
                    "status": "rejected",
                    "reason": "Trading disabled or emergency stop active"
                }
            
            # Check daily limits
            if not await self._check_daily_limits():
                return {
                    "status": "rejected",
                    "reason": "Daily limits exceeded"
                }
            
            # Validate signal strength
            if abs(signal_data["strength"]) < 0.7:
                return {
                    "status": "rejected",
                    "reason": "Signal strength too weak"
                }
            
            # Calculate position size
            position_size = await self._calculate_position_size(
                signal_data["symbol"], 
                signal_data["strength"]
            )
            
            if position_size <= 0:
                return {
                    "status": "rejected",
                    "reason": "Position size calculation failed"
                }
            
            # Create and execute order
            order_result = await self._execute_order(
                symbol=signal_data["symbol"],
                action=TradeAction(signal_data["action"]),
                quantity=position_size,
                order_type=OrderType.MARKET,
                metadata={
                    "signal_type": signal_data.get("signal_type"),
                    "signal_strength": signal_data["strength"],
                    "source": "market_worker"
                }
            )
            
            return order_result
            
        except Exception as e:
            logger.error("Failed to process signal", error=str(e))
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def _check_daily_limits(self) -> bool:
        """Check if daily limits allow trading"""
        await self._check_and_reset_daily_limits()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.daily_loss_limit:
            logger.warning("Daily loss limit exceeded", 
                          daily_pnl=float(self.daily_pnl),
                          limit=float(self.daily_loss_limit))
            self.trading_enabled = False
            await self._send_alert("Daily Loss Limit Exceeded", 
                                 f"Trading disabled. Daily P&L: ${self.daily_pnl}")
            return False
        
        return True
    
    async def _calculate_position_size(self, symbol: str, signal_strength: float) -> Decimal:
        """Calculate position size based on risk management rules"""
        try:
            # Get account information
            account_info = await self._get_account_info()
            if not account_info:
                return Decimal("0.0")
            
            # Base position size (e.g., 1% of account balance)
            account_balance = Decimal(str(account_info.get("balance", 0)))
            base_size = account_balance * Decimal("0.01")  # 1% risk
            
            # Adjust based on signal strength
            strength_multiplier = Decimal(str(abs(signal_strength)))
            position_size = base_size * strength_multiplier
            
            # Apply maximum order size limit
            if position_size > self.max_order_size:
                position_size = self.max_order_size
            
            # Convert to lot size for forex (simplified)
            if symbol.endswith("USD") or symbol.startswith("USD"):
                # For forex, convert to lots (100,000 units = 1 lot)
                lot_size = position_size / Decimal("100000")
                # Round to 2 decimal places (0.01 lot minimum)
                lot_size = lot_size.quantize(Decimal("0.01"))
                return lot_size
            
            return position_size
            
        except Exception as e:
            logger.error("Failed to calculate position size", symbol=symbol, error=str(e))
            return Decimal("0.0")
    
    # Order Execution
    
    async def _execute_order(self, symbol: str, action: TradeAction, quantity: Decimal, 
                           order_type: OrderType, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a trading order"""
        try:
            logger.info("Executing order", 
                       symbol=symbol, 
                       action=action.value, 
                       quantity=float(quantity),
                       order_type=order_type.value)
            
            # Create trade record
            trade = Trade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type=order_type,
                status=TradeStatus.PENDING,
                metadata=metadata or {}
            )
            
            if self.settings.dry_run_mode or not self.settings.bvm_mt5_enabled or not self.mt5_client or not self.mt5_client.is_connected():
                # Simulate order execution if dry run, BVM MT5 not enabled, or not connected
                result = await self._simulate_order_execution(trade)
            else:
                # Execute real order via MT5
                result = await self._execute_real_order(trade)
            
            # Record trade in finance worker
            await self._record_trade(trade)
            
            # Update daily statistics
            self.daily_trades_count += 1
            
            return result
            
        except Exception as e:
            logger.error("Failed to execute order", error=str(e))
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def _simulate_order_execution(self, trade: Trade) -> Dict[str, Any]:
        """Simulate order execution for dry-run mode"""
        try:
            # Get current market price
            market_data = await self._get_market_data(trade.symbol)
            
            if not market_data:
                return {
                    "status": "failed",
                    "reason": "No market data available"
                }
            
            # Use bid/ask based on trade direction
            if trade.action == TradeAction.BUY:
                execution_price = Decimal(str(market_data["ask"]))
            else:
                execution_price = Decimal(str(market_data["bid"]))
            
            # Update trade record
            trade.price = execution_price
            trade.status = TradeStatus.FILLED
            trade.filled_at = datetime.utcnow()
            trade.broker_order_id = f"SIM_{datetime.utcnow().timestamp()}"
            
            # Simulate commission (0.1 pip)
            pip_value = Decimal("0.0001") if "JPY" not in trade.symbol else Decimal("0.01")
            trade.commission = pip_value * trade.quantity
            
            logger.info("Order simulated successfully", 
                       trade_id=trade.id,
                       price=float(execution_price))
            
            return {
                "status": "filled",
                "trade_id": trade.id,
                "execution_price": float(execution_price),
                "broker_order_id": trade.broker_order_id
            }
            
        except Exception as e:
            logger.error("Failed to simulate order", error=str(e))
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def _execute_real_order(self, trade: Trade) -> Dict[str, Any]:
        """Execute real order via MT5"""
        try:
            if not self.mt5_client or not self.mt5_client.is_connected():
                raise Exception("MT5 client not connected or not initialized")

            # Map TradeAction to MT5 order type string
            mt5_order_type = "BUY" if trade.action == TradeAction.BUY else "SELL"

            # Execute order through BVM MT5 client
            result = await self.mt5_client.place_order(
                symbol=trade.symbol,
                order_type=mt5_order_type,
                volume=float(trade.quantity),
                # price=trade.price, # Price is usually not needed for market orders
                # sl=trade.stop_loss, # Add SL/TP if available in Trade model
                # tp=trade.take_profit
            )
            
            if result and result.get("retcode") == 10009: # 10009 is TRADE_RETCODE_DONE
                trade.price = Decimal(str(result.get("price")))
                trade.status = TradeStatus.FILLED
                trade.filled_at = datetime.utcnow()
                trade.broker_order_id = str(result.get("order"))
                trade.commission = Decimal(str(result.get("commission", 0)))
                
                logger.info("Order executed successfully", 
                           trade_id=trade.id,
                           broker_order_id=trade.broker_order_id)
                
                return {
                    "status": "filled",
                    "trade_id": trade.id,
                    "execution_price": float(trade.price),
                    "broker_order_id": trade.broker_order_id
                }
            else:
                trade.status = TradeStatus.REJECTED
                error_msg = result.get("comment", "Unknown broker error") if result else "No result from broker"
                logger.error("Order rejected by broker", reason=error_msg)
                
                return {
                    "status": "rejected",
                    "reason": error_msg
                }
                
        except Exception as e:
            logger.error("Failed to execute real order", error=str(e))
            trade.status = TradeStatus.FAILED
            return {
                "status": "error",
                "reason": str(e)
            }
    
    # Account and Market Data
    
    async def _get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            if self.settings.dry_run_mode or not self.settings.bvm_mt5_enabled or not self.mt5_client or not self.mt5_client.is_connected():
                # Return simulated account info
                return {
                    "balance": 10000.0,
                    "equity": 10000.0,
                    "margin": 0.0,
                    "free_margin": 10000.0,
                    "currency": "USD",
                    "leverage": 100
                }
            else:
                # Get real account info from MT5
                return await self.mt5_client.get_account_info()
                
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            return None
    
    async def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market data"""
        try:
            if self.settings.dry_run_mode or not self.settings.bvm_mt5_enabled or not self.mt5_client or not self.mt5_client.is_connected():
                # Return simulated market data
                base_prices = {
                    "EURUSD": {"bid": 1.0850, "ask": 1.0852},
                    "GBPUSD": {"bid": 1.2650, "ask": 1.2652},
                    "USDJPY": {"bid": 149.50, "ask": 149.52},
                    "AUDUSD": {"bid": 0.6750, "ask": 0.6752},
                    "USDCAD": {"bid": 1.3450, "ask": 1.3452}
                }
                
                if symbol in base_prices:
                    return base_prices[symbol]
                else:
                    return {"bid": 1.0000, "ask": 1.0002}
            else:
                # Get real market data from MT5
                return await self.mt5_client.get_current_price(symbol)
                
        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            return None
    
    # Trade Recording
    
    async def _record_trade(self, trade: Trade) -> None:
        """Record trade in finance worker"""
        try:
            trade_data = {
                "symbol": trade.symbol,
                "action": trade.action.value,
                "quantity": float(trade.quantity),
                "price": float(trade.price) if trade.price else None,
                "order_type": trade.order_type.value,
                "broker_order_id": trade.broker_order_id,
                "metadata": trade.metadata
            }
            
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.finance_worker_port}/trades",
                headers={
                    "Authorization": f"Bearer {self.settings.api_token}"
                },
                json=trade_data
            )
            
            if response.status_code == 200:
                logger.info("Trade recorded in finance worker", trade_id=trade.id)
            else:
                logger.warning("Failed to record trade in finance worker", 
                             status_code=response.status_code)
                
        except Exception as e:
            logger.error("Failed to record trade", error=str(e))
    
    # Control Methods
    
    async def enable_trading(self) -> Dict[str, Any]:
        """Enable trading"""
        try:
            if self.emergency_stop:
                return {"status": "failed", "reason": "Emergency stop is active"}
            
            self.trading_enabled = True
            logger.info("Trading enabled")
            return {"status": "success", "message": "Trading enabled"}
        except Exception as e:
            logger.error("Failed to enable trading", error=str(e))
            return {"status": "error", "reason": str(e)}

    async def disable_trading(self) -> Dict[str, Any]:
        """Disable trading"""
        try:
            self.trading_enabled = False
            logger.info("Trading disabled")
            return {"status": "success", "message": "Trading disabled"}
        except Exception as e:
            logger.error("Failed to disable trading", error=str(e))
            return {"status": "error", "reason": str(e)}

    async def activate_emergency_stop(self) -> Dict[str, Any]:
        """Activate emergency stop"""
        try:
            self.emergency_stop = True
            self.trading_enabled = False
            logger.warning("Emergency stop activated! All trading disabled.")
            await self._send_alert("EMERGENCY STOP", "All trading has been disabled due to emergency stop activation.")
            return {"status": "success", "message": "Emergency stop activated"}
        except Exception as e:
            logger.error("Failed to activate emergency stop", error=str(e))
            return {"status": "error", "reason": str(e)}

    async def deactivate_emergency_stop(self) -> Dict[str, Any]:
        """Deactivate emergency stop"""
        try:
            self.emergency_stop = False
            logger.info("Emergency stop deactivated.")
            return {"status": "success", "message": "Emergency stop deactivated"}
        except Exception as e:
            logger.error("Failed to deactivate emergency stop", error=str(e))
            return {"status": "error", "reason": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get current status of the execution service"""
        try:
            account_info = await self._get_account_info()
            return {
                "trading_enabled": self.trading_enabled,
                "emergency_stop": self.emergency_stop,
                "daily_pnl": float(self.daily_pnl),
                "daily_loss_limit": float(self.daily_loss_limit),
                "daily_trades_count": self.daily_trades_count,
                "last_reset_date": str(self.last_reset_date),
                "account_info": account_info,
                "mt5_connected": self.mt5_client.is_connected() if self.mt5_client else False,
                "dry_run_mode": self.settings.dry_run_mode
            }
        except Exception as e:
            logger.error("Failed to get status", error=str(e))
            return {"status": "error", "reason": str(e)}

    async def _send_alert(self, subject: str, message: str) -> None:
        """Send alert via Telegram bot gateway"""
        try:
            alert_data = {
                "chat_id": self.settings.allowed_chat_id,
                "message": f"**{subject}**\n{message}"
            }
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.bot_gateway_port}/send_message",
                headers={
                    "Authorization": f"Bearer {self.settings.api_token}"
                },
                json=alert_data
            )
            if response.status_code == 200:
                logger.info("Alert sent successfully", subject=subject)
            else:
                logger.warning("Failed to send alert", status_code=response.status_code)
        except Exception as e:
            logger.error("Failed to send alert", error=str(e))


# Example usage (for testing)
async def main():
    settings = get_settings()
    settings.dry_run_mode = True # Set to False to test real MT5 connection
    settings.bvm_mt5_enabled = True # Set to True to test BVM MT5 connection
    settings.mt5_login = "YOUR_MT5_LOGIN"
    settings.mt5_password = "YOUR_MT5_PASSWORD"
    settings.mt5_server = "YOUR_MT5_SERVER"
    settings.bvm_vm_ip = "127.0.0.1" # Or your VM's IP
    settings.bvm_vm_port = 8080

    service = ExecutionService()
    await service.initialize()

    # Simulate a signal
    signal = {
        "symbol": "EURUSD",
        "action": "BUY",
        "strength": 0.8,
        "signal_type": "test_signal"
    }
    result = await service.process_signal(signal)
    logger.info(f"Signal processing result: {result}")

    status = await service.get_status()
    logger.info(f"Service status: {status}")

    await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())


