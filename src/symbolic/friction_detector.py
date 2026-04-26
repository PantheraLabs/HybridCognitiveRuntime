from typing import List, Optional
from ..causal.event_store import EventStore

class FrictionDetector:
    """
    Detects user friction (e.g. repeated terminal failures, rapid reverts)
    to prevent the AI from repeating the same mistakes in a loop.
    """
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.friction_warnings: List[str] = []

    def analyze_friction(self) -> List[str]:
        """
        Analyze recent events for friction patterns.
        Returns a list of warning strings to be injected into the MCP context.
        """
        self.friction_warnings.clear()
        self._check_terminal_loops()
        return self.friction_warnings

    def _check_terminal_loops(self):
        """Detect if the last few terminal commands failed repeatedly."""
        terminal_events = [e for e in self.event_store.events if e.event_type == "terminal"]
        
        if len(terminal_events) < 2:
            return
            
        # Look at the last 3 terminal events
        recent_terminals = terminal_events[-3:]
        
        # A simple heuristic: if the details contain common error keywords
        # and the command is the same or similar, we have a loop.
        error_keywords = ["error", "exception", "failed", "traceback", "fatal"]
        
        failed_count = 0
        last_failed_cmd = None
        
        for event in recent_terminals:
            # Check if details indicate an error
            details_lower = str(event.details).lower()
            if any(kw in details_lower for kw in error_keywords):
                failed_count += 1
                last_failed_cmd = event.source
        
        if failed_count >= 2:
            self.friction_warnings.append(
                f"[FRICTION DETECTED] The command '{last_failed_cmd}' has failed {failed_count} times recently. "
                f"Do NOT attempt to run this exact command again without changing the approach."
            )
