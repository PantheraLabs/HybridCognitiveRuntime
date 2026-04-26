"""
HCR MCP Server - STDIO Transport

For Windsurf/Cascade integration.
Communicates via stdin/stdout using JSON-RPC.
"""

import sys
import json
import requests
from typing import Dict, Any, Optional

HCR_HOST = "localhost"
HCR_PORT = 8733
HCR_BASE_URL = f"http://{HCR_HOST}:{HCR_PORT}"


class HCRMCPBridge:
    """Bridge between MCP and HCR Engine HTTP API"""
    
    def __init__(self):
        self.base_url = HCR_BASE_URL
    
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
        return self._hcr_get("/context")
    
    def resume_session(self, gap_minutes: float = 0) -> Dict[str, Any]:
        return self._hcr_post("/resume", {"gap_minutes": gap_minutes})
    
    def update_state(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._hcr_post("/event", {"type": event_type, "data": event_data})
    
    def check_status(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=2)
            return {"running": r.status_code == 200, **r.json()}
        except:
            return {"running": False}


# Create bridge
hcr = HCRMCPBridge()


def send_message(msg: dict):
    """Send JSON message to stdout"""
    print(json.dumps(msg), flush=True)


def handle_initialize(id: int):
    """Handle initialize request"""
    send_message({
        "jsonrpc": "2.0",
        "id": id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "hcr-cognitive-runtime",
                "version": "0.1.0"
            }
        }
    })


def handle_tools_list(id: int):
    """Handle tools/list request"""
    send_message({
        "jsonrpc": "2.0",
        "id": id,
        "result": {
            "tools": [
                {
                    "name": "get_hcr_context",
                    "description": "Get current cognitive context from HCR including task, progress, and next action",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "resume_session",
                    "description": "Trigger HCR resume analysis with time gap",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "gap_minutes": {
                                "type": "number",
                                "description": "Minutes since last activity"
                            }
                        }
                    }
                },
                {
                    "name": "update_hcr_state",
                    "description": "Update HCR state with an event (file_edit, git_commit, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Type of event: file_edit, git_commit, terminal, manual"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "File path for file_edit events"
                            },
                            "command": {
                                "type": "string",
                                "description": "Command for terminal events"
                            }
                        }
                    }
                },
                {
                    "name": "check_hcr_status",
                    "description": "Check if HCR engine is running",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
    })


def handle_tool_call(id: int, name: str, arguments: dict):
    """Handle tools/call request"""
    result_text = ""
    
    if name == "get_hcr_context":
        context = hcr.get_context()
        if "error" in context:
            result_text = f"HCR Error: {context['error']}"
        else:
            result_text = f"""HCR Context:
Current Task: {context.get('current_task', 'Unknown')}
Progress: {context.get('progress_percent', 0)}%
Next Action: {context.get('next_action', 'Unknown')}
Confidence: {context.get('confidence', 0):.2f}
Time Gap: {context.get('gap_minutes', 0):.1f} minutes

Context Facts:
"""
            for fact in context.get('facts', [])[:10]:
                result_text += f"- {fact}\n"
    
    elif name == "resume_session":
        gap = arguments.get("gap_minutes", 0)
        result = hcr.resume_session(gap)
        if "error" in result:
            result_text = f"HCR Error: {result['error']}"
        else:
            result_text = f"""HCR Resume Analysis (gap: {gap} min):
Current Task: {result.get('current_task', 'Unknown')}
Progress: {result.get('progress_percent', 0)}%
Next Action: {result.get('next_action', 'Unknown')}
Confidence: {result.get('confidence', 0):.2f}"""
    
    elif name == "update_hcr_state":
        event_type = arguments.get("event_type", "manual")
        event_data = {}
        if arguments.get("file_path"):
            event_data["path"] = arguments["file_path"]
        if arguments.get("command"):
            event_data["command"] = arguments["command"]
        
        result = hcr.update_state(event_type, event_data)
        if "error" in result:
            result_text = f"HCR Error: {result['error']}"
        else:
            result_text = f"HCR state updated: {event_type} event recorded"
    
    elif name == "check_hcr_status":
        status = hcr.check_status()
        result_text = f"HCR Status: {'Running' if status.get('running') else 'Not Running'}\n"
        if status.get('status'):
            result_text += f"Engine: {status.get('status')}\n"
        if not status.get('running'):
            result_text += "Start HCR with: python -m product.cli.resume --server --project <path>"
    
    else:
        result_text = f"Unknown tool: {name}"
    
    send_message({
        "jsonrpc": "2.0",
        "id": id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
    })


def main():
    """Main server loop - JSON-RPC over stdio"""
    # Log to stderr (not stdout - that's for JSON-RPC)
    print("HCR MCP Server starting...", file=sys.stderr)
    print(f"Connecting to HCR at {HCR_BASE_URL}", file=sys.stderr)
    
    # Check HCR is running
    status = hcr.check_status()
    if status.get('running'):
        print("HCR engine connected", file=sys.stderr)
    else:
        print("WARNING: HCR engine not running", file=sys.stderr)
        print("Start it with: python -m product.cli.resume --server --project <path>", file=sys.stderr)
    
    print("MCP Server ready", file=sys.stderr)
    
    # Process JSON-RPC messages from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            msg = json.loads(line)
            method = msg.get("method", "")
            msg_id = msg.get("id")
            
            if method == "initialize":
                handle_initialize(msg_id)
            
            elif method == "tools/list":
                handle_tools_list(msg_id)
            
            elif method == "tools/call":
                params = msg.get("params", {})
                handle_tool_call(
                    msg_id,
                    params.get("name", ""),
                    params.get("arguments", {})
                )
            
            # Ignore other methods (notifications, etc.)
            
        except json.JSONDecodeError:
            print(f"Invalid JSON: {line}", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
