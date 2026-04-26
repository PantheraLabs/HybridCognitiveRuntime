"""
HCR Daemon Core

Manages the background processes that provide autonomous context extraction.
Handles PID management, signal handling, and service orchestration.
"""

import os
import sys
import time
import signal
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import load_config

class HCRDaemon:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).absolute()
        self.config = load_config(str(self.project_path))
        
        self.hcr_dir = self.project_path / ".hcr"
        self.hcr_dir.mkdir(exist_ok=True)
        
        self.pid_file = self.hcr_dir / "daemon.pid"
        self.log_file = self.hcr_dir / "daemon.log"
        
        self._setup_logging()
        self.services = []
        self.is_running = False

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stderr)
            ]
        )
        self.logger = logging.getLogger("HCRDaemon")

    def is_already_running(self) -> bool:
        if not self.pid_file.exists():
            return False
        
        try:
            pid = int(self.pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False

    def start(self):
        if self.is_already_running():
            self.logger.error("Daemon is already running.")
            return

        # Write PID
        pid = os.getpid()
        self.pid_file.write_text(str(pid))
        
        self.logger.info(f"HCR Daemon started (PID: {pid}) for project: {self.project_path}")
        self.is_running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_exit)
        signal.signal(signal.SIGINT, self._handle_exit)

        try:
            self._run_main_loop()
        finally:
            self._cleanup()

    def stop(self):
        if not self.pid_file.exists():
            print("Daemon is not running.")
            return

        try:
            pid = int(self.pid_file.read_text().strip())
            print(f"Stopping HCR Daemon (PID: {pid})...")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for cleanup
            for _ in range(10):
                if not self.pid_file.exists():
                    print("Stopped successfully.")
                    return
                time.sleep(0.5)
            
            # Force kill if still there
            if self.pid_file.exists():
                print("Force killing...")
                os.kill(pid, signal.SIGKILL)
                self.pid_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Error stopping daemon: {e}")

    def status(self):
        if self.is_already_running():
            pid = self.pid_file.read_text().strip()
            print(f"HCR Daemon is RUNNING (PID: {pid})")
            print(f"Project: {self.project_path}")
            print(f"Log: {self.log_file}")
            
            # Check engine connectivity
            try:
                resp = requests.get(f"http://localhost:{self.config.engine_port}/health", timeout=1)
                if resp.status_code == 200:
                    print(f"Engine: CONNECTED (Port: {self.config.engine_port})")
                else:
                    print(f"Engine: UNHEALTHY (Status: {resp.status_code})")
            except:
                print("Engine: NOT RUNNING")
        else:
            print("HCR Daemon is STOPPED")

    def _handle_exit(self, signum, frame):
        self.logger.info(f"Received signal {signum}. Shutting down...")
        self.is_running = False

    def _cleanup(self):
        self.logger.info("Cleaning up...")
        # Stop all services (to be implemented)
        for service in self.services:
            try:
                service.stop()
            except:
                pass
        
        if self.pid_file.exists():
            self.pid_file.unlink()
        self.logger.info("Daemon exited.")

    def _run_main_loop(self):
        """Main daemon loop"""
        from .file_watcher_service import FileWatcherService
        
        engine_url = f"http://localhost:{self.config.engine_port}"
        watcher = FileWatcherService(str(self.project_path), engine_url)
        
        try:
            watcher.start()
            self.services.append(watcher)
            
            while self.is_running:
                # Monitor health of services if needed
                time.sleep(2)
        finally:
            watcher.stop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HCR Daemon Management")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"])
    parser.add_argument("--project", default=".")
    
    args = parser.parse_args()
    daemon = HCRDaemon(args.project)
    
    if args.action == "start":
        daemon.start()
    elif args.action == "stop":
        daemon.stop()
    elif args.action == "status":
        daemon.status()
    elif args.action == "restart":
        daemon.stop()
        daemon.start()
