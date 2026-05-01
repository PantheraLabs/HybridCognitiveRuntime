"""
Health monitoring tools for HCR system diagnostics.

Handles:
- hcr_get_system_health: Returns component status and metrics

k2.6 fixes:
- Caches health results for 60s to avoid repeated expensive checks
- Runs blocking metrics in thread pool
- Returns structured component status (engine, storage, cross_project, security)
"""

import time
from datetime import datetime
from typing import Any, Dict

from .base_tool import BaseMCPTool


class HealthTools(BaseMCPTool):
    """System health monitoring with caching and async metrics gathering."""
    
    def __init__(self, responder=None):
        super().__init__(responder)
        self._cache_ttl = 60.0
        self._health_cache = None
        self._health_cache_ts = 0.0
    
    def _cache_valid(self, cache_ts: float) -> bool:
        return (time.time() - cache_ts) < self._cache_ttl
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Return system health status with caching."""
        return await self._tool_get_system_health(args)
    
    async def _tool_get_system_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health with caching and async metrics gathering."""
        engine = self._get_engine()
        if not engine:
            return {"status": "unhealthy", "error": "Engine not initialized"}
        
        # Return cached health if fresh
        if self._cache_valid(self._health_cache_ts) and self._health_cache is not None:
            cached = self._health_cache.copy()
            cached["cached"] = True
            cached["timestamp"] = datetime.now().isoformat()
            return cached
        
        try:
            def _gather_health():
                state = engine.load_state()
                event_count = len(engine.event_store.events)
                
                cross_project = None
                security = None
                if self.responder:
                    cross_project = getattr(self.responder, 'cross_project', None)
                    security = getattr(self.responder, 'security', None)
                
                projects = 0
                shared = 0
                learned = 0
                if cross_project:
                    try:
                        projects = len(cross_project.get_all_projects())
                        shared = len(cross_project.list_shared_keys())
                        learned = len(cross_project.list_learned_operators())
                    except Exception:
                        pass
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "components": {
                        "engine": "healthy",
                        "state_persistence": "healthy" if state else "no_state",
                        "cross_project": "healthy" if cross_project else "unavailable",
                        "security": "healthy" if security else "unavailable",
                    },
                    "metrics": {
                        "state_exists": state is not None,
                        "event_count": event_count,
                        "projects_registered": projects,
                        "shared_states": shared,
                        "learned_operators": learned,
                    }
                }
            
            health = await self._run_blocking(_gather_health, timeout=5.0)
            self._health_cache = health
            self._health_cache_ts = time.time()
            health["cached"] = False
            return health
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return {
                "status": "degraded",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
