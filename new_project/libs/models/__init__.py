"""
ML models and model management
"""

from .base import BaseModel, ModelRegistry
from .simple_models import TrendFollowingModel, MeanReversionModel

__all__ = [
    "BaseModel",
    "ModelRegistry",
    "TrendFollowingModel",
    "MeanReversionModel",
]

