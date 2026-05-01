"""
File System Watcher

Captures file system state relevant to developer context:
- Recently modified files
- Open files (from editor state)
- File structure changes
- Last N files touched
"""

import os
import difflib
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Optional AST parsing for Python files
try:
    import ast
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False


@dataclass
class FileChange:
    """Detailed file change information"""
    path: str
    change_type: str  # 'added', 'removed', 'modified', 'unchanged'
    lines_added: int = 0
    lines_removed: int = 0
    functions_changed: List[str] = None
    classes_changed: List[str] = None
    imports_changed: List[str] = None
    diff_summary: str = ""
    
    def __post_init__(self):
        if self.functions_changed is None:
            self.functions_changed = []
        if self.classes_changed is None:
            self.classes_changed = []
        if self.imports_changed is None:
            self.imports_changed = []


class FileWatcher:
    """Tracks file system state for developer context with detailed change detection"""
    
    def __init__(self, project_path: str, ignore_patterns: Optional[List[str]] = None):
        self.project_path = Path(project_path)
        self.ignore_patterns = ignore_patterns or [
            "node_modules", ".git", "__pycache__", ".hcr",
            "dist", "build", ".next", ".vercel"
        ]
        # Store file snapshots for diff computation
        self._file_snapshots: Dict[str, str] = {}
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content if it's a text file"""
        try:
            # Skip binary files
            text_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', 
                              '.rs', '.cpp', '.c', '.h', '.rb', '.php', '.swift',
                              '.kt', '.scala', '.html', '.css', '.scss', '.json',
                              '.yaml', '.yml', '.xml', '.md', '.txt', '.sql'}
            if file_path.suffix not in text_extensions:
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None
    
    def _compute_diff(self, old_content: str, new_content: str) -> Tuple[int, int, str]:
        """Compute diff between two file contents"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        
        lines_added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        # Create summary (first 10 lines of diff)
        diff_summary = '\n'.join(diff[:15]) if diff else "No changes"
        
        return lines_added, lines_removed, diff_summary
    
    def _extract_python_changes(self, old_content: str, new_content: str) -> Dict[str, List[str]]:
        """Extract function, class, and import changes from Python files"""
        if not AST_AVAILABLE:
            return {"functions": [], "classes": [], "imports": []}
        
        try:
            old_tree = ast.parse(old_content) if old_content else ast.Module(body=[], type_ignores=[])
            new_tree = ast.parse(new_content)
            
            old_funcs = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.FunctionDef)}
            new_funcs = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.FunctionDef)}
            
            old_classes = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.ClassDef)}
            new_classes = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.ClassDef)}
            
            old_imports = set()
            new_imports = set()
            
            for node in ast.walk(old_tree):
                if isinstance(node, ast.Import):
                    old_imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    old_imports.add(node.module or "")
            
            for node in ast.walk(new_tree):
                if isinstance(node, ast.Import):
                    new_imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    new_imports.add(node.module or "")
            
            return {
                "functions": list(new_funcs - old_funcs) + list(old_funcs - new_funcs),
                "classes": list(new_classes - old_classes) + list(old_classes - new_classes),
                "imports": list(new_imports - old_imports)
            }
        except SyntaxError:
            return {"functions": [], "classes": [], "imports": []}
    
    def capture_file_change(self, file_path: str, old_content: Optional[str] = None) -> Optional[FileChange]:
        """
        Capture detailed change information for a single file.
        
        Args:
            file_path: Path to the file (relative to project root)
            old_content: Previous content of the file (if None, will check snapshot)
            
        Returns:
            FileChange object with detailed diff information, or None on error
        """
        try:
            abs_path = self.project_path / file_path
            
            if not abs_path.exists():
                # File was deleted
                return FileChange(
                    path=file_path,
                    change_type='removed',
                    lines_removed=len((old_content or "").splitlines())
                )
            
            new_content = self._read_file_content(abs_path)
            if new_content is None:
                return None  # Binary or unreadable file
            
            # Get old content
            if old_content is None:
                old_content = self._file_snapshots.get(file_path, "")
            
            # Update snapshot
            self._file_snapshots[file_path] = new_content
            
            # Compute diff
            lines_added, lines_removed, diff_summary = self._compute_diff(old_content, new_content)
            
            # Determine change type
            if not old_content:
                change_type = 'added'
            elif lines_added == 0 and lines_removed == 0:
                change_type = 'unchanged'
            else:
                change_type = 'modified'
            
            # Extract AST changes for Python files
            funcs, classes, imports = [], [], []
            if abs_path.suffix == '.py':
                try:
                    changes = self._extract_python_changes(old_content, new_content)
                    funcs = changes["functions"]
                    classes = changes["classes"]
                    imports = changes["imports"]
                except Exception:
                    # AST parsing failed - continue without function details
                    pass
            
            return FileChange(
                path=file_path,
                change_type=change_type,
                lines_added=lines_added,
                lines_removed=lines_removed,
                functions_changed=funcs,
                classes_changed=classes,
                imports_changed=imports,
                diff_summary=diff_summary
            )
        except Exception:
            # Error boundary: return None on any failure
            return None
    
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
        Capture current file system state with detailed change tracking.
        
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
            "file_snapshots_loaded": len(self._file_snapshots),
            "captured_at": datetime.now().isoformat()
        }
    
    def get_changed_files_with_details(self, since_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get detailed change information for all recently modified files.
        
        Returns:
            List of FileChange objects as dictionaries
        """
        recent_files = self.get_recent_files(minutes=since_minutes)
        changes = []
        
        for file_info in recent_files:
            file_path = file_info["path"]
            change = self.capture_file_change(file_path)
            if change:
                changes.append(asdict(change))
        
        return changes
