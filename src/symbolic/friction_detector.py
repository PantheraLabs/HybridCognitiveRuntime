"""
Friction Detector - Part of the Cognitive Twin

Detects when developer workflow hits friction (errors, blockers).
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FrictionEvent:
    """A detected friction point in the workflow"""
    type: str  # 'error', 'blocker', 'timeout', 'unknown'
    source: str  # Where it came from (terminal, git, etc.)
    message: str
    timestamp: datetime
    severity: float  # 0.0 to 1.0


class FrictionDetector:
    """Detects friction in developer workflow"""
    
    def __init__(self):
        self.events: List[FrictionEvent] = []
        self.error_patterns = [
            "error", "failed", "exception", "traceback",
            "WinError", "ConnectionAborted", "BrokenPipe",
            "timeout", "refused"
        ]
    
    def analyze_terminal_output(self, output: str, exit_code: int) -> Optional[FrictionEvent]:
        """Analyze terminal output for friction"""
        if exit_code == 0 and not any(p in output.lower() for p in self.error_patterns):
            return None
        
        # Determine severity
        severity = 0.5
        if exit_code != 0:
            severity += 0.3
        if "WinError" in output or "Error" in output:
            severity += 0.2
        
        return FrictionEvent(
            type='error' if exit_code != 0 else 'warning',
            source='terminal',
            message=output[:200],  # Truncate
            timestamp=datetime.now(),
            severity=min(severity, 1.0)
        )
    
    def get_recent_friction(self, minutes: int = 30) -> List[FrictionEvent]:
        """Get friction events from last N minutes"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp > cutoff]
    
    def record_event(self, event: FrictionEvent):
        """Record a friction event"""
        self.events.append(event)
        # Keep only last 100 events
        if len(self.events) > 100:
            self.events = self.events[-100:]

    def analyze_friction(self) -> List[str]:
        """Analyze current friction state and return warnings"""
        recent = self.get_recent_friction(60)  # Last hour
        warnings = []
        
        if not recent:
            return []
            
        # Group by type
        errors = [e for e in recent if e.type == 'error']
        if errors:
            warnings.append(f"Detected {len(errors)} errors in recent activity")
            
        # Check for high severity
        high_severity = [e for e in recent if e.severity > 0.8]
        if high_severity:
            warnings.append(f"Critical friction detected: {high_severity[-1].message}")
            
        return warnings
