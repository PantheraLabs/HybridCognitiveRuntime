"""
State Tools - HCR state management tools.

Handles:
- hcr_get_state: Get current HCR cognitive state
- hcr_get_causal_graph: Get dependency graph
- hcr_get_recent_activity: Get recent events
"""

from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool


class GetStateTool(BaseMCPTool):
    """Get current HCR state with formatted output"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current HCR state.
        
        Args:
            include_history: Whether to include event history
            session_id: Session for snapshot recording
            
        Returns:
            State summary with facts and metrics
        """
        include_history = args.get("include_history", False)
        session_id = args.get("session_id")
        
        engine = self._get_engine()
        if not engine:
            return {"content": "Engine not initialized. Run 'hcr init' first.", "exists": False}
        
        # State already loaded by _handle_tools_call, just use it
        state = engine._current_state
        if not state:
            return {"content": "No HCR state found for this project.", "exists": False}
        
        # Build formatted summary
        facts = state.symbolic.facts[-15:] if state.symbolic.facts else []
        deps = len(state.causal.dependencies)
        events = len(engine.event_store.events)
        
        content = f"""## HCR State Summary

**Status:** Active
**Facts Recorded:** {len(state.symbolic.facts)}
**Causal Dependencies:** {deps}
**Event History:** {events} events
**Confidence:** {state.meta.confidence:.0%}
**Uncertainty:** {state.meta.uncertainty:.0%}

**Recent Facts:**
"""
        if facts:
            for f in facts:
                content += f"- {f}\n"
        else:
            content += "- No facts recorded yet\n"
        
        result = {"content": content, "exists": True}
        
        if include_history:
            try:
                recent_events = await self._run_blocking(
                    lambda: engine.event_store.get_recent_events(50),
                    timeout=5.0
                )
                result["recent_events"] = [
                    {
                        "type": e.event_type,
                        "source": e.source,
                        "timestamp": str(e.timestamp),
                        "details": e.details
                    }
                    for e in recent_events
                ]
            except Exception as e:
                self.logger.warning(f"History load failed: {e}")
                result["recent_events"] = []
        
        # Record session snapshot via responder
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, content, {"exists": True})
        
        return result


class GetCausalGraphTool(BaseMCPTool):
    """Get causal dependency graph"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get causal graph of dependencies.
        
        Returns:
            Graph with forward and reverse edges
        """
        engine = self._get_engine()
        if not engine:
            return {"error": "Engine not initialized", "exists": False}
        
        # State preloaded by _handle_tools_call
        if not engine.dependency_graph:
            return {"content": "No causal graph found for this project. Edit some files to build the graph.", "exists": False}
        
        graph = {
            "forward": {k: list(v) for k, v in engine.dependency_graph.forward_edges.items()},
            "reverse": {k: list(v) for k, v in engine.dependency_graph.reverse_edges.items()}
        }
        
        # Build human-readable content string
        parts = ["## Causal Dependency Graph\n"]
        fwd = graph["forward"]
        if fwd:
            parts.append("### Forward Dependencies")
            for src, deps in fwd.items():
                parts.append(f"- **{src}** → {', '.join(deps)}")
        else:
            parts.append("No forward dependencies recorded.")
        rev = graph["reverse"]
        if rev:
            parts.append("\n### Reverse Dependencies")
            for tgt, srcs in rev.items():
                parts.append(f"- **{tgt}** ← {', '.join(srcs)}")
        parts.append(f"\n*Total forward edges: {len(fwd)} | reverse edges: {len(rev)}*")
        content = "\n".join(parts)
        
        return {"content": content, "graph": graph, "exists": True}


class GetRecentActivityTool(BaseMCPTool):
    """Get recent activity from event store"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recent activity events.
        
        Args:
            limit: Maximum events to return (default 10)
            session_id: Session for snapshot recording
            
        Returns:
            Formatted activity summary and raw events
        """
        limit = args.get("limit", 10)
        session_id = args.get("session_id")
        
        engine = self._get_engine()
        if not engine:
            return {"content": "HCR Engine not initialized. No activity recorded yet.", "activities": []}
        
        # Load events in thread pool to avoid blocking on JSONL read
        try:
            events = await self._run_blocking(
                lambda: engine.event_store.get_recent_events(limit),
                timeout=5.0
            )
        except Exception as e:
            self.logger.warning(f"Recent activity load failed: {e}")
            events = []
        
        if not events:
            return {
                "content": "No recent activity recorded. This appears to be a fresh session or the project was not previously tracked.",
                "activities": []
            }
        
        # Build formatted activity summary
        content = f"## Recent Activity ({len(events)} events)\n\n"
        
        for e in events:
            if e.event_type == "mcp_tool_call":
                tool_name = e.details.get("tool", "unknown") if e.details else "unknown"
                content += f"- **Tool Call:** `{tool_name}`\n"
            elif e.event_type == "file_edit":
                file_path = e.source
                content += f"- **File Edit:** `{file_path}`\n"
            elif e.event_type == "git_commit":
                commit_msg = e.details.get("message", "")[:50] if e.details else ""
                content += f"- **Git Commit:** {commit_msg}...\n"
            else:
                content += f"- **{e.event_type}:** {e.source}\n"
        
        # Also return raw data for programmatic use
        activities = [
            {
                "type": e.event_type,
                "source": e.source,
                "timestamp": str(e.timestamp),
                "details": e.details
            }
            for e in events
        ]
        
        snapshot_meta = {"count": len(activities)}
        if self.responder and hasattr(self.responder, '_record_session_snapshot'):
            self.responder._record_session_snapshot(session_id, content, snapshot_meta)
        
        return {"content": content, "activities": activities, "count": len(activities)}
