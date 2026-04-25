"""
Git State Tracker

Captures relevant git state for context:
- Current branch
- Last commit message
- Uncommitted changes (files, not content)
- Recent commit history
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class GitTracker:
    """Tracks git state for developer context"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.git_dir = self.project_path / ".git"
    
    def is_git_repo(self) -> bool:
        """Check if project is a git repository"""
        return self.git_dir.exists()
    
    def _run_git(self, args: List[str]) -> Optional[str]:
        """Run git command and return output"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    
    def get_current_branch(self) -> str:
        """Get current git branch"""
        branch = self._run_git(["branch", "--show-current"])
        return branch or "unknown"
    
    def get_last_commit(self) -> Dict[str, str]:
        """Get information about last commit"""
        # Get commit hash
        commit_hash = self._run_git(["rev-parse", "--short", "HEAD"]) or "unknown"
        
        # Get commit message
        message = self._run_git(["log", "-1", "--pretty=%B"]) or "unknown"
        
        # Get commit time
        timestamp = self._run_git(["log", "-1", "--pretty=%ct"])
        commit_time = None
        if timestamp:
            try:
                commit_time = datetime.fromtimestamp(int(timestamp)).isoformat()
            except:
                pass
        
        # Get author
        author = self._run_git(["log", "-1", "--pretty=%an"]) or "unknown"
        
        return {
            "hash": commit_hash,
            "message": message.strip(),
            "time": commit_time or "unknown",
            "author": author
        }
    
    def get_uncommitted_changes(self) -> Dict[str, Any]:
        """
        Get summary of uncommitted changes.
        Returns file counts, not actual diffs (to keep state lightweight).
        """
        # Get modified files
        modified = self._run_git(["diff", "--name-only"])
        modified_files = modified.split("\n") if modified else []
        
        # Get staged files
        staged = self._run_git(["diff", "--cached", "--name-only"])
        staged_files = staged.split("\n") if staged else []
        
        # Get untracked files
        untracked = self._run_git(["ls-files", "--others", "--exclude-standard"])
        untracked_files = untracked.split("\n") if untracked else []
        
        # Filter empty strings
        modified_files = [f for f in modified_files if f]
        staged_files = [f for f in staged_files if f]
        untracked_files = [f for f in untracked_files if f]
        
        return {
            "modified_count": len(modified_files),
            "staged_count": len(staged_files),
            "untracked_count": len(untracked_files),
            "modified_files": modified_files[:10],  # Limit to 10 files
            "staged_files": staged_files[:10],
            "has_changes": any([modified_files, staged_files, untracked_files])
        }
    
    def get_recent_commits(self, count: int = 3) -> List[Dict[str, str]]:
        """Get recent commit history"""
        output = self._run_git(["log", f"-{count}", "--pretty=%h|%s|%cr"])
        
        if not output:
            return []
        
        commits = []
        for line in output.split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) >= 2:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "time_ago": parts[2] if len(parts) > 2 else ""
                    })
        
        return commits
    
    def capture_state(self) -> Dict[str, Any]:
        """
        Capture complete git state for developer context.
        
        Returns empty dict if not a git repo.
        """
        if not self.is_git_repo():
            return {}
        
        return {
            "is_git_repo": True,
            "branch": self.get_current_branch(),
            "last_commit": self.get_last_commit(),
            "uncommitted_changes": self.get_uncommitted_changes(),
            "recent_commits": self.get_recent_commits(),
            "captured_at": datetime.now().isoformat()
        }
