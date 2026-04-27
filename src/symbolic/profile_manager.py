"""
Profile Manager - Part of the Cognitive Twin

Tracks developer behavioral patterns and preferences.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json


@dataclass
class DeveloperProfile:
    """Developer behavioral profile"""
    # Workflow patterns
    preferred_working_hours: List[int] = field(default_factory=list)  # Hours of day (0-23)
    average_session_length: float = 0.0  # minutes
    
    # File patterns
    most_edited_file_types: List[str] = field(default_factory=list)
    typical_file_batch_size: int = 0  # files per commit
    
    # Tool preferences
    primary_ide: str = ""
    preferred_llm_provider: str = "groq"  # default
    
    # Meta
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ProfileManager:
    """Manages developer behavioral profiles"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.profile = DeveloperProfile()
        self._load_profile()
    
    def _load_profile(self):
        """Load profile from disk if exists"""
        if not self.storage_path:
            return
        
        path = Path(self.storage_path)
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.profile = DeveloperProfile(**data)
            except:
                pass
    
    def save_profile(self):
        """Save profile to disk"""
        if not self.storage_path:
            return
        
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.profile.__dict__, f, default=str)
    
    def record_session(self, duration_minutes: float):
        """Record a completed session"""
        # Update running average
        if self.profile.average_session_length == 0:
            self.profile.average_session_length = duration_minutes
        else:
            # Exponential moving average
            self.profile.average_session_length = (
                0.7 * self.profile.average_session_length + 
                0.3 * duration_minutes
            )
        
        self.profile.updated_at = datetime.now()
        self.save_profile()
    
    def get_workflow_prediction(self, current_hour: int) -> Dict[str, Any]:
        """Predict developer behavior based on profile"""
        # Simple heuristic: if they've worked at this hour before, likely to continue
        hour_match = current_hour in self.profile.preferred_working_hours
        
        return {
            "likely_to_continue": hour_match,
            "typical_session_remaining": self.profile.average_session_length * 0.3,
            "suggested_break": self.profile.average_session_length > 90,
        }

    def get_context_injection(self) -> List[str]:
        """Get profile-based rules for context injection"""
        rules = []
        if self.profile.primary_ide:
            rules.append(f"- Optimized for {self.profile.primary_ide}")
        if self.profile.most_edited_file_types:
            rules.append(f"- Preferred languages: {', '.join(self.profile.most_edited_file_types)}")
        
        return rules
