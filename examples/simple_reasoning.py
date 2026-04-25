"""
Simple Reasoning Example

Demonstrates the HCR system with a simple reasoning task:
Given some facts and rules, deduce conclusions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state.cognitive_state import CognitiveState
from src.operators.neural_operator import NeuralOperator
from src.operators.symbolic_operator import SymbolicOperator, LogicOperator
from src.operators.causal_operator import CausalOperator
from src.core.hco_engine import HCOEngine


def create_initial_state() -> CognitiveState:
    """Create initial state with some facts"""
    state = CognitiveState()
    
    # Add facts
    state.symbolic.facts = [
        "it_is_raining",
        "the_ground_is_wet"
    ]
    
    # Add rules
    state.symbolic.rules = [
        "if it_is_raining then the_ground_is_wet",
        "if the_ground_is_wet then grass_grows",
        "if it_is_raining then take_an_umbrella"
    ]
    
    return state


def create_goal_state() -> CognitiveState:
    """Create goal state with desired conclusions"""
    state = CognitiveState()
    
    # Goal facts we want to deduce
    state.symbolic.facts = [
        "conclusion:grass_grows",
        "conclusion:take_an_umbrella"
    ]
    
    return state


def simple_deduction_example():
    """
    Example: Simple deductive reasoning
    Given facts and rules, deduce new conclusions.
    """
    print("=" * 60)
    print("EXAMPLE 1: Simple Deductive Reasoning")
    print("=" * 60)
    
    # Create initial state
    initial_state = create_initial_state()
    
    print("\nInitial State:")
    print(f"  Facts: {initial_state.symbolic.facts}")
    print(f"  Rules: {initial_state.symbolic.rules}")
    print(f"  Confidence: {initial_state.meta.confidence}")
    
    # Create symbolic operator for deduction
    deduce_op = SymbolicOperator(
        operator_id="deducer",
        description="Deduces conclusions from facts and rules"
    )
    
    # Execute deduction
    result_state = deduce_op.execute(
        initial_state,
        confidence=0.8,
        operation="deduce"
    )
    
    print("\nAfter Deduction:")
    print(f"  Facts: {result_state.symbolic.facts}")
    print(f"  New Facts: {[f for f in result_state.symbolic.facts if f not in initial_state.symbolic.facts]}")
    print(f"  Confidence: {result_state.meta.confidence}")
    print(f"  Uncertainty: {result_state.meta.uncertainty}")


def causal_reasoning_example():
    """
    Example: Causal reasoning
    Trace cause-effect relationships.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Causal Reasoning")
    print("=" * 60)
    
    # Create state with causal relationships
    state = CognitiveState()
    state.symbolic.facts = ["rain_clouds_form"]
    state.causal.dependencies = [
        "rain_clouds_form -> it_starts_raining",
        "it_starts_raining -> ground_gets_wet",
        "ground_gets_wet -> plants_absorb_water",
        "plants_absorb_water -> plants_grow"
    ]
    
    print("\nInitial State:")
    print(f"  Facts: {state.symbolic.facts}")
    print(f"  Causal Dependencies: {state.causal.dependencies}")
    
    # Create causal operator
    causal_op = CausalOperator(
        operator_id="causal_predictor",
        description="Predicts effects from causes"
    )
    
    # Predict effects
    result = causal_op.execute(
        state,
        confidence=0.9,
        operation="predict"
    )
    
    print("\nAfter Causal Prediction:")
    print(f"  Predicted Effects: {result.causal.effects}")
    print(f"  New Facts: {result.symbolic.facts}")
    
    # Trace causal chain
    trace_result = causal_op.execute(
        result,
        confidence=0.9,
        operation="trace",
        start_cause="rain_clouds_form",
        max_depth=5
    )
    
    print("\nCausal Chain from 'rain_clouds_form':")
    print(f"  Chain: {trace_result.causal.dependencies}")


