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
from libs.broker.mt5_client import MT5Client

logger = get_logger(__name__)


class ExecutionService:
    """Execution service for order management and trade execution"""
    
    def __init__(self):
        self.settings = get_settings()
        self.mt5_client = MT5Client()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Trading state
        self.trading_enabled = not self.settings.dry_run_mode
        self.emergency_stop = False
        
        # Risk management
        self.daily_pnl = Decimal('0.0')
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
            if not self.settings.dry_run_mode:
                await self.mt5_client.initialize()
                logger.info("MT5 client initialized")
            else:
                logger.info("Running in dry-run mode, MT5 client not initialized")
            
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
            if not self.settings.dry_run_mode:
                await self.mt5_client.cleanup()
            
            await self.http_client.aclose()
            logger.info("Execution Service cleanup completed")
        except Exception as e:
            logger.error("Error during Execution Service cleanup", error=str(e))
    
    async def _check_and_reset_daily_limits(self) -> None:
        """Check and reset daily limits if new day"""
        current_date = datetime.utcnow().date()
        
        if current_date > self.last_reset_date:
            logger.info("Resetting daily limits for new trading day", date=current_date)
            self.daily_pnl = Decimal('0.0')
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
                       symbol=signal_data['symbol'], 
                       action=signal_data['action'],
                       strength=signal_data['strength'])
            
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
            if abs(signal_data['strength']) < 0.7:
                return {
                    "status": "rejected",
                    "reason": "Signal strength too weak"
                }
            
            # Calculate position size
            position_size = await self._calculate_position_size(
                signal_data['symbol'], 
                signal_data['strength']
            )
            
            if position_size <= 0:
                return {
                    "status": "rejected",
                    "reason": "Position size calculation failed"
                }
            
            # Create and execute order
            order_result = await self._execute_order(
                symbol=signal_data['symbol'],
                action=TradeAction(signal_data['action']),
                quantity=position_size,
                order_type=OrderType.MARKET,
                metadata={
                    "signal_type": signal_data.get('signal_type'),
                    "signal_strength": signal_data['strength'],
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
                return Decimal('0.0')
            
            # Base position size (e.g., 1% of account balance)
            account_balance = Decimal(str(account_info.get('balance', 0)))
            base_size = account_balance * Decimal('0.01')  # 1% risk
            
            # Adjust based on signal strength
            strength_multiplier = Decimal(str(abs(signal_strength)))
            position_size = base_size * strength_multiplier
            
            # Apply maximum order size limit
            if position_size > self.max_order_size:
                position_size = self.max_order_size
            
            # Convert to lot size for forex (simplified)
            if symbol.endswith('USD') or symbol.startswith('USD'):
                # For forex, convert to lots (100,000 units = 1 lot)
                lot_size = position_size / Decimal('100000')
                # Round to 2 decimal places (0.01 lot minimum)
                lot_size = lot_size.quantize(Decimal('0.01'))
                return lot_size
            
            return position_size
            
        except Exception as e:
            logger.error("Failed to calculate position size", symbol=symbol, error=str(e))
            return Decimal('0.0')
    
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
            
            if self.settings.dry_run_mode:
                # Simulate order execution
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
                execution_price = Decimal(str(market_data['ask']))
            else:
                execution_price = Decimal(str(market_data['bid']))
            
            # Update trade record
            trade.price = execution_price
            trade.status = TradeStatus.FILLED
            trade.filled_at = datetime.utcnow()
            trade.broker_order_id = f"SIM_{datetime.utcnow().timestamp()}"
            
            # Simulate commission (0.1 pip)
            pip_value = Decimal('0.0001') if 'JPY' not in trade.symbol else Decimal('0.01')
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
            # Execute order through MT5 client
            result = await self.mt5_client.place_order(
                symbol=trade.symbol,
                action=trade.action,
                quantity=float(trade.quantity),
                order_type=trade.order_type
            )
            
            if result['success']:
                trade.price = Decimal(str(result['price']))
                trade.status = TradeStatus.FILLED
                trade.filled_at = datetime.utcnow()
                trade.broker_order_id = result['order_id']
                trade.commission = Decimal(str(result.get('commission', 0)))
                
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
                logger.error("Order rejected by broker", reason=result.get('error'))
                
                return {
                    "status": "rejected",
                    "reason": result.get('error', 'Unknown broker error')
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
            if self.settings.dry_run_mode:
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
            if self.settings.dry_run_mode:
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
                return await self.mt5_client.get_market_data(symbol)
                
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
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
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
                return {
                    "status": "failed",
                    "reason": "Emergency stop is active. Clear emergency stop first."
                }
            
            # Check daily limits
            if not await self._check_daily_limits():
                return {
                    "status": "failed",
                    "reason": "Daily limits exceeded"
                }
            
            self.trading_enabled = True
            logger.info("Trading enabled")
            
            await self._send_alert("Trading Enabled", "Automated trading has been enabled.")
            
            return {"status": "success", "message": "Trading enabled"}
            
        except Exception as e:
            logger.error("Failed to enable trading", error=str(e))
            return {"status": "error", "reason": str(e)}
    
    async def disable_trading(self) -> Dict[str, Any]:
        """Disable trading"""
        try:
            self.trading_enabled = False
            logger.info("Trading disabled")
            
            await self._send_alert("Trading Disabled", "Automated trading has been disabled.")
            
            return {"status": "success", "message": "Trading disabled"}
            
        except Exception as e:
            logger.error("Failed to disable trading", error=str(e))
            return {"status": "error", "reason": str(e)}
    
    async def emergency_stop_trading(self) -> Dict[str, Any]:
        """Emergency stop - disable all trading immediately"""
        try:
            self.emergency_stop = True
            self.trading_enabled = False
            
            logger.critical("EMERGENCY STOP ACTIVATED")
            
            # Close all open positions if not in dry-run mode
            if not self.settings.dry_run_mode:
                await self._close_all_positions()
            
            await self._send_alert("🚨 EMERGENCY STOP ACTIVATED", 
                                 "All trading has been stopped immediately. Manual intervention required.")
            
            return {"status": "success", "message": "Emergency stop activated"}
            
        except Exception as e:
            logger.error("Failed to activate emergency stop", error=str(e))
            return {"status": "error", "reason": str(e)}
    
    async def clear_emergency_stop(self) -> Dict[str, Any]:
        """Clear emergency stop"""
        try:
            self.emergency_stop = False
            logger.info("Emergency stop cleared")
            
            await self._send_alert("Emergency Stop Cleared", 
                                 "Emergency stop has been cleared. Trading can be re-enabled.")
            
            return {"status": "success", "message": "Emergency stop cleared"}
            
        except Exception as e:
            logger.error("Failed to clear emergency stop", error=str(e))
            return {"status": "error", "reason": str(e)}
    
    async def reset_daily_limits(self) -> Dict[str, Any]:
        """Reset daily limits"""
        try:
            self.daily_pnl = Decimal('0.0')
            self.daily_trades_count = 0
            self.last_reset_date = datetime.utcnow().date()
            
            logger.info("Daily limits reset")
            
            return {"status": "success", "message": "Daily limits reset"}
            
        except Exception as e:
            logger.error("Failed to reset daily limits", error=str(e))
            return {"status": "error", "reason": str(e)}
    
    # Helper Methods
    
    async def _close_all_positions(self) -> None:
        """Close all open positions"""
        try:
            if not self.settings.dry_run_mode:
                await self.mt5_client.close_all_positions()
                logger.info("All positions closed")
        except Exception as e:
            logger.error("Failed to close all positions", error=str(e))
    
    async def _send_alert(self, title: str, message: str) -> None:
        """Send alert via Telegram bot"""
        try:
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.bot_gateway_port}/alert",
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
                json={
                    "title": title,
                    "message": message
                }
            )
            
            if response.status_code != 200:
                logger.warning("Failed to send alert", status_code=response.status_code)
                
        except Exception as e:
            logger.error("Failed to send alert", error=str(e))
    
    # Status Methods
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get current trading status"""
        return {
            "trading_enabled": self.trading_enabled,
            "emergency_stop": self.emergency_stop,
            "dry_run_mode": self.settings.dry_run_mode,
            "daily_pnl": float(self.daily_pnl),
            "daily_trades_count": self.daily_trades_count,
            "daily_loss_limit": float(self.daily_loss_limit),
            "max_order_size": float(self.max_order_size),
            "last_reset_date": self.last_reset_date.isoformat()
        }

