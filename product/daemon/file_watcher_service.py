"""
HCR File Watcher Service

Uses watchdog to monitor file system events and report them to the HCR engine.
Includes debouncing to prevent event storms during rapid saves.
NOW WITH: Diff tracking, AST analysis, and direct HCREngine integration
"""

import time
import logging
import sys
from pathlib import Path
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from product.state_capture.file_watcher import FileWatcher, FileChange
from src.engine_api import EngineEvent, HCREngine


class HCRFileEventHandler(FileSystemEventHandler):
    """
    Enhanced file event handler that captures detailed changes.
    
    Features:
    - Diff computation (lines added/removed)
    - AST parsing for Python files (functions, classes, imports)
    - Direct HCREngine integration (no HTTP needed)
    - File content snapshots for accurate diffs
    """
    
    def __init__(self, project_path: str, engine: HCREngine, ignore_patterns: list = None):
        self.project_path = Path(project_path)
        self.engine = engine
        self.ignore_patterns = ignore_patterns or [
            ".git", "__pycache__", ".hcr", ".pytest_cache", 
            ".venv", "venv", "node_modules", "dist", "build"
        ]
        self.logger = logging.getLogger("HCRFileWatcher")
        self.last_event_time: Dict[tuple, float] = {}
        self.debounce_interval = 0.5  # seconds
        
        # Use the enhanced FileWatcher for diff tracking
        self.file_watcher = FileWatcher(project_path, self.ignore_patterns)
        
        # Pre-load snapshots for recently modified files
        self._load_recent_snapshots()
    
    def _load_recent_snapshots(self):
        """Pre-load file snapshots for files modified recently"""
        recent = self.file_watcher.get_recent_files(minutes=60, max_files=50)
        for file_info in recent:
            path = file_info["path"]
            abs_path = self.project_path / path
            if abs_path.exists():
                content = self.file_watcher._read_file_content(abs_path)
                if content is not None:
                    self.file_watcher._file_snapshots[path] = content
        self.logger.info(f"Pre-loaded {len(self.file_watcher._file_snapshots)} file snapshots")
    
    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        for pattern in self.ignore_patterns:
            if pattern in p.parts:
                return True
        return False
    
    def _get_relative_path(self, abs_path: str) -> str:
        """Convert absolute path to project-relative path"""
        try:
            return str(Path(abs_path).relative_to(self.project_path))
        except ValueError:
            return abs_path
    
    def _report_file_change(self, rel_path: str, change_type: str):
        """
        Report a detailed file change to HCR engine.
        
        This captures:
        - Line-by-line diffs
        - Function/class changes (Python)
        - Import changes (Python)
        - Summary statistics
        """
        try:
            # Use enhanced file watcher to compute detailed change
            change = self.file_watcher.capture_file_change(rel_path)
            
            if not change:
                self.logger.debug(f"Could not capture change for: {rel_path}")
                return
            
            # Create rich EngineEvent
            event = EngineEvent(
                event_type='file_edit',
                timestamp=__import__('datetime').datetime.now(),
                data={
                    'path': rel_path,
                    'change_type': change_type,
                    'lines_added': change.lines_added,
                    'lines_removed': change.lines_removed,
                    'functions_changed': change.functions_changed,
                    'classes_changed': change.classes_changed,
                    'imports_changed': change.imports_changed,
                    'diff_summary': change.diff_summary[:500] if change.diff_summary else ""
                }
            )
            
            # Update HCR engine directly
            self.engine.update_from_environment(event)
            
            # Log summary
            funcs_str = f" (funcs: {', '.join(change.functions_changed)})" if change.functions_changed else ""
            imports_str = f" (imports: {', '.join(change.imports_changed)})" if change.imports_changed else ""
            self.logger.info(
                f"✓ {rel_path}: +{change.lines_added}/-{change.lines_removed} lines{funcs_str}{imports_str}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to report file change: {e}")
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        # Debounce check
        rel_path = self._get_relative_path(event.src_path)
        current_time = time.time()
        key = ("modified", rel_path)
        
        if key in self.last_event_time:
            if current_time - self.last_event_time[key] < self.debounce_interval:
                return
        
        self.last_event_time[key] = current_time
        self._report_file_change(rel_path, "modified")
    
    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        rel_path = self._get_relative_path(event.src_path)
        self.logger.info(f"File created: {rel_path}")
        
        # For new files, record as added with full content
        change = self.file_watcher.capture_file_change(rel_path, old_content="")
        if change:
            event = EngineEvent(
                event_type='file_edit',
                timestamp=__import__('datetime').datetime.now(),
                data={
                    'path': rel_path,
                    'change_type': 'added',
                    'lines_added': change.lines_added,
                    'lines_removed': 0,
                    'functions_changed': change.functions_changed,
                    'classes_changed': change.classes_changed,
                    'imports_changed': change.imports_changed,
                    'diff_summary': f"New file: {change.lines_added} lines"
                }
            )
            self.engine.update_from_environment(event)
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        rel_path = self._get_relative_path(event.src_path)
        self.logger.info(f"File deleted: {rel_path}")
        
        # Get old content from snapshot for proper diff
        old_content = self.file_watcher._file_snapshots.get(rel_path, "")
        lines_removed = len(old_content.splitlines()) if old_content else 0
        
        event = EngineEvent(
            event_type='file_edit',
            timestamp=__import__('datetime').datetime.now(),
            data={
                'path': rel_path,
                'change_type': 'deleted',
                'lines_added': 0,
                'lines_removed': lines_removed,
                'functions_changed': [],
                'classes_changed': [],
                'imports_changed': [],
                'diff_summary': f"File deleted: {lines_removed} lines removed"
            }
        )
        self.engine.update_from_environment(event)
        
        # Remove from snapshots
        if rel_path in self.file_watcher._file_snapshots:
            del self.file_watcher._file_snapshots[rel_path]


class FileWatcherService:
    """
    Enhanced file watcher service with detailed change tracking.
    
    Now integrates directly with HCREngine instead of using HTTP.
    Captures diffs, AST analysis, and maintains file snapshots.
    """
    
    def __init__(self, project_path: str, engine: HCREngine):
        self.project_path = project_path
        self.engine = engine
        self.observer = Observer()
        self.handler = HCRFileEventHandler(project_path, engine)
        self.logger = logging.getLogger("FileWatcherService")
    
    def start(self):
        self.logger.info(f"Starting enhanced file watcher for: {self.project_path}")
        self.observer.schedule(self.handler, self.project_path, recursive=True)
        self.observer.start()
        self.logger.info("✓ File watcher active - capturing diffs and AST changes")
    
    def stop(self):
        self.logger.info("Stopping file watcher...")
        self.observer.stop()
        self.observer.join()
        self.logger.info("✓ File watcher stopped")
