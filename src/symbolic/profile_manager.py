import json
import os
from typing import Dict, Any, List

class ProfileManager:
    """
    Maintains a behavioral profile of the user to inject personalized coding style
    constraints into the AI's context.
    """
    def __init__(self, workspace_path: str):
        self.profile_path = os.path.join(workspace_path, ".hcr", "profile.json")
        self.profile: Dict[str, Any] = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
                
        # Default empty profile
        return {
            "coding_style": [],
            "preferred_patterns": [],
            "strictness_level": "medium"
        }

    def save_profile(self):
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, "w") as f:
            json.dump(self.profile, f, indent=2)

    def add_style_rule(self, rule: str):
        """Add an observed coding style rule to the profile."""
        if rule not in self.profile.setdefault("coding_style", []):
            self.profile["coding_style"].append(rule)
            self.save_profile()

    def get_context_injection(self) -> List[str]:
        """Format the profile as a list of constraints for the MCP context."""
        constraints = []
        if self.profile.get("coding_style"):
            constraints.append("User Coding Style Preferences:")
            for style in self.profile["coding_style"]:
                constraints.append(f" - {style}")
                
        if self.profile.get("preferred_patterns"):
            constraints.append("Preferred Patterns:")
            for pattern in self.profile["preferred_patterns"]:
                constraints.append(f" - {pattern}")
                
        return constraints
