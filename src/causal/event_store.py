"""
Temporal Event Store

An immutable append-only event log that tracks all cognitive and file state changes.
Provides the foundation for time-travel and temporal reasoning.
"""

import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

@dataclass
class CausalEvent:
    event_id: str
    timestamp: str
    event_type: str  # e.g., 'file_modified', 'rule_added', 'test_failed'
    source: str      # file path, command, etc.
    details: Dict[str, Any]
    parent_event_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalEvent':
        return cls(**data)

class EventStore:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.log_file = self.storage_path / "causal_events.jsonl"
        self.events: List[CausalEvent] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        with self._lock:
            if not self.log_file.exists():
                return

            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.events.append(CausalEvent.from_dict(data))

    def append(self, event: CausalEvent):
        """Append a new event to the immutable log."""
        with self._lock:
            self.events.append(event)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def get_events_for_source(self, source: str) -> List[CausalEvent]:
        """Retrieve all events related to a specific source (e.g., file)."""
        return [e for e in self.events if e.source == source]

    def get_recent_events(self, limit: int = 50) -> List[CausalEvent]:
        """Get the most recent events."""
        return self.events[-limit:]
