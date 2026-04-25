"""
Unit tests for HCO Engine
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.state.cognitive_state import CognitiveState
from src.operators.symbolic_operator import SymbolicOperator
from src.operators.neural_operator import NeuralOperator
from src.operators.causal_operator import CausalOperator
from src.core.hco_engine import HCOEngine


class TestHCOEngine(unittest.TestCase):
    """Test HCO Engine"""
    
    def test_operator_registration(self):
        """Test registering operators"""
        engine = HCOEngine()
        op = SymbolicOperator("test_op")
        
        engine.register_operator(op)
        
        self.assertIn("test_op", engine.operator_registry)
    
    def test_sequence_execution(self):
        """Test executing operator sequence"""
        engine = HCOEngine()
        
        # Register operators
        engine.register_operators([
            SymbolicOperator("deducer", description="Deduces facts"),
            CausalOperator("causal", description="Analyzes causality")
        ])
        
        # Create state
        state = CognitiveState()
        state.symbolic.facts = ["fact_A"]
        state.symbolic.rules = ["if fact_A then fact_B"]
        state.causal.dependencies = ["fact_B -> fact_C"]
        
        # Execute sequence
        result = engine.execute_sequence(state, ["deducer", "causal"], confidence=0.8)
        
        # Check results
        self.assertIn("fact_B", result.symbolic.facts)
        self.assertTrue(len(engine.execution_history) > 0)
    
    def test_execution_summary(self):
        """Test getting execution summary"""
        engine = HCOEngine()
        engine.register_operator(SymbolicOperator("op1"))
        
        state = CognitiveState()
        engine.execute_sequence(state, ["op1"], confidence=0.7)
        
        summary = engine.get_execution_summary()
        
        self.assertEqual(summary["total_steps"], 1)
        self.assertIn("average_confidence", summary)


if __name__ == "__main__":
    unittest.main()
