"""
Technical analysis based trading signals
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from .base import BaseSignal
from ..data.models import SignalData, TradeAction


class MovingAverageSignal(BaseSignal):
    """Moving Average Crossover Signal"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        super().__init__("MA_CROSSOVER", {
            "fast_period": fast_period,
            "slow_period": slow_period
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def get_required_periods(self) -> int:
        return max(self.fast_period, self.slow_period) + 1
    
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Calculate moving average crossover signal"""
        if len(data) < self.get_required_periods():
            return None
        
        # Calculate moving averages
        data['ma_fast'] = data['close'].rolling(window=self.fast_period).mean()
        data['ma_slow'] = data['close'].rolling(window=self.slow_period).mean()
        
        # Get last two values to detect crossover
        current_fast = data['ma_fast'].iloc[-1]
        current_slow = data['ma_slow'].iloc[-1]
        prev_fast = data['ma_fast'].iloc[-2]
        prev_slow = data['ma_slow'].iloc[-2]
        
        # Check for crossover
        if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
            return None
        
        # Bullish crossover: fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            strength = min((current_fast - current_slow) / current_slow, 1.0)
            return SignalData(
                signal_type=self.name,
                strength=abs(strength),
                action=TradeAction.BUY,
                confidence=0.7,
                metadata={
                    "fast_ma": current_fast,
                    "slow_ma": current_slow,
                    "crossover_type": "bullish"
                }
            )
        
        # Bearish crossover: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            strength = min((current_slow - current_fast) / current_slow, 1.0)
            return SignalData(
                signal_type=self.name,
                strength=abs(strength),
                action=TradeAction.SELL,
                confidence=0.7,
                metadata={
                    "fast_ma": current_fast,
                    "slow_ma": current_slow,
                    "crossover_type": "bearish"
                }
            )
        
        return None


class RSISignal(BaseSignal):
    """RSI Overbought/Oversold Signal"""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        super().__init__("RSI_SIGNAL", {
            "period": period,
            "overbought": overbought,
            "oversold": oversold
        })
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def get_required_periods(self) -> int:
        return self.period + 1
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Calculate RSI signal"""
        if len(data) < self.get_required_periods():
            return None
        
        rsi = self.calculate_rsi(data['close'])
        current_rsi = rsi.iloc[-1]
        
        if pd.isna(current_rsi):
            return None
        
        # Oversold condition (potential buy signal)
        if current_rsi < self.oversold:
            strength = (self.oversold - current_rsi) / self.oversold
            return SignalData(
                signal_type=self.name,
                strength=min(strength, 1.0),
                action=TradeAction.BUY,
                confidence=0.6,
                metadata={
                    "rsi": current_rsi,
                    "condition": "oversold",
                    "threshold": self.oversold
                }
            )
        
        # Overbought condition (potential sell signal)
        elif current_rsi > self.overbought:
            strength = (current_rsi - self.overbought) / (100 - self.overbought)
            return SignalData(
                signal_type=self.name,
                strength=min(strength, 1.0),
                action=TradeAction.SELL,
                confidence=0.6,
                metadata={
                    "rsi": current_rsi,
                    "condition": "overbought",
                    "threshold": self.overbought
                }
            )
        
        return None


class MACDSignal(BaseSignal):
    """MACD Signal"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("MACD_SIGNAL", {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def get_required_periods(self) -> int:
        return self.slow_period + self.signal_period + 1
    
    def calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = prices.ewm(span=self.fast_period).mean()
        ema_slow = prices.ewm(span=self.slow_period).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Calculate MACD signal"""
        if len(data) < self.get_required_periods():
            return None
        
        macd_line, signal_line, histogram = self.calculate_macd(data['close'])
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2]
        
        if pd.isna(current_macd) or pd.isna(current_signal) or pd.isna(current_histogram) or pd.isna(prev_histogram):
            return None
        
        # Bullish signal: MACD crosses above signal line
        if prev_histogram <= 0 and current_histogram > 0:
            strength = min(abs(current_histogram) / abs(current_macd), 1.0) if current_macd != 0 else 0.5
            return SignalData(
                signal_type=self.name,
                strength=strength,
                action=TradeAction.BUY,
                confidence=0.65,
                metadata={
                    "macd": current_macd,
                    "signal": current_signal,
                    "histogram": current_histogram,
                    "crossover_type": "bullish"
                }
            )
        
        # Bearish signal: MACD crosses below signal line
        elif prev_histogram >= 0 and current_histogram < 0:
            strength = min(abs(current_histogram) / abs(current_macd), 1.0) if current_macd != 0 else 0.5
            return SignalData(
                signal_type=self.name,
                strength=strength,
                action=TradeAction.SELL,
                confidence=0.65,
                metadata={
                    "macd": current_macd,
                    "signal": current_signal,
                    "histogram": current_histogram,
                    "crossover_type": "bearish"
                }
            )
        
        return None


class BollingerBandsSignal(BaseSignal):
    """Bollinger Bands Signal"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("BOLLINGER_BANDS", {
            "period": period,
            "std_dev": std_dev
        })
        self.period = period
        self.std_dev = std_dev
    
    def get_required_periods(self) -> int:
        return self.period + 1
    
    def calculate(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Calculate Bollinger Bands signal"""
        if len(data) < self.get_required_periods():
            return None
        
        # Calculate Bollinger Bands
        sma = data['close'].rolling(window=self.period).mean()
        std = data['close'].rolling(window=self.period).std()
        
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        current_price = data['close'].iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]
        
        if pd.isna(current_upper) or pd.isna(current_lower) or pd.isna(current_sma):
            return None
        
        # Price touches or breaks lower band (potential buy signal)
        if current_price <= current_lower:
            strength = (current_lower - current_price) / (current_sma - current_lower)
            return SignalData(
                signal_type=self.name,
                strength=min(abs(strength), 1.0),
                action=TradeAction.BUY,
                confidence=0.55,
                metadata={
                    "price": current_price,
                    "upper_band": current_upper,
                    "lower_band": current_lower,
                    "sma": current_sma,
                    "condition": "lower_band_touch"
                }
            )
        
        # Price touches or breaks upper band (potential sell signal)
        elif current_price >= current_upper:
            strength = (current_price - current_upper) / (current_upper - current_sma)
            return SignalData(
                signal_type=self.name,
                strength=min(abs(strength), 1.0),
                action=TradeAction.SELL,
                confidence=0.55,
                metadata={
                    "price": current_price,
                    "upper_band": current_upper,
                    "lower_band": current_lower,
                    "sma": current_sma,
                    "condition": "upper_band_touch"
                }
            )
        
        return None

