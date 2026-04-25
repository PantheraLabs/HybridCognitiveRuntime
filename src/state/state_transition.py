"""
State Transition Logic

ΔS: The state transition function that transforms S_current to S_next.
S_next = ΔS(S_current, operation_result)
"""

from typing import Callable, Dict, Any, Optional
from datetime import datetime
from .cognitive_state import CognitiveState


class StateTransition:
    """
    Handles state transitions by applying operations to the current state.
    
    S_next = ΔS(S_current, HCO_sequence)
    """
    
    @staticmethod
    def apply(
        current_state: CognitiveState,
        operation_result: Dict[str, Any],
        confidence: float = 0.5
    ) -> CognitiveState:
        """
        Apply an operation result to the current state, producing a new state.
        
        Args:
            current_state: The current cognitive state
            operation_result: The result of applying an HCO
            confidence: Confidence level for this transition
            
        Returns:
            A new cognitive state with the transition applied
        """
        # Create a copy to avoid mutation
        new_state = current_state.copy()
        
        # Update latent state if provided
        if "latent" in operation_result:
            new_state.latent = operation_result["latent"]
        
        # Update symbolic state
        if "facts" in operation_result:
            new_state.symbolic.facts.extend(operation_result["facts"])
        if "rules" in operation_result:
            new_state.symbolic.rules.extend(operation_result["rules"])
        if "constraints" in operation_result:
            new_state.symbolic.constraints.extend(operation_result["constraints"])
        
        # Update causal state
        if "dependencies" in operation_result:
            new_state.causal.dependencies.extend(operation_result["dependencies"])
        if "effects" in operation_result:
            new_state.causal.effects.extend(operation_result["effects"])
        
        # Update meta state
        new_state.meta.confidence = confidence
        new_state.meta.uncertainty = 1.0 - confidence
        new_state.meta.timestamp = datetime.now()
        
        return new_state
    
    @staticmethod
    def merge_states(
        state1: CognitiveState,
        state2: CognitiveState,
        weights: tuple = (0.5, 0.5)
    ) -> CognitiveState:
        """
        Merge two cognitive states with given weights.
        
        Args:
            state1: First cognitive state
            state2: Second cognitive state
            weights: Tuple of (weight1, weight2) for merging
            
        Returns:
            A merged cognitive state
        """
        w1, w2 = weights
        
        merged = CognitiveState()
        
        # Merge latent state (weighted average)
        if state1.latent and state2.latent and len(state1.latent) == len(state2.latent):
            merged.latent = [
                w1 * a + w2 * b 
                for a, b in zip(state1.latent, state2.latent)
            ]
        elif state1.latent:
            merged.latent = state1.latent.copy()
        elif state2.latent:
            merged.latent = state2.latent.copy()
        
        # Merge symbolic state (union)
        merged.symbolic.facts = list(set(state1.symbolic.facts + state2.symbolic.facts))
        merged.symbolic.rules = list(set(state1.symbolic.rules + state2.symbolic.rules))
        merged.symbolic.constraints = list(set(
            state1.symbolic.constraints + state2.symbolic.constraints
        ))
        
        # Merge causal state (union)
        merged.causal.dependencies = list(set(
            state1.causal.dependencies + state2.causal.dependencies
        ))
        merged.causal.effects = list(set(
            state1.causal.effects + state2.causal.effects
        ))
        
        # Merge meta state (weighted average)
        merged.meta.confidence = w1 * state1.meta.confidence + w2 * state2.meta.confidence
        merged.meta.uncertainty = w1 * state1.meta.uncertainty + w2 * state2.meta.uncertainty
        merged.meta.timestamp = datetime.now()
        
        return merged
