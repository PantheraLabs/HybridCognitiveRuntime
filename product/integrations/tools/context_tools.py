"""
Context capture tools for full developer state gathering.

Handles:
- hcr_capture_full_context: Capture complete developer context (git + files + HCR state)

k2.6 fixes:
- All I/O operations run in parallel via asyncio.gather()
- Timeout on each parallel task (3-5s)
- LLM inference defaults to False for speed
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

from .base_tool import BaseMCPTool


class ContextTools(BaseMCPTool):
    """Full context capture with parallel async I/O."""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Capture full developer context."""
        return await self._tool_capture_full_context(args)
    
    async def _tool_capture_full_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Capture complete developer context with parallel I/O (k2.6 fix)."""
        include_diffs = args.get("include_diffs", False)
        session_id = args.get("session_id")
        max_diff_files = 5
        
        engine = self._get_engine()
        if not engine:
            return {"content": "Engine not initialized", "captured": False}
        
        from product.state_capture.git_tracker import GitTracker
        from product.state_capture.file_watcher import FileWatcher
        
        # k2.6 FIX: Define async wrapper tasks that run in parallel
        async def _capture_git():
            try:
                git = GitTracker(self.responder.project_path if self.responder else ".")
                return await self._run_blocking(git.capture_state, timeout=5.0)
            except Exception as e:
                self.logger.warning(f"Git capture timed out or failed: {e}")
                return {"error": str(e), "branch": "unknown"}
        
        async def _capture_files():
            try:
                watcher = FileWatcher(self.responder.project_path if self.responder else ".")
                return await self._run_blocking(
                    lambda: watcher.capture_state(lookback_minutes=120),
                    timeout=5.0
                )
            except Exception as e:
                self.logger.warning(f"File capture timed out or failed: {e}")
                return {"error": str(e), "file_count": 0}
        
        async def _infer_context():
            try:
                # State already loaded by _handle_tools_call, just infer
                use_llm = args.get("use_llm", False)
                return await self._run_blocking(lambda: engine.infer_context(use_llm=use_llm), timeout=3.0)
            except Exception as e:
                self.logger.warning(f"Context inference timed out: {e}")
                from src.engine_api import EngineContext
                return EngineContext(
                    current_task="Unknown (inference timeout)",
                    progress_percent=0,
                    next_action="Retry context capture",
                    confidence=0.0,
                    gap_minutes=0,
                    facts=[]
                )
        
        # k2.6 FIX: Run all I/O tasks in parallel using asyncio.gather()
        git_state, file_state, context = await asyncio.gather(
            _capture_git(),
            _capture_files(),
            _infer_context(),
            return_exceptions=False
        )
        
        # Get detailed changes if requested (only after file_state available)
        detailed_changes = []
        if include_diffs and isinstance(file_state, dict) and file_state.get("file_count", 0) > 0:
            try:
                watcher = FileWatcher(self.responder.project_path if self.responder else ".")
                changes = await self._run_blocking(
                    lambda: watcher.get_changed_files_with_details(since_minutes=60),
                    timeout=5.0
                )
                detailed_changes = changes[:max_diff_files]
            except Exception as e:
                self.logger.warning(f"Detailed changes timed out: {e}")
        
        # Build comprehensive response
        current_task = getattr(context, 'current_task', 'Unknown') if hasattr(context, 'current_task') else 'Unknown'
        progress = getattr(context, 'progress_percent', 0) if hasattr(context, 'progress_percent') else 0
        confidence = getattr(context, 'confidence', 0.0) if hasattr(context, 'confidence') else 0.0
        next_action = getattr(context, 'next_action', 'Unknown') if hasattr(context, 'next_action') else 'Unknown'
        facts = getattr(context, 'facts', []) if hasattr(context, 'facts') else []
        
        content = f"""## Complete Developer Context Captured

### Git State
- **Branch:** {git_state.get('branch', 'unknown') if isinstance(git_state, dict) else 'unknown'}
- **Last Commit:** {git_state.get('last_commit', {}).get('message', 'unknown')[:50] if isinstance(git_state, dict) and isinstance(git_state.get('last_commit'), dict) else 'unknown'}
- **Uncommitted:** {git_state.get('uncommitted_changes', {}).get('modified_count', 0) if isinstance(git_state, dict) and isinstance(git_state.get('uncommitted_changes'), dict) else 0} modified, {git_state.get('uncommitted_changes', {}).get('staged_count', 0) if isinstance(git_state, dict) and isinstance(git_state.get('uncommitted_changes'), dict) else 0} staged

### Recent File Activity
- **Files Changed (2h):** {file_state.get('file_count', 0) if isinstance(file_state, dict) else 0}
- **Primary Language:** {file_state.get('primary_language', 'unknown') if isinstance(file_state, dict) else 'unknown'}
- **Active Directories:** {', '.join(list(file_state.get('active_directories', {}).keys())[:3]) if isinstance(file_state, dict) and isinstance(file_state.get('active_directories'), dict) else 'unknown'}

### HCR Cognitive State
- **Current Task:** {current_task}
- **Progress:** {progress}%
- **Confidence:** {f'{confidence:.0%}' if isinstance(confidence, float) else '0%'}
- **Next Action:** {next_action}

### Facts ({len(facts[-10:]) if facts else 0} recent)
"""
        if facts:
            for fact in facts[-5:]:
                content += f"- {fact}\n"
        else:
            content += "- No facts available\n"
        
        if detailed_changes:
            content += f"\n### Detailed Changes ({len(detailed_changes)} files)\n"
            for change in detailed_changes:
                content += f"- `{change.get('path', 'unknown')}`: +{change.get('lines_added', 0)}/-{change.get('lines_removed', 0)} lines"
                if change.get('functions_changed'):
                    content += f" (funcs: {', '.join(change['functions_changed'][:3])})"
                content += "\n"
        
        result = {
            "content": content,
            "captured": True,
            "timestamp": datetime.now().isoformat(),
            "git": git_state if isinstance(git_state, dict) else {},
            "files": file_state if isinstance(file_state, dict) else {},
            "detailed_changes": detailed_changes,
            "hcr": {
                "current_task": current_task,
                "progress_percent": progress,
                "next_action": next_action,
                "confidence": confidence,
                "recent_facts": facts[-10:] if facts else []
            }
        }
        
        # Record session snapshot if available
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, content, {"full_context": True})
        
        return result
