"""
Git Fact Extractor

Parses git commits and extracts structured facts for HCR memory.
Simple, fast, no LLM required for basic extraction.

Usage:
    from product.state_capture.git_extractor import GitFactExtractor
    extractor = GitFactExtractor("/path/to/project")
    facts = extractor.extract_recent_facts(count=5)
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class GitFactExtractor:
    """Extract facts from git commit history"""
    
    # Patterns that indicate meaningful commits (not noise)
    MEANINGFUL_PATTERNS = [
        r"^(feat|feature)",
        r"^(fix|bugfix|hotfix)",
        r"^(refactor|rewrite)",
        r"^(implement|add|create)",
        r"^(update|modify|change)",
        r"^(remove|delete|clean)",
        r"^(test|spec)",
        r"^(docs|documentation)",
    ]
    
    # Patterns that indicate noise (to skip)
    NOISE_PATTERNS = [
        r"^merge",
        r"^wip",
        r"^tmp",
        r"^temp",
        r"^checkpoint",
        r"^save",
        r"^auto",
        r"^lint",
        r"^format",
    ]
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
    
    def _run_git(self, args: List[str]) -> Optional[str]:
        """Run git command and return stdout"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_path)] + args,
                capture_output=True,
                text=True,
                timeout=5.0
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    
    def _is_meaningful(self, message: str) -> bool:
        """Check if commit message is meaningful (not noise)"""
        lower = message.lower().strip()
        
        # Check noise patterns first
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, lower):
                return False
        
        # Check meaningful patterns
        for pattern in self.MEANINGFUL_PATTERNS:
            if re.search(pattern, lower):
                return True
        
        # Default: if it's a decent length and not just "update", keep it
        return len(message) > 15 and not message.lower().startswith("update")
    
    def _extract_files_changed(self, commit_hash: str) -> List[str]:
        """Get list of files changed in a commit"""
        output = self._run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash])
        if output:
            return [f.strip() for f in output.split("\n") if f.strip()]
        return []
    
    def _parse_commit_message(self, message: str, files: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a commit message into a structured fact"""
        if not self._is_meaningful(message):
            return None
        
        # Clean up the message
        clean = message.strip()
        # Remove trailing punctuation
        clean = re.sub(r'[.!?]+$', '', clean)
        
        # Determine type
        lower = clean.lower()
        if lower.startswith(("feat", "feature", "implement", "add", "create")):
            fact_type = "feature"
        elif lower.startswith(("fix", "bugfix", "hotfix")):
            fact_type = "bugfix"
        elif lower.startswith(("refactor", "rewrite", "restructure")):
            fact_type = "refactor"
        elif lower.startswith(("test", "spec")):
            fact_type = "test"
        elif lower.startswith(("docs", "doc", "readme")):
            fact_type = "docs"
        else:
            fact_type = "change"
        
        # Build fact
        fact = {
            "type": fact_type,
            "content": clean,
            "files": files[:5],  # Limit files
            "source": "git_commit",
            "extracted_at": datetime.now().isoformat(),
        }
        
        return fact
    
    def extract_recent_facts(self, count: int = 5, since_hours: int = 48) -> List[Dict[str, Any]]:
        """
        Extract facts from recent git commits.
        
        Args:
            count: Maximum number of commits to analyze
            since_hours: Only look at commits from last N hours
            
        Returns:
            List of extracted fact dictionaries
        """
        # Get recent commits: hash, subject, author date
        format_str = "%H|%s|%ad"
        output = self._run_git([
            "log", f"--since={since_hours} hours ago",
            f"--max-count={count}",
            f"--format={format_str}",
            "--date=iso"
        ])
        
        if not output:
            return []
        
        facts = []
        for line in output.split("\n"):
            line = line.strip()
            if "|" not in line:
                continue
            
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            
            commit_hash, subject, date_str = parts
            
            # Get files changed
            files = self._extract_files_changed(commit_hash)
            
            # Parse into fact
            fact = self._parse_commit_message(subject, files)
            if fact:
                fact["commit_hash"] = commit_hash[:8]
                fact["commit_date"] = date_str
                facts.append(fact)
        
        return facts
    
    def extract_all_recent(self, max_facts: int = 10) -> List[str]:
        """
        Extract recent facts and return as simple strings for HCR state.
        
        Returns:
            List of fact strings ready for HCR symbolic.facts
        """
        facts = self.extract_recent_facts(count=max_facts)
        result = []
        
        for f in facts:
            # Format: "git: [type] message (files: a, b, c)"
            files_str = ", ".join(f["files"][:3]) if f["files"] else ""
            if files_str:
                fact_str = f"git:{f['type']}: {f['content']} (files: {files_str})"
            else:
                fact_str = f"git:{f['type']}: {f['content']}"
            result.append(fact_str)
        
        return result


def quick_extract(project_path: str, max_facts: int = 5) -> List[str]:
    """Quick helper to extract git facts from a project"""
    extractor = GitFactExtractor(project_path)
    return extractor.extract_all_recent(max_facts=max_facts)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    extractor = GitFactExtractor(path)
    facts = extractor.extract_recent_facts(count=5)
    
    print(f"Extracted {len(facts)} facts from git history:\n")
    for f in facts:
        print(f"  [{f['type']}] {f['content']}")
        if f['files']:
            print(f"    Files: {', '.join(f['files'][:3])}")
        print()
