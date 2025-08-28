"""
Simple ML models for trading signals
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from .base import BaseModel
from ..data.models import SignalData, TradeAction


class TrendFollowingModel(BaseModel):
    """Simple trend following model using moving averages and momentum"""
    
    def __init__(self, name: str = "trend_following", version: str = "1.0"):
        super().__init__(name, version)
        self.short_window = 10
        self.long_window = 30
        self.momentum_window = 5
        self.threshold = 0.02  # 2% threshold for signal generation
        self.feature_weights = {}
    
    def train(self, data: pd.DataFrame, target: pd.Series) -> None:
        """Train the model (simplified - just calculate optimal parameters)"""
        # Calculate features
        features = self._calculate_features(data)
        
        if len(features) != len(target):
            # Align lengths
            min_len = min(len(features), len(target))
            features = features.iloc[-min_len:]
            target = target.iloc[-min_len:]
        
        # Simple correlation-based feature weighting
        correlations = {}
        for col in features.columns:
            if not features[col].isna().all():
                corr = features[col].corr(target)
                correlations[col] = abs(corr) if not pd.isna(corr) else 0.0
        
        # Normalize weights
        total_corr = sum(correlations.values())
        if total_corr > 0:
            self.feature_weights = {k: v/total_corr for k, v in correlations.items()}
        else:
            self.feature_weights = {k: 1.0/len(correlations) for k in correlations.keys()}
        
        self.trained = True
        self.updated_at = datetime.utcnow()
        
        # Store training metadata
        self.metadata.update({
            'training_samples': len(target),
            'feature_count': len(features.columns),
            'training_date': datetime.utcnow().isoformat(),
            'feature_weights': self.feature_weights
        })
    
    def predict(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Make prediction"""
        if not self.trained:
            return None
        
        features = self._calculate_features(data)
        if features.empty or len(features) < 2:
            return None
        
        # Get latest feature values
        latest_features = features.iloc[-1]
        
        # Calculate weighted score
        score = 0.0
        for feature, weight in self.feature_weights.items():
            if feature in latest_features and not pd.isna(latest_features[feature]):
                score += latest_features[feature] * weight
        
        # Generate signal based on score
        if score > self.threshold:
            action = TradeAction.BUY
            strength = min(abs(score), 1.0)
            confidence = min(0.5 + abs(score) * 0.3, 0.9)
        elif score < -self.threshold:
            action = TradeAction.SELL
            strength = min(abs(score), 1.0)
            confidence = min(0.5 + abs(score) * 0.3, 0.9)
        else:
            return None  # No clear signal
        
        return SignalData(
            signal_type=f"ML_{self.name.upper()}",
            strength=strength,
            action=action,
            confidence=confidence,
            metadata={
                'model_name': self.name,
                'model_version': self.version,
                'score': score,
                'features': latest_features.to_dict()
            }
        )
    
    def _calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate features for the model"""
        features = pd.DataFrame(index=data.index)
        
        # Moving averages
        features['sma_short'] = data['close'].rolling(self.short_window).mean()
        features['sma_long'] = data['close'].rolling(self.long_window).mean()
        
        # Moving average ratio
        features['ma_ratio'] = features['sma_short'] / features['sma_long'] - 1
        
        # Price momentum
        features['momentum'] = data['close'].pct_change(self.momentum_window)
        
        # Volume momentum
        if 'volume' in data.columns:
            features['volume_momentum'] = data['volume'].pct_change(self.momentum_window)
        
        # Price position relative to recent high/low
        features['price_position'] = (data['close'] - data['low'].rolling(20).min()) / (
            data['high'].rolling(20).max() - data['low'].rolling(20).min()
        )
        
        # Volatility
        features['volatility'] = data['close'].rolling(10).std() / data['close'].rolling(10).mean()
        
        return features.dropna()
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return self.feature_weights.copy()
    
    def _get_model_state(self) -> Dict[str, Any]:
        """Get model state for serialization"""
        return {
            'short_window': self.short_window,
            'long_window': self.long_window,
            'momentum_window': self.momentum_window,
            'threshold': self.threshold,
            'feature_weights': self.feature_weights
        }
    
    def _set_model_state(self, state: Dict[str, Any]) -> None:
        """Set model state from deserialization"""
        self.short_window = state.get('short_window', 10)
        self.long_window = state.get('long_window', 30)
        self.momentum_window = state.get('momentum_window', 5)
        self.threshold = state.get('threshold', 0.02)
        self.feature_weights = state.get('feature_weights', {})


class MeanReversionModel(BaseModel):
    """Simple mean reversion model"""
    
    def __init__(self, name: str = "mean_reversion", version: str = "1.0"):
        super().__init__(name, version)
        self.lookback_window = 20
        self.std_threshold = 2.0
        self.feature_weights = {}
    
    def train(self, data: pd.DataFrame, target: pd.Series) -> None:
        """Train the model"""
        features = self._calculate_features(data)
        
        if len(features) != len(target):
            min_len = min(len(features), len(target))
            features = features.iloc[-min_len:]
            target = target.iloc[-min_len:]
        
        # Calculate feature correlations with target
        correlations = {}
        for col in features.columns:
            if not features[col].isna().all():
                corr = features[col].corr(target)
                correlations[col] = abs(corr) if not pd.isna(corr) else 0.0
        
        # Normalize weights
        total_corr = sum(correlations.values())
        if total_corr > 0:
            self.feature_weights = {k: v/total_corr for k, v in correlations.items()}
        else:
            self.feature_weights = {k: 1.0/len(correlations) for k in correlations.keys()}
        
        self.trained = True
        self.updated_at = datetime.utcnow()
        
        self.metadata.update({
            'training_samples': len(target),
            'feature_count': len(features.columns),
            'training_date': datetime.utcnow().isoformat(),
            'feature_weights': self.feature_weights
        })
    
    def predict(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Make prediction based on mean reversion"""
        if not self.trained:
            return None
        
        features = self._calculate_features(data)
        if features.empty:
            return None
        
        latest_features = features.iloc[-1]
        
        # Calculate z-score based signal
        z_score = latest_features.get('z_score', 0)
        
        if pd.isna(z_score):
            return None
        
        # Mean reversion signals
        if z_score > self.std_threshold:
            # Price is too high, expect reversion down
            action = TradeAction.SELL
            strength = min(abs(z_score) / 4.0, 1.0)  # Scale to 0-1
            confidence = min(0.4 + abs(z_score) * 0.1, 0.8)
        elif z_score < -self.std_threshold:
            # Price is too low, expect reversion up
            action = TradeAction.BUY
            strength = min(abs(z_score) / 4.0, 1.0)
            confidence = min(0.4 + abs(z_score) * 0.1, 0.8)
        else:
            return None  # No clear signal
        
        return SignalData(
            signal_type=f"ML_{self.name.upper()}",
            strength=strength,
            action=action,
            confidence=confidence,
            metadata={
                'model_name': self.name,
                'model_version': self.version,
                'z_score': z_score,
                'features': latest_features.to_dict()
            }
        )
    
    def _calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate features for mean reversion"""
        features = pd.DataFrame(index=data.index)
        
        # Rolling mean and std
        rolling_mean = data['close'].rolling(self.lookback_window).mean()
        rolling_std = data['close'].rolling(self.lookback_window).std()
        
        # Z-score (how many standard deviations from mean)
        features['z_score'] = (data['close'] - rolling_mean) / rolling_std
        
        # Distance from mean as percentage
        features['mean_distance'] = (data['close'] - rolling_mean) / rolling_mean
        
        # Bollinger Band position
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        features['bb_position'] = (data['close'] - lower_band) / (upper_band - lower_band)
        
        # RSI-like momentum
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        return features.dropna()
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return self.feature_weights.copy()
    
    def _get_model_state(self) -> Dict[str, Any]:
        """Get model state for serialization"""
        return {
            'lookback_window': self.lookback_window,
            'std_threshold': self.std_threshold,
            'feature_weights': self.feature_weights
        }
    
    def _set_model_state(self, state: Dict[str, Any]) -> None:
        """Set model state from deserialization"""
        self.lookback_window = state.get('lookback_window', 20)
        self.std_threshold = state.get('std_threshold', 2.0)
        self.feature_weights = state.get('feature_weights', {})

