"""
Policy Selector (Π)

Chooses which operator to apply based on:
- Uncertainty
- Constraint violations
- Goal state
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState


class SelectionCriteria(Enum):
    """Criteria for operator selection"""
    UNCERTAINTY_HIGH = "uncertainty_high"      # Neural operator preferred
    CONSTRAINT_VIOLATION = "constraint_violation"  # Symbolic operator preferred
    CAUSAL_CHAIN = "causal_chain"              # Causal operator preferred
    UNCERTAINTY_LOW = "uncertainty_low"        # Symbolic operator preferred
    BALANCED = "balanced"                      # Choose based on success rate


@dataclass
class OperatorScore:
    """Score for an operator based on selection criteria"""
    operator: BaseOperator
    score: float
    reason: str


class PolicySelector:
    """
    Policy selector that chooses the best operator given the current state.
    
    Π(S) → operator
    """
    
    def __init__(
        self,
        selector_id: str = "default",
        selection_strategy: Optional[Callable] = None
    ):
        self.selector_id = selector_id
        self.selection_strategy = selection_strategy or self._default_strategy
        self.selection_history: List[Dict[str, Any]] = []
    
    def select(
        self,
        state: CognitiveState,
        available_operators: List[BaseOperator],
        goal_state: Optional[CognitiveState] = None,
        **kwargs
    ) -> Optional[BaseOperator]:
        """
        Select the best operator for the current state.
        
        Args:
            state: Current cognitive state
            available_operators: List of operators to choose from
            goal_state: Optional goal state to work toward
            **kwargs: Additional selection parameters
            
        Returns:
            Selected operator or None if no suitable operator found
        """
        if not available_operators:
            return None
        
        # Determine selection criteria based on state
        criteria = self._determine_criteria(state, goal_state)
        
        # Score all operators
        scored_operators = []
        for op in available_operators:
            score = self._score_operator(op, state, criteria, goal_state)
            scored_operators.append(OperatorScore(op, score, criteria.value))
        
        # Select best operator
        best = max(scored_operators, key=lambda x: x.score)
        
        # Record selection
        self.selection_history.append({
            "criteria": criteria.value,
            "selected_operator": best.operator.operator_id,
            "score": best.score,
            "state_confidence": state.meta.confidence,
            "state_uncertainty": state.meta.uncertainty
        })
        
        return best.operator
    
    def _determine_criteria(
        self,
        state: CognitiveState,
        goal_state: Optional[CognitiveState]
    ) -> SelectionCriteria:
        """Determine selection criteria based on state characteristics"""
        
        # High uncertainty → Neural operator
        if state.meta.uncertainty > 0.7:
            return SelectionCriteria.UNCERTAINTY_HIGH
        
        # Check for constraint violations
        constraint_violations = [
            f for f in state.symbolic.facts if f.startswith("violation:")
        ]
        if constraint_violations:
            return SelectionCriteria.CONSTRAINT_VIOLATION
        
        # Check for causal chain opportunities
        if state.causal.dependencies:
            return SelectionCriteria.CAUSAL_CHAIN
        
        # Low uncertainty → Symbolic reasoning
        if state.meta.uncertainty < 0.3:
            return SelectionCriteria.UNCERTAINTY_LOW
        
        return SelectionCriteria.BALANCED
    
    def _score_operator(
        self,
        operator: BaseOperator,
        state: CognitiveState,
        criteria: SelectionCriteria,
        goal_state: Optional[CognitiveState]
    ) -> float:
        """Score an operator based on selection criteria"""
        
        base_score = 0.5
        
        # Adjust based on operator type and criteria
        if criteria == SelectionCriteria.UNCERTAINTY_HIGH:
            if operator.operator_type == OperatorType.NEURAL:
                base_score += 0.3
            else:
                base_score -= 0.1
        
        elif criteria == SelectionCriteria.CONSTRAINT_VIOLATION:
            if operator.operator_type == OperatorType.SYMBOLIC:
                base_score += 0.3
            else:
                base_score -= 0.1
        
        elif criteria == SelectionCriteria.CAUSAL_CHAIN:
            if operator.operator_type == OperatorType.CAUSAL:
                base_score += 0.3
            else:
                base_score -= 0.1
        
        elif criteria == SelectionCriteria.UNCERTAINTY_LOW:
            if operator.operator_type == OperatorType.SYMBOLIC:
                base_score += 0.3
            else:
                base_score -= 0.1
        
        # Factor in historical success rate
        base_score += operator.success_rate * 0.2
        
        return min(1.0, max(0.0, base_score))
    
    def _default_strategy(
        self,
        state: CognitiveState,
        operators: List[BaseOperator],
        goal: Optional[CognitiveState]
    ) -> BaseOperator:
        """Default selection strategy - picks first available"""
        return operators[0] if operators else None
    
    def get_selection_stats(self) -> Dict[str, Any]:
        """Get statistics about selection history"""
        if not self.selection_history:
            return {"total_selections": 0}
        
        type_counts = {}
        for entry in self.selection_history:
            op_id = entry["selected_operator"]
            type_counts[op_id] = type_counts.get(op_id, 0) + 1
        
        return {
            "total_selections": len(self.selection_history),
            "operator_distribution": type_counts,
            "avg_confidence": sum(e["state_confidence"] for e in self.selection_history) / len(self.selection_history),
            "avg_uncertainty": sum(e["state_uncertainty"] for e in self.selection_history) / len(self.selection_history)
        }


class AdaptivePolicySelector(PolicySelector):
    """
    Adaptive policy selector that learns from selection outcomes.
    """
    
    def __init__(self, selector_id: str = "adaptive"):
        super().__init__(selector_id)
        self.operator_rewards: Dict[str, float] = {}
        self.learning_rate = 0.1
    
    def update_from_feedback(
        self,
        operator_id: str,
        success: bool,
        reward: float = 1.0
    ):
        """Update operator rewards based on feedback"""
        current_reward = self.operator_rewards.get(operator_id, 0.5)
        
        if success:
            new_reward = current_reward + self.learning_rate * reward
        else:
            new_reward = current_reward - self.learning_rate * reward
        
        self.operator_rewards[operator_id] = min(1.0, max(0.0, new_reward))
    
    def _score_operator(
        self,
        operator: BaseOperator,
        state: CognitiveState,
        criteria: SelectionCriteria,
        goal_state: Optional[CognitiveState]
    ) -> float:
        """Score with learned rewards"""
        base_score = super()._score_operator(operator, state, criteria, goal_state)
        
        # Add learned reward factor
        learned_reward = self.operator_rewards.get(operator.operator_id, 0.5)
        
        return (base_score + learned_reward) / 2
