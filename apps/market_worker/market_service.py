"""
Market Service Implementation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json

import pandas as pd
import numpy as np
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import get_logger
from libs.data.repository import MarketDataRepository, SignalRepository
from libs.data.models import MarketData, SignalData, TradeAction
from libs.signals.processor import SignalProcessor
from libs.signals.technical import MovingAverageSignal, RSISignal, MACDSignal, BollingerBandsSignal

logger = get_logger(__name__)


class MarketService:
    """Market service for data collection and signal generation"""
    
    def __init__(self):
        self.settings = get_settings()
        self.market_data_repo = MarketDataRepository()
        self.signal_repo = SignalRepository()
        self.signal_processor = SignalProcessor()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Market data storage
        self.market_data_cache = {}
        self.price_history = {}
        
        # Data collection control
        self.collecting_data = False
        self.collection_task = None
        
        # Symbols to monitor
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        
    async def initialize(self) -> None:
        """Initialize the market service"""
        try:
            logger.info("Initializing Market Service")
            
            # Initialize database repositories
            self.market_data_repo.init_db()
            self.signal_repo.init_db()
            
            # Setup signal generators
            self._setup_signal_generators()
            
            # Initialize price history cache
            await self._initialize_price_history()
            
            logger.info("Market Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Market Service", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.collecting_data = False
            if self.collection_task:
                self.collection_task.cancel()
                try:
                    await self.collection_task
                except asyncio.CancelledError:
                    pass
            
            await self.http_client.aclose()
            logger.info("Market Service cleanup completed")
        except Exception as e:
            logger.error("Error during Market Service cleanup", error=str(e))
    
    def _setup_signal_generators(self) -> None:
        """Setup signal generators"""
        try:
            # Moving Average signals
            self.signal_processor.add_signal_generator(
                MovingAverageSignal(fast_period=10, slow_period=20),
                weight=1.0
            )
            self.signal_processor.add_signal_generator(
                MovingAverageSignal(fast_period=20, slow_period=50),
                weight=1.5
            )
            
            # RSI signals
            self.signal_processor.add_signal_generator(
                RSISignal(period=14, oversold_threshold=30, overbought_threshold=70),
                weight=1.2
            )
            
            # MACD signals
            self.signal_processor.add_signal_generator(
                MACDSignal(fast_period=12, slow_period=26, signal_period=9),
                weight=1.3
            )
            
            # Bollinger Bands signals
            self.signal_processor.add_signal_generator(
                BollingerBandsSignal(period=20, std_dev=2.0),
                weight=1.1
            )
            
            logger.info("Signal generators configured", count=len(self.signal_processor.signal_generators))
            
        except Exception as e:
            logger.error("Failed to setup signal generators", error=str(e))
            raise
    
    async def _initialize_price_history(self) -> None:
        """Initialize price history from database"""
        try:
            for symbol in self.symbols:
                # Get recent market data from database
                recent_data = self.market_data_repo.get_recent_data(symbol, limit=200)
                
                if recent_data:
                    # Convert to DataFrame for analysis
                    df_data = []
                    for data_point in recent_data:
                        df_data.append({
                            'timestamp': data_point.timestamp,
                            'open': float(data_point.bid),  # Simplified - using bid as open
                            'high': float(max(data_point.bid, data_point.ask)),
                            'low': float(min(data_point.bid, data_point.ask)),
                            'close': float(data_point.ask),  # Using ask as close
                            'volume': 1000  # Placeholder volume
                        })
                    
                    self.price_history[symbol] = pd.DataFrame(df_data)
                    logger.info("Price history initialized", symbol=symbol, records=len(df_data))
                else:
                    # Initialize empty DataFrame
                    self.price_history[symbol] = pd.DataFrame(columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume'
                    ])
                    logger.info("Empty price history initialized", symbol=symbol)
                    
        except Exception as e:
            logger.error("Failed to initialize price history", error=str(e))
    
    async def start_data_collection(self) -> None:
        """Start market data collection"""
        try:
            logger.info("Starting market data collection")
            self.collecting_data = True
            
            # Start data collection task
            self.collection_task = asyncio.create_task(self._data_collection_loop())
            
        except Exception as e:
            logger.error("Failed to start data collection", error=str(e))
            raise
    
    async def _data_collection_loop(self) -> None:
        """Main data collection loop"""
        while self.collecting_data:
            try:
                # Collect market data for all symbols
                for symbol in self.symbols:
                    await self._collect_market_data(symbol)
                
                # Generate signals for all symbols
                for symbol in self.symbols:
                    await self._generate_signals(symbol)
                
                # Wait before next collection cycle
                await asyncio.sleep(5)  # Collect data every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in data collection loop", error=str(e))
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _collect_market_data(self, symbol: str) -> None:
        """Collect market data for a symbol"""
        try:
            # In a real implementation, this would connect to a broker API or data feed
            # For now, we'll simulate market data or try to get it from the execution worker
            
            market_data = await self._get_market_data_from_broker(symbol)
            
            if market_data:
                # Store in database
                self.market_data_repo.create(market_data)
                
                # Update cache
                self.market_data_cache[symbol] = market_data
                
                # Update price history
                await self._update_price_history(symbol, market_data)
                
        except Exception as e:
            logger.error("Failed to collect market data", symbol=symbol, error=str(e))
    
    async def _get_market_data_from_broker(self, symbol: str) -> Optional[MarketData]:
        """Get market data from broker API"""
        try:
            # Try to get data from execution worker (which connects to broker)
            response = await self.http_client.get(
                f"http://127.0.0.1:{self.settings.execution_worker_port}/market-data/{symbol}",
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return MarketData(
                    symbol=symbol,
                    bid=Decimal(str(data['bid'])),
                    ask=Decimal(str(data['ask'])),
                    timestamp=datetime.utcnow()
                )
            
            # Fallback: Generate simulated data for testing
            return self._generate_simulated_data(symbol)
            
        except Exception as e:
            logger.debug("Failed to get market data from broker, using simulation", symbol=symbol, error=str(e))
            return self._generate_simulated_data(symbol)
    
    def _generate_simulated_data(self, symbol: str) -> MarketData:
        """Generate simulated market data for testing"""
        # Base prices for different symbols
        base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50,
            "AUDUSD": 0.6750,
            "USDCAD": 1.3450
        }
        
        base_price = base_prices.get(symbol, 1.0000)
        
        # Add some random variation
        import random
        variation = random.uniform(-0.001, 0.001)  # ±0.1% variation
        
        bid = Decimal(str(base_price + variation))
        ask = bid + Decimal("0.0002")  # 2 pip spread
        
        return MarketData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            timestamp=datetime.utcnow()
        )
    
    async def _update_price_history(self, symbol: str, market_data: MarketData) -> None:
        """Update price history with new market data"""
        try:
            if symbol not in self.price_history:
                self.price_history[symbol] = pd.DataFrame(columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume'
                ])
            
            # Calculate mid price
            mid_price = float((market_data.bid + market_data.ask) / 2)
            
            # Add new data point
            new_row = {
                'timestamp': market_data.timestamp,
                'open': mid_price,  # Simplified
                'high': mid_price,
                'low': mid_price,
                'close': mid_price,
                'volume': 1000
            }
            
            # Use pd.concat instead of append (which is deprecated)
            new_df = pd.DataFrame([new_row])
            self.price_history[symbol] = pd.concat([self.price_history[symbol], new_df], ignore_index=True)
            
            # Keep only last 1000 records
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol].tail(1000).reset_index(drop=True)
                
        except Exception as e:
            logger.error("Failed to update price history", symbol=symbol, error=str(e))
    
    async def _generate_signals(self, symbol: str) -> None:
        """Generate trading signals for a symbol"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 50:
                return  # Need enough data for signal generation
            
            # Get price data
            price_data = self.price_history[symbol].copy()
            
            # Generate signals using signal processor
            signals = self.signal_processor.process_signals(price_data)
            
            if signals:
                # Store the strongest signal
                strongest_signal = max(signals, key=lambda s: abs(s.strength))
                
                # Only store signals with sufficient strength
                if abs(strongest_signal.strength) > 0.3:
                    self.signal_repo.create(strongest_signal)
                    
                    # Send signal to execution worker if strong enough
                    if abs(strongest_signal.strength) > 0.7:
                        await self._send_signal_to_execution(strongest_signal)
                        
        except Exception as e:
            logger.error("Failed to generate signals", symbol=symbol, error=str(e))
    
    async def _send_signal_to_execution(self, signal: SignalData) -> None:
        """Send strong signal to execution worker"""
        try:
            signal_data = {
                "symbol": signal.symbol,
                "action": signal.action.value,
                "strength": signal.strength,
                "signal_type": signal.signal_type,
                "metadata": signal.metadata
            }
            
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.execution_worker_port}/signals",
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
                json=signal_data
            )
            
            if response.status_code == 200:
                logger.info("Signal sent to execution worker", symbol=signal.symbol, strength=signal.strength)
            else:
                logger.warning("Failed to send signal to execution worker", status_code=response.status_code)
                
        except Exception as e:
            logger.error("Failed to send signal to execution worker", error=str(e))
    
    # Public API methods
    
    async def get_current_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market data for a symbol"""
        try:
            if symbol in self.market_data_cache:
                market_data = self.market_data_cache[symbol]
                return {
                    "symbol": market_data.symbol,
                    "bid": float(market_data.bid),
                    "ask": float(market_data.ask),
                    "timestamp": market_data.timestamp.isoformat(),
                    "spread": float(market_data.ask - market_data.bid)
                }
            
            # Try to get from database
            latest_data = self.market_data_repo.get_latest_price(symbol)
            if latest_data:
                return {
                    "symbol": latest_data.symbol,
                    "bid": float(latest_data.bid),
                    "ask": float(latest_data.ask),
                    "timestamp": latest_data.timestamp.isoformat(),
                    "spread": float(latest_data.ask - latest_data.bid)
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get current market data", symbol=symbol, error=str(e))
            return None
    
    async def get_recent_signals(self, symbol: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        try:
            signals = self.signal_repo.get_recent_signals(symbol, limit)
            
            return [
                {
                    "id": signal.id,
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type,
                    "action": signal.action.value,
                    "strength": signal.strength,
                    "timestamp": signal.timestamp.isoformat(),
                    "metadata": signal.metadata
                }
                for signal in signals
            ]
            
        except Exception as e:
            logger.error("Failed to get recent signals", error=str(e))
            return []
    
    async def get_signal_statistics(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get signal statistics for a symbol"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            signals = self.signal_repo.get_signals_since(symbol, cutoff_time)
            
            if not signals:
                return {
                    "symbol": symbol,
                    "period_hours": hours,
                    "total_signals": 0,
                    "buy_signals": 0,
                    "sell_signals": 0,
                    "avg_strength": 0.0
                }
            
            buy_signals = [s for s in signals if s.action == TradeAction.BUY]
            sell_signals = [s for s in signals if s.action == TradeAction.SELL]
            avg_strength = sum(abs(s.strength) for s in signals) / len(signals)
            
            return {
                "symbol": symbol,
                "period_hours": hours,
                "total_signals": len(signals),
                "buy_signals": len(buy_signals),
                "sell_signals": len(sell_signals),
                "avg_strength": round(avg_strength, 3)
            }
            
        except Exception as e:
            logger.error("Failed to get signal statistics", symbol=symbol, error=str(e))
            return {}
    
    async def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get price history for a symbol"""
        try:
            if symbol in self.price_history and not self.price_history[symbol].empty:
                df = self.price_history[symbol].tail(limit)
                
                return [
                    {
                        "timestamp": row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                        "open": row['open'],
                        "high": row['high'],
                        "low": row['low'],
                        "close": row['close'],
                        "volume": row['volume']
                    }
                    for _, row in df.iterrows()
                ]
            
            return []
            
        except Exception as e:
            logger.error("Failed to get price history", symbol=symbol, error=str(e))
            return []
    
    def get_monitored_symbols(self) -> List[str]:
        """Get list of monitored symbols"""
        return self.symbols.copy()
    
    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to monitoring"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.price_history[symbol] = pd.DataFrame(columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
            logger.info("Symbol added to monitoring", symbol=symbol)
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from monitoring"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if symbol in self.price_history:
                del self.price_history[symbol]
            if symbol in self.market_data_cache:
                del self.market_data_cache[symbol]
            logger.info("Symbol removed from monitoring", symbol=symbol)

