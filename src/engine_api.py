"""
HCR Engine API

Clean interface for all HCR operations.
Both CLI and IDE call these methods directly.
NO subprocess, NO shell execution.

Now with LLM-powered context inference and state compression (k2.6).
"""

import gzip
import json
import logging
import os
import tempfile
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .state.cognitive_state import CognitiveState
from .core.hco_engine import HCOEngine
from .operators.base_operator import BaseOperator
from .config import HCRConfig, load_config
from .cache import LLMCache
import uuid
from .causal.event_store import EventStore, CausalEvent
from .causal.dependency_graph import DependencyGraph
from .causal.impact_analyzer import ImpactAnalyzer
from .causal.ast_extractor import extract_dependencies
from .causal.workflow_predictor import WorkflowPredictor
from .symbolic.friction_detector import FrictionDetector
from .symbolic.profile_manager import ProfileManager


# System prompts for engine-level LLM calls
CONTEXT_INFERENCE_PROMPT = """You are a cognitive reasoning engine that analyzes developer workflow state.
Given a set of symbolic facts, causal dependencies, and effects from a developer's session,
produce a concise JSON summary.

Respond ONLY with valid JSON in this exact format:
{
    "current_task": "a clear, human-readable description of what the developer is working on",
    "progress_percent": 65,
    "next_action": "a specific, actionable suggestion for what to do next",
    "confidence": 0.85,
    "reasoning": "brief explanation of why you inferred this"
}

Rules:
- progress_percent must be between 10 and 90
- next_action must be specific and actionable (not generic like "continue working")
- current_task should synthesize all facts into one coherent task description
- If facts mention uncommitted changes, suggest committing
- If facts mention tests, factor that into progress"""


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

    def __init__(self, project_path: str, config: Optional[HCRConfig] = None):
        self.project_path = Path(project_path)
        self.hcr_dir = self.project_path / ".hcr"
        self.state_file = self.hcr_dir / "state.json"
        self.logger = logging.getLogger("HCREngine")

        # Load config
        self.config = config or load_config(project_path)

        # Initialize HCO engine
        self.hco_engine = HCOEngine(engine_id="hcr_core")

        # Initialize LLM provider (lazy — only created when first needed)
        self._llm_provider = None
        self._llm_initialized = False

        # Cache for LLM responses
        self._cache = LLMCache(ttl_seconds=self.config.cache_ttl_seconds)

        # Register operators
        self._register_default_operators()

        # Current state
        self._current_state: Optional[CognitiveState] = None
        self._last_saved: Optional[datetime] = None
        
        # Initialize Causal Graph components (Phase 3 & 5)
        self.event_store = EventStore(str(self.hcr_dir))
        self.dependency_graph = DependencyGraph()
        self.impact_analyzer = ImpactAnalyzer(self.dependency_graph)
        
        self.profile_manager = ProfileManager(str(self.project_path))
        self.friction_detector = FrictionDetector()
        self.workflow_predictor = WorkflowPredictor(self.event_store)
        # NOTE: Event replay is deferred to first load_state() call to avoid blocking init
        self._events_replayed = False
        self._state_lock = threading.RLock()

    def _replay_causal_events(self):
        """Replay events from EventStore to rebuild in-memory Causal Graph and Symbolic Facts.
        Called lazily on first load_state() to avoid blocking engine initialization.
        NOTE: Skips expensive AST parsing during batch replay for performance.
        Dependency graph rebuilds incrementally from new file edits."""
        if self._events_replayed:
            return
        
        self._events_replayed = True
        self.logger.info(f"Replaying {len(self.event_store.events)} causal events (fast mode)...")
        
        # Ensure we have a state to populate
        if not self._current_state:
            self._current_state = CognitiveState()

        # Batch restore symbolic facts only - skip expensive AST parsing
        # The causal graph will rebuild incrementally from new edits
        for event in self.event_store.events:
            if event.event_type == "file_edit":
                fact = f"edited:{event.source}"
            elif event.event_type == "terminal":
                fact = f"cmd:{event.source}"
            elif event.event_type == "git_commit":
                fact = f"commit:{event.source}"
            else:
                fact = None

            if fact and fact not in self._current_state.symbolic.facts:
                self._current_state.symbolic.facts.append(fact)
        
        self.logger.info(f"Restored {len(self._current_state.symbolic.facts)} symbolic facts.")

    def _get_llm_provider(self):
        """Lazy-initialize the LLM provider"""
        if not self._llm_initialized:
            self._llm_initialized = True
            try:
                from .llm import get_provider
                self._llm_provider = get_provider(
                    provider_name=self.config.llm_provider,
                    model=self.config.get_model(),
                    api_key=self.config.get_api_key(),
                    host=self.config.ollama_host,
                )
                self.logger.info(f"LLM provider: {self.config.llm_provider} ({self.config.get_model()})")
            except Exception as e:
                self.logger.warning(f"LLM not available ({e}). Using heuristic fallback.")
                self._llm_provider = None
        return self._llm_provider

    def _register_default_operators(self):
        """Register default HCOs for dev context"""
        from .operators.symbolic_operator import SymbolicOperator
        from .operators.neural_operator import NeuralOperator
        from .operators.causal_operator import CausalOperator
        from .operators.neural_causal_operator import NeuralCausalOperator

        self.hco_engine.register_operators([
            SymbolicOperator("context_ingest", description="Ingest context into state"),
            NeuralOperator("intent_inference", pattern_size=64, description="Infer intent"),
            NeuralCausalOperator("causal_discovery", description="Discover latent causal links"),
            CausalOperator("action_suggester", description="Suggest next actions")
        ])

    def _ensure_llm_on_neural_ops(self):
        """Wire the LLM provider into neural operators if available"""
        llm = self._get_llm_provider()
        if llm:
            for op in self.hco_engine.operator_registry.values():
                if hasattr(op, 'set_llm_provider'):
                    op.set_llm_provider(llm)

    def load_state(self) -> Optional[CognitiveState]:
        """
        Load cognitive state from disk.
        Supports both gzip-compressed (k2.6) and plain JSON files.
        Returns None if no state exists.
        """
        try:
            with self._state_lock:
                if not self.state_file.exists():
                    # Fallback to uncompressed debug file if present
                    debug_file = self.state_file.with_suffix('.json')
                    if debug_file.exists():
                        with open(debug_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        return None
                else:
                    # k2.6: Try gzip first, fall back to plain JSON
                    raw = self.state_file.read_bytes()
                    try:
                        decompressed = gzip.decompress(raw)
                        data = json.loads(decompressed.decode('utf-8'))
                    except (gzip.BadGzipFile, OSError, ValueError):
                        # Not gzip - try plain JSON
                        with open(self.state_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

            # Parse unified state format (v2.0)
            if "state" in data:
                # New unified format
                self._current_state = CognitiveState.from_dict(data["state"])
                self._last_saved = datetime.fromisoformat(data.get("metadata", {}).get("merged_at", datetime.now().isoformat()))
            elif "cognitive_state" in data:
                # Legacy format
                self._current_state = CognitiveState.from_dict(data["cognitive_state"])
                self._last_saved = datetime.fromisoformat(data.get("saved_at", datetime.now().isoformat()))
            else:
                # Very legacy: reconstruct
                self._current_state = self._reconstruct_state_from_legacy(data)
                self._last_saved = datetime.now()
            
            # Lazily replay causal events to rebuild graph (non-blocking for init)
            if not self._events_replayed:
                self._replay_causal_events()
            
            return self._current_state

        except Exception as e:
            self.logger.warning(f"Error loading state: {e}")
            return None

    def _deduplicate_facts(self, facts: List[str], max_facts: int = 100) -> List[str]:
        """
        Deduplicate and limit facts to prevent state bloat.
        
        - Removes exact duplicates
        - Removes low-value observation noise
        - Keeps most recent facts up to max_facts
        """
        if not facts:
            return facts
        
        # Filter out low-value noise
        noise_prefixes = ('observation:mcp_tool:', 'pattern:checking_')
        filtered = [f for f in facts if not f.startswith(noise_prefixes)]
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for f in filtered:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        
        # Keep only most recent facts
        return unique[-max_facts:]
    
    def save_state(self) -> bool:
        """Save current cognitive state to disk with deduplication, atomic writes, and compression (k2.6)."""
        try:
            with self._state_lock:
                self.hcr_dir.mkdir(exist_ok=True)

                # Clean up state before saving
                if self._current_state and hasattr(self._current_state, 'symbolic'):
                    original_count = len(self._current_state.symbolic.facts)
                    self._current_state.symbolic.facts = self._deduplicate_facts(
                        self._current_state.symbolic.facts, max_facts=100
                    )
                    if original_count != len(self._current_state.symbolic.facts):
                        self.logger.info(f"Cleaned facts: {original_count} -> {len(self._current_state.symbolic.facts)}")

                # Build unified state format (v2.0)
                data = {
                    "version": "2.0.0",
                    "saved_at": datetime.now().isoformat(),
                    "project_path": str(self.project_path),
                    "state": self._current_state.to_dict() if self._current_state else {},
                    "metadata": {
                        "fact_count": len(self._current_state.symbolic.facts) if self._current_state else 0,
                        "last_saved": datetime.now().isoformat(),
                        "compression": "gzip"
                    }
                }

                # ATOMIC WRITE: write to temp file, then rename
                temp_fd, temp_name = tempfile.mkstemp(prefix='hcr_state_', dir=self.hcr_dir)
                temp_file = Path(temp_name)
                try:
                    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
                    compressed = gzip.compress(json_bytes, compresslevel=6)
                    with os.fdopen(temp_fd, 'wb') as f:
                        f.write(compressed)
                        f.flush()
                        os.fsync(f.fileno())

                    os.replace(temp_file, self.state_file)

                    debug_file = self.state_file.with_suffix('.json')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    self._last_saved = datetime.now()
                    return True
                except Exception:
                    if temp_file.exists():
                        temp_file.unlink(missing_ok=True)
                    raise

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
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
        elif event.event_type == "mcp_tool_call":
            self._handle_mcp_tool_call(event.data)

        # Run HCO analysis if significant event
        if event.event_type in ["window_focus", "git_commit", "mcp_tool_call"]:
            self._ensure_llm_on_neural_ops()
            self._run_analysis()

        # Invalidate cache since state changed
        self._cache.invalidate()

        # Avoid rewriting project state for every MCP read/query.
        # File edits, commits, terminal events, and manual updates still persist immediately.
        if event.event_type != "mcp_tool_call":
            self.save_state()

        return self._current_state

    def _handle_file_edit(self, data: Dict[str, Any]):
        """Process file edit event and update Causal Graph"""
        file_path = data.get("path", "")

        # 1. Log immutable event
        event = CausalEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type="file_edit",
            source=file_path,
            details=data
        )
        self.event_store.append(event)
        
        # 2. Extract AST dependencies
        abs_path = self.project_path / file_path
        if abs_path.exists() and abs_path.suffix == '.py':
            deps = extract_dependencies(abs_path)
            all_deps = deps["imports"] + deps["calls"]
            if all_deps:
                self.dependency_graph.update_file_dependencies(file_path, all_deps)
                
        # 3. Add to symbolic facts
        fact = f"edited:{file_path}"
        if fact not in self._current_state.symbolic.facts:
            self._current_state.symbolic.facts.append(fact)

        # Add causal dependency (Legacy, can be phased out as TCG matures)
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

    def _handle_mcp_tool_call(self, data: Dict[str, Any]):
        """Process MCP tool call event"""
        tool_name = data.get("tool", "unknown")
        args = data.get("args", {})

        # Log to event store
        event = CausalEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type="mcp_tool_call",
            source=tool_name,
            details=data
        )
        self.event_store.append(event)

        # Add to symbolic facts
        fact = f"mcp_tool:{tool_name}"
        if fact not in self._current_state.symbolic.facts:
            self._current_state.symbolic.facts.append(fact)

        # Track specific tool usage patterns
        if "state" in tool_name.lower():
            self._current_state.symbolic.facts.append("pattern:checking_state")
        if "task" in tool_name.lower() or "action" in tool_name.lower():
            self._current_state.symbolic.facts.append("pattern:querying_context")

    def _run_analysis(self):
        """Run HCO analysis on current state"""
        # Run context ingestion
        sequence = ["context_ingest", "intent_inference", "causal_discovery", "action_suggester"]

        self._current_state = self.hco_engine.execute_sequence(
            initial_state=self._current_state,
            operator_sequence=sequence,
            confidence=0.75
        )
        
        # Sync latent links to the causal graph
        for fact in self._current_state.symbolic.facts:
            if fact.startswith("latent_link:"):
                try:
                    # Parse: latent_link:source->target (type)
                    content = fact.replace("latent_link:", "")
                    source, rest = content.split("->")
                    target = rest.split(" (")[0].strip()
                    l_type = rest.split(" (")[1].replace(")", "").strip() if "(" in rest else "latent"
                    
                    self.dependency_graph.add_latent_link(source.strip(), target, l_type)
                except Exception:
                    continue

    def infer_context(self, use_llm: bool = True) -> EngineContext:
        """
        Infer current context from state.
        Uses LLM if available and use_llm=True, with caching to avoid redundant calls.

        Args:
            use_llm: Whether to use LLM for inference (default True). Set False for fast heuristic-only inference.

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

        # Calculate gap
        gap = None
        if self._last_saved:
            gap = (datetime.now() - self._last_saved).total_seconds() / 60

        # Get relevant facts (use the most recent ones for inference)
        facts = self._current_state.symbolic.facts[-20:]

        # Try LLM-powered inference (with cache) - only if explicitly requested
        if use_llm:
            llm = self._get_llm_provider()
            if llm:
                llm_result = self._infer_with_llm(llm)
                if llm_result:
                    return EngineContext(
                        current_task=llm_result.get("current_task", "Unknown"),
                        progress_percent=llm_result.get("progress_percent", 50),
                        next_action=llm_result.get("next_action", "Continue working"),
                        confidence=llm_result.get("confidence", self._current_state.meta.confidence),
                        gap_minutes=gap,
                        facts=facts,
                    )

        # Fast heuristic inference (no LLM)
        task = self._extract_task()
        progress = self._calculate_progress()
        next_action = self._extract_next_action()

        return EngineContext(
            current_task=task,
            progress_percent=progress,
            next_action=next_action,
            confidence=self._current_state.meta.confidence,
            gap_minutes=gap,
            facts=facts
        )

    def _infer_with_llm(self, llm) -> Optional[Dict[str, Any]]:
        """Use LLM to infer context, with caching"""
        state_dict = self._current_state.to_dict()

        # Check cache first
        if self.config.cache_enabled:
            cached = self._cache.get(state_dict, cache_key="context_inference")
            if cached:
                return cached

        # Build prompt from state
        prompt = self._build_inference_prompt()

        try:
            result = llm.structured_complete(
                prompt=prompt,
                system=CONTEXT_INFERENCE_PROMPT,
                temperature=0.3,
                max_tokens=512,
            )

            if result:
                # Clamp progress
                result["progress_percent"] = max(10, min(90, result.get("progress_percent", 50)))

                # Cache the result
                if self.config.cache_enabled:
                    self._cache.put(state_dict, result, cache_key="context_inference")

                return result

        except Exception as e:
            self.logger.warning(f"LLM inference failed: {e}")

        return None

    def _build_inference_prompt(self) -> str:
        """Build a rich prompt from current cognitive state for context inference"""
        lines = ["## Developer Session State\n"]

        facts = self._current_state.symbolic.facts
        deps = self._current_state.causal.dependencies
        effects = self._current_state.causal.effects

        if facts:
            lines.append("### Facts:")
            for f in facts[:20]:
                lines.append(f"- {f}")

        if deps:
            lines.append("\n### Causal Dependencies:")
            for d in deps[:10]:
                lines.append(f"- {d}")

        if effects:
            lines.append("\n### Known Effects:")
            for e in effects[:10]:
                lines.append(f"- {e}")

        # Phase 3: Temporal Causal Graph - Impact Prediction
        recent_edits = [f.replace("edited:", "") for f in facts if f.startswith("edited:")]
        if recent_edits:
            latest_edit = recent_edits[-1]
            impacted_files = self.impact_analyzer.predict_impact(latest_edit)
            if impacted_files:
                lines.append("\n### Predicted Causal Impact:")
                lines.append(f"Based on recent edits to `{latest_edit}`, the Temporal Causal Graph predicts the following files will be affected and may need updates:")
                for imp in impacted_files[:5]:
                    lines.append(f"- {imp}")
                if len(impacted_files) > 5:
                    lines.append(f"- ... and {len(impacted_files) - 5} more files.")

        # Phase 5: Cognitive Twin Integration
        profile_rules = self.profile_manager.get_context_injection()
        if profile_rules:
            lines.append("\n### Developer Profile (Strict Constraints):")
            lines.extend(profile_rules)

        friction_warnings = self.friction_detector.analyze_friction()
        if friction_warnings:
            lines.append("\n### Friction Warnings (DO NOT REPEAT MISTAKES):")
            for warning in friction_warnings:
                lines.append(f"- {warning}")

        if recent_edits:
            latest_edit = recent_edits[-1]
            predictions = self.workflow_predictor.predict_next_files(latest_edit)
            if predictions:
                lines.append("\n### Workflow Anticipation:")
                lines.append(f"Based on Markov transition probabilities from `{latest_edit}`, the user is highly likely to edit these next:")
                for p_file, prob in predictions:
                    lines.append(f"- {p_file} ({prob*100:.0f}% probability)")

        lines.append(f"\n### Session Meta:")
        lines.append(f"- Confidence: {self._current_state.meta.confidence:.2f}")
        lines.append(f"- Uncertainty: {self._current_state.meta.uncertainty:.2f}")
        lines.append(f"- Last active: {self._current_state.meta.timestamp.isoformat()}")

        return "\n".join(lines)

    # --- Heuristic Fallbacks (used when no LLM is available) ---

    def _extract_task(self) -> str:
        """Extract current task from state facts (heuristic fallback)"""
        # Scan in reverse to find the most RECENT task
        for fact in reversed(self._current_state.symbolic.facts):
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
        """Calculate progress percentage (heuristic fallback)"""
        score = 50
        facts = self._current_state.symbolic.facts

        # Check for completion indicators (scan recent facts)
        recent_facts = facts[-20:]
        if any("commit:" in f for f in recent_facts):
            score += 20
        if any("test" in f.lower() for f in recent_facts):
            score += 10

        # Check for file activity
        edited_count = sum(1 for f in recent_facts if "edited:" in f)
        if edited_count > 3:
            score += 10

        return max(10, min(90, score))

    def _extract_next_action(self) -> str:
        """Extract suggested next action (heuristic fallback)"""
        # Check causal effects
        for effect in self._current_state.causal.effects:
            if "predicted:" in effect:
                return effect.replace("predicted:", "")

        # Default suggestions based on recent state
        facts = self._current_state.symbolic.facts[-20:]

        if any("edited:" in f for f in facts) and not any("commit:" in f for f in facts):
            return "Commit your Phase 5 changes"

        return "Continue working on the Cognitive Twin"

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
            self._cache.invalidate()
            return True
        except Exception as e:
            self.logger.warning(f"Error clearing state: {e}")
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
