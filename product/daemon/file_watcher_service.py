"""
HCR File Watcher Service

Uses watchdog to monitor file system events and report them to the HCR engine.
Includes debouncing to prevent event storms during rapid saves.
"""

import time
import logging
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class HCRFileEventHandler(FileSystemEventHandler):
    def __init__(self, engine_url: str, ignore_patterns: list = None):
        self.engine_url = engine_url
        self.ignore_patterns = ignore_patterns or [".git", "__pycache__", ".hcr", ".pytest_cache", ".venv", "venv", "node_modules"]
        self.logger = logging.getLogger("HCRFileWatcher")
        self.last_event_time = {}
        self.debounce_interval = 0.5 # seconds

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        for pattern in self.ignore_patterns:
            if pattern in p.parts:
                return True
        return False

    def _report_event(self, event_type: str, path: str):
        if self._should_ignore(path):
            return

        # Debounce
        current_time = time.time()
        key = (event_type, path)
        if key in self.last_event_time:
            if current_time - self.last_event_time[key] < self.debounce_interval:
                return
        
        self.last_event_time[key] = current_time

        self.logger.info(f"Reporting {event_type} for: {path}")
        try:
            requests.post(
                f"{self.engine_url}/event",
                json={
                    "type": event_type,
                    "data": {"path": str(path)}
                },
                timeout=1
            )
        except Exception as e:
            self.logger.debug(f"Failed to report event: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._report_event("file_edit", event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._report_event("file_create", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._report_event("file_delete", event.src_path)

class FileWatcherService:
    def __init__(self, project_path: str, engine_url: str):
        self.project_path = project_path
        self.engine_url = engine_url
        self.observer = Observer()
        self.handler = HCRFileEventHandler(engine_url)
        self.logger = logging.getLogger("FileWatcherService")

    def start(self):
        self.logger.info(f"Starting file watcher for: {self.project_path}")
        self.observer.schedule(self.handler, self.project_path, recursive=True)
        self.observer.start()

    def stop(self):
        self.logger.info("Stopping file watcher...")
        self.observer.stop()
        self.observer.join()
