import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.operators.base_operator import BaseOperator, CompositeOperator, OperatorType
from src.state.cognitive_state import CognitiveState


class DummyOperator(BaseOperator):
    def __init__(self, operator_id: str, should_fail: bool = False):
        super().__init__(operator_id, OperatorType.SYMBOLIC)
        self.should_fail = should_fail

    def _execute(self, state: CognitiveState, **kwargs):
        if self.should_fail:
            raise ValueError("boom")
        return {"facts": [f"ran:{self.operator_id}"]}


def test_base_operator_success_and_failure():
    state = CognitiveState()

    op = DummyOperator("ok")
    new_state = op.execute(state, confidence=0.8)
    assert "ran:ok" in new_state.symbolic.facts
    assert op.execution_count == 1
    assert op.success_rate == 1.0

    failing = DummyOperator("fail", should_fail=True)
    failed_state = failing.execute(state, confidence=0.5)
    assert failing.execution_count == 1
    assert failing.success_rate == 0.0
    assert failed_state.meta.confidence == 0.2


def test_composite_operator_executes_all():
    state = CognitiveState()
    op1 = DummyOperator("one")
    op2 = DummyOperator("two")

    composite = CompositeOperator("combo", [op1, op2])
    composite_state = composite.execute(state, confidence=0.7)

    assert "ran:one" in composite_state.symbolic.facts
    assert "ran:two" in composite_state.symbolic.facts
    assert composite.execution_count == 1
