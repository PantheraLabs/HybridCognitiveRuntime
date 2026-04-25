"""
Neural Operator (Φ_n)

Handles ambiguity and pattern recognition.
Operates on the latent vector space.
"""

from typing import Dict, Any, List, Callable, Optional
import random
from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState


class NeuralOperator(BaseOperator):
    """
    Neural operator for pattern recognition and handling ambiguity.
    
    In a production system, this would use actual neural networks.
    For this implementation, we simulate pattern operations.
    """
    
    def __init__(
        self,
        operator_id: str,
        pattern_size: int = 128,
        pattern_detector: Optional[Callable[[List[float]], bool]] = None,
        description: str = ""
    ):
        super().__init__(operator_id, OperatorType.NEURAL, description)
        self.pattern_size = pattern_size
        self.pattern_detector = pattern_detector or self._default_detector
    
    def _default_detector(self, latent: List[float]) -> bool:
        """Default pattern detection - checks if latent has non-zero values"""
        return any(l != 0 for l in latent)
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute neural pattern recognition on latent state.
        
        Args:
            state: Current cognitive state
            **kwargs:
                - pattern_type: type of pattern to detect
                - transformation: optional transformation to apply
                
        Returns:
            Operation result with updated latent state and detected patterns
        """
        latent = state.latent.copy() if state.latent else []
        
        # Initialize latent if empty
        if not latent:
            latent = [0.0] * self.pattern_size
        
        # Ensure correct size
        if len(latent) < self.pattern_size:
            latent.extend([0.0] * (self.pattern_size - len(latent)))
        elif len(latent) > self.pattern_size:
            latent = latent[:self.pattern_size]
        
        # Pattern detection
        pattern_detected = self.pattern_detector(latent)
        
        # Pattern transformation (simulated)
        pattern_type = kwargs.get("pattern_type", "default")
        transformation = kwargs.get("transformation")
        
        if transformation:
            transformed = transformation(latent)
        else:
            # Simple pattern enhancement simulation
            transformed = self._apply_pattern_transformation(latent, pattern_type)
        
        # Detect patterns in facts
        facts = []
        if pattern_detected:
            facts.append(f"pattern_detected:{pattern_type}")
            if kwargs.get("extract_features", False):
                features = self._extract_features(transformed)
                for feature in features:
                    facts.append(f"feature:{feature}")
        
        return {
            "latent": transformed,
            "facts": facts,
            "dependencies": [f"pattern_recognition:{pattern_type}"]
        }
    
    def _apply_pattern_transformation(
        self,
        latent: List[float],
        pattern_type: str
    ) -> List[float]:
        """
        Apply a transformation based on pattern type.
        
        This is a simulated neural transformation.
        """
        if pattern_type == "amplify":
            # Amplify strong signals
            return [
                l * 1.5 if abs(l) > 0.5 else l * 0.8
                for l in latent
            ]
        elif pattern_type == "smooth":
            # Smooth values toward mean
            mean = sum(latent) / len(latent) if latent else 0
            return [
                l * 0.7 + mean * 0.3
                for l in latent
            ]
        elif pattern_type == "sharpen":
            # Increase contrast
            mean = sum(latent) / len(latent) if latent else 0
            return [
                l + (l - mean) * 0.5
                for l in latent
            ]
        else:
            # Default: small random perturbation (simulated learning)
            return [
                l + random.gauss(0, 0.01)
                for l in latent
            ]
    
    def _extract_features(self, latent: List[float]) -> List[str]:
        """Extract symbolic features from latent representation"""
        features = []
        
        # Simple feature extraction based on statistics
        mean = sum(latent) / len(latent) if latent else 0
        variance = sum((l - mean) ** 2 for l in latent) / len(latent) if latent else 0
        max_val = max(latent) if latent else 0
        min_val = min(latent) if latent else 0
        
        if mean > 0.3:
            features.append("high_activation")
        elif mean < -0.3:
            features.append("low_activation")
        
        if variance > 0.5:
            features.append("high_variance")
        else:
            features.append("low_variance")
        
        if max_val - min_val > 1.0:
            features.append("wide_range")
        
        return features


class SimilarityOperator(NeuralOperator):
    """
    Neural operator for computing similarity between states.
    """
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Compute similarity between current state and reference.
        
        Args:
            **kwargs:
                - reference_state: another CognitiveState to compare
                - similarity_threshold: threshold for declaring similarity
        """
        reference = kwargs.get("reference_state")
        threshold = kwargs.get("similarity_threshold", 0.7)
        
        if not reference or not reference.latent or not state.latent:
            return {
                "facts": ["similarity:no_comparison_possible"],
                "dependencies": ["similarity_check:failed"]
            }
        
        # Cosine similarity computation
        similarity = self._cosine_similarity(state.latent, reference.latent)
        
        facts = [f"similarity_score:{similarity:.3f}"]
        
        if similarity >= threshold:
            facts.append("similarity:high")
            facts.append("pattern:match")
        else:
            facts.append("similarity:low")
            facts.append("pattern:divergence")
        
        return {
            "facts": facts,
            "dependencies": ["similarity_check:completed"]
        }
    
    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        # Pad or truncate to match lengths
        length = min(len(v1), len(v2))
        v1 = v1[:length]
        v2 = v2[:length]
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = sum(a * a for a in v1) ** 0.5
        magnitude2 = sum(b * b for b in v2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
