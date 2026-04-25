"""
Base Hybrid Cognitive Operator (HCO)

An HCO is the smallest executable unit of reasoning.

HCO = (S_in, Φ_n, Φ_s, Φ_c, Π, ΔS)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..state.cognitive_state import CognitiveState
from ..state.state_transition import StateTransition


class OperatorType(Enum):
    """Types of cognitive operators"""
    NEURAL = "neural"
    SYMBOLIC = "symbolic"
    CAUSAL = "causal"


class BaseOperator(ABC):
    """
    Base class for all Hybrid Cognitive Operators.
    
    Every HCO must:
    1. Accept an input state (S_in)
    2. Apply its specific operation
    3. Return an output state via state transition (ΔS)
    """
    
    def __init__(
        self,
        operator_id: str,
        operator_type: OperatorType,
        description: str = ""
    ):
        self.operator_id = operator_id
        self.operator_type = operator_type
        self.description = description
        self.created_at = datetime.now()
        self.execution_count = 0
        self.success_count = 0
    
    @abstractmethod
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute the operator's core logic.
        
        Args:
            state: Current cognitive state
            **kwargs: Additional parameters
            
        Returns:
            Operation result dict with keys like:
            - latent: updated latent vector
            - facts: new facts to add
            - rules: new rules to add
            - dependencies: new dependencies
            - effects: new effects
        """
        pass
    
    def execute(
        self,
        state: CognitiveState,
        confidence: float = 0.5,
        **kwargs
    ) -> CognitiveState:
        """
        Execute the operator and apply state transition.
        
        S_next = ΔS(S_current, operation_result)
        
        Args:
            state: Current cognitive state (S_current)
            confidence: Confidence in this operation
            **kwargs: Additional parameters for the operation
            
        Returns:
            New cognitive state (S_next)
        """
        try:
            # Execute the core operation
            operation_result = self._execute(state, **kwargs)
            
            # Apply state transition
            new_state = StateTransition.apply(
                current_state=state,
                operation_result=operation_result,
                confidence=confidence
            )
            
            # Track execution metrics
            self.execution_count += 1
            self.success_count += 1
            
            return new_state
            
        except Exception as e:
            # On failure, return original state with reduced confidence
            self.execution_count += 1
            failed_state = state.copy()
            failed_state.meta.confidence = max(0.0, confidence - 0.3)
            failed_state.meta.uncertainty = 1.0 - failed_state.meta.confidence
            failed_state.meta.timestamp = datetime.now()
            return failed_state
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of this operator"""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize operator metadata"""
        return {
            "operator_id": self.operator_id,
            "operator_type": self.operator_type.value,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate
        }


class CompositeOperator(BaseOperator):
    """
    A composite operator that chains multiple operators.
    
    compose(op1, op2, op3) executes them in sequence
    """
    
    def __init__(
        self,
        operator_id: str,
        operators: List[BaseOperator],
        description: str = ""
    ):
        super().__init__(operator_id, OperatorType.SYMBOLIC, description)
        self.operators = operators
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute all operators in sequence.
        
        Note: This returns the state directly rather than operation_result
        because each sub-operator applies its own transition.
        """
        current_state = state.copy()
        
        for op in self.operators:
            current_state = op.execute(current_state, **kwargs)
        
        # Return the final state as latent update
        return {"final_state": current_state.to_dict()}
    
    def execute(
        self,
        state: CognitiveState,
        confidence: float = 0.5,
        **kwargs
    ) -> CognitiveState:
        """
        Override to handle the composite execution pattern
        """
        current_state = state.copy()
        
        for op in self.operators:
            current_state = op.execute(current_state, confidence=confidence, **kwargs)
        
        self.execution_count += 1
        self.success_count += 1
        
        return current_state
