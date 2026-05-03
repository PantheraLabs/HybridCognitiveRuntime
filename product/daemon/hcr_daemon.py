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
    """HCR Daemon for background context extraction."""

    def __init__(self, project_path: str, engine=None):
        self.project_path = Path(project_path).absolute()
        self.hcr_dir = self.project_path / ".hcr"
        self.hcr_dir.mkdir(exist_ok=True)
        
        self.log_file = self.hcr_dir / "daemon.log"
        self.pid_file = self.hcr_dir / "daemon.pid"
        self.is_running = False
        self._external_engine = engine  # optional shared engine from responder
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(str(self.project_path / ".hcr" / "daemon.log")),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("HCR-Daemon")

    def is_already_running(self) -> bool:
        if not self.pid_file.exists():
            return False
        
        try:
            pid = int(self.pid_file.read_text().strip())
            # Windows: os.kill(pid, 0) raises OSError for stale PIDs
            # Use psutil if available for cross-platform process checking
            try:
                import psutil
                return psutil.pid_exists(pid)
            except ImportError:
                # Fallback: try to open process (Windows-specific via ctypes)
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
        except (ValueError, OSError, Exception):
            # Stale PID file - clean it up
            try:
                self.pid_file.unlink(missing_ok=True)
            except:
                pass
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
        
        # Setup signal handlers - only in main thread (Windows restriction)
        import threading
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGTERM, self._handle_exit)
                signal.signal(signal.SIGINT, self._handle_exit)
            except (ValueError, OSError):
                pass  # Not main thread or Windows limitation

        try:
            self._run_main_loop()
        except Exception as e:
            self.logger.error(f"Daemon crashed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
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
        
        # Use external engine if provided (from responder) so state changes
        # from tool calls are visible to the daemon and persisted.
        engine = self._external_engine
        if engine is None:
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
            self.logger.info("File watcher started successfully")
        except Exception as e:
            self.logger.warning(f"File watcher failed to start: {e}")
            self.logger.warning("Daemon will continue without file watching - state saved via tool calls")
        
        self.logger.info("=" * 60)
        self.logger.info("HCR Daemon is FULLY ACTIVE")
        self.logger.info("Watching for file changes with diff tracking...")
        self.logger.info("=" * 60)
        
        try:
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
