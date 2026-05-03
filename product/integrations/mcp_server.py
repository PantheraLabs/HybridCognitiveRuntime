"""
HCR MCP Server - Model Context Protocol Integration

Exposes HCR state management as MCP tools for integration with:
- Cursor AI
- Windsurf (Cascade)
- Claude Code
- Claude Desktop
- Any MCP-compatible client

This makes HCR the standard state infrastructure layer for AI development tools.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, override=False):
        pass

SMART_RESUME_SYSTEM = """You are the HCR "Resume Without Re-Explaining" formatter.\nReturn JSON with keys:\n- panel_text: fully formatted panel (markdown) matching the classic HCR assistant layout.\n- tone_hint: short note (e.g., high_confidence / low_confidence).\n- summary: single sentence TL;DR.\nRules:\n- Preserve headings and emojis (⏱️, 📋, 📊, 👉, ✅, 📝).\n- Keep suggestions actionable.\n- If data missing, explicitly say so instead of hallucinating.\n- Reflect confidence and time gap accurately.\n"""

# Add project root to path for imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
sys.path.insert(0, str(_project_root))

# Import modular tool handlers
from product.integrations.tools.state_tools import (
    GetStateTool, GetCausalGraphTool, GetRecentActivityTool
)
from product.integrations.tools.task_tools import GetCurrentTaskTool, GetNextActionTool
from product.integrations.tools.session_tools import SessionTools
from product.integrations.tools.shared_state_tools import SharedStateTools
from product.integrations.tools.version_tools import VersionTools
from product.integrations.tools.health_tools import HealthTools
from product.integrations.tools.file_tools import FileTools
from product.integrations.tools.context_tools import ContextTools
from product.integrations.tools.search_tools import SearchTools
from product.integrations.tools.recommendation_tools import RecommendationTools
from product.integrations.tools.operator_tools import OperatorTools
from product.integrations.tools.impact_tools import ImpactTools
from product.integrations.tools.output_synthesizer import OutputSynthesizer

# MCP Protocol Types
@dataclass
class MCPTool:
    """MCP Tool Definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class MCPResource:
    """MCP Resource Definition"""
    uri: str
    name: str
    description: str
    mime_type: str

