"""
HCO Engine - Main reasoning engine

Orchestrates the execution of Hybrid Cognitive Operators.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from ..state.cognitive_state import CognitiveState
from ..operators.base_operator import BaseOperator, CompositeOperator
from ..operators.policy_selector import PolicySelector, AdaptivePolicySelector


@dataclass
class ExecutionRecord:
    """Record of a single execution step"""
    step_number: int
    operator_id: str
    operator_type: str
    input_state_hash: str
    output_state_hash: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


class HCOEngine:
    """
    Main reasoning engine for Hybrid Cognitive Runtime.
    
    S_next = ΔS(S_current, HCO_sequence)
    """
    
    def __init__(
        self,
        engine_id: str = "default",
        policy_selector: Optional[PolicySelector] = None,
        max_iterations: int = 100
    ):
        self.engine_id = engine_id
        self.policy_selector = policy_selector or AdaptivePolicySelector()
        self.max_iterations = max_iterations
        
        self.operator_registry: Dict[str, BaseOperator] = {}
        self.execution_history: List[ExecutionRecord] = []
        self.initialized = False
    
    def register_operator(self, operator: BaseOperator) -> 'HCOEngine':
        """Register an operator in the registry"""
        self.operator_registry[operator.operator_id] = operator
        return self
    
    def register_operators(self, operators: List[BaseOperator]) -> 'HCOEngine':
        """Register multiple operators"""
        for op in operators:
            self.register_operator(op)
        return self
    
    def execute_sequence(
        self,
        initial_state: CognitiveState,
        operator_sequence: List[str],
        confidence: float = 0.5,
        **kwargs
    ) -> CognitiveState:
        """
        Execute a predefined sequence of operators.
        
        Args:
            initial_state: Starting cognitive state
            operator_sequence: List of operator IDs to execute in order
            confidence: Base confidence level
            **kwargs: Additional parameters for operators
            
        Returns:
            Final cognitive state after sequence execution
        """
        current_state = initial_state.copy()
        
        for step_num, operator_id in enumerate(operator_sequence):
            operator = self.operator_registry.get(operator_id)
            
            if not operator:
                # Record failure
                self.execution_history.append(ExecutionRecord(
                    step_number=step_num,
                    operator_id=operator_id,
                    operator_type="unknown",
                    input_state_hash=self._state_hash(current_state),
                    output_state_hash="error",
                    confidence=0.0
                ))
                continue
            
            # Execute operator
            input_hash = self._state_hash(current_state)
            current_state = operator.execute(current_state, confidence=confidence, **kwargs)
            output_hash = self._state_hash(current_state)
            
            # Record execution
            self.execution_history.append(ExecutionRecord(
                step_number=step_num,
                operator_id=operator_id,
                operator_type=operator.operator_type.value,
                input_state_hash=input_hash,
                output_state_hash=output_hash,
                confidence=current_state.meta.confidence
            ))
        
        return current_state
    
    def execute_reasoning(
        self,
        initial_state: CognitiveState,
        goal_state: Optional[CognitiveState] = None,
        max_iterations: Optional[int] = None,
        **kwargs
    ) -> CognitiveState:
        """
        Execute adaptive reasoning until goal reached or max iterations.
        
        Policy selector chooses operators dynamically based on state.
        
        Args:
            initial_state: Starting cognitive state
            goal_state: Target cognitive state (optional)
            max_iterations: Override default max iterations
            **kwargs: Additional parameters
            
        Returns:
            Final cognitive state
        """
        current_state = initial_state.copy()
        iterations = 0
        max_iter = max_iterations or self.max_iterations
        
        while iterations < max_iter:
            # Check if goal reached (if goal specified)
            if goal_state and self._goal_reached(current_state, goal_state):
                break
            
            # Select operator
            available_operators = list(self.operator_registry.values())
            selected_op = self.policy_selector.select(
                current_state,
                available_operators,
                goal_state,
                **kwargs
            )
            
            if not selected_op:
                # No suitable operator found
                break
            
            # Execute selected operator
            input_hash = self._state_hash(current_state)
            current_state = selected_op.execute(current_state, **kwargs)
            output_hash = self._state_hash(current_state)
            
            # Record execution
            self.execution_history.append(ExecutionRecord(
                step_number=iterations,
                operator_id=selected_op.operator_id,
                operator_type=selected_op.operator_type.value,
                input_state_hash=input_hash,
                output_state_hash=output_hash,
                confidence=current_state.meta.confidence
            ))
            
            # Update policy selector with feedback
            if isinstance(self.policy_selector, AdaptivePolicySelector):
                success = current_state.meta.confidence > 0.5
                self.policy_selector.update_from_feedback(
                    selected_op.operator_id,
                    success,
                    reward=current_state.meta.confidence
                )
            
            iterations += 1
        
        return current_state
    
    def create_composite(
        self,
        composite_id: str,
        operator_ids: List[str],
        description: str = ""
    ) -> CompositeOperator:
        """
        Create a composite operator from registered operators.
        
        Args:
            composite_id: ID for the new composite operator
            operator_ids: List of operator IDs to compose
            description: Description of the composite
            
        Returns:
            Composite operator (not automatically registered)
        """
        operators = []
        for op_id in operator_ids:
            op = self.operator_registry.get(op_id)
            if op:
                operators.append(op)
        
        return CompositeOperator(composite_id, operators, description)
    
    def _goal_reached(
        self,
        current: CognitiveState,
        goal: CognitiveState
    ) -> bool:
        """Check if current state satisfies goal conditions"""
        # Check if all goal facts are present
        goal_facts = set(goal.symbolic.facts)
        current_facts = set(current.symbolic.facts)
        
        # Simple goal check: all goal facts should be in current facts
        missing_facts = goal_facts - current_facts
        
        return len(missing_facts) == 0
    
    def _state_hash(self, state: CognitiveState) -> str:
        """Generate a simple hash for state identification"""
        # Simple hash based on number of facts and rules
        facts_count = len(state.symbolic.facts)
        rules_count = len(state.symbolic.rules)
        return f"s:{facts_count}:{rules_count}"
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution history"""
        if not self.execution_history:
            return {"total_steps": 0}
        
        operator_counts = {}
        confidence_values = []
        
        for record in self.execution_history:
            op_type = record.operator_type
            operator_counts[op_type] = operator_counts.get(op_type, 0) + 1
            confidence_values.append(record.confidence)
        
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
        
        return {
            "total_steps": len(self.execution_history),
            "operator_distribution": operator_counts,
            "average_confidence": avg_confidence,
            "final_confidence": self.execution_history[-1].confidence if self.execution_history else 0
        }
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
