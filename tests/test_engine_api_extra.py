import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine_api import HCREngine, EngineEvent
from src.state.cognitive_state import CognitiveState


def _make_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    project_path = tmp_path / "project"
    project_path.mkdir()
    return HCREngine(str(project_path))


def test_deduplicate_facts_removes_noise(monkeypatch, tmp_path):
    engine = _make_engine(tmp_path, monkeypatch)
    facts = [
        "observation:mcp_tool:foo",
        "pattern:checking_state",
        "fact1",
        "fact1",
        "fact2",
    ]

    deduped = engine._deduplicate_facts(facts, max_facts=10)

    assert "observation:mcp_tool:foo" not in deduped
    assert "pattern:checking_state" not in deduped
    assert deduped == ["fact1", "fact2"]


def test_heuristic_inference_helpers(monkeypatch, tmp_path):
    engine = _make_engine(tmp_path, monkeypatch)
    engine._current_state = CognitiveState()
    engine._current_state.symbolic.facts = [
        "edited:alpha.py",
        "commit:add feature",
        "test:pytest",
        "edited:beta.py",
        "edited:gamma.py",
        "edited:delta.py",
        "task:fixing_bug",
    ]
    engine._current_state.causal.effects = ["predicted:Run unit tests"]

    expected_task = "fixing_bug".replace("_", " ")
    expected_progress = min(90, 50 + 20 + 10 + 10)
    assert engine._extract_task() == expected_task
    assert engine._calculate_progress() == expected_progress
    assert engine._extract_next_action() == "Run unit tests"


def test_state_save_load_clear(monkeypatch, tmp_path):
    engine = _make_engine(tmp_path, monkeypatch)
    engine._current_state = CognitiveState()
    engine._current_state.symbolic.facts = ["fact:one"]

    assert engine.save_state() is True
    assert engine.state_exists() is True

    reloaded = HCREngine(str(engine.project_path))
    assert reloaded.load_state() is not None

    assert reloaded.clear_state() is True
    assert reloaded.state_exists() is False


def test_update_from_environment_file_edit(monkeypatch, tmp_path):
    engine = _make_engine(tmp_path, monkeypatch)
    file_path = engine.project_path / "sample.py"
    file_path.write_text("import os\nos.path.join('a', 'b')\n")

    event = EngineEvent(
        event_type="file_edit",
        timestamp=datetime.now(),
        data={"path": "sample.py"}
    )

    state = engine.update_from_environment(event)

    assert "edited:sample.py" in state.symbolic.facts
    dependencies = engine.dependency_graph.get_dependencies("sample.py")
    assert "os" in dependencies
