"""
Developer Context HCO Wrappers

Bridges developer workflow context with HCR operators.
Transforms captured state into cognitive operations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional
from datetime import datetime

from src.state.cognitive_state import CognitiveState
from src.operators.neural_operator import NeuralOperator, SimilarityOperator
from src.operators.symbolic_operator import SymbolicOperator, LogicOperator
from src.operators.causal_operator import CausalOperator
from src.core.hco_engine import HCOEngine


class DevContextOperators:
    """
    Pre-built HCO sequences for developer context analysis.
    
    These operators work on developer-specific state rather than
    generic cognitive state.
    """
    
    @staticmethod
    def create_context_ingestion_op() -> SymbolicOperator:
        """
        Creates an operator that ingests developer context into cognitive state.
        
        Transforms:
        - git state -> symbolic facts
        - file changes -> causal dependencies
        - time gaps -> uncertainty levels
        """
        return SymbolicOperator(
            operator_id="dev_context_ingest",
            description="Ingests developer context into cognitive state",
            rules=[
                "if has_uncommitted_changes then task_in_progress",
                "if time_gap > 60 then context_stale",
                "if recent_commit mentions feature then working_on_feature",
                "if file_extension is .test then writing_tests"
            ]
        )
    
    @staticmethod
    def create_intent_inference_op() -> NeuralOperator:
        """
        Creates an operator that infers developer intent from context.
        
        Pattern recognition on:
        - File types being edited
        - Commit message themes
        - Recent command history
        """
        return NeuralOperator(
            operator_id="intent_inference",
            pattern_size=64,
            description="Infers developer intent from context patterns"
        )
    
    @staticmethod
    def create_task_causal_op() -> CausalOperator:
        """
        Creates an operator that traces task causality.
        
        Analyzes:
        - What file changes caused what
        - What likely comes next
        - Dependencies between work items
        """
        return CausalOperator(
            operator_id="task_causal_analyzer",
            causal_rules=[
                "modify_model -> need_migration",
                "add_test -> run_tests",
                "fix_bug -> verify_fix",
                "edit_config -> restart_server",
                "commit_changes -> push_to_remote"
            ],
            description="Analyzes causal relationships in dev work"
        )


class DevContextEngine:
    """
    Engine that runs HCO sequences on developer context.
    """
    
    def __init__(self):
        self.engine = HCOEngine(engine_id="dev_context_engine")
        self._register_dev_ops()
    
    def _register_dev_ops(self):
        """Register developer-specific operators"""
        ops = DevContextOperators()
        
        self.engine.register_operators([
            ops.create_context_ingestion_op(),
            ops.create_intent_inference_op(),
            ops.create_task_causal_op()
        ])
    
    def analyze_context(
        self,
        git_state: Dict[str, Any],
        file_state: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run HCO analysis on developer context.
        
        Args:
            git_state: State from GitTracker
            file_state: State from FileWatcher
            previous_state: Previous developer cognitive state
            
        Returns:
            Analysis results with inferred task, progress, and suggestions
        """
        # Create initial cognitive state from context
        state = self._context_to_state(git_state, file_state, previous_state)
        
        # Run HCO sequence
        sequence = ["dev_context_ingest", "intent_inference", "task_causal_analyzer"]
        
        final_state = self.engine.execute_sequence(
            initial_state=state,
            operator_sequence=sequence,
            confidence=0.75
        )
        
        # Extract results from final state
        return self._state_to_analysis(final_state, git_state, file_state)
    
    def _context_to_state(
        self,
        git_state: Dict[str, Any],
        file_state: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]]
    ) -> CognitiveState:
        """Convert captured context to cognitive state"""
        state = CognitiveState()
        
        # Add git facts
        if git_state.get("is_git_repo"):
            state.symbolic.facts.append(f"branch:{git_state.get('branch', 'unknown')}")
            
            last_commit = git_state.get("last_commit", {})
            if last_commit:
                commit_msg = last_commit.get("message", "")[:50]  # Truncate
                state.symbolic.facts.append(f"last_commit:{commit_msg}")
            
            changes = git_state.get("uncommitted_changes", {})
            if changes.get("has_changes"):
                state.symbolic.facts.append("has_uncommitted_changes")
                state.symbolic.facts.append(f"modified_files:{changes.get('modified_count', 0)}")
        
        # Add file facts
        if file_state.get("recent_files"):
            primary_lang = file_state.get("primary_language", "unknown")
            state.symbolic.facts.append(f"primary_language:{primary_lang}")
            
            # Add file count
            file_count = file_state.get("file_count", 0)
            state.symbolic.facts.append(f"recent_file_changes:{file_count}")
            
            # Add active directories as facts
            for dir_name in file_state.get("active_directories", {}).keys():
                state.symbolic.facts.append(f"active_dir:{dir_name}")
        
        # Add causal dependencies from file changes
        recent_files = file_state.get("recent_files", [])
        for file_info in recent_files[:5]:  # Top 5 files
            path = file_info.get("path", "")
            state.causal.dependencies.append(f"edited:{path} -> file_in_focus")
        
        # Set uncertainty based on time gap
        if previous_state:
            saved_at = previous_state.get("saved_at")
            if saved_at:
                try:
                    last_time = datetime.fromisoformat(saved_at)
                    gap_hours = (datetime.now() - last_time).total_seconds() / 3600
                    
                    # Higher uncertainty for longer gaps
                    if gap_hours > 24:
                        state.meta.uncertainty = 0.8
                    elif gap_hours > 4:
                        state.meta.uncertainty = 0.5
                    else:
                        state.meta.uncertainty = 0.2
                except:
                    state.meta.uncertainty = 0.5
        else:
            state.meta.uncertainty = 0.7  # No previous state = high uncertainty
        
        state.meta.confidence = 1.0 - state.meta.uncertainty
        
        return state
    
    def _state_to_analysis(
        self,
        state: CognitiveState,
        git_state: Dict[str, Any],
        file_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert final cognitive state to analysis output"""
        
        # Extract inferred task from facts
        inferred_task = "unknown"
        task_keywords = []
        
        for fact in state.symbolic.facts:
            if "working_on" in fact or "feature" in fact:
                inferred_task = fact.replace("working_on:", "").replace("feature:", "")
            if "last_commit:" in fact:
                # Use commit message as task hint
                msg = fact.replace("last_commit:", "").lower()
                if any(k in msg for k in ["add", "implement", "create"]):
                    inferred_task = f"Implementing: {msg[:40]}"
                elif any(k in msg for k in ["fix", "bug", "resolve"]):
                    inferred_task = f"Fixing: {msg[:40]}"
                elif any(k in msg for k in ["test", "spec"]):
                    inferred_task = f"Testing: {msg[:40]}"
        
        # If still unknown, infer from file extensions
        if inferred_task == "unknown":
            primary_lang = file_state.get("primary_language", "")
            extensions = file_state.get("extensions", {})
            
            if ".test." in str(extensions) or "spec" in str(extensions):
                inferred_task = f"Writing tests ({primary_lang})"
            elif file_state.get("file_count", 0) > 0:
                inferred_task = f"Developing {primary_lang} code"
        
        # Calculate progress estimate
        progress = self._estimate_progress(git_state, file_state)
        
        # Generate next action suggestion
        next_action = self._suggest_next_action(state, git_state, file_state)
        
        return {
            "current_task": inferred_task,
            "progress_percent": progress,
            "next_action": next_action,
            "confidence": state.meta.confidence,
            "uncertainty": state.meta.uncertainty,
            "relevant_facts": state.symbolic.facts[:10],
            "detected_effects": state.causal.effects[:5]
        }
    
    def _estimate_progress(
        self,
        git_state: Dict[str, Any],
        file_state: Dict[str, Any]
    ) -> int:
        """Estimate progress percentage based on context heuristics"""
        score = 50  # Default: 50% (middle of task)
        
        # Recent commits suggest progress
        recent_commits = git_state.get("recent_commits", [])
        if len(recent_commits) > 0:
            latest_msg = recent_commits[0].get("message", "").lower()
            if any(k in latest_msg for k in ["complete", "finish", "done", "implement"]):
                score += 20
            if any(k in latest_msg for k in ["start", "init", "begin", "setup"]):
                score -= 20
        
        # Many file changes might mean nearing completion
        file_count = file_state.get("file_count", 0)
        if file_count > 10:
            score += 10
        elif file_count == 0:
            score -= 10
        
        # Uncommitted changes suggest work in progress
        changes = git_state.get("uncommitted_changes", {})
        if changes.get("has_changes"):
            score += 5
        
        return max(10, min(90, score))  # Clamp between 10-90%
    
    def _suggest_next_action(
        self,
        state: CognitiveState,
        git_state: Dict[str, Any],
        file_state: Dict[str, Any]
    ) -> str:
        """Generate suggestion for next action"""
        
        # Check causal effects from state
        effects = state.causal.effects
        
        # Check git state for obvious next steps
        changes = git_state.get("uncommitted_changes", {})
        
        if changes.get("has_changes"):
            modified = changes.get("modified_count", 0)
            if modified > 0:
                return f"Commit {modified} modified file(s)"
        
        # Check if tests exist in recent files
        extensions = file_state.get("extensions", {})
        if any("test" in str(ext).lower() for ext in extensions.keys()):
            return "Run tests to verify changes"
        
        # Check for unstaged files
        if changes.get("untracked_count", 0) > 0:
            return f"Review {changes.get('untracked_count')} new file(s)"
        
        # Default based on file activity
        recent_files = file_state.get("recent_files", [])
        if recent_files:
            last_file = recent_files[0].get("path", "")
            return f"Continue working on {Path(last_file).name}"
        
        return "Review recent changes and plan next steps"


from pathlib import Path
