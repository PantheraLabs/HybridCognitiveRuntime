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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict

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
        
        try:
            # Import HCR modules
            from product.storage.state_persistence import DevStatePersistence, CrossProjectStateManager
            from product.security.enterprise_security import EnterpriseSecurityManager
            
            self.persistence = DevStatePersistence(self.project_path)
            self.cross_project = CrossProjectStateManager()
            self.security = EnterpriseSecurityManager()
        except Exception as e:
            self.logger.error(f"Failed to initialize HCR modules: {e}")
            self.persistence = None
            self.cross_project = None
            self.security = None
        
        # Define available tools
        self.tools = self._define_tools()
        self.resources = self._define_resources()
        self.prompts = self._define_prompts()
    
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
                name="hcr_get_system_health",
                description="Get HCR system health metrics",
                input_schema={
                    "type": "object",
                    "properties": {}
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
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
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
        """Execute a tool call"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
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
            "hcr_get_system_health": self._tool_get_system_health,
        }
        
        handler = handlers.get(name)
        if not handler:
            return self._error_response(f"Unknown tool: {name}")
        
        result = await handler(arguments)
        return {"result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
    
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
        
        if uri == "hcr://state/current":
            state = self.persistence.load_state()
            content = json.dumps(state, indent=2) if state else "{}"
        elif uri == "hcr://causal-graph/main":
            graph = self.persistence.load_causal_graph("main")
            content = json.dumps(asdict(graph), indent=2) if graph else "{}"
        elif uri == "hcr://task/current":
            state = self.persistence.load_state()
            task = state.get("analysis", {}).get("current_task", "No current task") if state else "No current task"
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
        
        if name == "hcr_resume_session":
            state = self.persistence.load_state()
            gap = self.persistence.get_gap_duration()
            
            prompt_text = self._generate_resume_prompt(state, gap)
            
        elif name == "hcr_context_aware_coding":
            query = arguments.get("query", "")
            state = self.persistence.load_state()
            
            prompt_text = self._generate_coding_prompt(query, state)
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
        """Get current HCR state"""
        include_history = args.get("include_history", False)
        
        state = self.persistence.load_state()
        if not state:
            return {"error": "No state found", "exists": False}
        
        result = {"state": state, "exists": True}
        
        if include_history:
            result["version_history"] = [
                asdict(v) for v in self.persistence.get_version_history()
            ]
        
        return result
    
    async def _tool_get_causal_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get causal graph"""
        graph_name = args.get("graph_name", "main")
        graph = self.persistence.load_causal_graph(graph_name)
        
        if not graph:
            return {"error": f"Graph '{graph_name}' not found", "exists": False}
        
        return {"graph": asdict(graph), "exists": True}
    
    async def _tool_get_recent_activity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent activity"""
        limit = args.get("limit", 10)
        state = self.persistence.load_state()
        
        if not state:
            return {"error": "No state found", "activities": []}
        
        activities = state.get("recent_activity", [])[-limit:]
        return {"activities": activities, "count": len(activities)}
    
    async def _tool_get_current_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current task"""
        state = self.persistence.load_state()
        
        if not state:
            return {"error": "No state found", "task": None}
        
        task = state.get("analysis", {}).get("current_task", "Unknown")
        progress = state.get("analysis", {}).get("progress_percent", 0)
        
        return {"task": task, "progress_percent": progress}
    
    async def _tool_get_next_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get next action suggestion"""
        state = self.persistence.load_state()
        
        if not state:
            return {"error": "No state found", "next_action": None}
        
        next_action = state.get("analysis", {}).get("next_action", "No suggestion available")
        confidence = state.get("analysis", {}).get("confidence", 0)
        
        return {"next_action": next_action, "confidence": confidence}
    
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
        limit = args.get("limit", 20)
        versions = self.persistence.get_version_history(limit)
        
        return {"versions": [asdict(v) for v in versions], "count": len(versions)}
    
    async def _tool_restore_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Restore version"""
        version_hash = args.get("version_hash")
        state = self.persistence.restore_version(version_hash)
        
        if not state:
            return {"error": f"Version '{version_hash}' not found", "success": False}
        
        # Save as current state
        self.persistence.save_state(state, f"Restored version {version_hash}")
        
        return {"success": True, "restored_hash": version_hash}
    
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
        # Gather health metrics
        state = self.persistence.load_state()
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "state_persistence": "healthy",
                "cross_project": "healthy",
                "security": "healthy",
            },
            "metrics": {
                "state_exists": state is not None,
                "projects_registered": len(self.cross_project.get_all_projects()),
                "shared_states": len(self.cross_project.list_shared_keys()),
                "learned_operators": len(self.cross_project.list_learned_operators()),
            }
        }
        
        return health
    
    # --- Prompt Generators ---
    
    def _generate_resume_prompt(self, state: Optional[Dict], gap: Optional[float]) -> str:
        """Generate resume session prompt"""
        if not state:
            return """No previous HCR session found for this project.

This is the first time HCR is tracking this project. I will:
1. Capture current project context (git state, files)
2. Initialize cognitive state
3. Start tracking development activity

Would you like me to start tracking this project?"""
        
        task = state.get("analysis", {}).get("current_task", "Unknown task")
        progress = state.get("analysis", {}).get("progress_percent", 0)
        next_action = state.get("analysis", {}).get("next_action", "No suggestion")
        
        gap_text = ""
        if gap:
            if gap < 60:
                gap_text = f"Last active {gap:.0f} minutes ago."
            elif gap < 1440:
                gap_text = f"Last active {gap/60:.1f} hours ago."
            else:
                gap_text = f"Last active {gap/1440:.1f} days ago."
        
        prompt = f"""## HCR Session Resume

**Current Task:** {task}
**Progress:** {progress}%
**{gap_text}**

**Context Summary:**
- Project: {state.get("project_context", {}).get("name", "Unknown")}
- Branch: {state.get("git_state", {}).get("branch", "Unknown")}
- Uncommitted changes: {len(state.get("git_state", {}).get("modified_files", []))} files

**Next Suggested Action:**
{next_action}

**How would you like to proceed?**
1. Continue with the current task
2. Start a new task
3. Review detailed context"""
        
        return prompt
    
    def _generate_coding_prompt(self, query: str, state: Optional[Dict]) -> str:
        """Generate context-aware coding prompt"""
        context = ""
        if state:
            task = state.get("analysis", {}).get("current_task", "")
            branch = state.get("git_state", {}).get("branch", "")
            files = state.get("file_state", {}).get("recent_files", [])
            
            context = f"""
**Current HCR Context:**
- Active Task: {task}
- Current Branch: {branch}
- Recently Modified Files: {', '.join(files[:5]) if files else 'None'}
"""
        
        return f"""{context}

**Coding Query:** {query}

Please provide assistance using the full HCR context above. Consider:
- Current development task and progress
- Recent file changes and patterns
- Project architecture from causal graph
- Previous reasoning and decisions"""
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            "error": {
                "code": -32600,
                "message": message
            }
        }


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
    
    def __init__(self, host: str = "localhost", port: int = 8734, project_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.responder = HCRMCPResponder(project_path)
        self.logger = logging.getLogger("HCR-MCP-HTTP")
    
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
