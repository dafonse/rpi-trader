"""
Base classes for trading signals
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

from ..data.models import SignalData, TradeAction


class BaseSignal(ABC):
    """Base class for trading signals"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Calculate signal from market data"""
        pass
    
    @abstractmethod
    def get_required_periods(self) -> int:
        """Get minimum number of periods required for calculation"""
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_columns)


class SignalGenerator:
    """Manages multiple signals and generates combined signals"""
    
    def __init__(self):
        self.signals: List[BaseSignal] = []
        self.weights: Dict[str, float] = {}
    
    def add_signal(self, signal: BaseSignal, weight: float = 1.0) -> None:
        """Add a signal with optional weight"""
        self.signals.append(signal)
        self.weights[signal.name] = weight
    
    def remove_signal(self, signal_name: str) -> None:
        """Remove a signal by name"""
        self.signals = [s for s in self.signals if s.name != signal_name]
        self.weights.pop(signal_name, None)
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> List[SignalData]:
        """Generate signals from all registered signal generators"""
        signals = []
        
        for signal_generator in self.signals:
            try:
                if not signal_generator.validate_data(data):
                    continue
                
                if len(data) < signal_generator.get_required_periods():
                    continue
                
                signal = signal_generator.calculate(data)
                if signal:
                    signal.symbol = symbol
                    signals.append(signal)
                    
            except Exception as e:
                # Log error but continue with other signals
                print(f"Error generating signal {signal_generator.name}: {e}")
        
        return signals
    
    def get_combined_signal(self, symbol: str, data: pd.DataFrame) -> Optional[SignalData]:
        """Generate a combined signal from all individual signals"""
        individual_signals = self.generate_signals(symbol, data)
        
        if not individual_signals:
            return None
        
        # Calculate weighted average
        total_weight = 0.0
        weighted_strength = 0.0
        weighted_confidence = 0.0
        buy_signals = 0
        sell_signals = 0
        
        for signal in individual_signals:
            weight = self.weights.get(signal.signal_type, 1.0)
            total_weight += weight
            weighted_strength += signal.strength * weight
            weighted_confidence += signal.confidence * weight
            
            if signal.action == TradeAction.BUY:
                buy_signals += weight
            else:
                sell_signals += weight
        
        if total_weight == 0:
            return None
        
        # Determine combined action
        if buy_signals > sell_signals:
            action = TradeAction.BUY
        elif sell_signals > buy_signals:
            action = TradeAction.SELL
        else:
            return None  # No clear direction
        
        return SignalData(
            symbol=symbol,
            signal_type="COMBINED",
            strength=weighted_strength / total_weight,
            action=action,
            confidence=weighted_confidence / total_weight,
            metadata={
                "individual_signals": len(individual_signals),
                "buy_weight": buy_signals,
                "sell_weight": sell_signals,
                "component_signals": [s.signal_type for s in individual_signals]
            }
        )

