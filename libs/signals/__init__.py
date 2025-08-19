"""
Trading signal generation and processing
"""

from .base import BaseSignal, SignalGenerator
from .technical import MovingAverageSignal, RSISignal, MACDSignal
from .processor import SignalProcessor

__all__ = [
    "BaseSignal",
    "SignalGenerator",
    "MovingAverageSignal",
    "RSISignal", 
    "MACDSignal",
    "SignalProcessor",
]

