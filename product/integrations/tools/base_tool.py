"""
Base MCP Tool Handler

Provides common infrastructure for all MCP tool implementations:
- Logging & error handling
- Circuit breaker integration
- Request tracing
- Rate limiting
- Timeout management
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import asyncio


class BaseMCPTool(ABC):
    """
    Base class for all MCP tool handlers.
    
    Implements common patterns:
    - Async/await patterns with timeouts
    - Circuit breaker checks
    - Request tracing integration
    - Error handling with context
    - Rate limiting
    """
    
    def __init__(self, responder=None):
        """
        Initialize tool handler.
        
        Args:
            responder: Reference to parent HCRMCPResponder for access to:
                - engine: HCREngine instance
                - logger: Logging instance
                - _run_blocking: Thread pool execution
                - _check_circuit_breaker: Resilience checks
                - _record_circuit_breaker_*: State tracking
        """
        self.responder = responder
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tool_name = self._infer_tool_name()
    
    def _infer_tool_name(self) -> str:
        """Infer tool name from class name (e.g., StateTools -> hcr_get_state)"""
        class_name = self.__class__.__name__
        # Convert CamelCase to snake_case and add hcr_ prefix if not present
        s1 = ''.join(['_' + c.lower() if c.isupper() else c for c in class_name]).lstrip('_')
        if not s1.startswith('hcr_'):
            s1 = f'hcr_{s1}'
        return s1
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given arguments.
        
        Must be implemented by subclasses.
        
        Args:
            args: Tool arguments from MCP call
            
        Returns:
            Tool result as dict with MCP-compatible format
        """
        pass
    
    def _error_response(self, message: str, error_code: str = "TOOL_ERROR") -> Dict[str, Any]:
        """
        Generate standardized error response.
        
        Args:
            message: Error description
            error_code: Error classification
            
        Returns:
            MCP-compatible error response dict
        """
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ {self.tool_name}: {message}\n\nError code: {error_code}\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ],
            "isError": True
        }
    
    def _success_response(self, content: str) -> Dict[str, Any]:
        """
        Generate standardized success response.
        
        Args:
            content: Success message/content
            
        Returns:
            MCP-compatible success response dict
        """
        return {
            "content": [{"type": "text", "text": content}],
            "isError": False
        }
    
    def _check_circuit_breaker(self, component: str) -> tuple[bool, str]:
        """Check circuit breaker status via responder."""
        if self.responder and hasattr(self.responder, '_check_circuit_breaker'):
            return self.responder._check_circuit_breaker(component)
        return True, "Circuit breaker unavailable"
    
    def _record_success(self, component: str):
        """Record successful operation for circuit breaker recovery."""
        if self.responder and hasattr(self.responder, '_record_circuit_breaker_success'):
            self.responder._record_circuit_breaker_success(component)
    
    def _record_failure(self, component: str):
        """Record failed operation for circuit breaker tracking."""
        if self.responder and hasattr(self.responder, '_record_circuit_breaker_failure'):
            self.responder._record_circuit_breaker_failure(component)
    
    async def _run_blocking(self, fn, timeout: float = 5.0) -> Any:
        """Run blocking operation via responder's thread pool."""
        if self.responder and hasattr(self.responder, '_run_blocking'):
            return await self.responder._run_blocking(fn, timeout)
        # Fallback: Run directly (not recommended)
        return fn()
    
    def _get_engine(self):
        """Get HCREngine from responder."""
        if self.responder and hasattr(self.responder, 'engine'):
            return self.responder.engine
        return None
    
    def _get_persistence(self):
        """Get DevStatePersistence from responder."""
        if self.responder and hasattr(self.responder, 'persistence'):
            return self.responder.persistence
        return None
    
    def _validate_args(self, args: Dict[str, Any], required_keys: list = None, optional_keys: list = None) -> Optional[Dict[str, Any]]:
        """
        Validate tool arguments.
        
        Args:
            args: Arguments dict to validate
            required_keys: Keys that must be present
            optional_keys: Keys that may be present
            
        Returns:
            Validated args dict, or None if validation fails
        """
        if not isinstance(args, dict):
            self.logger.warning(f"Invalid arguments (not dict): {type(args)}")
            return None
        
        required_keys = required_keys or []
        optional_keys = optional_keys or []
        
        # Check required keys
        for key in required_keys:
            if key not in args:
                self.logger.warning(f"Missing required argument: {key}")
                return None
        
        # Check for unexpected keys
        allowed = set(required_keys) | set(optional_keys)
        extra = set(args.keys()) - allowed
        if extra and allowed:  # Only warn if we specified allowed keys
            self.logger.warning(f"Unexpected arguments: {extra}")
        
        return args
    
    def _format_json_response(self, data: Any, key: str = None) -> Dict[str, Any]:
        """
        Format JSON data as MCP response.
        
        Args:
            data: Data to format
            key: Optional key to wrap data (e.g., 'state', 'graph')
            
        Returns:
            MCP-compatible response dict
        """
        import json
        
        if key:
            content = {key: data}
        else:
            content = data
        
        return {
            "content": [{"type": "text", "text": json.dumps(content, indent=2, default=str)}],
            "isError": False
        }
