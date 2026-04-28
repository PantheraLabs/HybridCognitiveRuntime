import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.symbolic.friction_detector import FrictionDetector, FrictionEvent
from src.symbolic.profile_manager import ProfileManager


def test_friction_detector_analysis_and_warnings():
    detector = FrictionDetector()

    assert detector.analyze_terminal_output("all good", 0) is None

    event = detector.analyze_terminal_output("Traceback: error occurred", 1)
    assert event is not None
    assert event.type == "error"
    assert event.severity > 0.5

    detector.record_event(event)
    detector.record_event(FrictionEvent(
        type="error",
        source="terminal",
        message="critical failure",
        timestamp=datetime.now(),
        severity=0.9,
    ))

    warnings = detector.analyze_friction()
    assert any("Detected" in warning for warning in warnings)
    assert any("Critical friction" in warning for warning in warnings)


def test_profile_manager_record_and_context(tmp_path):
    profile_path = tmp_path / "profile.json"
    manager = ProfileManager(str(profile_path))

    manager.record_session(100)
    assert manager.profile.average_session_length == 100

    manager.record_session(50)
    assert round(manager.profile.average_session_length, 2) == 85.0

    manager.profile.primary_ide = "VS Code"
    manager.profile.most_edited_file_types = ["py", "md"]
    manager.save_profile()

    reloaded = ProfileManager(str(profile_path))
    rules = reloaded.get_context_injection()
    assert any("VS Code" in rule for rule in rules)
    assert any("py" in rule for rule in rules)