@dataclass
class MCPPrompt:
    """MCP Prompt Definition"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]


class HCRMCPResponder:
    """
    HCR MCP Responder - Handles MCP protocol requests.
    
    Implements the Model Context Protocol to expose HCR functionality
    to any MCP-compatible client (Cursor, Windsurf, Claude, etc.)
    """
    
    def __init__(self, project_path: Optional[str] = None):
        # Derive project path from __file__ so .env is found even if CWD is elsewhere
        self.project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) or str(Path.cwd())
        self.logger = logging.getLogger("HCR-MCP")
        
        # Load .env file from project root to ensure LLM API keys are available
        env_file = Path(self.project_path) / ".env"
        if env_file.exists():
            load_dotenv(dotenv_path=str(env_file), override=True)
            self.logger.info(f"Loaded .env from {env_file}")
        else:
            # Fallback to CWD .env
            load_dotenv(override=True)
        
        # Rate limiting: max 30 calls per minute per tool
        self._rate_limits: Dict[str, List[float]] = {}
        self._max_calls_per_minute = 30
        
        # Circuit breaker for resilience (PHASE 2 FIX)
        # Prevents cascading failures from repeated errors
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {
            'engine': {'failures': 0, 'last_failure_time': 0.0, 'state': 'closed'},
            'git': {'failures': 0, 'last_failure_time': 0.0, 'state': 'closed'},
            'files': {'failures': 0, 'last_failure_time': 0.0, 'state': 'closed'},
            'llm': {'failures': 0, 'last_failure_time': 0.0, 'state': 'closed'},
        }
        self._circuit_breaker_threshold = 5  # failures before tripping
        self._circuit_breaker_reset_time = 30.0  # seconds before half-open

        # Thread pool for blocking operations (LLM calls, git, filesystem)
        # FIXED: Increased from 4 to 16 to handle concurrent requests without bottleneck
        # 4 workers was causing thread starvation in production
        self._executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="hcr-mcp")

        # Session-aware context windows (per IDE pane)
        self._session_states: Dict[str, Dict[str, Any]] = {}
        self._session_private_notes: Dict[str, List[str]] = defaultdict(list)
        
        # Caching infrastructure for commercial-grade reliability
        self._cache_ttl = 60.0  # seconds
        self._shared_keys_cache: Optional[List[str]] = None
        self._shared_keys_cache_ts = 0.0
        self._learned_ops_cache: Optional[List[str]] = None
        self._learned_ops_cache_ts = 0.0
        self._health_cache: Optional[Dict[str, Any]] = None
        self._health_cache_ts = 0.0
        self._version_cache: Optional[List[Dict[str, Any]]] = None
        self._version_cache_ts = 0.0
        self._state_cache_mtime = 0.0
        self._state_cached = False
        
        # Cache locks for thread-safe access (PHASE 2 FIX)
        # Prevents race conditions on cache writes from concurrent requests
        self._cache_locks = {
            'shared_keys': asyncio.Lock(),
            'learned_ops': asyncio.Lock(),
            'health': asyncio.Lock(),
            'version': asyncio.Lock(),
        }
        
        # Lock for protecting shared state (rate limits, circuit breakers, tracing)
        self._lock = asyncio.Lock()
        
        # Request tracing for observability (PHASE 2 FIX)
        # Tracks request ID and performance metrics
        self._request_counter = 0
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Auto-start daemon if not running (daemon provides background tracking)
        # FIXED: Run in background thread to avoid blocking initialization (k2.6)
        import threading
        daemon_thread = threading.Thread(target=self._ensure_daemon_running, daemon=True)
        daemon_thread.start()
        
        try:
            # Import HCR modules - use HCREngine for proper state management
            from src.engine_api import HCREngine, EngineEvent
            from product.storage.state_persistence import (
                CrossProjectStateManager,
                DevStatePersistence,
            )
            from product.security.enterprise_security import EnterpriseSecurityManager
            
            self.engine = HCREngine(self.project_path)
            self.cross_project = CrossProjectStateManager()
            self.persistence = DevStatePersistence(self.project_path)
            self.security = EnterpriseSecurityManager()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error(f"Failed to initialize HCR modules: {e}\n{tb}")

            # Persist the init error so IDEs can read it even if stdout is hidden
            try:
                project_root = Path(self.project_path or Path.cwd())
                hcr_dir = project_root / ".hcr"
                hcr_dir.mkdir(exist_ok=True)
                error_file = hcr_dir / "mcp_server_init_errors.log"
                with open(error_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] {e}\n{tb}\n")
            except Exception as log_exc:
                self.logger.warning(f"Failed to persist MCP init error: {log_exc}")
            self.engine = None
            self.cross_project = None
            self.persistence = None
            self.security = None
        
        # Commercial-grade output synthesizer (uses Groq via engine LLM)
        self._synthesizer = OutputSynthesizer(
            engine=self.engine,
            use_llm=True,          # Enable smart synthesis via Groq
            llm_timeout=2.0,       # 2s max — never block the IDE
        )
        
        # Instantiate modular tool handlers
        self._tool_instances = self._init_tool_instances()
        
        # Define available tools
        self.tools = self._define_tools()
        self.resources = self._define_resources()
        self.prompts = self._define_prompts()
    
    def _init_tool_instances(self) -> Dict[str, Any]:
        """Initialize all modular MCP tool handlers."""
        instances = {}
        
        # State tools (1:1 mapping)
        instances['hcr_get_state'] = GetStateTool(self)
        instances['hcr_get_causal_graph'] = GetCausalGraphTool(self)
        instances['hcr_get_recent_activity'] = GetRecentActivityTool(self)
        
        # Task tools (1:1 mapping)
        instances['hcr_get_current_task'] = GetCurrentTaskTool(self)
        instances['hcr_get_next_action'] = GetNextActionTool(self)
        
        # Session tools (multi-action: inject action based on tool name)
        session_tools = SessionTools(self)
        instances['hcr_create_session'] = session_tools
        instances['hcr_set_session_note'] = session_tools
        instances['hcr_merge_session'] = session_tools
        instances['hcr_list_sessions'] = session_tools
        
        # Shared state tools (multi-action)
        shared_tools = SharedStateTools(self)
        instances['hcr_share_state'] = shared_tools
        instances['hcr_get_shared_state'] = shared_tools
        instances['hcr_list_shared_states'] = shared_tools
        
        # Version tools (multi-action)
        version_tools = VersionTools(self)
        instances['hcr_get_version_history'] = version_tools
        instances['hcr_restore_version'] = version_tools
        
        # Single-purpose tools
        instances['hcr_get_system_health'] = HealthTools(self)
        instances['hcr_record_file_edit'] = FileTools(self)
        instances['hcr_capture_full_context'] = ContextTools(self)
        instances['hcr_search_history'] = SearchTools(self)
        instances['hcr_get_recommendations'] = RecommendationTools(self)
        instances['hcr_get_learned_operators'] = OperatorTools(self)
        instances['hcr_analyze_impact'] = ImpactTools(self)
        
        return instances
    
    def _ensure_daemon_running(self):
        """Auto-start daemon if not already running - ensures background tracking"""
        try:
            from product.daemon.hcr_daemon import HCRDaemon
            # Pass the responder's engine so the daemon persists tool-call state changes,
            # instead of using a separate engine whose state never updates.
            daemon = HCRDaemon(self.project_path, engine=self.engine)
            daemon.start()
        except Exception as e:
            self.logger.warning(f"Could not auto-start daemon: {e}")
            # Continue without daemon - engine will still work
    
    async def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool call is within rate limit. Returns True if allowed."""
        from time import time
        
        async with self._lock:
            now = time()
            minute_ago = now - 60
            
            # Get calls for this tool in last minute
            calls = self._rate_limits.get(tool_name, [])
            calls = [t for t in calls if t > minute_ago]  # Filter to last minute
            
            if len(calls) >= self._max_calls_per_minute:
                return False
            
            calls.append(now)
            self._rate_limits[tool_name] = calls
            return True
    
    async def _check_circuit_breaker(self, component: str) -> tuple[bool, str]:
        """Check circuit breaker state for a component.
        Returns (allowed: bool, reason: str)
        
        PHASE 2: Prevent cascading failures with circuit breaker pattern.
        States: 'closed' (normal), 'open' (rejecting), 'half-open' (testing recovery)
        """
        from time import time
        
        async with self._lock:
            cb = self._circuit_breakers.get(component)
            if not cb:
                return True, "Unknown component"
            
            now = time()
            
            # If closed, check if we should remain closed
            if cb['state'] == 'closed':
                if cb['failures'] >= self._circuit_breaker_threshold:
                    cb['state'] = 'open'
                    cb['last_failure_time'] = now
                    return False, f"Circuit breaker open for {component} (too many failures)"
                return True, "Circuit breaker closed (normal)"
            
            # If open, check if we should try half-open (recovery test)
            elif cb['state'] == 'open':
                if now - cb['last_failure_time'] > self._circuit_breaker_reset_time:
                    cb['state'] = 'half-open'
                    self.logger.info(f"Circuit breaker {component} entering half-open state")
                    return True, f"Circuit breaker half-open for {component} (recovery test)"
                return False, f"Circuit breaker open for {component}"
            
            # If half-open, allow the call to test recovery
            else:  # half-open
                return True, "Circuit breaker half-open (recovery test)"
    
    async def _record_circuit_breaker_success(self, component: str):
        """Record successful operation to recover from open circuit."""
        async with self._lock:
            cb = self._circuit_breakers.get(component)
            if cb and cb['state'] == 'half-open':
                cb['failures'] = 0
                cb['state'] = 'closed'
                self.logger.info(f"Circuit breaker {component} recovered to closed state")
            elif cb:
                cb['failures'] = max(0, cb['failures'] - 1)  # Decay failures slowly
    
    async def _record_circuit_breaker_failure(self, component: str):
        """Record failure to track component health."""
        from time import time
        async with self._lock:
            cb = self._circuit_breakers.get(component)
            if cb:
                cb['failures'] += 1
                cb['last_failure_time'] = time()
                if cb['state'] == 'half-open':
                    cb['state'] = 'open'
                    self.logger.warning(f"Circuit breaker {component} re-opened (recovery failed)")
    
    async def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracing (PHASE 2)."""
        from datetime import datetime
        import uuid
        async with self._lock:
            self._request_counter += 1
            request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._request_counter}_{str(uuid.uuid4())[:8]}"
            return request_id
    
    async def _trace_request_start(self, request_id: str, tool_name: str, args: Dict[str, Any]):
        """Record request start for observability (PHASE 2)."""
        import time
        async with self._lock:
            self._active_requests[request_id] = {
                'tool': tool_name,
                'start_time': time.time(),
                'args_keys': list(args.keys()) if args else [],
                'status': 'running'
            }
    
    async def _trace_request_end(self, request_id: str, status: str, duration_ms: float = 0):
        """Record request completion (PHASE 2)."""
        async with self._lock:
            if request_id in self._active_requests:
                self._active_requests[request_id]['status'] = status
                self._active_requests[request_id]['duration_ms'] = duration_ms
                # Keep last 100 requests for debugging
                if len(self._active_requests) > 100:
                    oldest_id = next(iter(self._active_requests))
                    del self._active_requests[oldest_id]
                self.logger.debug(f"[{request_id}] {self._active_requests[request_id]['tool']} completed in {duration_ms}ms: {status}")
    
    async def _run_blocking(self, fn, timeout: float = 5.0) -> Any:
        """Run a blocking function in the thread pool with timeout.
        
        FIXED: Reduced default timeout from 15s to 5s for faster failure modes.
        This prevents AI IDE from hanging on slow operations.
        """
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, fn),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation exceeded {timeout}s timeout")
    
    def _cache_valid(self, cache_ts: float) -> bool:
        """Check if a cache entry is still valid."""
        return (time.time() - cache_ts) < self._cache_ttl
    
    def _invalidate_caches(self):
        """Invalidate all caches after state mutation."""
        self._shared_keys_cache = None
        self._shared_keys_cache_ts = 0.0
        self._learned_ops_cache = None
        self._learned_ops_cache_ts = 0.0
        self._version_cache = None
        self._version_cache_ts = 0.0
        self._health_cache = None
        self._health_cache_ts = 0.0
    
    def _define_tools(self) -> List[MCPTool]:
        """Define MCP tools exposed by HCR"""
        return [
            MCPTool(
                name="hcr_get_state",
                description="Get current HCR cognitive state for this project",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_history": {
                            "type": "boolean",
                            "description": "Include state history",
                            "default": False
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_get_causal_graph",
                description="Get the causal dependency graph for this project",
                input_schema={
                    "type": "object",
                    "properties": {
                        "graph_name": {
                            "type": "string",
                            "description": "Name of the causal graph",
                            "default": "main"
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_get_recent_activity",
                description="Get recent developer activity from HCR state",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of activities to return",
                            "default": 10
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_get_current_task",
                description="Get inferred current task from HCR analysis",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_get_next_action",
                description="Get HCR-suggested next action",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_list_shared_states",
                description="List all shared states across projects",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_get_shared_state",
                description="Get a shared state value by key",
                input_schema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Shared state key"
                        }
                    },
                    "required": ["key"]
                }
            ),
            MCPTool(
                name="hcr_share_state",
                description="Share a state value across projects",
                input_schema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Key to share"
                        },
                        "value": {
                            "description": "Value to share",
                            "oneOf": [
                                {"type": "string"},
                                {"type": "number"},
                                {"type": "integer"},
                                {"type": "boolean"},
                                {"type": "object"},
                                {"type": "array", "items": {}},
                                {"type": "null"}
                            ]
                        }
                    },
                    "required": ["key", "value"]
                }
            ),
            MCPTool(
                name="hcr_get_version_history",
                description="Get state version history (like git log)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of versions to return",
                            "default": 20
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_restore_version",
                description="Restore state to a specific version",
                input_schema={
                    "type": "object",
                    "properties": {
                        "version_hash": {
                            "type": "string",
                            "description": "Version hash to restore"
                        }
                    },
                    "required": ["version_hash"]
                }
            ),
            MCPTool(
                name="hcr_get_learned_operators",
                description="Get learned operators available across projects",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_list_sessions",
                description="List all active HCR sessions (context windows)",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_create_session",
                description="Create a new HCR session (context window) with optional tag",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique session identifier (e.g., 'auth-refactor-pane')"
                        },
                        "tag": {
                            "type": "string",
                            "description": "Human-readable label for this context window",
                            "default": "untitled"
                        },
                        "clone_from": {
                            "type": "string",
                            "description": "Optional session_id to clone state from",
                            "default": ""
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="hcr_set_session_note",
                description="Add a private note to a specific session",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session to add note to"
                        },
                        "note": {
                            "type": "string",
                            "description": "Note text to remember for this context window"
                        }
                    },
                    "required": ["session_id", "note"]
                }
            ),
            MCPTool(
                name="hcr_merge_session",
                description="Merge session-specific facts back into global state",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session to merge into global state"
                        },
                        "preserve_notes": {
                            "type": "boolean",
                            "description": "Keep private notes after merge",
                            "default": True
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="hcr_get_system_health",
                description="Get HCR system health metrics",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="hcr_record_file_edit",
                description="Record a file edit event with detailed change information to update HCR state",
                input_schema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Relative path to the file that was edited"
                        },
                        "old_content": {
                            "type": "string",
                            "description": "Previous content of the file (for diff computation)"
                        },
                        "change_summary": {
                            "type": "string",
                            "description": "Human-readable summary of what changed"
                        },
                        "lines_added": {
                            "type": "integer",
                            "description": "Number of lines added",
                            "default": 0
                        },
                        "lines_removed": {
                            "type": "integer",
                            "description": "Number of lines removed",
                            "default": 0
                        },
                        "functions_changed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of function names that were added/removed/modified",
                            "default": []
                        },
                        "imports_changed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of imports that were added/removed",
                            "default": []
                        }
                    },
                    "required": ["filepath"]
                }
            ),
            MCPTool(
                name="hcr_capture_full_context",
                description="Capture complete developer context including git state, recent files, and current cognitive state",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_diffs": {
                            "type": "boolean",
                            "description": "Include detailed file diffs",
                            "default": True
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_analyze_impact",
                description="Analyze the ripple effect of changing a specific file using the causal dependency graph",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to analyze (relative to project root)"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth for impact propagation (1-5)",
                            "default": 3
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            MCPTool(
                name="hcr_get_recommendations",
                description="Get AI-powered recommendations for next actions with confidence scores",
                input_schema={
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "string",
                            "description": "Additional context about what you're working on"
                        },
                        "use_llm": {
                            "type": "boolean",
                            "description": "Use LLM for enhanced recommendations",
                            "default": True
                        }
                    }
                }
            ),
            MCPTool(
                name="hcr_search_history",
                description="Search event history for specific patterns, file changes, or keywords",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (file path, keyword, or event type)"
                        },
                        "event_type": {
                            "type": "string",
                            "description": "Filter by event type (file_edit, git_commit, etc.)",
                            "default": ""
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 20
                        }
                    },
                    "required": ["query"]
                }
            ),
        ]
    
    def _define_resources(self) -> List[MCPResource]:
        """Define MCP resources exposed by HCR"""
        return [
            MCPResource(
                uri="hcr://state/current",
                name="Current HCR State",
                description="The current cognitive state of the HCR engine",
                mime_type="application/json"
            ),
            MCPResource(
                uri="hcr://causal-graph/main",
                name="Main Causal Graph",
                description="The primary causal dependency graph",
                mime_type="application/json"
            ),
            MCPResource(
                uri="hcr://task/current",
                name="Current Task",
                description="The inferred current development task",
                mime_type="text/plain"
            ),
        ]
    
    def _define_prompts(self) -> List[MCPPrompt]:
        """Define MCP prompts exposed by HCR"""
        return [
            MCPPrompt(
                name="hcr_resume_session",
                description="Resume HCR session without re-explaining context",
                arguments=[
                    {
                        "name": "time_gap_minutes",
                        "description": "Minutes since last activity",
                        "required": False
                    }
                ]
            ),
            MCPPrompt(
                name="hcr_context_aware_coding",
                description="Get coding assistance with full HCR context",
                arguments=[
                    {
                        "name": "query",
                        "description": "The coding question or task",
                        "required": True
                    }
                ]
            ),
        ]
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP protocol request.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary with jsonrpc 2.0 envelope
        """
        # Validate JSON-RPC 2.0 request
        if not isinstance(request, dict):
            return self._error_response("Invalid request: not a JSON object", -32600)
        
        jsonrpc = request.get("jsonrpc")
        if jsonrpc != "2.0":
            return self._error_response("Invalid JSON-RPC version. Expected '2.0'", -32600)
        
        method = request.get("method")
        if not method or not isinstance(method, str):
            return self._error_response("Invalid request: missing or invalid 'method'", -32600)
        
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Request size limit check (1MB)
        request_size = len(json.dumps(request))
        if request_size > 1_000_000:
            return self._error_response("Request too large: max 1MB", -32600)
        
        try:
            if method == "initialize":
                result_data = await self._handle_initialize(params)
            elif method == "tools/list":
                result_data = await self._handle_tools_list(params)
            elif method == "tools/call":
                result_data = await self._handle_tools_call(params)
            elif method == "resources/list":
                result_data = await self._handle_resources_list(params)
            elif method == "resources/read":
                result_data = await self._handle_resources_read(params)
            elif method == "prompts/list":
                result_data = await self._handle_prompts_list(params)
            elif method == "prompts/get":
                result_data = await self._handle_prompts_get(params)
            else:
                result_data = self._error_response(f"Unknown method: {method}")
            
            # Extract result from handler (handlers return {"result": ...} or {"error": ...})
            if "result" in result_data:
                response = {
                    "jsonrpc": "2.0",
                    "result": result_data["result"]
                }
            elif (
                "error" in result_data
                and isinstance(result_data["error"], dict)
                and "message" in result_data["error"]
            ):
                response = {
                    "jsonrpc": "2.0",
                    "error": result_data["error"]
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "result": result_data
                }
            
            if request_id is not None:
                response["id"] = request_id
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            error_response = self._error_response(str(e))
            response = {
                "jsonrpc": "2.0",
                "error": error_response.get("error", {})
            }
            if request_id is not None:
                response["id"] = request_id
            return response
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "hcr-mcp-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                }
            }
        }
    
    def _tool_to_dict(self, tool: MCPTool) -> Dict[str, Any]:
        """Convert MCPTool to dict with camelCase field names"""
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema  # camelCase for MCP spec
        }
    
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        return {
            "result": {
                "tools": [self._tool_to_dict(tool) for tool in self.tools]
            }
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and record as HCR event"""
        import time
        
        # PHASE 2: Generate request ID for tracing
        request_id = await self._generate_request_id()
        start_time = time.time()
        
        # FIXED: Added input validation to prevent DoS and injection attacks
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments", {}) if isinstance(params, dict) else {}
        
        # PHASE 2: Trace request start
        await self._trace_request_start(request_id, name or "unknown", arguments)
        
        if not isinstance(name, str) or not name.startswith("hcr_"):
            await self._trace_request_end(request_id, "invalid_input", (time.time() - start_time) * 1000)
            return self._error_response("Invalid tool name")
        
        if not isinstance(arguments, dict):
            await self._trace_request_end(request_id, "invalid_args", (time.time() - start_time) * 1000)
            return self._error_response("Arguments must be an object")
        
        # FIXED: Limit argument payload to 100KB
        if len(json.dumps(arguments)) > 100_000:
            await self._trace_request_end(request_id, "payload_exceeded", (time.time() - start_time) * 1000)
            return self._error_response("Arguments payload exceeds 100KB")
        
        session_id = arguments.get("session_id") if isinstance(arguments, dict) else None
        
        # Log tool invocation as event to update context (fire-and-forget, non-blocking)
        if self.engine:
            try:
                from src.engine_api import EngineEvent
                from datetime import datetime
                event = EngineEvent(
                    event_type='mcp_tool_call',
                    timestamp=datetime.now(),
                    data={'tool': name, 'args': arguments}
                )
                # Don't block tool execution on disk write
                asyncio.get_running_loop().run_in_executor(
                    self._executor, self.engine.update_from_environment, event
                )
            except Exception:
                pass  # Logging failures should never break tool calls
        
        # Route to modular tool instance
        # Multi-action tools need action injected based on tool name
        _tool_action_map = {
            'hcr_create_session': 'create',
            'hcr_set_session_note': 'set_note',
            'hcr_merge_session': 'merge',
            'hcr_list_sessions': 'list',
            'hcr_share_state': 'share',
            'hcr_get_shared_state': 'get',
            'hcr_list_shared_states': 'list',
            'hcr_get_version_history': 'history',
            'hcr_restore_version': 'restore',
        }
        
        tool_instance = self._tool_instances.get(name)
        if not tool_instance:
            return self._error_response(f"Unknown tool: {name}")
        
        # Inject action for multi-action tools
        if name in _tool_action_map:
            arguments = dict(arguments)
            arguments['action'] = _tool_action_map[name]
        
        # Check rate limit
        if not await self._check_rate_limit(name):
            return {
                "result": {
                    "content": [{"type": "text", "text": f"Rate limit exceeded for {name}. Max 30 calls per minute."}],
                    "isError": True
                }
            }
        
        # Smart state loading: only reload if file changed (optimization)
        # Skip for fast read-only tools that don't need fresh state
        fast_tools = {"hcr_get_state", "hcr_get_causal_graph", "hcr_get_current_task", 
                      "hcr_get_next_action", "hcr_get_system_health", "hcr_list_shared_states",
                      "hcr_get_shared_state", "hcr_get_version_history", "hcr_get_learned_operators",
                      "hcr_list_sessions", "hcr_search_history"}
        
        if self.engine and name not in fast_tools:
            try:
                state_file = self.engine.state_file
                current_mtime = 0
                if state_file.exists():
                    current_mtime = state_file.stat().st_mtime
                
                # Only reload if file modified since last cache
                if not self._state_cached or current_mtime > self._state_cache_mtime:
                    try:
                        await self._run_blocking(self.engine.load_state, timeout=2.0)
                        self._state_cache_mtime = current_mtime
                        self._state_cached = True
                        self.logger.debug(f"State loaded from disk (mtime: {current_mtime})")
                    except Exception as e:
                        self.logger.warning(f"State load timed out: {e}")
                        # Continue with potentially stale state rather than hang
                else:
                    self.logger.debug("Using cached state (file unchanged)")
            except Exception as e:
                self.logger.warning(f"Failed to preload state: {e}")
        
        # FIXED: Reduced timeout from 15s to 5s for faster failure modes
        try:
            result = await asyncio.wait_for(tool_instance.execute(arguments), timeout=5.0)
            # PHASE 2: Trace successful completion
            duration_ms = (time.time() - start_time) * 1000
            await self._trace_request_end(request_id, "success", duration_ms)
            # Normalize & synthesize tool result to commercial-grade MCP format
            return await self._normalize_tool_result(result, session_id=session_id, tool_name=name)
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            await self._trace_request_end(request_id, "timeout", duration_ms)
            self.logger.warning(f"[{request_id}] Tool {name} timed out after 5s")
            return {
                "result": {
                    "content": [{"type": "text", "text": f"⏱️ Tool '{name}' exceeded 5s timeout.\n\nThis usually means:\n- LLM inference is slow\n- Git operations on large repo\n- File diff computation\n\nTry with simpler inputs or check system resources. Run `hcr_get_system_health` to diagnose."}],
                    "isError": True
                }
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            await self._trace_request_end(request_id, "error", duration_ms)
            self.logger.error(f"[{request_id}] Tool {name} failed with exception: {e}", exc_info=True)
            return {
                "result": {
                    "content": [{"type": "text", "text": f"❌ Tool '{name}' failed: {str(e)[:100]}\n\nDebug info:\n- Request ID: {request_id}\n- Error type: {type(e).__name__}\n- Timestamp: {datetime.now().isoformat()}\n\nCheck engine status with `hcr_get_system_health`."}],
                    "isError": True
                }
            }

    def _format_structured_result(self, result: Dict[str, Any]) -> str:
        """Intelligently format structured tool output into human-readable markdown.

        Handles common tool response shapes: graph, task, state, sessions,
        operators, recommendations, version history, etc.
        """
        parts: list[str] = []

        # --- Graph output ---
        if "graph" in result:
            g = result["graph"]
            parts.append("## Causal Dependency Graph")
            forward = g.get("forward", {})
            if forward:
                parts.append("\n### Forward Dependencies")
                for src, deps in forward.items():
                    parts.append(f"- **{src}** → {', '.join(deps)}")
            else:
                parts.append("\nNo forward dependencies recorded.")
            reverse = g.get("reverse", {})
            if reverse:
                parts.append("\n### Reverse Dependencies")
                for tgt, srcs in reverse.items():
                    parts.append(f"- **{tgt}** ← {', '.join(srcs)}")
            parts.append(f"\n*Total forward edges: {len(forward)} | reverse edges: {len(reverse)}*")
            return "\n".join(parts)

        # --- Task output ---
        if "task" in result:
            parts.append(f"## Current Task: {result.get('task', 'Unknown')}")
            if "progress_percent" in result:
                bar = "█" * int(result["progress_percent"] / 5) + "░" * (20 - int(result["progress_percent"] / 5))
                parts.append(f"\nProgress: [{bar}] {result['progress_percent']}%")
            return "\n".join(parts)

        # --- Next action output ---
        if "next_action" in result:
            parts.append(f"## Recommended Next Action\n\n{result.get('next_action', 'Unknown')}")
            if "confidence" in result:
                conf = result["confidence"]
                if isinstance(conf, float):
                    parts.append(f"\nConfidence: {conf:.0%}")
                else:
                    parts.append(f"\nConfidence: {conf}")
            return "\n".join(parts)

        # --- Sessions list ---
        if "sessions" in result:
            sessions = result.get("sessions", [])
            parts.append(f"## Active HCR Sessions ({len(sessions)})\n")
            for s in sessions:
                sid = s.get("session_id", "unknown")
                tag = s.get("tag", "untitled")
                last = s.get("last_active", "?")
                notes = s.get("notes_count", 0)
                preview = s.get("preview", "")
                parts.append(f"- **{sid}** ({tag})")
                parts.append(f"  Last active: {last} | Notes: {notes}")
                if preview:
                    parts.append(f"  Preview: {preview}")
                parts.append("")
            return "\n".join(parts)

        # --- Operators / learned patterns ---
        if "operators" in result:
            ops = result.get("operators", [])
            parts.append(f"## Learned Operators ({len(ops)})\n")
            if ops:
                for i, op in enumerate(ops[:20], 1):
                    parts.append(f"{i}. `{op}`")
            else:
                parts.append("No operators learned yet.")
            return "\n".join(parts)

        # --- Recommendations ---
        if "recommendations" in result:
            recs = result.get("recommendations", [])
            parts.append(f"## AI Recommendations ({len(recs)})\n")
            for r in recs:
                action = r.get("action", "?")
                conf = r.get("confidence", 0.0)
                if isinstance(conf, float):
                    parts.append(f"- **{action}** (confidence: {conf:.0%})")
                else:
                    parts.append(f"- **{action}** (confidence: {conf})")
            return "\n".join(parts)

        # --- Version history ---
        if "versions" in result:
            versions = result.get("versions", [])
            parts.append(f"## Version History ({len(versions)})\n")
            for v in versions[:20]:
                ts = v.get("timestamp", v.get("created", "?"))
                msg = v.get("message", "no message")
                author = v.get("author", "?")
                parts.append(f"- `{ts}` — {msg} ({author})")
            return "\n".join(parts)

        # --- Shared states ---
        if "shared_states" in result:
            states = result.get("shared_states", [])
            parts.append(f"## Shared States ({len(states)})\n")
            if states:
                for k in states:
                    parts.append(f"- `{k}`")
            else:
                parts.append("No shared states.")
            return "\n".join(parts)

        # --- Impact analysis ---
        if "impacted_files" in result:
            files = result.get("impacted_files", [])
            parts.append(f"## Impact Analysis\n\n**{len(files)} file(s) potentially impacted:**\n")
            for f in files[:20]:
                parts.append(f"- `{f}`")
            return "\n".join(parts)

        # --- Shared state key-value ---
        if "key" in result and "value" in result:
            parts.append(f"## Shared State: `{result.get('key')}`")
            val = result.get("value")
            parts.append(f"Value: `{str(val)[:200]}`")
            if len(str(val)) > 200:
                parts.append("*(truncated)*")
            return "\n".join(parts)

        # --- System health / status ---
        if "status" in result or "error" in result:
            status = result.get("status", "unknown")
            error = result.get("error", "")
            if error:
                parts.append(f"## Status: {status}\n\n⚠️ {error}")
            else:
                parts.append(f"## Status: {status}")
                for k, v in result.items():
                    if k not in ("status", "error"):
                        parts.append(f"- **{k}**: {v}")
            return "\n".join(parts)

        # --- Generic error state ---
        if result.get("isError"):
            err = result.get("error", "Unknown error")
            return f"❌ Error: {err}"

        # --- Success confirmation ---
        if result.get("success") is True:
            msg = result.get("message", result.get("content", "Operation completed successfully."))
            return f"✅ {msg}"
        if result.get("success") is False:
            err = result.get("error", result.get("message", "Operation failed."))
            return f"❌ {err}"

        # --- Fallback: clean JSON ---
        import json
        return json.dumps(result, indent=2, default=str)

    async def _normalize_tool_result(
        self, result: Any, session_id: Optional[str] = None, tool_name: Optional[str] = ""
    ) -> Dict[str, Any]:
        """Normalize and synthesize any tool result into commercial-grade MCP output.

        Two-stage pipeline:
        1. Synthesis (optional): Feed raw data to Groq LLM for polished markdown.
           Skipped for simple confirmation tools; 2s timeout; cached per data hash.
        2. Normalization: Wrap in standard MCP {"content": [{"type":"text","text":...}]} format.
        """
        import json

        # --- Stage 1: Commercial-grade synthesis (fast path for simple tools) ---
        synthesized_text: Optional[str] = None
        if (
            isinstance(result, dict)
            and tool_name
            and self._synthesizer
            and tool_name not in {"hcr_create_session", "hcr_set_session_note", "hcr_merge_session",
                                   "hcr_share_state", "hcr_get_shared_state", "hcr_record_file_edit",
                                   "hcr_restore_version"}
        ):
            try:
                synthesized_text = await asyncio.wait_for(
                    self._synthesizer.synthesize_async(tool_name, result),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                self.logger.debug(f"Synthesis timeout for {tool_name}, falling back to fast format")
            except Exception as e:
                self.logger.debug(f"Synthesis failed for {tool_name}: {e}")

        # --- Stage 2: Normalization into MCP protocol format ---
        if not isinstance(result, dict):
            return {"result": {"content": [{"type": "text", "text": str(result)}], "isError": False}}

        if "content" in result:
            content = result.get("content", "")
            if isinstance(content, str):
                # Use synthesized text if available, else original content
                text_content = synthesized_text if synthesized_text is not None else content
                remaining = {k: v for k, v in result.items() if k != "content"}
                # Append metadata only if NOT synthesized (synthesized already includes structured insight)
                if remaining and synthesized_text is None:
                    try:
                        meta_json = json.dumps(remaining, indent=2, default=str)
                        text_content += f"\n\n[Metadata: {meta_json}]"
                    except (TypeError, ValueError):
                        pass
                if session_id and "session_snapshot" not in remaining:
                    self._record_session_snapshot(session_id, text_content, remaining)
                return {
                    "result": {
                        "content": [{"type": "text", "text": text_content}],
                        "isError": result.get("isError", False)
                    }
                }
            elif isinstance(content, list):
                if session_id:
                    remaining = {k: v for k, v in result.items() if k != "content"}
                    text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                    if text_parts:
                        self._record_session_snapshot(session_id, "\n".join(text_parts), remaining)
                return {"result": result}
            else:
                return {
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
                        "isError": False
                    }
                }
        else:
            # No content field: intelligently format structured data
            if synthesized_text is not None:
                text_content = synthesized_text
            else:
                text_content = self._format_structured_result(result)
            return {
                "result": {
                    "content": [{"type": "text", "text": text_content}],
                    "isError": False
                }
            }

    def _resource_to_dict(self, resource: MCPResource) -> Dict[str, Any]:
        """Convert MCPResource to dict with camelCase field names"""
        return {
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mimeType": resource.mime_type  # camelCase for MCP spec
        }
    
    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources"""
        return {
            "result": {
                "resources": [self._resource_to_dict(r) for r in self.resources]
            }
        }
    
    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource with async I/O to avoid blocking the event loop."""
        uri = params.get("uri")
        mime_type = "application/json"
        
        if not self.engine:
            return self._error_response("Engine not initialized")
        
        try:
            if uri == "hcr://state/current":
                # State already loaded by _handle_tools_call / engine init
                def _get_state():
                    state = self.engine._current_state
                    return json.dumps(state.to_dict(), indent=2) if state else "{}"
                content = await self._run_blocking(_get_state, timeout=2.0)
            elif uri == "hcr://causal-graph/main":
                # Graph already loaded with state
                def _get_graph():
                    if self.engine.dependency_graph:
                        graph = {
                            "forward": {k: list(v) for k, v in self.engine.dependency_graph.forward_edges.items()},
                            "reverse": {k: list(v) for k, v in self.engine.dependency_graph.reverse_edges.items()}
                        }
                        return json.dumps(graph, indent=2)
                    return "{}"
                content = await self._run_blocking(_get_graph, timeout=2.0)
            elif uri == "hcr://task/current":
                # Fast heuristic inference, no LLM, no redundant load_state
                def _infer_task():
                    context = self.engine.infer_context(use_llm=False)
                    return context.current_task if context else "No current task"
                content = await self._run_blocking(_infer_task, timeout=2.0)
                mime_type = "text/plain"
            else:
                return self._error_response(f"Unknown resource: {uri}")
        except Exception as e:
            self.logger.warning(f"Resource read failed for {uri}: {e}")
            content = f"Error loading resource: {e}"
            mime_type = "text/plain"
        
        return {
            "result": {
                "contents": [{"uri": uri, "mimeType": mime_type, "text": content}]
            }
        }
    
    def _prompt_to_dict(self, prompt: MCPPrompt) -> Dict[str, Any]:
        """Convert MCPPrompt to dict with camelCase field names"""
        return {
            "name": prompt.name,
            "description": prompt.description,
            "arguments": prompt.arguments  # Already correct format
        }
    
    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompts"""
        return {
            "result": {
                "prompts": [self._prompt_to_dict(p) for p in self.prompts]
            }
        }
    
    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a prompt with fast LLM-free fallback."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        use_llm = arguments.get("use_llm", False)  # Default False for speed
        
        if not self.engine:
            return self._error_response("Engine not initialized")
        
        # FIXED: Fast heuristic inference with use_llm=False, reduced timeout to 2s
        try:
            context = await self._run_blocking(lambda: self.engine.infer_context(use_llm=False), timeout=2.0)
        except Exception as e:
            self.logger.warning(f"Prompt inference failed: {e}")
            from src.engine_api import EngineContext
            context = EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Initialize HCR",
                confidence=0.0,
                gap_minutes=0,
                facts=[]
            )
        
        if name == "hcr_resume_session":
            # Calculate gap from _last_saved
            gap = None
            if hasattr(self.engine, '_last_saved') and self.engine._last_saved:
                gap = (datetime.now() - self.engine._last_saved).total_seconds() / 60
            
            prompt_text = await self._generate_smart_resume(context, use_llm=use_llm, mode="resume", gap_override=gap)
            
        elif name == "hcr_context_aware_coding":
            query = arguments.get("query", "")
            prompt_text = await self._generate_smart_resume(context, use_llm=use_llm, mode="coding", extra_query=query)
        else:
            return self._error_response(f"Unknown prompt: {name}")
        
        return {
            "result": {
                "description": f"HCR Prompt: {name}",
                "messages": [{"role": "user", "content": {"type": "text", "text": prompt_text}}]
            }
        }
    
    # --- Tool Implementations ---
    
    async def _tool_get_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current HCR state with formatted output"""
        include_history = args.get("include_history", False)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized. Run 'hcr init' first.", "exists": False}
        
        # State already loaded by _handle_tools_call, just use it
        state = self.engine._current_state
        if not state:
            return {"content": "No HCR state found for this project.", "exists": False}
        
        # Build formatted summary
        facts = state.symbolic.facts[-15:] if state.symbolic.facts else []
        deps = len(state.causal.dependencies)
        events = len(self.engine.event_store.events)
        
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
                from src.causal.event_store import CausalEvent
                recent_events = await self._run_blocking(
                    lambda: self.engine.event_store.get_recent_events(50),
                    timeout=5.0
                )
                result["recent_events"] = [asdict(e) for e in recent_events]
            except Exception as e:
                self.logger.warning(f"History load failed: {e}")
                result["recent_events"] = []
        
        self._record_session_snapshot(session_id, content, {"exists": True})

        return result
    
    async def _tool_get_causal_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get causal graph"""
        if not self.engine:
            return {"error": "Engine not initialized", "exists": False}
        
        # State preloaded by _handle_tools_call
        if not self.engine.dependency_graph:
            return {"content": "No causal graph found for this project. Edit some files to build the graph.", "exists": False}
        
        graph = {
            "forward": {k: list(v) for k, v in self.engine.dependency_graph.forward_edges.items()},
            "reverse": {k: list(v) for k, v in self.engine.dependency_graph.reverse_edges.items()}
        }
        
        return {"graph": graph, "exists": True}
    
    async def _tool_get_recent_activity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent activity from event store - returns formatted activity summary"""
        limit = args.get("limit", 10)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "HCR Engine not initialized. No activity recorded yet.", "activities": []}
        
        # Load events in thread pool to avoid blocking on JSONL read
        try:
            events = await self._run_blocking(
                lambda: self.engine.event_store.get_recent_events(limit),
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
        
        activities = [
            {
                "type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp,
                "details": e.details
            }
            for e in events
        ]
        
        suggested_actions = []
        file_edits = [a for a in activities if a["type"] == "file_edit"]
        if file_edits:
            last_edit = file_edits[0]
            suggested_actions.append({"action": f"Continue editing {last_edit['source']}", "description": last_edit['details'].get('change_summary', 'recent changes')})
        
        tool_calls = [a for a in activities if a["type"] == "mcp_tool_call"]
        if tool_calls:
            last_tool = tool_calls[0]
            suggested_actions.append({"action": f"Continue using tool `{last_tool['source']}`", "description": last_tool['details'].get('args', '')})
        
        if suggested_actions:
            content += f"\n\n**Suggested Actions:**\n"
            for action in suggested_actions:
                content += f"- **{action['action']}**: {action['description']}\n"
        
        # Also return raw data for programmatic use
        snapshot_meta = {"count": len(activities)}
        self._record_session_snapshot(session_id, content, snapshot_meta)
        return {"content": content, "activities": activities, "count": len(activities)}
    
    async def _tool_get_current_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current task from engine context inference - returns formatted context for AI"""
        use_llm = args.get("use_llm", False)  # Default False for speed
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "task": None}
        
        # FIXED: Use use_llm=False for fast heuristic inference, reduced timeout to 2s
        try:
            context = await self._run_blocking(lambda: self.engine.infer_context(use_llm=False), timeout=2.0)
        except Exception as e:
            self.logger.warning(f"Task inference failed: {e}")
            from src.engine_api import EngineContext
            context = EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Initialize HCR",
                confidence=0.0,
                gap_minutes=0,
                facts=[]
            )
        
        summary = await self._generate_smart_resume(context, use_llm=use_llm, mode="resume", session_id=session_id)
        self._record_session_snapshot(session_id, summary, {
            "task": context.current_task,
            "progress_percent": context.progress_percent,
            "mode": "resume"
        })

        return {
            "content": summary,
            "task": context.current_task,
            "progress_percent": context.progress_percent
        }
    
    async def _tool_get_next_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get next action suggestion from engine - returns formatted recommendation"""
        use_llm = args.get("use_llm", False)  # Default False for speed
        session_id = args.get("session_id")

        if not self.engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "task": None}

        
        # FIXED: Use use_llm=False for fast heuristic inference, reduced timeout to 2s
        try:
            context = await self._run_blocking(lambda: self.engine.infer_context(use_llm=False), timeout=2.0)
        except Exception as e:
            self.logger.warning(f"Next action inference failed: {e}")
            from src.engine_api import EngineContext
            context = EngineContext(
                current_task="Unknown",
                progress_percent=0,
                next_action="Initialize HCR",
                confidence=0.0,
                gap_minutes=0,
                facts=[]
            )

        summary = await self._generate_smart_resume(context, use_llm=use_llm, mode="action", session_id=session_id)
        self._record_session_snapshot(session_id, summary, {
            "next_action": context.next_action,
            "confidence": context.confidence,
            "mode": "action"
        })

        return {
            "content": summary,
            "next_action": context.next_action,
            "confidence": context.confidence
        }
    
    async def _tool_list_shared_states(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List shared states with caching."""
        if not self.cross_project:
            return {"content": "No cross-project manager available.", "shared_states": [], "count": 0}
        
        # k2.6 FIX: Use asyncio lock for thread-safe cache access
        async with self._cache_locks['shared_keys']:
            if self._cache_valid(self._shared_keys_cache_ts) and self._shared_keys_cache is not None:
                keys = self._shared_keys_cache
                content = f"## Shared States ({len(keys)})\n\n"
                if keys:
                    for k in keys:
                        content += f"- `{k}`\n"
                else:
                    content += "No shared states.\n"
                return {"content": content, "shared_states": keys, "count": len(keys), "cached": True}
        
        try:
            keys = await self._run_blocking(self.cross_project.list_shared_keys, timeout=5.0)
            async with self._cache_locks['shared_keys']:
                self._shared_keys_cache = keys
                self._shared_keys_cache_ts = time.time()
            content = f"## Shared States ({len(keys)})\n\n"
            if keys:
                for k in keys:
                    content += f"- `{k}`\n"
            else:
                content += "No shared states.\n"
            return {"content": content, "shared_states": keys, "count": len(keys), "cached": False}
        except Exception as e:
            self.logger.warning(f"List shared states failed: {e}")
            return {"content": f"Error listing shared states: {e}", "error": str(e), "shared_states": [], "count": 0}
    
    async def _tool_get_shared_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get a shared state value."""
        if not self.cross_project:
            return {"content": "Cross-project state manager not available.", "error": "Cross-project state manager not available", "exists": False}
        
        key = args.get("key", "")
        if not key:
            return {"content": "`key` parameter is required.", "error": "key is required", "exists": False}
        
        try:
            value = await self._run_blocking(lambda: self.cross_project.get_shared_state(key), timeout=3.0)
            val_str = str(value)[:200] if value is not None else "None"
            content = f"## Shared State: `{key}`\n\nValue: `{val_str}`"
            if value is not None and len(str(value)) > 200:
                content += "\n*(truncated)*"
            return {"content": content, "key": key, "value": value, "exists": value is not None}
        except Exception as e:
            self.logger.warning(f"Get shared state failed: {e}")
            return {"content": f"Error getting shared state `{key}`: {e}", "error": str(e), "exists": False}
    
    async def _tool_share_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Share state with cache invalidation."""
        if not self.cross_project:
            return {"content": "Cross-project manager not initialized.", "error": "Cross-project manager not initialized", "success": False}
        
        key = args.get("key")
        value = args.get("value")
        if not key or value is None:
            return {"content": "`key` and `value` parameters are required.", "error": "key and value are required", "success": False}
        
        try:
            project_id = await self._run_blocking(
                lambda: self.cross_project.register_project(self.project_path, "current"),
                timeout=5.0
            )
            
            success = await self._run_blocking(
                lambda: self.cross_project.share_state_across_projects(key, value, project_id),
                timeout=5.0
            )
            
            if success:
                # k2.6 FIX: Lock cache invalidation to prevent race with concurrent reads
                async with self._cache_locks['shared_keys']:
                    self._shared_keys_cache = None
                    self._shared_keys_cache_ts = 0.0
            
            return {"content": f"Shared state saved: `{key}`", "success": success, "key": key}
        except Exception as e:
            self.logger.warning(f"Share state failed: {e}")
            return {"content": f"Error sharing state `{key}`: {e}", "error": str(e), "success": False}
    
    async def _tool_get_version_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get version history using DevStatePersistence with caching."""
        if not self.persistence:
            return {"content": "Persistence not initialized.", "error": "Persistence not initialized", "versions": []}
        
        limit = args.get("limit", 20)
        
        # k2.6 FIX: Use asyncio lock for thread-safe cache access
        async with self._cache_locks['version']:
            if self._cache_valid(self._version_cache_ts) and self._version_cache is not None:
                versions = self._version_cache[-limit:]
                content = f"## Version History ({len(versions)})\n\n"
                for v in versions[:20]:
                    ts = v.get("timestamp", v.get("created", "?"))
                    msg = v.get("message", "no message")
                    author = v.get("author", "?")
                    content += f"- `{ts}` — {msg} ({author})\n"
                return {"content": content, "versions": versions, "count": len(versions), "cached": True}
        
        try:
            # FIXED: Reduced from 10.0 to 5.0
            versions_raw = await self._run_blocking(
                lambda: self.persistence.get_version_history(limit=limit),
                timeout=5.0
            )
            versions = [
                {
                    "hash": v.hash,
                    "timestamp": v.timestamp,
                    "message": v.message,
                    "state_size_bytes": v.state_size_bytes
                }
                for v in versions_raw
            ]
            async with self._cache_locks['version']:
                self._version_cache = versions
                self._version_cache_ts = time.time()
            content = f"## Version History ({len(versions)})\n\n"
            for v in versions[:20]:
                ts = v.get("timestamp", v.get("created", "?"))
                msg = v.get("message", "no message")
                author = v.get("author", "?")
                content += f"- `{ts}` — {msg} ({author})\n"
            return {"content": content, "versions": versions, "count": len(versions), "cached": False}
        except Exception as e:
            self.logger.warning(f"Version history fetch failed: {e}")
            return {"content": f"Version history fetch failed: {e}", "error": str(e), "versions": [], "count": 0}
    
    async def _tool_restore_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Restore version - replays events up to specific point in history"""
        if not self.engine:
            return {"content": "Engine not initialized.", "error": "Engine not initialized", "success": False}

        version_hash = args.get("version_hash")

        # Find event with matching ID
        all_events = self.engine.event_store.events
        target_idx = None
        for idx, e in enumerate(all_events):
            if e.event_id == version_hash:
                target_idx = idx
                break

        if target_idx is None:
            return {"content": f"Version '{version_hash}' not found.", "error": f"Version '{version_hash}' not found", "success": False}

        # Replay events in thread pool with timeout
        try:
            def _replay():
                from src.state import CognitiveState
                self.engine._current_state = CognitiveState.create_fresh()
                self.engine.dependency_graph = self.engine.dependency_graph.__class__()
                replayed = 0
                for e in all_events[:target_idx + 1]:
                    from src.engine_api import EngineEvent
                    event = EngineEvent(
                        event_type=e.event_type,
                        timestamp=e.timestamp,
                        source=e.source,
                        data=e.details
                    )
                    self.engine.update_from_environment(event)
                    replayed += 1
                self.engine.save_state()
                return replayed
            
            # FIXED: Reduced from 10.0 to 5.0
            replayed = await self._run_blocking(_replay, timeout=5.0)
            self._invalidate_caches()
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
            "target_timestamp": all_events[target_idx].timestamp.isoformat()
        }
    
    async def _tool_get_learned_operators(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get learned operators with caching and async loading."""
        if not self.cross_project:
            return {"operators": [], "count": 0}
        
        # k2.6 FIX: Use asyncio lock for thread-safe cache access
        async with self._cache_locks['learned_ops']:
            if self._cache_valid(self._learned_ops_cache_ts) and self._learned_ops_cache is not None:
                ops = self._learned_ops_cache
                content = f"## Learned Operators ({len(ops)})\n\n"
                if ops:
                    for i, op in enumerate(ops[:20], 1):
                        content += f"{i}. `{op}`\n"
                else:
                    content += "No operators learned yet.\n"
                return {"content": content, "operators": ops, "count": len(ops), "cached": True}
        
        try:
            # Get operator list asynchronously (fast)
            op_names = await self._run_blocking(
                self.cross_project.list_learned_operators,
                timeout=5.0
            )
            
            # Load operator data with limit to avoid disk thrashing
            max_ops = 50
            op_names = op_names[:max_ops]
            
            def _load_ops():
                data = []
                for name in op_names:
                    op = self.cross_project.load_learned_operator(name)
                    if op:
                        data.append({"name": name, "learned_at": op.get("learned_at"), "source_project": op.get("source_project")})
                return data
            
            # FIXED: Reduced from 10.0 to 5.0
            operator_data = await self._run_blocking(_load_ops, timeout=5.0)
            async with self._cache_locks['learned_ops']:
                self._learned_ops_cache = operator_data
                self._learned_ops_cache_ts = time.time()
            content = f"## Learned Operators ({len(operator_data)})\n\n"
            if operator_data:
                for i, op in enumerate(operator_data[:20], 1):
                    content += f"{i}. `{op}`\n"
            else:
                content += "No operators learned yet.\n"
            return {"content": content, "operators": operator_data, "count": len(operator_data), "cached": False}
        except Exception as e:
            self.logger.warning(f"Learned operators fetch failed: {e}")
            return {"content": f"## Learned Operators\n\n⚠️ Fetch failed: {e}", "error": str(e), "operators": [], "count": 0}
    
    async def _tool_get_system_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health with caching and async metrics gathering."""
        if not self.engine:
            return {"content": "## System Health\n\n⚠️ Engine not initialized.", "status": "unhealthy", "error": "Engine not initialized", "metrics": {}}
        
        # k2.6 FIX: Use asyncio lock for thread-safe cache access
        async with self._cache_locks['health']:
            if self._cache_valid(self._health_cache_ts) and self._health_cache is not None:
                cached = self._health_cache.copy()
                cached["cached"] = True
                cached["timestamp"] = datetime.now().isoformat()
                # Ensure content exists for display normalization
                if "content" not in cached:
                    metrics = cached.get("metrics", {})
                    comp = cached.get("components", {})
                    content = f"## System Health (cached)\n\n**Status:** {cached.get('status', 'unknown')}\n\n**Components:**\n"
                    for k, v in comp.items():
                        content += f"- {k}: {v}\n"
                    content += "\n**Metrics:**\n"
                    for k, v in metrics.items():
                        content += f"- {k}: {v}\n"
                    cached["content"] = content
                return cached
        
        try:
            def _gather_health():
                # State already loaded by engine/_handle_tools_call, use current state
                state = self.engine._current_state
                event_count = len(self.engine.event_store.events)
                projects = 0
                shared = 0
                learned = 0
                if self.cross_project:
                    projects = len(self.cross_project.get_all_projects())
                    shared = len(self.cross_project.list_shared_keys())
                    learned = len(self.cross_project.list_learned_operators())
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "components": {
                        "engine": "healthy",
                        "state_persistence": "healthy" if state else "no_state",
                        "cross_project": "healthy" if self.cross_project else "unavailable",
                        "security": "healthy" if self.security else "unavailable",
                    },
                    "metrics": {
                        "state_exists": state is not None,
                        "event_count": event_count,
                        "projects_registered": projects,
                        "shared_states": shared,
                        "learned_operators": learned,
                    }
                }
            
            # FAST: Reduced to 2.0s - this is a simple status check
            health = await self._run_blocking(_gather_health, timeout=2.0)
            # Build human-readable content for normalization layer
            metrics = health.get("metrics", {})
            comp = health.get("components", {})
            content = "## System Health\n\n**Status:** Healthy\n\n**Components:**\n"
            for k, v in comp.items():
                content += f"- {k}: {v}\n"
            content += "\n**Metrics:**\n"
            for k, v in metrics.items():
                content += f"- {k}: {v}\n"
            health["content"] = content
            async with self._cache_locks['health']:
                self._health_cache = health
                self._health_cache_ts = time.time()
            health["cached"] = False
            return health
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return {"content": f"## System Health\n\n⚠️ Health check failed: {e}", "status": "unhealthy", "error": str(e), "metrics": {}}
    
    async def _tool_list_sessions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all active HCR sessions (context windows)"""
        sessions = []
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
    
    async def _tool_create_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new HCR session with fast LLM-free initialization."""
        session_id = args.get("session_id")
        tag = args.get("tag", "untitled")
        clone_from = args.get("clone_from", "")
        use_llm = args.get("use_llm", False)  # Default False for speed
        
        if not session_id:
            return {"content": "session_id is required", "success": False}
        
        if session_id in self._session_states:
            return {
                "content": f"Session '{session_id}' already exists. Use a different ID.",
                "success": False
            }
        
        # Initialize with current state or clone from another session
        if clone_from and clone_from in self._session_states:
            source = self._session_states[clone_from]
            self._session_states[session_id] = {
                "panel": source["panel"],
                "metadata": {**source.get("metadata", {}), "tag": tag, "cloned_from": clone_from},
                "timestamp": datetime.now().isoformat()
            }
            self._session_private_notes[session_id] = list(self._session_private_notes.get(clone_from, []))
        else:
            # Fresh session with current engine state - fast path, no LLM by default
            panel = "No engine state available"
            if self.engine:
                try:
                    def _infer_ctx():
                        self.engine.load_state()
                        return self.engine.infer_context()
                    # FIXED: Reduced from 8.0 to 3.0
                    context = await self._run_blocking(_infer_ctx, timeout=3.0)
                    panel = self._format_classic_panel(context, mode="resume")
                    # Optionally enhance with LLM if explicitly requested
                    if use_llm:
                        panel = await self._generate_smart_resume(context, use_llm=True, mode="resume", session_id=session_id)
                except Exception as e:
                    self.logger.warning(f"Session context inference failed: {e}")
                    panel = f"Session created but context inference timed out.\nTag: {tag}"
            
            self._session_states[session_id] = {
                "panel": panel,
                "metadata": {"tag": tag},
                "timestamp": datetime.now().isoformat()
            }
            self._session_private_notes[session_id] = []
        
        return {
            "content": f"Session '{session_id}' created with tag '{tag}'.\n\nUse this session_id in other tools to maintain separate context.",
            "session_id": session_id,
            "tag": tag,
            "success": True
        }
    
    async def _tool_set_session_note(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a private note to a session"""
        session_id = args.get("session_id")
        note = args.get("note")
        
        if not session_id:
            return {"content": "session_id required", "success": False}
        
        if session_id not in self._session_states:
            return {"content": f"Session '{session_id}' not found. Create it first.", "success": False}
        
        self._append_private_note(session_id, note)
        notes = self._session_private_notes.get(session_id, [])
        
        content = f"## Note added to session '{session_id}'\n\n"
        content += f"Total notes: {len(notes)}\n\n"
        content += "Recent notes:\n"
        for n in notes[-5:]:
            content += f"- {n}\n"
        
        return {
            "content": content,
            "notes_count": len(notes),
            "success": True
        }
    
    async def _tool_merge_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Merge session-specific facts back into global state"""
        session_id = args.get("session_id")
        preserve_notes = args.get("preserve_notes", True)
        
        if not session_id or session_id not in self._session_states:
            return {"content": f"Session '{session_id}' not found.", "success": False}
        
        session_data = self._session_states[session_id]
        notes = self._session_private_notes.get(session_id, [])
        
        # Log merge event to global state
        if self.engine:
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
                    self.engine.update_from_environment(event)
                    self.engine.save_state()
                
                await self._run_blocking(_merge, timeout=5.0)
                # Invalidate cache since we just saved new state
                self._state_cached = False
            except Exception as e:
                self.logger.warning(f"Session merge state save failed: {e}")
        
        # Clear session state (but optionally keep notes)
        if not preserve_notes:
            del self._session_private_notes[session_id]
        del self._session_states[session_id]
        
        content = f"## Session '{session_id}' merged into global state\n\n"
        content += f"Notes preserved: {preserve_notes}\n"
        content += "Session-specific context is now part of the shared project memory."
        
        return {
            "content": content,
            "success": True,
            "notes_preserved": preserve_notes
        }
    
    async def _tool_record_file_edit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a file edit event with detailed change information.
        This is the primary way for IDE extensions to report actual file changes.
        """
        filepath = args.get("filepath")
        old_content = args.get("old_content", "")
        change_summary = args.get("change_summary", "")
        lines_added = args.get("lines_added", 0)
        lines_removed = args.get("lines_removed", 0)
        functions_changed = args.get("functions_changed", [])
        imports_changed = args.get("imports_changed", [])
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized", "recorded": False}
        
        # Import the enhanced file watcher
        from product.state_capture.file_watcher import FileWatcher, FileChange
        
        watcher = FileWatcher(self.project_path)
        
        # Compute changes in thread pool to avoid blocking on AST/diff
        change = None
        try:
            if old_content:
                change = await self._run_blocking(
                    lambda: watcher.capture_file_change(filepath, old_content),
                    timeout=5.0
                )
            else:
                change = FileChange(
                    path=filepath,
                    change_type='modified',
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    functions_changed=functions_changed,
                    imports_changed=imports_changed,
                    diff_summary=change_summary
                )
        except Exception as e:
            self.logger.warning(f"File change capture failed: {e}")
            change = FileChange(
                path=filepath,
                change_type='modified',
                lines_added=lines_added,
                lines_removed=lines_removed,
                functions_changed=functions_changed,
                imports_changed=imports_changed,
                diff_summary=change_summary
            )
        
        # Create EngineEvent with detailed change info
        from src.engine_api import EngineEvent
        event = EngineEvent(
            event_type='file_edit',
            timestamp=datetime.now(),
            data={
                'path': filepath,
                'lines_added': change.lines_added,
                'lines_removed': change.lines_removed,
                'functions_changed': change.functions_changed,
                'classes_changed': change.classes_changed,
                'imports_changed': change.imports_changed,
                'diff_summary': change.diff_summary[:500],  # Truncate for storage
                'change_summary': change_summary
            }
        )
        
        # Update engine state
        self.engine.update_from_environment(event)
        
        # Persist immediately so task inference and activity tracking stay current
        try:
            self.engine.save_state()
        except Exception:
            pass  # Non-fatal: daemon will eventually save
        
        # Build response
        content = f"## File Edit Recorded\n\n"
        content += f"**File:** `{filepath}`\n"
        content += f"**Change Type:** {change.change_type}\n"
        content += f"**Lines:** +{change.lines_added} / -{change.lines_removed}\n"
        
        if change.functions_changed:
            content += f"**Functions:** {', '.join(change.functions_changed)}\n"
        if change.imports_changed:
            content += f"**Imports:** {', '.join(change.imports_changed)}\n"
        if change_summary:
            content += f"**Summary:** {change_summary}\n"
        
        content += "\n✅ Causal graph and cognitive state updated."
        
        # Update dependency graph if imports changed
        if change.imports_changed and filepath.endswith('.py'):
            for imp in change.imports_changed:
                resolved = self._resolve_import_to_file(imp)
                if resolved:
                    self.engine.dependency_graph.add_dependency(resolved, filepath)
            content += f"\n🔗 Updated {len(change.imports_changed)} dependencies in causal graph."
        
        result = {
            "content": content,
            "recorded": True,
            "filepath": filepath,
            "change_type": change.change_type,
            "lines_changed": change.lines_added + change.lines_removed
        }
        
        self._record_session_snapshot(session_id, content, result)
        return result
    
    def _resolve_import_to_file(self, module_name: str) -> Optional[str]:
        """Resolve a Python module import to a file path"""
        # Simple resolution - convert module dots to path
        parts = module_name.split('.')
        
        # Try common patterns
        candidates = [
            Path(self.project_path) / f"{'/'.join(parts)}.py",
            Path(self.project_path) / '/'.join(parts) / "__init__.py"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate.relative_to(self.project_path))
        
        return None
    
    async def _tool_capture_full_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture complete developer context with commercial-grade reliability.
        Heavy operations run in thread pool with timeouts and limits.
        
        PHASE 2 OPTIMIZATION: All I/O operations run in parallel using asyncio.gather()
        Instead of sequential 5+5+3+8=21s, now ~8s (max of parallel operations).
        """
        include_diffs = args.get("include_diffs", False)  # Default False for speed
        session_id = args.get("session_id")
        max_diff_files = 5
        
        if not self.engine:
            return {"content": "Engine not initialized", "captured": False}
        
        # Import state capture modules
        from product.state_capture.git_tracker import GitTracker
        from product.state_capture.file_watcher import FileWatcher
        
        # PHASE 2 FIX: Define async wrapper tasks that can run in parallel
        async def _capture_git():
            """Capture git state with error handling"""
            try:
                git = GitTracker(self.project_path)
                return await self._run_blocking(git.capture_state, timeout=5.0)
            except Exception as e:
                self.logger.warning(f"Git capture timed out or failed: {e}")
                return {"error": str(e), "branch": "unknown"}
        
        async def _capture_files():
            """Capture file activity with error handling"""
            try:
                watcher = FileWatcher(self.project_path)
                return await self._run_blocking(
                    lambda: watcher.capture_state(lookback_minutes=120),
                    timeout=5.0
                )
            except Exception as e:
                self.logger.warning(f"File capture timed out or failed: {e}")
                return {"error": str(e), "file_count": 0}
        
        async def _infer_context_async():
            """Infer context using already-loaded state (no redundant load_state, no LLM)"""
            try:
                # State already loaded by _handle_tools_call, use fast heuristic inference
                return await self._run_blocking(lambda: self.engine.infer_context(use_llm=False), timeout=2.0)
            except Exception as e:
                self.logger.warning(f"Context inference timed out: {e}")
                # Use fallback context
                from src.engine_api import EngineContext
                return EngineContext(
                    current_task="Unknown (inference timeout)",
                    progress_percent=0,
                    next_action="Retry context capture",
                    confidence=0.0,
                    gap_minutes=0,
                    facts=[]
                )
        
        # PHASE 2 FIX: Run all I/O tasks in parallel using asyncio.gather()
        # This reduces latency from 5+5+3=13s sequential to ~5s parallel (max)
        git_state, file_state, context = await asyncio.gather(
            _capture_git(),
            _capture_files(),
            _infer_context_async(),
            return_exceptions=False
        )
        
        # 3. Get detailed changes if requested (only after file_state available)
        detailed_changes = []
        if include_diffs and file_state.get("file_count", 0) > 0:
            try:
                watcher = FileWatcher(self.project_path)
                changes = await self._run_blocking(
                    lambda: watcher.get_changed_files_with_details(since_minutes=60),
                    timeout=5.0
                )
                detailed_changes = changes[:max_diff_files]
            except Exception as e:
                self.logger.warning(f"Detailed changes timed out: {e}")
        
        # Build comprehensive response
        content = f"""## Complete Developer Context Captured

### 🌿 Git State
- **Branch:** {git_state.get('branch', 'unknown')}
- **Last Commit:** {git_state.get('last_commit', {}).get('message', 'unknown')[:50] if isinstance(git_state.get('last_commit'), dict) else 'unknown'}
- **Uncommitted:** {git_state.get('uncommitted_changes', {}).get('modified_count', 0) if isinstance(git_state.get('uncommitted_changes'), dict) else 0} modified, {git_state.get('uncommitted_changes', {}).get('staged_count', 0) if isinstance(git_state.get('uncommitted_changes'), dict) else 0} staged

### 📁 Recent File Activity
- **Files Changed (2h):** {file_state.get('file_count', 0)}
- **Primary Language:** {file_state.get('primary_language', 'unknown')}
- **Active Directories:** {', '.join(list(file_state.get('active_directories', {}).keys())[:3]) if isinstance(file_state.get('active_directories'), dict) else 'unknown'}

### 🧠 HCR Cognitive State
- **Current Task:** {context.current_task if context else 'Unknown'}
- **Progress:** {context.progress_percent if context else 0}%
- **Confidence:** {f'{context.confidence:.0%}' if context else '0%'}
- **Next Action:** {context.next_action if context else 'Unknown'}

### 📝 Facts ({len(context.facts[-10:]) if context else 0} recent)
"""
        if context and context.facts:
            for fact in context.facts[-5:]:
                content += f"- {fact}\n"
        else:
            content += "- No facts available\n"
        
        if detailed_changes:
            content += f"\n### 🔧 Detailed Changes ({len(detailed_changes)} files)\n"
            for change in detailed_changes:
                content += f"- `{change['path']}`: +{change['lines_added']}/-{change['lines_removed']} lines"
                if change.get('functions_changed'):
                    content += f" (funcs: {', '.join(change['functions_changed'][:3])})"
                content += "\n"
        
        # Build structured result for programmatic use
        result = {
            "content": content,
            "captured": True,
            "timestamp": datetime.now().isoformat(),
            "git": git_state,
            "files": file_state,
            "detailed_changes": detailed_changes,
            "hcr": {
                "current_task": context.current_task if context else "Unknown",
                "progress_percent": context.progress_percent if context else 0,
                "next_action": context.next_action if context else "Unknown",
                "confidence": context.confidence if context else 0.0,
                "recent_facts": context.facts[-10:] if context else []
            }
        }
        
        self._record_session_snapshot(session_id, content, {"full_context": True})
        
        # Persist state so task inference and recent activity stay current
        try:
            self.engine.save_state()
        except Exception:
            pass
        
        return result
    
    async def _tool_analyze_impact(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ripple effects of changing a file using the causal graph"""
        file_path = args.get("file_path")
        max_depth = args.get("max_depth", 3)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized", "impacted": []}
        
        if not self.engine.dependency_graph:
            return {"content": "No causal graph available. Edit some files first.", "impacted": []}
        
        # Clamp depth to reasonable range
        max_depth = max(1, min(5, max_depth))
        
        # Run impact analysis
        def _analyze():
            return self.engine.impact_analyzer.predict_impact(file_path, max_depth=max_depth)
        
        try:
            impacted = await self._run_blocking(_analyze, timeout=5.0)
        except Exception as e:
            self.logger.warning(f"Impact analysis failed: {e}")
            impacted = []
        
        # Build formatted response
        if not impacted:
            content = f"""## Impact Analysis: `{file_path}`

**Result:** No dependent files found in the causal graph.

This file appears to be a leaf node (nothing depends on it) or the dependency graph hasn't been fully built yet.
"""
        else:
            content = f"""## Impact Analysis: `{file_path}`

**Propagation Depth:** {max_depth}
**Impacted Files:** {len(impacted)}

### Affected Files (may need updates):
"""
            for f in impacted[:10]:
                content += f"- `{f}`\n"
            if len(impacted) > 10:
                content += f"- ... and {len(impacted) - 10} more files\n"
            
            content += f"\n**Advice:** Modifying `{file_path}` may require updates to these {len(impacted)} files."
        
        result = {
            "content": content,
            "impacted_files": impacted,
            "file_path": file_path,
            "max_depth": max_depth,
            "count": len(impacted)
        }
        
        self._record_session_snapshot(session_id, content, result)
        return result
    
    async def _tool_get_recommendations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered recommendations with confidence scores"""
        context_hint = args.get("context", "")
        use_llm = args.get("use_llm", True)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized", "recommendations": []}
        
        # Get current context
        try:
            def _get_context():
                self.engine.load_state()
                return self.engine.infer_context()
            
            context = await self._run_blocking(_get_context, timeout=3.0)
        except Exception as e:
            self.logger.warning(f"Context inference failed: {e}")
            context = None
        
        # Build recommendations
        recommendations = []
        
        # Primary recommendation from engine
        if context and context.next_action:
            recommendations.append({
                "action": context.next_action,
                "confidence": context.confidence,
                "source": "hcr_engine",
                "reason": f"Current task: {context.current_task}"
            })
        
        # LLM-enhanced recommendations if available
        if use_llm and self.engine:
            llm = self.engine._get_llm_provider()
            if llm:
                def _get_llm_recs():
                    prompt = f"""Based on this development context, suggest 3 specific next actions:

Current Task: {context.current_task if context else 'Unknown'}
Progress: {context.progress_percent if context else 0}%
Facts: {context.facts[-10:] if context else []}
Additional Context: {context_hint}

Return JSON array with fields: action, confidence (0-1), reason."""
                    
                    try:
                        response = llm.structured_complete(
                            prompt=prompt,
                            system="You are a development productivity assistant. Be specific and actionable.",
                            temperature=0.3,
                            max_tokens=400
                        )
                        if isinstance(response, list):
                            return response
                    except Exception as exc:
                        self.logger.warning(f"LLM recommendations failed: {exc}")
                    return []
                
                try:
                    llm_recs = await self._run_blocking(_get_llm_recs, timeout=3.0)
                    for rec in llm_recs:
                        if isinstance(rec, dict) and rec.get("action"):
                            recommendations.append({
                                "action": rec["action"],
                                "confidence": rec.get("confidence", 0.5),
                                "source": "llm_enhanced",
                                "reason": rec.get("reason", "AI suggestion")
                            })
                except Exception as e:
                    self.logger.warning(f"LLM recommendations timed out: {e}")
        
        # Fallback recommendations if we have none
        if not recommendations:
            recommendations = [
                {"action": "Review recent changes", "confidence": 0.6, "source": "fallback", "reason": "Best practice"},
                {"action": "Commit work in progress", "confidence": 0.5, "source": "fallback", "reason": "Prevent loss"}
            ]
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Build formatted output
        content = "## HCR Recommendations\n\n"
        for i, rec in enumerate(recommendations[:5], 1):
            conf_pct = int(rec.get("confidence", 0) * 100)
            content += f"{i}. **{rec['action']}** ({conf_pct}% confidence)\n"
            content += f"   _{rec.get('reason', 'No reason provided')}_\n\n"
        
        result = {
            "content": content,
            "recommendations": recommendations,
            "count": len(recommendations),
            "current_task": context.current_task if context else None,
            "progress_percent": context.progress_percent if context else 0
        }
        
        self._record_session_snapshot(session_id, content, result)
        return result
    
    async def _tool_search_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search event history for patterns, files, or keywords"""
        query = args.get("query", "").lower()
        event_type = args.get("event_type", "")
        limit = args.get("limit", 20)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized", "matches": []}
        
        if not query:
            return {"content": "Search query required", "matches": []}
        
        # Search through events
        def _search():
            matches = []
            for e in self.engine.event_store.events:
                # Filter by event type if specified
                if event_type and e.event_type != event_type:
                    continue
                
                # Search in source and details
                score = 0
                if query in e.source.lower():
                    score += 10
                if e.details and isinstance(e.details, dict):
                    details_str = json.dumps(e.details).lower()
                    if query in details_str:
                        score += 5
                if query in e.event_type.lower():
                    score += 3
                
                if score > 0:
                    matches.append({
                        "event": asdict(e),
                        "score": score
                    })
            
            # Sort by score and recency
            matches.sort(key=lambda x: (x["score"], x["event"]["timestamp"]), reverse=True)
            return matches[:limit]
        
        try:
            matches = await self._run_blocking(_search, timeout=5.0)
        except Exception as e:
            self.logger.warning(f"Search failed: {e}")
            matches = []
        
        # Build formatted output
        if not matches:
            content = f"""## History Search: "{query}"

No matching events found.

Try:
- Different keywords
- File paths (e.g., "src/main.py")
- Event types: file_edit, git_commit, session_merge
"""
        else:
            content = f"""## History Search: "{query}"

**Found:** {len(matches)} matching events\n
### Results:
"""
            for m in matches[:10]:
                e = m["event"]
                content += f"- **{e['event_type']}** at {e['timestamp'][:19]}\n"
                content += f"  Source: `{e['source'][:50]}`\n"
                if e.get("details"):
                    content += f"  Details: {str(e['details'])[:80]}...\n"
                content += "\n"
        
        result = {
            "content": content,
            "matches": matches,
            "count": len(matches),
            "query": query
        }
        
        self._record_session_snapshot(session_id, content, result)
        return result
    
    # --- Smart Panel Helpers ---

    def _format_classic_panel(
        self,
        context,
        mode: str = "resume",
        gap: Optional[float] = None,
        extra_query: Optional[str] = None,
    ) -> str:
        """Fallback formatter that mirrors the original HCR assistant panel"""
        lines = [
            "============================================================",
            "  HCR SESSION RESUME" if mode == "resume" else "  HCR NEXT ACTION",
            "============================================================",
        ]

        gap_val = gap if gap is not None else context.gap_minutes
        if gap_val is not None:
            if gap_val < 1:
                lines.append("\n⏱️  Last active: just now")
            elif gap_val < 60:
                lines.append(f"\n⏱️  Last active: {int(gap_val)} minutes ago")
            elif gap_val < 1440:
                lines.append(f"\n⏱️  Last active: {gap_val/60:.1f} hours ago")
            else:
                lines.append(f"\n⏱️  Last active: {gap_val/1440:.1f} days ago")

        lines.append(f"\n📋 Current Task: {context.current_task}")
        lines.append(f"\n📊 Progress: {context.progress_percent}%")
        filled = max(0, min(20, int(context.progress_percent / 5)))
        bar = "█" * filled + "░" * (20 - filled)
        lines.append(f"           [{bar}]")
        lines.append(f"\n👉 Next Action: {context.next_action}")

        if context.confidence > 0.7:
            lines.append("\n✅ High confidence")
        elif context.confidence > 0.4:
            lines.append("\n⚠️ Moderate confidence")
        else:
            lines.append("\n❓ Low confidence")

        if context.facts:
            lines.append("\n📝 Context Facts:")
            for fact in context.facts[:5]:
                lines.append(f"  • {fact}")

        if extra_query:
            lines.append("\n💬 Developer Query:")
            lines.append(f"  {extra_query}")

        lines.append("\n============================================================")
        return "\n".join(lines)

    async def _generate_smart_resume(
        self,
        context,
        use_llm: bool = True,
        mode: str = "resume",
        gap_override: Optional[float] = None,
        extra_query: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Generate a rich resume/action panel, optionally using the LLM"""
        base_panel = self._format_classic_panel(
            context,
            mode=mode,
            gap=gap_override,
            extra_query=extra_query,
        )

        if not use_llm or not self.engine:
            return base_panel

        llm = self.engine._get_llm_provider()
        if not llm:
            return base_panel

        session_notes = []
        if session_id:
            session_notes = self._session_private_notes.get(session_id, [])

        payload = {
            "mode": mode,
            "gap_minutes": gap_override if gap_override is not None else context.gap_minutes,
            "context": context.to_dict(),
            "extra_query": extra_query,
            "private_notes": session_notes,
        }

        # FIXED: Added timeout protection to LLM call to prevent indefinite hangs
        def _call_llm_with_timeout():
            """Call LLM with timeout protection"""
            # Use signal-based timeout for LLM provider if available
            # Otherwise rely on asyncio timeout from caller
            try:
                response = llm.structured_complete(
                    prompt=json.dumps(payload, indent=2),
                    system=SMART_RESUME_SYSTEM,
                    temperature=0.2,
                    max_tokens=600,
                )
                return response or {}
            except Exception as exc:
                self.logger.warning(f"LLM smart resume failed: {exc}")
                return {}

        try:
            # FIXED: Reduced timeout from 10.0 to 3.0 for consistency
            result = await self._run_blocking(_call_llm_with_timeout, timeout=3.0)
        except asyncio.TimeoutError:
            self.logger.warning(f"LLM smart resume exceeded 3s timeout, using base panel")
            result = {}
        except Exception as exc:
            self.logger.warning(f"LLM smart resume failed: {exc}")
            result = {}

        if isinstance(result, dict) and result.get("panel_text"):
            panel = result["panel_text"]
            metadata = []
            if result.get("tone_hint"):
                metadata.append(f"tone={result['tone_hint']}")
            if result.get("summary"):
                metadata.append(f"summary={result['summary']}")
            if metadata:
                panel += f"\n\n[Metadata: {', '.join(metadata)}]"
            return panel

        return base_panel

    def _record_session_snapshot(self, session_id: Optional[str], content: str, metadata: Optional[Dict[str, Any]] = None):
        """Persist latest panel content per session for multi-window IDEs"""
        if not session_id:
            return
        snapshot = {
            "panel": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self._session_states[session_id] = snapshot

    def _append_private_note(self, session_id: str, note: str):
        if not session_id or not note:
            return
        notes = self._session_private_notes[session_id]
        notes.append(f"[{datetime.now().strftime('%H:%M')}] {note}")
        # Keep last 20 notes max
        if len(notes) > 20:
            self._session_private_notes[session_id] = notes[-20:]

    def _error_response(self, message: str, code: int = -32600, data: Any = None) -> Dict[str, Any]:
        """Generate error response with optional data for debugging"""
        error = {
            "error": {
                "code": code,
                "message": message
            }
        }
        if data is not None:
            error["error"]["data"] = data
        return error


class MCPServerStdio:
    """
    Commercial-Ready MCP Server using async stdio transport.
    
    Patterned after official SDKs:
    - Dedicated background thread for non-blocking stdin reading
    - Asyncio Queue for message dispatch
    - Task tracking for concurrent request handling
    - Atomic stdout write synchronization
    """
    
    def __init__(self, project_path: Optional[str] = None):
        self.responder = HCRMCPResponder(project_path)
        self.logger = logging.getLogger("HCR-MCP-Stdio")
        self._write_lock = asyncio.Lock()
        self._tasks: Dict[Any, asyncio.Task] = {}
        self._input_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def _stdin_reader(self, loop: asyncio.AbstractEventLoop):
        """Dedicated thread for blocking stdin reads."""
        import sys
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    loop.call_soon_threadsafe(self._input_queue.put_nowait, None)
                    break
                loop.call_soon_threadsafe(self._input_queue.put_nowait, line)
            except EOFError:
                loop.call_soon_threadsafe(self._input_queue.put_nowait, None)
                break
            except Exception as e:
                self.logger.error(f"Stdin reader error: {e}")
                break

    async def _handle_request_task(self, request: Dict[str, Any]):
        """Background task to handle a single MCP request."""
        request_id = request.get("id")
        method = request.get("method")
        
        try:
            # Handle notifications (no response expected)
            if request_id is None:
                if method == "notifications/cancelled":
                    cancelled_id = request.get("params", {}).get("requestId")
                    if cancelled_id in self._tasks:
                        self.logger.info(f"Cancelling task {cancelled_id}")
                        self._tasks[cancelled_id].cancel()
                else:
                    # Process other notifications silently
                    await self.responder.handle_request(request)
                return

            # Handle requests (response expected)
            response = await self.responder.handle_request(request)
            
            # Send response atomically
            payload = (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
            async with self._write_lock:
                import sys
                sys.stdout.buffer.write(payload)
                sys.stdout.buffer.flush()
                
        except asyncio.CancelledError:
            self.logger.info(f"Request {request_id} was cancelled")
        except Exception as e:
            self.logger.error(f"Error handling request {request_id}: {e}")
            if request_id is not None:
                err_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Internal error: {e}"}
                }
                payload = (json.dumps(err_response, ensure_ascii=False) + "\n").encode("utf-8")
                async with self._write_lock:
                    import sys
                    sys.stdout.buffer.write(payload)
                    sys.stdout.buffer.flush()
        finally:
            if request_id in self._tasks:
                del self._tasks[request_id]

    async def run(self):
        """Run the high-performance async stdio server."""
        self.logger.info("HCR MCP Server starting (Commercial Grade)...")
        self._running = True
        import sys
        import threading
        
        # Start background reader thread
        loop = asyncio.get_running_loop()
        reader_thread = threading.Thread(target=self._stdin_reader, args=(loop,), daemon=True)
        reader_thread.start()
        
        print("HCR MCP Server ready", flush=True, file=sys.stderr)

        try:
            while self._running:
                line = await self._input_queue.get()
                if line is None:  # EOF
                    break
                
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    if not isinstance(request, dict):
                        continue
                    
                    request_id = request.get("id")
                    
                    # Dispatch to background task
                    task = asyncio.create_task(self._handle_request_task(request))
                    
                    # Track task if it has an ID
                    if request_id is not None:
                        self._tasks[request_id] = task
                        
                except json.JSONDecodeError:
                    self.logger.warning("Dropped malformed JSON-RPC line")
                    continue
        finally:
            self._running = False
            # Graceful shutdown: cancel all pending tasks
            if self._tasks:
                self.logger.info(f"Cancelling {len(self._tasks)} pending tasks...")
                for task in self._tasks.values():
                    task.cancel()
                await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            
        self.logger.info("HCR MCP Server shut down.")

        self.logger.info("HCR MCP Server shutting down...")

        self.logger.info("HCR MCP Server shutting down...")


class MCPServerHTTP:
    """
    MCP Server using HTTP/SSE transport.
    
    For web-based integrations and custom clients.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8734, project_path: str = "."):
        self.host = host
        self.port = port
        self.project_path = Path(project_path).absolute()
        self.hcr_dir = self.project_path / ".hcr"
        self.responder = HCRMCPResponder(str(self.project_path))
        self.engine = self.responder.engine
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._call_counts = {}
        self._call_times = {}
        self.logger = logging.getLogger("HCRMCPServer")
        
        # State caching to avoid reloading from disk
        self._state_cache_mtime = 0
        self._state_cached = False
    
    async def handle_http_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle HTTP request"""
        return await self.responder.handle_request(request)
    
    async def run(self):
        """Run the HTTP MCP server"""
        from aiohttp import web
        
        async def handle_post(request):
            try:
                body = await request.json()
                response = await self.handle_http_request(body)
                return web.json_response(response)
            except Exception as e:
                return web.json_response(
                    {"error": {"code": -32603, "message": str(e)}},
                    status=500
                )
        
        async def handle_get(request):
            return web.json_response({
                "name": "hcr-mcp-server",
                "version": "1.0.0",
                "tools_endpoint": "/mcp/tools",
                "resources_endpoint": "/mcp/resources",
                "prompts_endpoint": "/mcp/prompts"
            })
        
        app = web.Application()
        app.router.add_post('/mcp', handle_post)
        app.router.add_get('/mcp', handle_get)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"HCR MCP HTTP Server running on http://{self.host}:{self.port}")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


# --- Entry Point ---
def main():
    """Main entry point for MCP server"""
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description="HCR MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport protocol (stdio for Claude/Cursor, http for web)")
    parser.add_argument("--host", default="localhost", help="HTTP host")
    parser.add_argument("--port", type=int, default=8734, help="HTTP port")
    parser.add_argument("--project", default=os.environ.get("HCR_PROJECT"), help="Project path")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    if args.transport == "stdio":
        server = MCPServerStdio(args.project)
    else:
        server = MCPServerHTTP(args.host, args.port, args.project)
    
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
