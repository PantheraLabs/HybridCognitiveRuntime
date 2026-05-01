"""Recommendation tools for AI-powered next action suggestions.

Handles:
- hcr_get_recommendations: Get next action recommendations with confidence scores
"""
from .base_tool import BaseMCPTool
from typing import Any, Dict


class RecommendationTools(BaseMCPTool):
    """AI-powered action recommendations with confidence scoring."""

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommendations - delegates to responder's implementation."""
        if self.responder and hasattr(self.responder, '_tool_get_recommendations'):
            return await self.responder._tool_get_recommendations(args)
        return {"error": "Recommendations not available", "recommendations": []}
