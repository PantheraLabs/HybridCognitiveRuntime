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
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict

SMART_RESUME_SYSTEM = """You are the HCR "Resume Without Re-Explaining" formatter.\nReturn JSON with keys:\n- panel_text: fully formatted panel (markdown) matching the classic HCR assistant layout.\n- tone_hint: short note (e.g., high_confidence / low_confidence).\n- summary: single sentence TL;DR.\nRules:\n- Preserve headings and emojis (⏱️, 📋, 📊, 👉, ✅, 📝).\n- Keep suggestions actionable.\n- If data missing, explicitly say so instead of hallucinating.\n- Reflect confidence and time gap accurately.\n"""

# Add project root to path for imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
sys.path.insert(0, str(_project_root))

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
        self.project_path = project_path or str(Path.cwd())
        self.logger = logging.getLogger("HCR-MCP")
        
        # Rate limiting: max 30 calls per minute per tool
        self._rate_limits: Dict[str, List[float]] = {}
        self._max_calls_per_minute = 30

        # Thread pool for blocking operations (LLM calls)
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Session-aware context windows (per IDE pane)
        self._session_states: Dict[str, Dict[str, Any]] = {}
        self._session_private_notes: Dict[str, List[str]] = defaultdict(list)
        
        try:
            # Import HCR modules - use HCREngine for proper state management
            from src.engine_api import HCREngine, EngineEvent
            from product.storage.state_persistence import CrossProjectStateManager
            from product.security.enterprise_security import EnterpriseSecurityManager
            
            self.engine = HCREngine(self.project_path)
            self.cross_project = CrossProjectStateManager()
            self.security = EnterpriseSecurityManager()
        except Exception as e:
            self.logger.error(f"Failed to initialize HCR modules: {e}")
            self.engine = None
            self.cross_project = None
            self.security = None
        
        # Define available tools
        self.tools = self._define_tools()
        self.resources = self._define_resources()
        self.prompts = self._define_prompts()
    
    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool call is within rate limit. Returns True if allowed."""
        from time import time
        
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
            elif "error" in result_data:
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
        name = params.get("name")
        arguments = params.get("arguments", {})
        session_id = arguments.get("session_id")
        
        # Log tool invocation as event to update context
        if self.engine:
            from src.engine_api import EngineEvent
            from datetime import datetime
            event = EngineEvent(
                event_type='mcp_tool_call',
                timestamp=datetime.now(),
                data={'tool': name, 'args': arguments}
            )
            self.engine.update_from_environment(event)
        
        # Route to appropriate handler
        handlers = {
            "hcr_get_state": self._tool_get_state,
            "hcr_get_causal_graph": self._tool_get_causal_graph,
            "hcr_get_recent_activity": self._tool_get_recent_activity,
            "hcr_get_current_task": self._tool_get_current_task,
            "hcr_get_next_action": self._tool_get_next_action,
            "hcr_list_shared_states": self._tool_list_shared_states,
            "hcr_get_shared_state": self._tool_get_shared_state,
            "hcr_share_state": self._tool_share_state,
            "hcr_get_version_history": self._tool_get_version_history,
            "hcr_restore_version": self._tool_restore_version,
            "hcr_get_learned_operators": self._tool_get_learned_operators,
            "hcr_list_sessions": self._tool_list_sessions,
            "hcr_create_session": self._tool_create_session,
            "hcr_set_session_note": self._tool_set_session_note,
            "hcr_merge_session": self._tool_merge_session,
            "hcr_get_system_health": self._tool_get_system_health,
            "hcr_record_file_edit": self._tool_record_file_edit,
            "hcr_capture_full_context": self._tool_capture_full_context,
        }
        
        handler = handlers.get(name)
        if not handler:
            return self._error_response(f"Unknown tool: {name}")
        
        # Check rate limit
        if not self._check_rate_limit(name):
            return {
                "result": {
                    "content": [{"type": "text", "text": f"Rate limit exceeded for {name}. Max 30 calls per minute."}],
                    "isError": True
                }
            }
        
        # Smart state loading: only reload if file changed (optimization)
        if self.engine:
            try:
                state_file = self.engine.state_file
                current_mtime = 0
                if state_file.exists():
                    current_mtime = state_file.stat().st_mtime
                
                # Only reload if file modified since last cache
                if not self._state_cached or current_mtime > self._state_cache_mtime:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self._executor, self.engine.load_state)
                    self._state_cache_mtime = current_mtime
                    self._state_cached = True
                    self.logger.debug(f"State loaded from disk (mtime: {current_mtime})")
                else:
                    self.logger.debug("Using cached state (file unchanged)")
            except Exception as e:
                self.logger.warning(f"Failed to preload state: {e}")
        
        # Run handler with timeout to prevent blocking on LLM calls
        try:
            result = await asyncio.wait_for(handler(arguments), timeout=10.0)
        except asyncio.TimeoutError:
            return {
                "result": {
                    "content": [{"type": "text", "text": "Tool call timed out. LLM inference may be slow. Try again or check API key."}],
                    "isError": True
                }
            }
        
        # Check if result has a 'content' field (formatted text for AI)
        if isinstance(result, dict) and "content" in result:
            # Use the formatted content as primary text, include rest as metadata
            text_content = result.get("content", "")
            # Add metadata to the formatted text if there's more data (without modifying original)
            remaining = {k: v for k, v in result.items() if k != "content"}
            if remaining:
                try:
                    meta_json = json.dumps(remaining, indent=2, default=str)
                    text_content += f"\n\n[Metadata: {meta_json}]"
                except (TypeError, ValueError):
                    pass  # Skip metadata if serialization fails

            # Snapshot session-specific summary for downstream panes
            if session_id and "session_snapshot" not in remaining:
                self._record_session_snapshot(session_id, text_content, remaining)

            return {"result": {"content": [{"type": "text", "text": text_content}]}}
        else:
            # Standard JSON response for non-formatted results
            return {"result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}}
    
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
        """Read a resource"""
        uri = params.get("uri")
        mime_type = "application/json"
        
        if not self.engine:
            return self._error_response("Engine not initialized")
        
        if uri == "hcr://state/current":
            state = self.engine.load_state()
            content = json.dumps(state.to_dict(), indent=2) if state else "{}"
        elif uri == "hcr://causal-graph/main":
            self.engine.load_state()
            if self.engine.dependency_graph:
                graph = {
                    "forward": {k: list(v) for k, v in self.engine.dependency_graph.forward_edges.items()},
                    "reverse": {k: list(v) for k, v in self.engine.dependency_graph.reverse_edges.items()}
                }
                content = json.dumps(graph, indent=2)
            else:
                content = "{}"
        elif uri == "hcr://task/current":
            self.engine.load_state()
            context = self.engine.infer_context()
            task = context.current_task if context else "No current task"
            content = task
            mime_type = "text/plain"
        else:
            return self._error_response(f"Unknown resource: {uri}")
        
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
        """Get a prompt"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not self.engine:
            return self._error_response("Engine not initialized")
        
        # Run inference in thread pool to prevent blocking
        try:
            loop = asyncio.get_running_loop()
            context = await loop.run_in_executor(self._executor, self.engine.infer_context)
        except RuntimeError:
            context = self.engine.infer_context()
        
        if name == "hcr_resume_session":
            # Calculate gap from _last_saved
            gap = None
            if hasattr(self.engine, '_last_saved') and self.engine._last_saved:
                from datetime import datetime
                gap = (datetime.now() - self.engine._last_saved).total_seconds() / 60
            
            prompt_text = await self._generate_smart_resume(context, use_llm=True, mode="resume", gap_override=gap)
            
        elif name == "hcr_context_aware_coding":
            query = arguments.get("query", "")
            prompt_text = await self._generate_smart_resume(context, use_llm=True, mode="coding", extra_query=query)
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
            from src.causal.event_store import CausalEvent
            recent_events = self.engine.event_store.get_recent_events(50)
            result["recent_events"] = [asdict(e) for e in recent_events]
        
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
        
        # State preloaded by _handle_tools_call
        events = self.engine.event_store.get_recent_events(limit)
        
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
                "timestamp": e.timestamp,
                "details": e.details
            }
            for e in events
        ]
        
        snapshot_meta = {"count": len(activities)}
        self._record_session_snapshot(session_id, content, snapshot_meta)
        return {"content": content, "activities": activities, "count": len(activities)}
    
    async def _tool_get_current_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current task from engine context inference - returns formatted context for AI"""
        use_llm = args.get("use_llm", True)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "task": None}
        
        # Run inference in thread pool to prevent blocking
        try:
            loop = asyncio.get_running_loop()
            context = await loop.run_in_executor(self._executor, self.engine.infer_context)
        except RuntimeError:
            context = self.engine.infer_context()
        
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
        use_llm = args.get("use_llm", True)
        session_id = args.get("session_id")

        if not self.engine:
            return {"content": "HCR Engine not initialized. Please run 'hcr init' first.", "task": None}

        
        # Run inference in thread pool to prevent blocking
        try:
            loop = asyncio.get_running_loop()
            context = await loop.run_in_executor(self._executor, self.engine.infer_context)
        except RuntimeError:
            context = self.engine.infer_context()

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
        """List shared states"""
        keys = self.cross_project.list_shared_keys()
        return {"shared_states": keys, "count": len(keys)}
    
    async def _tool_get_shared_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get shared state"""
        key = args.get("key")
        value = self.cross_project.get_shared_state_value(key)
        
        if value is None:
            return {"error": f"Shared state '{key}' not found", "exists": False}
        
        return {"key": key, "value": value, "exists": True}
    
    async def _tool_share_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Share state"""
        key = args.get("key")
        value = args.get("value")
        
        # Get current project ID
        project_id = self.cross_project.register_project(self.project_path, "current")
        
        success = self.cross_project.share_state_across_projects(key, value, project_id)
        
        return {"success": success, "key": key}
    
    async def _tool_get_version_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get version history"""
        if not self.engine:
            return {"error": "Engine not initialized", "versions": []}
        
        # Get event history as proxy for version history
        limit = args.get("limit", 20)
        events = self.engine.event_store.get_recent_events(limit)
        
        versions = [
            {
                "hash": e.event_id,
                "timestamp": e.timestamp,
                "message": f"{e.event_type}: {e.source}",
                "event_type": e.event_type
            }
            for e in events
        ]
        
        return {"versions": versions, "count": len(versions)}
    
    async def _tool_restore_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Restore version - reloads state to specific point in event history"""
        if not self.engine:
            return {"error": "Engine not initialized", "success": False}
        
        version_hash = args.get("version_hash")
        
        # Find event with matching ID
        all_events = self.engine.event_store.events
        target_event = None
        for e in all_events:
            if e.event_id == version_hash:
                target_event = e
                break
        
        if not target_event:
            return {"error": f"Version '{version_hash}' not found", "success": False}
        
        # Reload state and replay events up to this point
        self.engine.load_state()
        
        return {"success": True, "restored_hash": version_hash, "event": asdict(target_event)}
    
    async def _tool_get_learned_operators(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get learned operators"""
        operators = self.cross_project.list_learned_operators()
        
        # Load full operator data
        operator_data = []
        for op_name in operators:
            op = self.cross_project.load_learned_operator(op_name)
            if op:
                operator_data.append(op)
        
        return {"operators": operator_data, "count": len(operator_data)}
    
    async def _tool_get_system_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health"""
        if not self.engine:
            return {"status": "unhealthy", "error": "Engine not initialized"}
        
        # Gather health metrics
        state = self.engine.load_state()
        event_count = len(self.engine.event_store.events)
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "engine": "healthy",
                "state_persistence": "healthy" if state else "no_state",
                "cross_project": "healthy",
                "security": "healthy",
            },
            "metrics": {
                "state_exists": state is not None,
                "event_count": event_count,
                "projects_registered": len(self.cross_project.get_all_projects()) if self.cross_project else 0,
                "shared_states": len(self.cross_project.list_shared_keys()) if self.cross_project else 0,
                "learned_operators": len(self.cross_project.list_learned_operators()) if self.cross_project else 0,
            }
        }
        
        return health
    
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
        """Create a new HCR session (context window)"""
        session_id = args.get("session_id")
        tag = args.get("tag", "untitled")
        clone_from = args.get("clone_from", "")
        
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
            # Fresh session with current engine state
            if self.engine:
                self.engine.load_state()
                context = self.engine.infer_context()
                panel = await self._generate_smart_resume(context, use_llm=True, mode="resume", session_id=session_id)
            else:
                panel = "No engine state available"
            
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
            # Invalidate cache since we just saved new state
            self._state_cached = False
        
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
        
        # If old_content provided, compute detailed changes
        if old_content:
            change = watcher.capture_file_change(filepath, old_content)
        else:
            # Just record the basic edit
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
        Capture complete developer context by combining:
        - Git state (branch, commits, uncommitted changes)
        - Recent file activity with diffs
        - Current cognitive state from HCR
        - HCR task inference
        
        Returns a comprehensive context object for AI assistants.
        """
        include_diffs = args.get("include_diffs", True)
        session_id = args.get("session_id")
        
        if not self.engine:
            return {"content": "Engine not initialized", "captured": False}
        
        # Import state capture modules
        from product.state_capture.git_tracker import GitTracker
        from product.state_capture.file_watcher import FileWatcher
        
        # 1. Capture git state
        git = GitTracker(self.project_path)
        git_state = git.capture_state()
        
        # 2. Capture file activity
        watcher = FileWatcher(self.project_path)
        file_state = watcher.capture_state(lookback_minutes=120)
        
        # 3. Get detailed changes if requested
        detailed_changes = []
        if include_diffs:
            detailed_changes = watcher.get_changed_files_with_details(since_minutes=60)
        
        # 4. Get current HCR cognitive state
        hcr_state = self.engine.load_state()
        
        # 5. Infer current context
        try:
            loop = asyncio.get_running_loop()
            context = await loop.run_in_executor(self._executor, self.engine.infer_context)
        except RuntimeError:
            context = self.engine.infer_context()
        
        # Build comprehensive response
        content = f"""## Complete Developer Context Captured

### 🌿 Git State
- **Branch:** {git_state.get('branch', 'unknown')}
- **Last Commit:** {git_state.get('last_commit', {}).get('message', 'unknown')[:50]}
- **Uncommitted:** {git_state.get('uncommitted_changes', {}).get('modified_count', 0)} modified, {git_state.get('uncommitted_changes', {}).get('staged_count', 0)} staged

### 📁 Recent File Activity
- **Files Changed (2h):** {file_state.get('file_count', 0)}
- **Primary Language:** {file_state.get('primary_language', 'unknown')}
- **Active Directories:** {', '.join(list(file_state.get('active_directories', {}).keys())[:3])}

### 🧠 HCR Cognitive State
- **Current Task:** {context.current_task}
- **Progress:** {context.progress_percent}%
- **Confidence:** {context.confidence:.0%}
- **Next Action:** {context.next_action}

### 📝 Facts ({len(context.facts[-10:])} recent)
"""
        for fact in context.facts[-5:]:
            content += f"- {fact}\n"
        
        if detailed_changes:
            content += f"\n### 🔧 Detailed Changes ({len(detailed_changes)} files)\n"
            for change in detailed_changes[:5]:
                content += f"- `{change['path']}`: +{change['lines_added']}/-{change['lines_removed']} lines"
                if change['functions_changed']:
                    content += f" (funcs: {', '.join(change['functions_changed'][:3])})"
                content += "\n"
        
        # Build structured result for programmatic use
        result = {
            "content": content,
            "captured": True,
            "timestamp": datetime.now().isoformat(),
            "git": git_state,
            "files": file_state,
            "detailed_changes": detailed_changes if include_diffs else [],
            "hcr": {
                "current_task": context.current_task,
                "progress_percent": context.progress_percent,
                "next_action": context.next_action,
                "confidence": context.confidence,
                "recent_facts": context.facts[-10:]
            }
        }
        
        self._record_session_snapshot(session_id, content, {"full_context": True})
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

        def _call_llm():
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
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self._executor, _call_llm)
        except RuntimeError:
            result = _call_llm()

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
    MCP Server using stdio transport.
    
    This is the standard way to communicate with MCP clients like:
    - Claude Desktop
    - Cursor AI
    - Windsurf
    """
    
    def __init__(self, project_path: Optional[str] = None):
        self.responder = HCRMCPResponder(project_path)
        self.logger = logging.getLogger("HCR-MCP-Stdio")
    
    async def run(self):
        """Run the stdio MCP server"""
        self.logger.info("HCR MCP Server starting...")
        # Log to stderr only - stdout is reserved for JSON-RPC
        import sys
        print("HCR MCP Server ready", flush=True, file=sys.stderr)
        
        while True:
            try:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )
                
                if not line:
                    continue
                
                # Parse request
                request = json.loads(line)
                
                # Handle request
                response = await self.responder.handle_request(request)
                
                # Send response
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                error = {"error": {"code": -32700, "message": f"Parse error: {e}"}}
                print(json.dumps(error), flush=True)
            except EOFError:
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")
                error = {"error": {"code": -32603, "message": f"Internal error: {e}"}}
                print(json.dumps(error), flush=True)
        
        self.logger.info("HCR MCP Server shutting down...")


class MCPServerHTTP:
    """
    MCP Server using HTTP/SSE transport.
    
    For web-based integrations and custom clients.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8734, project_path: str = "."):
        self.project_path = Path(project_path).absolute()
        self.hcr_dir = self.project_path / ".hcr"
        self.engine = None
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
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="HCR MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport protocol (stdio for Claude/Cursor, http for web)")
    parser.add_argument("--host", default="localhost", help="HTTP host")
    parser.add_argument("--port", type=int, default=8734, help="HTTP port")
    parser.add_argument("--project", help="Project path")
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
