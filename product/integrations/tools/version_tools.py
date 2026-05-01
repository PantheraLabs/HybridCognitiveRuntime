"""
Version management tools for HCR state history.

Handles:
- hcr_get_version_history: Get git-like version history with metadata
- hcr_restore_version: Restore state to a specific version with timeout

k2.6 fixes:
- get_version_history: Returns full metadata (hash, timestamp, message, size)
- restore_version: Sync replay wrapped in thread pool with 5s timeout
"""

import time
from typing import Any, Dict

from .base_tool import BaseMCPTool


class VersionTools(BaseMCPTool):
    """Version history with async I/O and metadata query support."""
    
    def __init__(self, responder=None):
        super().__init__(responder)
        self._cache_ttl = 60.0
        self._version_cache = None
        self._version_cache_ts = 0.0
    
    def _cache_valid(self, cache_ts: float) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - cache_ts) < self._cache_ttl
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route to specific version tool."""
        action = args.get("action", "history")
        if action == "history":
            return await self._tool_get_version_history(args)
        elif action == "restore":
            return await self._tool_restore_version(args)
        else:
            return self._error_response(f"Unknown version action: {action}")
    
    async def _tool_get_version_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get version history with metadata query support (k2.6 fix)."""
        persistence = self._get_persistence()
        if not persistence:
            return {"error": "Persistence not initialized", "versions": []}
        
        limit = args.get("limit", 20)
        
        # Use cached result if fresh
        if self._cache_valid(self._version_cache_ts) and self._version_cache is not None:
            versions = self._version_cache[-limit:]
            return {"versions": versions, "count": len(versions), "cached": True}
        
        try:
            versions_raw = await self._run_blocking(
                lambda: persistence.get_version_history(limit=limit),
                timeout=5.0
            )
            # k2.6: Full metadata query - include all StateVersion fields
            versions = [
                {
                    "hash": v.hash,
                    "timestamp": v.timestamp,
                    "message": v.message,
                    "parent_hashes": v.parent_hashes,
                    "state_size_bytes": v.state_size_bytes,
                }
                for v in versions_raw
            ]
            self._version_cache = versions
            self._version_cache_ts = time.time()
            return {"versions": versions, "count": len(versions), "cached": False}
        except Exception as e:
            self.logger.warning(f"Version history fetch failed: {e}")
            return {"error": str(e), "versions": [], "count": 0}
    
    async def _tool_restore_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Restore version with sync replay in thread pool (k2.6 fix)."""
        engine = self._get_engine()
        if not engine:
            return {"error": "Engine not initialized", "success": False}
        
        version_hash = args.get("version_hash")
        if not version_hash:
            return self._error_response("version_hash is required")
        
        # Find event with matching ID
        all_events = engine.event_store.events
        target_idx = None
        for idx, e in enumerate(all_events):
            if e.event_id == version_hash:
                target_idx = idx
                break
        
        if target_idx is None:
            return {"error": f"Version '{version_hash}' not found", "success": False}
        
        # Replay events in thread pool with timeout (k2.6 fix)
        try:
            def _replay():
                from src.state.cognitive_state import CognitiveState
                engine._current_state = CognitiveState()
                engine.dependency_graph = engine.dependency_graph.__class__()
                replayed = 0
                for e in all_events[:target_idx + 1]:
                    from src.engine_api import EngineEvent
                    event = EngineEvent(
                        event_type=e.event_type,
                        timestamp=e.timestamp,
                        data=e.details
                    )
                    engine.update_from_environment(event)
                    replayed += 1
                engine.save_state()
                return replayed
            
            replayed = await self._run_blocking(_replay, timeout=5.0)
            # Invalidate responder caches if available
            if self.responder and hasattr(self.responder, '_invalidate_caches'):
                self.responder._invalidate_caches()
        except Exception as e:
            self.logger.error(f"Version restore failed: {e}")
            return {"error": f"Restore failed: {e}", "success": False}
        
        content = f"""## State Restored

**Restored to:** `{version_hash}`
**Events replayed:** {replayed}
**Timestamp:** {all_events[target_idx].timestamp}

The cognitive state has been reset and replayed up to this point in history.
"""
        
        return {
            "content": content,
            "success": True,
            "restored_hash": version_hash,
            "events_replayed": replayed,
            "target_timestamp": str(all_events[target_idx].timestamp)
        }
