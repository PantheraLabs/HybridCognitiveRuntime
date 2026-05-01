"""Search history tools for HCR event log queries.

Handles:
- hcr_search_history: Search events by keyword, file, or type
"""
from .base_tool import BaseMCPTool
from typing import Any, Dict


class SearchTools(BaseMCPTool):
    """Event history search with keyword and type filtering."""

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search event history - delegates to responder's implementation."""
        if self.responder and hasattr(self.responder, '_tool_search_history'):
            return await self.responder._tool_search_history(args)
        return {"error": "Search not available", "results": []}
