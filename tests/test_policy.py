import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.operators.causal_operator import CausalOperator
from src.operators.neural_operator import NeuralOperator
from src.operators.symbolic_operator import SymbolicOperator
from src.operators.base_operator import OperatorType
from src.operators.policy_selector import PolicySelector, AdaptivePolicySelector
from src.state.cognitive_state import CognitiveState


def _state_with_uncertainty(value: float) -> CognitiveState:
    state = CognitiveState()
    state.meta.uncertainty = value
    state.meta.confidence = 1.0 - value
    return state


def test_policy_selector_prefers_neural_for_high_uncertainty():
    selector = PolicySelector()
    state = _state_with_uncertainty(0.8)
    ops = [SymbolicOperator("sym"), NeuralOperator("neu"), CausalOperator("causal")]

    selected = selector.select(state, ops)

    assert selected.operator_type == OperatorType.NEURAL


def test_policy_selector_prefers_symbolic_for_constraints():
    selector = PolicySelector()
    state = _state_with_uncertainty(0.5)
    state.symbolic.facts.append("violation:rule")
    ops = [SymbolicOperator("sym"), NeuralOperator("neu"), CausalOperator("causal")]

    selected = selector.select(state, ops)

    assert selected.operator_type == OperatorType.SYMBOLIC


def test_policy_selector_prefers_causal_for_dependencies():
    selector = PolicySelector()
    state = _state_with_uncertainty(0.5)
    state.causal.dependencies.append("a -> b")
    ops = [SymbolicOperator("sym"), NeuralOperator("neu"), CausalOperator("causal")]

    selected = selector.select(state, ops)

    assert selected.operator_type == OperatorType.CAUSAL


def test_policy_selector_prefers_symbolic_for_low_uncertainty():
    selector = PolicySelector()
    state = _state_with_uncertainty(0.1)
    ops = [SymbolicOperator("sym"), NeuralOperator("neu"), CausalOperator("causal")]

    selected = selector.select(state, ops)

    assert selected.operator_type == OperatorType.SYMBOLIC


def test_selection_stats_and_adaptive_rewards():
    selector = AdaptivePolicySelector()
    state = _state_with_uncertainty(0.1)
    ops = [SymbolicOperator("sym"), NeuralOperator("neu")]

    selector.select(state, ops)
    selector.select(state, ops)

    stats = selector.get_selection_stats()
    assert stats["total_selections"] == 2
    assert "sym" in stats["operator_distribution"]

    selector.update_from_feedback("sym", success=True, reward=1.0)
    selector.update_from_feedback("sym", success=False, reward=1.0)
    assert 0.0 <= selector.operator_rewards["sym"] <= 1.0