def hco_engine_example():
    """
    Example: Using the HCO Engine with multiple operators
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: HCO Engine with Operator Sequences")
    print("=" * 60)
    
    # Create engine
    engine = HCOEngine(engine_id="reasoning_engine")
    
    # Register operators
    engine.register_operators([
        SymbolicOperator(operator_id="deducer", description="Deduces from rules"),
        CausalOperator(operator_id="causal_analyzer", description="Analyzes causality"),
        NeuralOperator(operator_id="pattern_recognizer", description="Recognizes patterns")
    ])
    
    # Create initial state
    state = CognitiveState()
    state.symbolic.facts = ["observation:data_available"]
    state.symbolic.rules = [
        "if observation:data_available then process_data",
        "if process_data then generate_insights"
    ]
    state.causal.dependencies = [
        "generate_insights -> make_decisions",
        "make_decisions -> take_action"
    ]
    
    print("\nInitial State:")
    print(f"  Facts: {state.symbolic.facts}")
    
    # Execute sequence of operators
    sequence = ["deducer", "causal_analyzer"]
    
    final_state = engine.execute_sequence(
        initial_state=state,
        operator_sequence=sequence,
        confidence=0.85
    )
    
    print("\nAfter Operator Sequence:")
    print(f"  Facts: {final_state.symbolic.facts}")
    print(f"  Effects: {final_state.causal.effects}")
    print(f"  Confidence: {final_state.meta.confidence}")
    
    # Get execution summary
    summary = engine.get_execution_summary()
    print("\nExecution Summary:")
    print(f"  Total Steps: {summary['total_steps']}")
    print(f"  Operator Distribution: {summary['operator_distribution']}")
    print(f"  Average Confidence: {summary['average_confidence']:.3f}")


def adaptive_reasoning_example():
    """
    Example: Adaptive reasoning with policy selector
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Adaptive Reasoning")
    print("=" * 60)
    
    # Create engine with adaptive policy selector
    from src.operators.policy_selector import AdaptivePolicySelector
    
    selector = AdaptivePolicySelector(selector_id="adaptive_selector")
    engine = HCOEngine(
        engine_id="adaptive_engine",
        policy_selector=selector,
        max_iterations=10
    )
    
    # Register operators
    engine.register_operators([
        SymbolicOperator(operator_id="symbolic_reasoner", description="Symbolic reasoning"),
        NeuralOperator(operator_id="neural_processor", description="Neural processing"),
        CausalOperator(operator_id="causal_reasoner", description="Causal reasoning")
    ])
    
    # Create state with uncertainty (will trigger neural operator)
    state = CognitiveState()
    state.meta.uncertainty = 0.8  # High uncertainty
    state.symbolic.facts = ["ambiguous_input"]
    
    print("\nInitial State (High Uncertainty):")
    print(f"  Uncertainty: {state.meta.uncertainty}")
    print(f"  Facts: {state.symbolic.facts}")
    
    # Execute adaptive reasoning
    final_state = engine.execute_reasoning(
        initial_state=state,
        max_iterations=3
    )
    
    print("\nAfter Adaptive Reasoning:")
    print(f"  Facts: {final_state.symbolic.facts}")
    print(f"  Confidence: {final_state.meta.confidence}")
    print(f"  Uncertainty: {final_state.meta.uncertainty}")
    
    # Show selection stats
    stats = selector.get_selection_stats()
    print("\nPolicy Selection Stats:")
    print(f"  Total Selections: {stats['total_selections']}")
    print(f"  Operator Distribution: {stats.get('operator_distribution', {})}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  HYBRID COGNITIVE RUNTIME - REASONING EXAMPLES")
    print("=" * 70)
    
    simple_deduction_example()
    causal_reasoning_example()
    hco_engine_example()
    adaptive_reasoning_example()
    
    print("\n" + "=" * 70)
    print("  EXAMPLES COMPLETED")
    print("=" * 70)
