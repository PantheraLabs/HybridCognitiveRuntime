"""
Unit tests for operators
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.state.cognitive_state import CognitiveState
from src.operators.neural_operator import NeuralOperator, SimilarityOperator
from src.operators.symbolic_operator import SymbolicOperator, LogicOperator
from src.operators.causal_operator import CausalOperator, DependencyOperator


class TestNeuralOperator(unittest.TestCase):
    """Test neural operators"""
    
    def test_pattern_detection(self):
        """Test pattern detection via heuristic analysis (no LLM)"""
        state = CognitiveState()
        state.symbolic.facts = ["edited:fix_bug.py", "task:fixing_bug"]
        
        op = NeuralOperator("test_neural", pattern_size=4)
        result = op.execute(state)
        
        # Should have detected debugging pattern from facts
        self.assertTrue(len(result.symbolic.facts) > 0)
        self.assertIn("pattern_detected:debugging_activity", result.symbolic.facts)
    
    def test_similarity_computation(self):
        """Test cosine similarity between states"""
        state1 = CognitiveState()
        state1.latent = [1.0, 0.0, 1.0]
        
        state2 = CognitiveState()
        state2.latent = [1.0, 0.0, 1.0]
        
        sim_op = SimilarityOperator("sim_op")
        result = sim_op.execute(state1, reference_state=state2, similarity_threshold=0.9)
        
        self.assertIn("similarity:high", result.symbolic.facts)


class TestSymbolicOperator(unittest.TestCase):
    """Test symbolic operators"""
    
    def test_deduction(self):
        """Test deductive reasoning"""
        state = CognitiveState()
        state.symbolic.facts = ["raining"]
        state.symbolic.rules = ["if raining then wet_ground"]
        
        op = SymbolicOperator("deducer")
        result = op.execute(state, operation="deduce")
        
        self.assertIn("wet_ground", result.symbolic.facts)
    
    def test_constraint_validation(self):
        """Test constraint checking"""
        state = CognitiveState()
        state.symbolic.facts = ["data_loaded"]
        
        op = SymbolicOperator("constrainer")
        result = op.execute(state, operation="constrain", new_constraints=["must_have:data_loaded"])
        
        self.assertIn("validation:passed", result.symbolic.facts)
    
    def test_logic_and(self):
        """Test logical AND operation"""
        state = CognitiveState()
        state.symbolic.facts = ["A", "B"]
        
        op = LogicOperator("logic_op")
        result = op.execute(state, logic_op="AND", operands=["A", "B"])
        
        self.assertIn("conjunction:A,B", result.symbolic.facts)


class TestCausalOperator(unittest.TestCase):
    """Test causal operators"""
    
    def test_effect_prediction(self):
        """Test predicting effects from causes"""
        state = CognitiveState()
        state.symbolic.facts = ["cause_A"]
        state.causal.dependencies = ["cause_A -> effect_B"]
        
        op = CausalOperator("causal_op")
        result = op.execute(state, operation="predict")
        
        self.assertIn("effect_B", result.causal.effects)
    
    def test_causal_explanation(self):
        """Test explaining causes of effects"""
        state = CognitiveState()
        state.causal.dependencies = ["cause_X -> effect_Y"]
        
        op = CausalOperator("causal_op")
        result = op.execute(state, operation="explain", target_effect="effect_Y")
        
        self.assertIn("cause_X", result.causal.dependencies)


if __name__ == "__main__":
    unittest.main()
