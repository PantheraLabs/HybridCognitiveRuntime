"""Operator tools for learned HCO operator retrieval.

Handles:
- hcr_get_learned_operators: List operators learned across projects
"""
from .base_tool import BaseMCPTool
from typing import Any, Dict


class OperatorTools(BaseMCPTool):
    """Learned operator retrieval with caching."""

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get learned operators - delegates to responder's implementation."""
        if self.responder and hasattr(self.responder, '_tool_get_learned_operators'):
            return await self.responder._tool_get_learned_operators(args)
        return {"error": "Operators not available", "operators": []}
