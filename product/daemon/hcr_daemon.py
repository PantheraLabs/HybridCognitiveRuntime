"""
HCR Daemon Core

Manages the background processes that provide autonomous context extraction.
Handles PID management, signal handling, and service orchestration.
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

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
        except (ValueError, ProcessLookupError, PermissionError, OSError):
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
            print("\nFeatures active:")
            print("  ✓ File watcher with diff tracking")
            print("  ✓ AST analysis (functions, classes, imports)")
            print("  ✓ Direct HCREngine integration (no HTTP)")
            print("  ✓ Auto-save every 30 seconds")
            
            # Check if state exists
            state_file = self.hcr_dir / "session_state.json"
            if state_file.exists():
                import json
                try:
                    with open(state_file) as f:
                        data = json.load(f)
                    cog_state = data.get("cognitive_state", {})
                    facts = cog_state.get("symbolic", {}).get("facts", [])
                    print(f"\nState: {len(facts)} facts recorded")
                except:
                    print("\nState: exists (unreadable)")
            else:
                print("\nState: not initialized")
        else:
            print("HCR Daemon is STOPPED")
            print(f"Run 'python -m product.daemon start --project {self.project_path}' to start")

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
        """Main daemon loop - now with direct HCREngine integration"""
        from .file_watcher_service import FileWatcherService
        from src.engine_api import HCREngine
        
        # Initialize HCREngine directly (no HTTP needed)
        self.logger.info("Initializing HCREngine...")
        engine = HCREngine(str(self.project_path), self.config)
        
        # Load existing state if available
        if engine.state_exists():
            engine.load_state()
            self.logger.info("Loaded existing cognitive state")
        else:
            self.logger.info("No existing state found - starting fresh")
        
        # Start file watcher with direct engine integration
        watcher = FileWatcherService(str(self.project_path), engine)
        
        try:
            watcher.start()
            self.services.append(watcher)
            
            self.logger.info("=" * 60)
            self.logger.info("HCR Daemon is FULLY ACTIVE")
            self.logger.info("Watching for file changes with diff tracking...")
            self.logger.info("=" * 60)
            
            while self.is_running:
                # Periodic state save (every 30 seconds)
                time.sleep(30)
                if engine._current_state:
                    engine.save_state()
                    self.logger.debug("Auto-saved cognitive state")
                    
        finally:
            watcher.stop()
            # Final state save
            engine.save_state()
            self.logger.info("Final state saved")

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
