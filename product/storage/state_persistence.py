"""
State Persistence for "Resume Without Re-Explaining"

Saves and loads developer cognitive state to/from disk.
State stored in .hcr/ directory at project root.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class DevStatePersistence:
    """Handles saving and loading developer cognitive state"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.hcr_dir = self.project_path / ".hcr"
        self.state_file = self.hcr_dir / "session_state.json"
        self.history_dir = self.hcr_dir / "history"
    
    def _ensure_dirs(self):
        """Ensure .hcr directories exist"""
        self.hcr_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save current developer state to disk.
        
        Args:
            state: Developer cognitive state dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            self._ensure_dirs()
            
            # Add timestamp
            state["saved_at"] = datetime.now().isoformat()
            state["project_path"] = str(self.project_path)
            
            # Save to main state file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Also save to history for tracking
            history_file = self.history_dir / f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(history_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"[HCR] Error saving state: {e}")
            return False
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load developer state from disk.
        
        Returns:
            State dictionary or None if no state exists
        """
        try:
            if not self.state_file.exists():
                return None
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            return state
            
        except Exception as e:
            print(f"[HCR] Error loading state: {e}")
            return None
    
    def state_exists(self) -> bool:
        """Check if a saved state exists"""
        return self.state_file.exists()
    
    def get_last_activity_time(self) -> Optional[datetime]:
        """Get timestamp of last activity from saved state"""
        state = self.load_state()
        if state and "saved_at" in state:
            return datetime.fromisoformat(state["saved_at"])
        return None
    
    def get_gap_duration(self) -> Optional[float]:
        """
        Get minutes since last activity.
        
        Returns:
            Minutes as float, or None if no previous state
        """
        last_activity = self.get_last_activity_time()
        if not last_activity:
            return None
        
        gap = datetime.now() - last_activity
        return gap.total_seconds() / 60


def get_project_root() -> Path:
    """
    Find project root by looking for .git directory or package.json.
    Starts from current directory and walks up.
    """
    current = Path.cwd()
    
    while current != current.parent:
        if (current / ".git").exists() or (current / "package.json").exists():
            return current
        current = current.parent
    
    return Path.cwd()  # Fallback to current directory
