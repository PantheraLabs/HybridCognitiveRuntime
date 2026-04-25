"""
File System Watcher

Captures file system state relevant to developer context:
- Recently modified files
- Open files (from editor state)
- File structure changes
- Last N files touched
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta


class FileWatcher:
    """Tracks file system state for developer context"""
    
    def __init__(self, project_path: str, ignore_patterns: Optional[List[str]] = None):
        self.project_path = Path(project_path)
        self.ignore_patterns = ignore_patterns or [
            "node_modules", ".git", "__pycache__", ".hcr",
            "dist", "build", ".next", ".vercel"
        ]
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
        return False
    
    def get_recent_files(self, minutes: int = 60, max_files: int = 20) -> List[Dict[str, Any]]:
        """
        Get files modified in the last N minutes.
        
        Args:
            minutes: Time window to look back
            max_files: Maximum files to return
            
        Returns:
            List of file info dicts
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_files = []
        
        try:
            for root, dirs, files in os.walk(self.project_path):
                # Filter out ignored directories
                dirs[:] = [
                    d for d in dirs 
                    if not self._should_ignore(Path(root) / d)
                ]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if self._should_ignore(file_path):
                        continue
                    
                    try:
                        stat = file_path.stat()
                        mod_time = datetime.fromtimestamp(stat.st_mtime)
                        
                        if mod_time > cutoff:
                            recent_files.append({
                                "path": str(file_path.relative_to(self.project_path)),
                                "modified_at": mod_time.isoformat(),
                                "size_bytes": stat.st_size
                            })
                    except (OSError, PermissionError):
                        continue
                        
        except Exception as e:
            print(f"[HCR] Error scanning files: {e}")
        
        # Sort by modification time (most recent first) and limit
        recent_files.sort(key=lambda x: x["modified_at"], reverse=True)
        return recent_files[:max_files]
    
    def get_file_extensions(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count file extensions from file list"""
        extensions = {}
        for file_info in files:
            ext = Path(file_info["path"]).suffix or "no_extension"
            extensions[ext] = extensions.get(ext, 0) + 1
        return extensions
    
    def get_primary_language(self, extensions: Dict[str, int]) -> str:
        """Infer primary programming language from file extensions"""
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".rb": "Ruby",
            ".php": "PHP"
        }
        
        if not extensions:
            return "unknown"
        
        # Get most common extension
        most_common = max(extensions.items(), key=lambda x: x[1])
        return lang_map.get(most_common[0], f"{most_common[0]} files")
    
    def get_open_files_from_state(self, saved_state: Optional[Dict]) -> List[str]:
        """
        Extract list of open files from previously saved state.
        VS Code integration would provide actual open files.
        """
        if not saved_state:
            return []
        
        # Try to get from previous context
        recent = saved_state.get("recent_files", [])
        return [f["path"] for f in recent[:5]]  # Assume last 5 were "open"
    
    def capture_state(self, lookback_minutes: int = 60) -> Dict[str, Any]:
        """
        Capture current file system state.
        
        Returns:
            Dictionary with file context
        """
        recent_files = self.get_recent_files(minutes=lookback_minutes)
        extensions = self.get_file_extensions(recent_files)
        primary_lang = self.get_primary_language(extensions)
        
        # Group files by directory
        dirs = {}
        for f in recent_files:
            dir_name = str(Path(f["path"]).parent)
            if dir_name == ".":
                dir_name = "root"
            dirs[dir_name] = dirs.get(dir_name, 0) + 1
        
        return {
            "recent_files": recent_files,
            "file_count": len(recent_files),
            "extensions": extensions,
            "primary_language": primary_lang,
            "active_directories": dirs,
            "captured_at": datetime.now().isoformat()
        }
