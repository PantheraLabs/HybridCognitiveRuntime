"""
HCR MCP Server

Exposes Hybrid Cognitive Runtime as an MCP tool for Windsurf/Cascade.
Thin wrapper around HCR HTTP API - no business logic here.
"""

import json
import requests
from typing import Dict, Any, Optional

# MCP SDK (will be available in Windsurf environment)
try:
    from mcp.server import Server
    from mcp.types import TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Fallback for development
    class Server:
        def __init__(self, name: str):
            self.name = name
        def tool(self):
            def decorator(func):
                return func
            return decorator


HCR_HOST = "localhost"
CR_PORT = 8733
HCR_BASE_URL = f"http://{HCR_HOST}:{HCR_PORT}"


class HCRMCPBridge:
    """Bridge between MCP and HCR Engine HTTP API"""
    
    def __init__(self):
        self.base_url = HCR_BASE_URL
        self._check_engine()
    
    def _check_engine(self):
        """Verify HCR engine is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            if response.status_code != 200:
                raise RuntimeError("HCR engine not responding")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"HCR engine not running at {self.base_url}\n"
                f"Start it with: python -m product.cli.resume --server --project <path>"
            )
    
    def _hcr_get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to HCR engine"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"HCR request failed: {str(e)}"}
    
    def _hcr_post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to HCR engine"""
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"HCR request failed: {str(e)}"}
    
    def get_context(self) -> Dict[str, Any]:
        """Get current HCR context"""
        return self._hcr_get("/context")
    
    def resume_session(self, gap_minutes: float = 0) -> Dict[str, Any]:
        """Trigger HCR resume with time gap"""
        return self._hcr_post("/resume", {"gap_minutes": gap_minutes})
    
    def update_state(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send event to update HCR state"""
        return self._hcr_post("/event", {
            "type": event_type,
            "data": event_data
        })
    
    def state_exists(self) -> bool:
        """Check if HCR has saved state"""
        result = self._hcr_get("/state/exists")
        return result.get("exists", False)


# Create bridge instance
hcr_bridge = HCRMCPBridge()

# Create MCP server
mcp = Server("hcr-cognitive-runtime")


@mcp.tool()
def get_hcr_context() -> str:
    """
    Get current cognitive context from HCR.
    
    Returns the current task, progress, and next action
    as determined by the Hybrid Cognitive Runtime.
    
    Use this to understand what the user is working on
    before providing assistance.
    """
    context = hcr_bridge.get_context()
    
    if "error" in context:
        return f"HCR Error: {context['error']}"
    
    # Format for Cascade consumption
    formatted = f"""## HCR Cognitive Context

**Current Task:** {context.get('current_task', 'Unknown')}
**Progress:** {context.get('progress_percent', 0)}%
**Next Action:** {context.get('next_action', 'Unknown')}
**Confidence:** {context.get('confidence', 0):.2f}
**Time Gap:** {context.get('gap_minutes', 0):.1f} minutes

**Context Facts:**
"""
    
    for fact in context.get('facts', [])[:10]:
        formatted += f"\n- {fact}"
    
    return formatted


@mcp.tool()
def resume_session(gap_minutes: float = 0) -> str:
    """
    Trigger HCR resume analysis.
    
    Args:
        gap_minutes: Minutes since last activity (for context freshness)
    
    Returns updated cognitive context after running HCO analysis.
    
    Use this when:
    - User returns after being away
    - You need fresh context about project state
    - Current context seems stale
    """
    result = hcr_bridge.resume_session(gap_minutes)
    
    if "error" in result:
        return f"HCR Error: {result['error']}"
    
    formatted = f"""## HCR Resume Analysis

**Task:** {result.get('current_task', 'Unknown')}
**Progress:** {result.get('progress_percent', 0)}%
**Suggested Next Action:** {result.get('next_action', 'Unknown')}
**Confidence:** {result.get('confidence', 0):.2f}

**Based on context:**
- Branch: {next((f for f in result.get('facts', []) if 'branch:' in f), 'unknown')}
- Language: {next((f for f in result.get('facts', []) if 'language:' in f), 'unknown')}
- Uncommitted: {'yes' if any('uncommitted' in f for f in result.get('facts', [])) else 'no'}
"""
    
    return formatted


@mcp.tool()
def update_hcr_state(event_type: str, file_path: str = "", command: str = "") -> str:
    """
    Update HCR cognitive state with an event.
    
    Args:
        event_type: Type of event ('file_edit', 'git_commit', 'terminal', 'manual')
        file_path: Path to file (for file_edit events)
        command: Command executed (for terminal events)
    
    Use this to inform HCR about:
    - Files being edited
    - Commands being run
    - Git operations
    
    This keeps the cognitive state current.
    """
    event_data = {}
    
    if file_path:
        event_data["path"] = file_path
    if command:
        event_data["command"] = command
    
    result = hcr_bridge.update_state(event_type, event_data)
    
    if "error" in result:
        return f"HCR Error: {result['error']}"
    
    return f"HCR state updated: {event_type} event recorded"


@mcp.tool()
def check_hcr_status() -> str:
    """
    Check if HCR engine is running and has state.
    
    Returns status of the cognitive runtime.
    """
    try:
        exists = hcr_bridge.state_exists()
        context = hcr_bridge.get_context()
        
        if "error" in context:
            return f"HCR Engine: Running but no context available\nState exists: {exists}"
        
        return f"""## HCR Status

**Engine:** Running on {HCR_BASE_URL}
**State exists:** {exists}
**Current task:** {context.get('current_task', 'None')}
**Progress:** {context.get('progress_percent', 0)}%

HCR is ready to provide cognitive context.
"""
    except Exception as e:
        return f"HCR Error: {str(e)}\n\nTo start HCR:\npython -m product.cli.resume --server --project <path>"


def main():
    """Run MCP server"""
    if MCP_AVAILABLE:
        print("Starting HCR MCP Server...", file=sys.stderr)
        print(f"Connecting to HCR at {HCR_BASE_URL}", file=sys.stderr)
        
        # Check HCR is running
        try:
            hcr_bridge._check_engine()
            print("HCR engine connected successfully", file=sys.stderr)
        except RuntimeError as e:
            print(f"Warning: {e}", file=sys.stderr)
            print("MCP server will start but tools may fail", file=sys.stderr)
        
        # Run server
        mcp.run()
    else:
        print("MCP SDK not available - running in development mode", file=sys.stderr)
        print("Available tools:")
        print("  - get_hcr_context()")
        print("  - resume_session(gap_minutes)")
        print("  - update_hcr_state(event_type, file_path, command)")
        print("  - check_hcr_status()")


if __name__ == "__main__":
    import sys
    main()
