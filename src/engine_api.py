"""
HCR Engine API

Clean interface for all HCR operations.
Both CLI and IDE call these methods directly.
NO subprocess, NO shell execution.
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .state.cognitive_state import CognitiveState
from .core.hco_engine import HCOEngine
from .operators.base_operator import BaseOperator


@dataclass
class EngineContext:
    """Context returned by engine for UI display"""
    current_task: str
    progress_percent: int
    next_action: str
    confidence: float
    gap_minutes: Optional[float]
    facts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass  
class EngineEvent:
    """Event that triggers state update"""
    event_type: str  # 'file_edit', 'window_focus', 'git_commit', 'terminal', 'manual'
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class HCREngine:
    """
    Primary HCR Engine API.
    
    All interfaces (CLI, IDE, etc.) call these methods directly.
    NO subprocess, NO shell execution at this layer.
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.hcr_dir = self.project_path / ".hcr"
        self.state_file = self.hcr_dir / "session_state.json"
        
        # Initialize HCO engine
        self.hco_engine = HCOEngine(engine_id="hcr_core")
        self._register_default_operators()
        
        # Current state
        self._current_state: Optional[CognitiveState] = None
        self._last_saved: Optional[datetime] = None
    
    def _register_default_operators(self):
        """Register default HCOs for dev context"""
        from .operators.symbolic_operator import SymbolicOperator
        from .operators.neural_operator import NeuralOperator
        from .operators.causal_operator import CausalOperator
        
        self.hco_engine.register_operators([
            SymbolicOperator("context_ingest", description="Ingest context into state"),
            NeuralOperator("intent_inference", pattern_size=64, description="Infer intent"),
            CausalOperator("action_suggester", description="Suggest next actions")
        ])
    
    def load_state(self) -> Optional[CognitiveState]:
        """
        Load cognitive state from disk.
        Returns None if no state exists.
        """
        try:
            if not self.state_file.exists():
                return None
            
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            # Parse cognitive state
            if "cognitive_state" in data:
                self._current_state = CognitiveState.from_dict(data["cognitive_state"])
            else:
                # Legacy: reconstruct from analysis
                self._current_state = self._reconstruct_state_from_legacy(data)
            
            self._last_saved = datetime.fromisoformat(data.get("saved_at", datetime.now().isoformat()))
            return self._current_state
            
        except Exception as e:
            print(f"[HCR Engine] Error loading state: {e}")
            return None
    
    def save_state(self) -> bool:
        """Save current cognitive state to disk"""
        try:
            self.hcr_dir.mkdir(exist_ok=True)
            
            data = {
                "saved_at": datetime.now().isoformat(),
                "project_path": str(self.project_path),
                "cognitive_state": self._current_state.to_dict() if self._current_state else {}
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"[HCR Engine] Error saving state: {e}")
            return False
    
    def update_from_environment(self, event: EngineEvent) -> CognitiveState:
        """
        Update state based on environment event.
        
        Args:
            event: What happened (file edit, focus change, etc.)
            
        Returns:
            Updated cognitive state
        """
        # Ensure we have a base state
        if not self._current_state:
            self._current_state = CognitiveState()
        
        # Update state based on event type
        if event.event_type == "file_edit":
            self._handle_file_edit(event.data)
        elif event.event_type == "window_focus":
            self._handle_window_focus(event.data)
        elif event.event_type == "git_commit":
            self._handle_git_commit(event.data)
        elif event.event_type == "terminal":
            self._handle_terminal(event.data)
        
        # Run HCO analysis if significant event
        if event.event_type in ["window_focus", "git_commit"]:
            self._run_analysis()
        
        # Save updated state
        self.save_state()
        
        return self._current_state
    
    def _handle_file_edit(self, data: Dict[str, Any]):
        """Process file edit event"""
        file_path = data.get("path", "")
        
        # Add to facts
        fact = f"edited:{file_path}"
        if fact not in self._current_state.symbolic.facts:
            self._current_state.symbolic.facts.append(fact)
        
        # Add causal dependency
        dep = f"edited:{file_path} -> file_in_focus"
        if dep not in self._current_state.causal.dependencies:
            self._current_state.causal.dependencies.append(dep)
    
    def _handle_window_focus(self, data: Dict[str, Any]):
        """Process window focus event"""
        gap_minutes = data.get("gap_minutes", 0)
        
        # Update uncertainty based on gap
        if gap_minutes > 60:
            self._current_state.meta.uncertainty = 0.7
        elif gap_minutes > 30:
            self._current_state.meta.uncertainty = 0.5
        else:
            self._current_state.meta.uncertainty = 0.2
        
        self._current_state.meta.confidence = 1.0 - self._current_state.meta.uncertainty
        self._current_state.meta.timestamp = datetime.now()
    
    def _handle_git_commit(self, data: Dict[str, Any]):
        """Process git commit event"""
        commit_msg = data.get("message", "")
        
        # Add commit fact
        fact = f"commit:{commit_msg[:50]}"
        if fact not in self._current_state.symbolic.facts:
            self._current_state.symbolic.facts.append(fact)
        
        # Infer task from commit
        if any(k in commit_msg.lower() for k in ["implement", "add", "create"]):
            self._current_state.symbolic.facts.append("task:implementing_feature")
        elif any(k in commit_msg.lower() for k in ["fix", "bug", "resolve"]):
            self._current_state.symbolic.facts.append("task:fixing_bug")
        elif any(k in commit_msg.lower() for k in ["test", "spec"]):
            self._current_state.symbolic.facts.append("task:writing_tests")
    
    def _handle_terminal(self, data: Dict[str, Any]):
        """Process terminal command event"""
        command = data.get("command", "")
        success = data.get("success", True)
        
        # Track commands
        fact = f"cmd:{command}"
        if fact not in self._current_state.symbolic.facts:
            self._current_state.symbolic.facts.append(fact)
        
        if not success:
            self._current_state.symbolic.facts.append(f"error:{command}")
    
    def _run_analysis(self):
        """Run HCO analysis on current state"""
        # Run context ingestion
        sequence = ["context_ingest", "intent_inference", "action_suggester"]
        
        self._current_state = self.hco_engine.execute_sequence(
            initial_state=self._current_state,
            operator_sequence=sequence,
            confidence=0.75
        )
    
    def infer_context(self) -> EngineContext:
        """
        Infer current context from state.
        
        Returns:
            Context object for UI display
        """
        if not self._current_state:
            self.load_state()
        
        if not self._current_state:
            # No state exists
            return EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Start tracking this project",
                confidence=0.0,
                gap_minutes=None,
                facts=[]
            )
        
        # Extract task from facts
        task = self._extract_task()
        
        # Calculate progress
        progress = self._calculate_progress()
        
        # Get next action
        next_action = self._extract_next_action()
        
        # Calculate gap
        gap = None
        if self._last_saved:
            gap = (datetime.now() - self._last_saved).total_seconds() / 60
        
        # Get relevant facts
        facts = self._current_state.symbolic.facts[:10]
        
        return EngineContext(
            current_task=task,
            progress_percent=progress,
            next_action=next_action,
            confidence=self._current_state.meta.confidence,
            gap_minutes=gap,
            facts=facts
        )
    
    def _extract_task(self) -> str:
        """Extract current task from state facts"""
        for fact in self._current_state.symbolic.facts:
            if "task:" in fact:
                return fact.replace("task:", "").replace("_", " ")
            if "commit:" in fact:
                return f"Working on: {fact.replace('commit:', '')}"
            if "edited:" in fact:
                # Extract filename
                path = fact.replace("edited:", "")
                return f"Editing: {Path(path).name}"
        
        return "Unknown task"
    
    def _calculate_progress(self) -> int:
        """Calculate progress percentage"""
        score = 50
        
        facts = self._current_state.symbolic.facts
        
        # Check for completion indicators
        if any("commit:" in f for f in facts):
            score += 10
        if any("test" in f.lower() for f in facts):
            score += 10
        
        # Check for file activity
        edited_count = sum(1 for f in facts if "edited:" in f)
        if edited_count > 5:
            score += 10
        
        return max(10, min(90, score))
    
    def _extract_next_action(self) -> str:
        """Extract suggested next action"""
        # Check causal effects
        for effect in self._current_state.causal.effects:
            if "predicted:" in effect:
                return effect.replace("predicted:", "")
        
        # Default suggestions based on state
        facts = self._current_state.symbolic.facts
        
        if any("edited:" in f for f in facts) and not any("commit:" in f for f in facts):
            return "Commit your changes"
        
        if any("commit:" in f for f in facts):
            return "Continue with next feature"
        
        return "Continue working"
    
    def get_next_action(self) -> str:
        """Get just the next action recommendation"""
        context = self.infer_context()
        return context.next_action
    
    def state_exists(self) -> bool:
        """Check if state file exists"""
        return self.state_file.exists()
    
    def clear_state(self) -> bool:
        """Clear all state"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            self._current_state = None
            self._last_saved = None
            return True
        except Exception as e:
            print(f"[HCR Engine] Error clearing state: {e}")
            return False
    
    def _reconstruct_state_from_legacy(self, data: Dict[str, Any]) -> CognitiveState:
        """Reconstruct state from legacy format"""
        state = CognitiveState()
        
        # Try to get from analysis
        analysis = data.get("analysis", {})
        
        # Add facts
        for fact in analysis.get("relevant_facts", []):
            state.symbolic.facts.append(fact)
        
        # Add meta
        state.meta.confidence = analysis.get("confidence", 0.5)
        state.meta.uncertainty = analysis.get("uncertainty", 0.5)
        
        return state
