"""
HCR Engine HTTP Server

Local server that exposes Engine API over HTTP.
VS Code extension calls this directly (NOT via CLI subprocess).
"""

import json
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine_api import HCREngine, EngineEvent


# Global engine instance (one per server)
engine: HCREngine = None
project_path: str = None


class HCREngineHandler(BaseHTTPRequestHandler):
    """HTTP request handler for HCR Engine API"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def _send_json(self, data: Dict[str, Any], status: int = 200):
        """Send JSON response"""
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except (BrokenPipeError, ConnectionAbortedError):
            # Client disconnected before we could send the data
            pass
    
    def _send_error(self, message: str, status: int = 400):
        """Send error response"""
        self._send_json({"error": message}, status)
    
    def do_GET(self):
        """Handle GET requests"""
        global engine
        
        if not engine:
            self._send_error("Engine not initialized", 500)
            return
        
        path = self.path
        
        if path == '/health':
            self._send_json({"status": "ok", "engine": "ready"})
        
        elif path == '/context':
            # Get current context
            try:
                context = engine.infer_context()
                self._send_json(context.to_dict())
            except Exception as e:
                self._send_error(str(e), 500)
        
        elif path == '/state/exists':
            # Check if state exists
            self._send_json({"exists": engine.state_exists()})
        
        elif path == '/state/clear':
            # Clear state
            try:
                success = engine.clear_state()
                self._send_json({"cleared": success})
            except Exception as e:
                self._send_error(str(e), 500)
        elif path == '/causal_graph':
            try:
                graph = {
                    "forward": engine.dependency_graph.forward_edges,
                    "reverse": engine.dependency_graph.reverse_edges
                }
                # Convert sets to lists for JSON serialization
                serializable_graph = {
                    "forward": {k: list(v) for k, v in graph["forward"].items()},
                    "reverse": {k: list(v) for k, v in graph["reverse"].items()}
                }
                self._send_json(serializable_graph)
            except Exception as e:
                self._send_error(str(e), 500)
                
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)
    
    def do_POST(self):
        """Handle POST requests"""
        global engine
        
        if not engine:
            self._send_error("Engine not initialized", 500)
            return
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
            return
        
        path = self.path
        
        if path == '/event':
            # Handle event
            try:
                event_type = data.get('type', 'manual')
                event_data = data.get('data', {})
                
                # Normalization (Fix #2): Auto-detect event type from payload
                if event_type == 'manual' and ('path' in event_data or 'file' in event_data):
                    event_type = 'file_edit'
                
                event = EngineEvent(
                    event_type=event_type,
                    timestamp=datetime.now(),
                    data=event_data
                )
                
                engine.update_from_environment(event)
                context = engine.infer_context()
                
                self._send_json({
                    "updated": True,
                    "context": context.to_dict()
                })
                
            except Exception as e:
                self._send_error(str(e), 500)
        
        elif path == '/resume':
            # Trigger full resume
            try:
                # Simulate window focus event
                event = EngineEvent(
                    event_type='window_focus',
                    timestamp=datetime.now(),
                    data={'gap_minutes': data.get('gap_minutes', 0)}
                )
                
                engine.update_from_environment(event)
                context = engine.infer_context()
                
                self._send_json(context.to_dict())
                
            except Exception as e:
                self._send_error(str(e), 500)
                
        elif path == '/impact':
            try:
                file_path = data.get('file_path')
                if not file_path:
                    self._send_error("Missing file_path", 400)
                    return
                
                impacted = engine.impact_analyzer.predict_impact(file_path)
                self._send_json({"impacted_files": impacted})
            except Exception as e:
                self._send_error(str(e), 500)
        
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)


def start_server(project_path: str, port: int = 8733):
    """
    Start HCR Engine HTTP server.
    
    Args:
        project_path: Path to project root
        port: HTTP port (default 8733)
    """
    global engine
    
    # Initialize engine
    engine = HCREngine(project_path)
    
    # Try to load existing state
    engine.load_state()
    
    # Create server
    server = HTTPServer(('localhost', port), HCREngineHandler)
    
    print(f"[HCR Engine Server] Running on http://localhost:{port}")
    print(f"[HCR Engine Server] Project: {project_path}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HCR Engine Server] Shutting down...")
        server.shutdown()


def get_engine_status(port: int = 8733) -> bool:
    """Check if engine server is running"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='HCR Engine Server')
    parser.add_argument('--project', '-p', required=True, help='Project path')
    parser.add_argument('--port', type=int, default=8733, help='HTTP port')
    
    args = parser.parse_args()
    
    start_server(args.project, args.port)
