"""
Base classes for ML models and model management
"""

import os
import pickle
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd

from ..data.models import SignalData


class BaseModel(ABC):
    """Base class for ML models"""
    
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.trained = False
        self.metadata: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    @abstractmethod
    def train(self, data: pd.DataFrame, target: pd.Series) -> None:
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, data: pd.DataFrame) -> Optional[SignalData]:
        """Make predictions"""
        pass
    
    @abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        pass
    
    def save(self, filepath: str) -> None:
        """Save model to file"""
        model_data = {
            'name': self.name,
            'version': self.version,
            'trained': self.trained,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'model_state': self._get_model_state()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load(self, filepath: str) -> None:
        """Load model from file"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.name = model_data['name']
        self.version = model_data['version']
        self.trained = model_data['trained']
        self.metadata = model_data['metadata']
        self.created_at = datetime.fromisoformat(model_data['created_at'])
        self.updated_at = datetime.fromisoformat(model_data['updated_at'])
        
        self._set_model_state(model_data['model_state'])
    
    @abstractmethod
    def _get_model_state(self) -> Dict[str, Any]:
        """Get model-specific state for serialization"""
        pass
    
    @abstractmethod
    def _set_model_state(self, state: Dict[str, Any]) -> None:
        """Set model-specific state from deserialization"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'name': self.name,
            'version': self.version,
            'trained': self.trained,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }


class ModelRegistry:
    """Registry for managing ML models"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.models: Dict[str, BaseModel] = {}
        
        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)
    
    def register_model(self, model: BaseModel) -> None:
        """Register a model"""
        self.models[model.name] = model
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """Get a model by name"""
        return self.models.get(name)
    
    def list_models(self) -> List[str]:
        """List all registered model names"""
        return list(self.models.keys())
    
    def save_model(self, name: str, filepath: str = None) -> None:
        """Save a model to disk"""
        model = self.models.get(name)
        if not model:
            raise ValueError(f"Model {name} not found")
        
        if filepath is None:
            filepath = os.path.join(self.models_dir, f"{name}_v{model.version}.pkl")
        
        model.save(filepath)
    
    def load_model(self, name: str, filepath: str = None) -> BaseModel:
        """Load a model from disk"""
        if filepath is None:
            # Find the latest version
            model_files = [f for f in os.listdir(self.models_dir) if f.startswith(f"{name}_v")]
            if not model_files:
                raise FileNotFoundError(f"No saved models found for {name}")
            
            # Sort by version and get the latest
            model_files.sort(reverse=True)
            filepath = os.path.join(self.models_dir, model_files[0])
        
        # Create a temporary model instance to load
        # This is a simplified approach - in practice, you'd need to know the model class
        from .simple_models import TrendFollowingModel
        temp_model = TrendFollowingModel(name)
        temp_model.load(filepath)
        
        self.models[name] = temp_model
        return temp_model
    
    def get_model_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model information"""
        model = self.models.get(name)
        return model.get_info() if model else None
    
    def list_saved_models(self) -> List[Dict[str, Any]]:
        """List all saved models on disk"""
        saved_models = []
        
        for filename in os.listdir(self.models_dir):
            if filename.endswith('.pkl'):
                filepath = os.path.join(self.models_dir, filename)
                try:
                    with open(filepath, 'rb') as f:
                        model_data = pickle.load(f)
                    
                    saved_models.append({
                        'filename': filename,
                        'name': model_data['name'],
                        'version': model_data['version'],
                        'trained': model_data['trained'],
                        'created_at': model_data['created_at'],
                        'updated_at': model_data['updated_at']
                    })
                except Exception:
                    # Skip corrupted files
                    continue
        
        return saved_models
    
    def delete_model(self, name: str, delete_file: bool = False) -> None:
        """Delete a model from registry and optionally from disk"""
        if name in self.models:
            model = self.models[name]
            del self.models[name]
            
            if delete_file:
                filepath = os.path.join(self.models_dir, f"{name}_v{model.version}.pkl")
                if os.path.exists(filepath):
                    os.remove(filepath)

