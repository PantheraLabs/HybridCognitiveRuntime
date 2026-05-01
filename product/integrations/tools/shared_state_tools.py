"""
Shared state tools for cross-project state management.

Handles:
- hcr_share_state: Share a value across projects with cache invalidation
- hcr_get_shared_state: Retrieve a shared value by key
- hcr_list_shared_states: List all shared keys

k2.6 fixes:
- share_state: Uses cache lock to prevent race conditions
- get_shared_state: Async I/O via thread pool
- list_shared_states: Async I/O via thread pool with caching
"""

import asyncio
import time
from typing import Any, Dict

from .base_tool import BaseMCPTool


class SharedStateTools(BaseMCPTool):
    """Shared state management with thread-safe cache invalidation."""
    
    def __init__(self, responder=None):
        super().__init__(responder)
        self._cache_ttl = 60.0
        self._shared_keys_cache = None
        self._shared_keys_cache_ts = 0.0
        # Use responder's cache locks if available, else create own
        self._cache_lock = asyncio.Lock()
    
    def _cache_valid(self, cache_ts: float) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - cache_ts) < self._cache_ttl
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route to specific shared state tool."""
        action = args.get("action", "share")
        if action == "share":
            return await self._tool_share_state(args)
        elif action == "get":
            return await self._tool_get_shared_state(args)
        elif action == "list":
            return await self._tool_list_shared_states(args)
        else:
            return self._error_response(f"Unknown shared state action: {action}")
    
    async def _tool_list_shared_states(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List shared states with async I/O and caching."""
        cross_project = self._get_cross_project()
        if not cross_project:
            return {"shared_states": [], "count": 0}
        
        # k2.6: Thread-safe cache check with lock
        async with self._cache_lock:
            if self._cache_valid(self._shared_keys_cache_ts) and self._shared_keys_cache is not None:
                return {
                    "shared_states": self._shared_keys_cache,
                    "count": len(self._shared_keys_cache),
                    "cached": True
                }
        
        try:
            keys = await self._run_blocking(cross_project.list_shared_keys, timeout=5.0)
            async with self._cache_lock:
                self._shared_keys_cache = keys
                self._shared_keys_cache_ts = time.time()
            return {"shared_states": keys, "count": len(keys), "cached": False}
        except Exception as e:
            self.logger.warning(f"List shared states failed: {e}")
            return {"error": str(e), "shared_states": [], "count": 0}
    
    async def _tool_get_shared_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get shared state value with async I/O."""
        cross_project = self._get_cross_project()
        if not cross_project:
            return {"error": "Cross-project manager not initialized", "exists": False}
        
        key = args.get("key")
        if not key:
            return self._error_response("key is required")
        
        try:
            value = await self._run_blocking(
                lambda: cross_project.get_shared_state_value(key),
                timeout=5.0
            )
            
            if value is None:
                return {"error": f"Shared state '{key}' not found", "exists": False}
            
            return {"key": key, "value": value, "exists": True}
        except Exception as e:
            self.logger.warning(f"Get shared state failed: {e}")
            return {"error": str(e), "exists": False}
    
    async def _tool_share_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Share state value with cache invalidation via lock (k2.6 fix)."""
        cross_project = self._get_cross_project()
        if not cross_project:
            return {"error": "Cross-project manager not initialized", "success": False}
        
        key = args.get("key")
        value = args.get("value")
        if key is None:
            return self._error_response("key is required")
        
        try:
            project_id = await self._run_blocking(
                lambda: cross_project.register_project(
                    self.responder.project_path if self.responder else ".", "current"
                ),
                timeout=5.0
            )
            
            success = await self._run_blocking(
                lambda: cross_project.share_state_across_projects(key, value, project_id),
                timeout=5.0
            )
            
            # k2.6: Thread-safe cache invalidation with lock
            if success:
                async with self._cache_lock:
                    self._shared_keys_cache = None
                    self._shared_keys_cache_ts = 0.0
            
            return {"success": success, "key": key}
        except Exception as e:
            self.logger.warning(f"Share state failed: {e}")
            return {"error": str(e), "success": False}
    
    def _get_cross_project(self):
        """Get cross-project manager from responder."""
        if self.responder and hasattr(self.responder, 'cross_project'):
            return self.responder.cross_project
        return None
