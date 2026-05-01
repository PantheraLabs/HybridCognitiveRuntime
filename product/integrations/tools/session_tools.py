"""
Session management tools for HCR MCP server.

Handles:
- hcr_create_session: Create new session with fast LLM-free init
- hcr_set_session_note: Add private notes with thread safety
- hcr_merge_session: Merge session back into global state
- hcr_list_sessions: List all active sessions

k2.6 fixes:
- create_session: Default LLM disabled (use_llm=False), 3s timeout
- set_session_note: Thread-safe with asyncio.Lock
- merge_session: Sync save wrapped in thread pool with timeout
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from collections import defaultdict

from .base_tool import BaseMCPTool


class SessionTools(BaseMCPTool):
    """Session management with async safety and fast initialization."""
    
    def __init__(self, responder=None):
        super().__init__(responder)
        # Per-session storage (mirrors HCRMCPResponder session state)
        self._session_states: Dict[str, Dict[str, Any]] = {}
        self._session_private_notes: Dict[str, list] = defaultdict(list)
        self._notes_lock = asyncio.Lock()
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route to specific session tool based on subcommand."""
        action = args.get("action", "create")
        if action == "create":
            return await self._tool_create_session(args)
        elif action == "set_note":
            return await self._tool_set_session_note(args)
        elif action == "merge":
            return await self._tool_merge_session(args)
        elif action == "list":
            return await self._tool_list_sessions(args)
        else:
            return self._error_response(f"Unknown session action: {action}")
    
    async def _tool_create_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new HCR session with fast LLM-free initialization."""
        session_id = args.get("session_id")
        tag = args.get("tag", "untitled")
        clone_from = args.get("clone_from", "")
        use_llm = args.get("use_llm", False)  # Default False for speed (k2.6 fix)
        
        if not session_id:
            return self._error_response("session_id is required")
        
        if session_id in self._session_states:
            return self._success_response(
                f"Session '{session_id}' already exists. Use a different ID."
            )
        
        # Initialize with current state or clone from another session
        if clone_from and clone_from in self._session_states:
            source = self._session_states[clone_from]
            self._session_states[session_id] = {
                "panel": source.get("panel", ""),
                "metadata": {**source.get("metadata", {}), "tag": tag, "cloned_from": clone_from},
                "timestamp": datetime.now().isoformat()
            }
            async with self._notes_lock:
                self._session_private_notes[session_id] = list(
                    self._session_private_notes.get(clone_from, [])
                )
        else:
            # Fresh session with current engine state - fast path, no LLM by default
            panel = "No engine state available"
            engine = self._get_engine()
            if engine:
                try:
                    def _infer_ctx():
                        engine.load_state()
                        return engine.infer_context()
                    # k2.6: 3s timeout, no LLM by default
                    context = await self._run_blocking(_infer_ctx, timeout=3.0)
                    panel = self._format_classic_panel(context, mode="resume")
                    if use_llm:
                        # Only call LLM if explicitly requested
                        panel = await self._generate_smart_resume(context, session_id=session_id)
                except Exception as e:
                    self.logger.warning(f"Session context inference failed: {e}")
                    panel = f"Session created but context inference timed out.\nTag: {tag}"
            
            self._session_states[session_id] = {
                "panel": panel,
                "metadata": {"tag": tag},
                "timestamp": datetime.now().isoformat()
            }
            async with self._notes_lock:
                self._session_private_notes[session_id] = []
        
        return self._success_response(
            f"Session '{session_id}' created with tag '{tag}'.\n\n"
            f"Use this session_id in other tools to maintain separate context."
        )
    
    async def _tool_set_session_note(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a private note to a session with async safety (k2.6 fix)."""
        session_id = args.get("session_id")
        note = args.get("note")
        
        if not session_id:
            return self._error_response("session_id required")
        
        if session_id not in self._session_states:
            return self._error_response(
                f"Session '{session_id}' not found. Create it first."
            )
        
        # k2.6: Async safety - use lock for concurrent note writes
        async with self._notes_lock:
            notes = self._session_private_notes[session_id]
            notes.append(f"[{datetime.now().strftime('%H:%M')}] {note}")
            # Keep last 20 notes max
            if len(notes) > 20:
                self._session_private_notes[session_id] = notes[-20:]
            notes_count = len(self._session_private_notes[session_id])
        
        content = f"## Note added to session '{session_id}'\n\n"
        content += f"Total notes: {notes_count}\n\n"
        content += "Recent notes:\n"
        async with self._notes_lock:
            recent = self._session_private_notes[session_id][-5:]
        for n in recent:
            content += f"- {n}\n"
        
        return self._success_response(content)
    
    async def _tool_merge_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Merge session-specific facts back into global state with timeout."""
        session_id = args.get("session_id")
        preserve_notes = args.get("preserve_notes", True)
        
        if not session_id or session_id not in self._session_states:
            return self._error_response(f"Session '{session_id}' not found.")
        
        session_data = self._session_states[session_id]
        async with self._notes_lock:
            notes = list(self._session_private_notes.get(session_id, []))
        
        # Log merge event to global state with thread pool timeout (k2.6 fix)
        engine = self._get_engine()
        if engine:
            try:
                def _merge():
                    from src.engine_api import EngineEvent
                    event = EngineEvent(
                        event_type='session_merge',
                        timestamp=datetime.now(),
                        data={
                            'session_id': session_id,
                            'tag': session_data.get('metadata', {}).get('tag'),
                            'notes_count': len(notes),
                            'panel_preview': session_data.get('panel', '')[:200]
                        }
                    )
                    engine.update_from_environment(event)
                    engine.save_state()
                
                await self._run_blocking(_merge, timeout=5.0)
                # Invalidate cache since we just saved new state
                if self.responder and hasattr(self.responder, '_state_cached'):
                    self.responder._state_cached = False
            except Exception as e:
                self.logger.warning(f"Session merge state save failed: {e}")
        
        # Clear session state (but optionally keep notes)
        if not preserve_notes:
            async with self._notes_lock:
                if session_id in self._session_private_notes:
                    del self._session_private_notes[session_id]
        del self._session_states[session_id]
        
        content = (
            f"## Session '{session_id}' merged into global state\n\n"
            f"Notes preserved: {preserve_notes}\n"
            f"Session-specific context is now part of the shared project memory."
        )
        
        return self._success_response(content)
    
    async def _tool_list_sessions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all active HCR sessions."""
        sessions = []
        async with self._notes_lock:
            for sid, data in self._session_states.items():
                notes = self._session_private_notes.get(sid, [])
                sessions.append({
                    "session_id": sid,
                    "tag": data.get("metadata", {}).get("tag", "untitled"),
                    "last_active": data.get("timestamp"),
                    "notes_count": len(notes),
                    "preview": data.get("panel", "")[:100] + "..." if len(data.get("panel", "")) > 100 else data.get("panel", "")
                })
        
        content = f"## Active HCR Sessions ({len(sessions)})\n\n"
        for s in sessions:
            content += f"- **{s['session_id']}** ({s['tag']})\n"
            content += f"  Last active: {s['last_active']}\n"
            content += f"  Notes: {s['notes_count']}\n"
        
        return {
            "content": content,
            "sessions": sessions,
            "count": len(sessions)
        }
    
    def _format_classic_panel(self, context, mode: str = "resume") -> str:
        """Fallback formatter that mirrors the original HCR assistant panel."""
        lines = [
            "============================================================",
            "  HCR SESSION RESUME" if mode == "resume" else "  HCR NEXT ACTION",
            "============================================================",
        ]
        
        gap_val = getattr(context, 'gap_minutes', None)
        if gap_val is not None:
            if gap_val < 1:
                lines.append("\nLast active: just now")
            elif gap_val < 60:
                lines.append(f"\nLast active: {int(gap_val)} minutes ago")
            elif gap_val < 1440:
                lines.append(f"\nLast active: {gap_val/60:.1f} hours ago")
            else:
                lines.append(f"\nLast active: {gap_val/1440:.1f} days ago")
        
        lines.append(f"\nCurrent Task: {context.current_task}")
        lines.append(f"\nProgress: {context.progress_percent}%")
        filled = max(0, min(20, int(context.progress_percent / 5)))
        bar = "█" * filled + "░" * (20 - filled)
        lines.append(f"           [{bar}]")
        lines.append(f"\nNext Action: {context.next_action}")
        
        if context.confidence > 0.7:
            lines.append("\nHigh confidence")
        elif context.confidence > 0.4:
            lines.append("\nModerate confidence")
        else:
            lines.append("\nLow confidence")
        
        if getattr(context, 'facts', None):
            lines.append("\nContext Facts:")
            for fact in context.facts[:5]:
                lines.append(f"  • {fact}")
        
        lines.append("\n============================================================")
        return "\n".join(lines)
    
    async def _generate_smart_resume(self, context, session_id: Optional[str] = None) -> str:
        """Generate rich resume panel optionally using LLM."""
        base = self._format_classic_panel(context)
        
        engine = self._get_engine()
        if not engine:
            return base
        
        llm = engine._get_llm_provider()
        if not llm:
            return base
        
        async with self._notes_lock:
            notes = list(self._session_private_notes.get(session_id or "", []))
        
        import json
        payload = {
            "mode": "resume",
            "gap_minutes": getattr(context, 'gap_minutes', None),
            "context": context.to_dict() if hasattr(context, 'to_dict') else {},
            "private_notes": notes,
        }
        
        def _call_llm():
            try:
                return llm.structured_complete(
                    prompt=json.dumps(payload, indent=2, default=str),
                    system="You are the HCR Resume formatter. Return JSON with panel_text, tone_hint, summary.",
                    temperature=0.2,
                    max_tokens=600,
                ) or {}
            except Exception as exc:
                self.logger.warning(f"LLM smart resume failed: {exc}")
                return {}
        
        try:
            # k2.6: 3s timeout for LLM call
            result = await self._run_blocking(_call_llm, timeout=3.0)
        except asyncio.TimeoutError:
            self.logger.warning("LLM smart resume exceeded 3s timeout")
            result = {}
        
        if isinstance(result, dict) and result.get("panel_text"):
            return result["panel_text"]
        return base
