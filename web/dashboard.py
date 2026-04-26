import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8734
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def launch_dashboard():
    """Launch the causal dashboard in the default web browser"""
    print(f"[HCR Dashboard] Starting dashboard server at http://localhost:{PORT}")
    
    # Check if dashboard.html exists
    html_file = Path(DIRECTORY) / "dashboard.html"
    if not html_file.exists():
        print(f"[HCR Error] dashboard.html not found in {DIRECTORY}")
        return

    # In a real app, we'd run this in a thread or separate process
    # For now, we'll just advise the user or use a simple serve
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"[HCR Dashboard] Opening browser...")
            webbrowser.open(f"http://localhost:{PORT}/dashboard.html")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[HCR Dashboard] Shutting down...")
    except Exception as e:
        print(f"[HCR Error] Failed to start dashboard: {e}")

if __name__ == "__main__":
    launch_dashboard()
