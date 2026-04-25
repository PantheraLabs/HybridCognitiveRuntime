"""
Unit tests for state management
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.state.cognitive_state import CognitiveState, SymbolicState, CausalState, MetaState
from src.state.state_transition import StateTransition


class TestCognitiveState(unittest.TestCase):
    """Test cognitive state dataclass"""
    
    def test_initialization(self):
        """Test state initializes with default values"""
        state = CognitiveState()
        self.assertEqual(state.latent, [])
        self.assertIsInstance(state.symbolic, SymbolicState)
        self.assertIsInstance(state.causal, CausalState)
        self.assertIsInstance(state.meta, MetaState)
    
    def test_serialization(self):
        """Test state serialization to/from JSON"""
        state = CognitiveState()
        state.symbolic.facts = ["fact1", "fact2"]
        state.symbolic.rules = ["rule1"]
        state.latent = [0.1, 0.2, 0.3]
        
        json_str = state.to_json()
        restored = CognitiveState.from_json(json_str)
        
        self.assertEqual(restored.symbolic.facts, ["fact1", "fact2"])
        self.assertEqual(restored.symbolic.rules, ["rule1"])
        self.assertEqual(restored.latent, [0.1, 0.2, 0.3])
    
    def test_copy(self):
        """Test state deep copy"""
        state = CognitiveState()
        state.symbolic.facts = ["fact1"]
        state.latent = [1.0, 2.0]
        
        copy = state.copy()
        
        # Modify original
        state.symbolic.facts.append("fact2")
        state.latent[0] = 99.0
        
        # Copy should be unchanged
        self.assertEqual(copy.symbolic.facts, ["fact1"])
        self.assertEqual(copy.latent, [1.0, 2.0])


class TestStateTransition(unittest.TestCase):
    """Test state transition logic"""
    
    def test_apply_operation(self):
        """Test applying operation results to state"""
        state = CognitiveState()
        state.symbolic.facts = ["initial"]
        
        operation_result = {
            "facts": ["new_fact"],
            "dependencies": ["dep1"]
        }
        
        new_state = StateTransition.apply(state, operation_result, confidence=0.8)
        
        self.assertIn("initial", new_state.symbolic.facts)
        self.assertIn("new_fact", new_state.symbolic.facts)
        self.assertIn("dep1", new_state.causal.dependencies)
        self.assertEqual(new_state.meta.confidence, 0.8)
    
    def test_merge_states(self):
        """Test merging two states"""
        state1 = CognitiveState()
        state1.symbolic.facts = ["fact1", "fact2"]
        state1.latent = [1.0, 2.0]
        
        state2 = CognitiveState()
        state2.symbolic.facts = ["fact2", "fact3"]
        state2.latent = [3.0, 4.0]
        
        merged = StateTransition.merge_states(state1, state2, weights=(0.5, 0.5))
        
        # Facts should be union
        self.assertIn("fact1", merged.symbolic.facts)
        self.assertIn("fact2", merged.symbolic.facts)
        self.assertIn("fact3", merged.symbolic.facts)
        
        # Latent should be averaged
        self.assertEqual(merged.latent[0], 2.0)
        self.assertEqual(merged.latent[1], 3.0)


if __name__ == "__main__":
    unittest.main()
