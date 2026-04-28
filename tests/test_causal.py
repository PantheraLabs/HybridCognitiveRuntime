import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.causal.ast_extractor import extract_dependencies
from src.causal.dependency_graph import DependencyGraph
from src.causal.event_store import EventStore, CausalEvent
from src.causal.impact_analyzer import ImpactAnalyzer
from src.causal.metrics import MetricsAnalyzer
from src.causal.workflow_predictor import WorkflowPredictor


def test_extract_dependencies(tmp_path):
    file_path = tmp_path / "sample.py"
    file_path.write_text("import os\nfrom math import sqrt\n\nsqrt(4)\nos.path.join('a', 'b')\n")

    deps = extract_dependencies(file_path)

    assert "os" in deps["imports"]
    assert "math" in deps["imports"]
    assert "sqrt" in deps["calls"]
    assert "join" in deps["calls"]


def test_dependency_graph_update_and_metrics(tmp_path):
    graph = DependencyGraph()
    graph.add_dependency("a.py", "b.py")
    graph.add_dependency("a.py", "c.py")

    graph.update_file_dependencies("a.py", ["d.py"])

    assert graph.get_dependencies("a.py") == ["d.py"]
    assert "a.py" not in graph.get_dependents("b.py")

    temp_file = tmp_path / "module.py"
    temp_file.write_text("def foo():\n    return 1\n")
    graph.add_dependency(str(temp_file), "other.py")

    metrics = graph.get_metrics(str(temp_file))
    assert 0.0 <= metrics["fragility"] <= 1.0
    assert 0.0 <= metrics["centrality"] <= 1.0
    assert 0.0 <= metrics["risk_score"] <= 1.0

    graph.add_latent_link("x.py", "y.py", link_type="config", reason="env")
    graph_dict = graph.to_dict()
    assert graph_dict["latent_links"]


def test_metrics_analyzer_defaults(tmp_path):
    assert MetricsAnalyzer.calculate_fragility("missing.py") == 0.5
    assert MetricsAnalyzer.calculate_centrality("missing.py", {}, {}) == 0.0


def test_impact_analyzer_predict():
    graph = DependencyGraph()
    graph.add_dependency("b.py", "a.py")
    graph.add_dependency("c.py", "b.py")

    analyzer = ImpactAnalyzer(graph)
    impacted = analyzer.predict_impact("a.py")

    assert set(impacted) == {"b.py", "c.py"}
    impacted_shallow = analyzer.predict_impact("a.py", max_depth=1)
    assert set(impacted_shallow) == {"b.py"}


def test_event_store_append_and_reload(tmp_path):
    store_path = tmp_path / "events"
    store = EventStore(str(store_path))

    event = CausalEvent(
        event_id="1",
        timestamp=datetime.now().isoformat(),
        event_type="file_edit",
        source="src/app.py",
        details={"path": "src/app.py"}
    )
    store.append(event)

    assert store.get_events_for_source("src/app.py")

    reloaded = EventStore(str(store_path))
    assert len(reloaded.events) == 1
    assert reloaded.get_recent_events(limit=1)[0].source == "src/app.py"


def test_workflow_predictor_probabilities(tmp_path):
    store = EventStore(str(tmp_path))
    events = [
        ("a.py", "file_edit"),
        ("a.py", "file_edit"),
        ("b.py", "file_edit"),
        ("c.py", "file_edit"),
        ("b.py", "file_edit"),
    ]
    for idx, (source, event_type) in enumerate(events):
        store.append(CausalEvent(
            event_id=str(idx),
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            source=source,
            details={}
        ))

    predictor = WorkflowPredictor(store)

    assert predictor.predict_next_files("a.py") == [("b.py", 1.0)]
    assert predictor.predict_next_files("b.py") == [("c.py", 1.0)]
    assert predictor.predict_next_files("missing.py") == []
