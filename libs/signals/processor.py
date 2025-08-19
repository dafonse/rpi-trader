"""
Signal processing and filtering
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from .base import SignalGenerator
from ..data.models import SignalData, TradeAction
from ..core.logging import get_logger

logger = get_logger(__name__)


class SignalProcessor:
    """Process and filter trading signals"""
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.signal_history: List[SignalData] = []
        self.min_confidence = 0.5
        self.min_strength = 0.3
        self.cooldown_period = timedelta(minutes=15)  # Minimum time between signals for same symbol
    
    def set_filters(self, min_confidence: float = 0.5, min_strength: float = 0.3, 
                   cooldown_minutes: int = 15) -> None:
        """Set signal filtering parameters"""
        self.min_confidence = min_confidence
        self.min_strength = min_strength
        self.cooldown_period = timedelta(minutes=cooldown_minutes)
    
    def add_signal_generator(self, signal_generator, weight: float = 1.0) -> None:
        """Add a signal generator"""
        self.signal_generator.add_signal(signal_generator, weight)
    
    def process_market_data(self, symbol: str, market_data: pd.DataFrame) -> Optional[SignalData]:
        """Process market data and generate filtered signals"""
        try:
            # Generate combined signal
            signal = self.signal_generator.get_combined_signal(symbol, market_data)
            
            if not signal:
                return None
            
            # Apply filters
            if not self._passes_filters(signal):
                logger.debug("Signal filtered out", 
                           symbol=symbol, 
                           confidence=signal.confidence,
                           strength=signal.strength)
                return None
            
            # Check cooldown period
            if self._is_in_cooldown(symbol, signal.action):
                logger.debug("Signal in cooldown period", symbol=symbol, action=signal.action.value)
                return None
            
            # Add to history
            self.signal_history.append(signal)
            
            # Clean old signals (keep last 1000)
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
            
            logger.info("Signal generated", 
                       symbol=symbol,
                       action=signal.action.value,
                       strength=signal.strength,
                       confidence=signal.confidence,
                       signal_type=signal.signal_type)
            
            return signal
            
        except Exception as e:
            logger.error("Error processing market data", symbol=symbol, error=str(e))
            return None
    
    def _passes_filters(self, signal: SignalData) -> bool:
        """Check if signal passes minimum filters"""
        return (signal.confidence >= self.min_confidence and 
                signal.strength >= self.min_strength)
    
    def _is_in_cooldown(self, symbol: str, action: TradeAction) -> bool:
        """Check if symbol/action is in cooldown period"""
        cutoff_time = datetime.utcnow() - self.cooldown_period
        
        for historical_signal in reversed(self.signal_history):
            if historical_signal.generated_at < cutoff_time:
                break
            
            if (historical_signal.symbol == symbol and 
                historical_signal.action == action):
                return True
        
        return False
    
    def get_signal_statistics(self, symbol: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get signal statistics for analysis"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter signals by time and optionally by symbol
        filtered_signals = [
            s for s in self.signal_history 
            if s.generated_at >= cutoff_time and (symbol is None or s.symbol == symbol)
        ]
        
        if not filtered_signals:
            return {
                "total_signals": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "avg_confidence": 0.0,
                "avg_strength": 0.0,
                "signal_types": {}
            }
        
        buy_signals = sum(1 for s in filtered_signals if s.action == TradeAction.BUY)
        sell_signals = sum(1 for s in filtered_signals if s.action == TradeAction.SELL)
        
        avg_confidence = sum(s.confidence for s in filtered_signals) / len(filtered_signals)
        avg_strength = sum(s.strength for s in filtered_signals) / len(filtered_signals)
        
        # Count signal types
        signal_types = {}
        for signal in filtered_signals:
            signal_types[signal.signal_type] = signal_types.get(signal.signal_type, 0) + 1
        
        return {
            "total_signals": len(filtered_signals),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "avg_confidence": round(avg_confidence, 3),
            "avg_strength": round(avg_strength, 3),
            "signal_types": signal_types,
            "time_period_hours": hours,
            "symbol": symbol
        }
    
    def get_recent_signals(self, symbol: str = None, limit: int = 10) -> List[SignalData]:
        """Get recent signals"""
        filtered_signals = [
            s for s in self.signal_history 
            if symbol is None or s.symbol == symbol
        ]
        
        # Sort by generation time (most recent first)
        filtered_signals.sort(key=lambda x: x.generated_at, reverse=True)
        
        return filtered_signals[:limit]
    
    def clear_history(self) -> None:
        """Clear signal history"""
        self.signal_history.clear()
        logger.info("Signal history cleared")

