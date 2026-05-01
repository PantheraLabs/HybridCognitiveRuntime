"""
MCP Tool Handlers - Modular architecture for HCR MCP tools.

Phase 3 Refactoring: Extracted from monolithic mcp_server.py into
modular, testable, maintainable tool handler classes.

Each tool inherits from BaseMCPTool and implements execute() method.
"""

from .base_tool import BaseMCPTool
from .state_tools import GetStateTool, GetCausalGraphTool, GetRecentActivityTool
from .task_tools import GetCurrentTaskTool, GetNextActionTool
from .shared_state_tools import SharedStateTools
from .version_tools import VersionTools
from .operator_tools import OperatorTools
from .health_tools import HealthTools
from .session_tools import SessionTools
from .file_tools import FileTools
from .context_tools import ContextTools
from .impact_tools import ImpactTools
from .recommendation_tools import RecommendationTools
from .search_tools import SearchTools

__all__ = [
    'BaseMCPTool',
    'GetStateTool',
    'GetCausalGraphTool',
    'GetRecentActivityTool',
    'GetCurrentTaskTool',
    'GetNextActionTool',
    'SharedStateTools',
    'VersionTools',
    'OperatorTools',
    'HealthTools',
    'SessionTools',
    'FileTools',
    'ContextTools',
    'ImpactTools',
    'RecommendationTools',
    'SearchTools',
]
