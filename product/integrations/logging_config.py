"""
Structured Logging for HCR MCP Server

Phase 3 Enhancement: Production-grade JSON logging with:
- Request correlation IDs
- Performance metrics
- Error context
- Component tracking

Integrates with ELK/Datadog/CloudWatch for centralized observability.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from .config import MCPConfig


class StructuredLogFormatter(logging.Formatter):
    """
    Custom formatter that produces JSON-structured logs.
    
    Each log line is a complete JSON object with:
    - timestamp: ISO 8601 format
    - level: Log level (INFO, WARNING, ERROR, DEBUG)
    - logger: Logger name
    - message: Log message
    - request_id: Optional request ID for correlation
    - context: Additional context fields
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        
        if hasattr(record, "context"):
            log_obj.update(record.context)
        
        return json.dumps(log_obj)


class RequestLogger:
    """
    Centralized request logging with structured format.
    
    Usage:
        logger = RequestLogger("tool-name")
        logger.log_request_start(request_id, tool_name, args)
        logger.log_request_event(request_id, "git_capture_complete", duration_ms=500)
        logger.log_request_end(request_id, "success", duration_ms=1234)
    """
    
    def __init__(self, component_name: str):
        """Initialize request logger for a component"""
        self.component = component_name
        self.logger = logging.getLogger(f"HCR.{component_name}")
    
    def log_request_start(self, request_id: str, operation: str, args: Dict[str, Any] = None):
        """Log request start"""
        context = {
            "operation": operation,
            "args_keys": list(args.keys()) if args else [],
            "status": "started"
        }
        self._log(logging.INFO, f"[{request_id}] {operation} started", request_id, context)
    
    def log_request_event(self, request_id: str, event: str, duration_ms: float = 0, details: Dict[str, Any] = None):
        """Log intermediate request event"""
        context = {
            "event": event,
            "duration_ms": duration_ms,
        }
        if details:
            context.update(details)
        
        self._log(logging.DEBUG, f"[{request_id}] {event}", request_id, context)
    
    def log_request_end(self, request_id: str, status: str, duration_ms: float = 0, error: str = None):
        """Log request completion"""
        context = {
            "status": status,
            "duration_ms": duration_ms,
        }
        if error:
            context["error"] = error
        
        level = logging.ERROR if status == "error" else logging.INFO
        self._log(level, f"[{request_id}] {status} after {duration_ms}ms", request_id, context)
    
    def log_error(self, request_id: str, error_msg: str, exception: Exception = None, context: Dict[str, Any] = None):
        """Log error with context"""
        ctx = context or {}
        ctx["error_type"] = type(exception).__name__ if exception else "Unknown"
        
        self._log(logging.ERROR, f"[{request_id}] {error_msg}", request_id, ctx, exc_info=exception)
    
    def _log(self, level: int, message: str, request_id: str = None, context: Dict[str, Any] = None, exc_info: Exception = None):
        """Internal log method"""
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        
        record.request_id = request_id
        record.context = context or {}
        
        self.logger.handle(record)


class MetricsLogger:
    """
    Log performance metrics in structured format.
    
    Usage:
        metrics = MetricsLogger()
        metrics.log_tool_latency("hcr_get_state", 234.5)
        metrics.log_circuit_breaker_state("engine", "closed")
        metrics.log_cache_hit("shared_keys", 0.85)  # 85% hit rate
    """
    
    def __init__(self):
        self.logger = logging.getLogger("HCR.metrics")
    
    def log_tool_latency(self, tool_name: str, latency_ms: float, status: str = "success"):
        """Log tool execution latency"""
        self.logger.info(
            f"Tool latency: {tool_name}",
            extra={
                "context": {
                    "metric_type": "tool_latency",
                    "tool": tool_name,
                    "latency_ms": latency_ms,
                    "status": status,
                    "timestamp": time.time()
                }
            }
        )
    
    def log_circuit_breaker_state(self, component: str, state: str, failures: int = 0):
        """Log circuit breaker state change"""
        self.logger.info(
            f"Circuit breaker: {component}={state}",
            extra={
                "context": {
                    "metric_type": "circuit_breaker",
                    "component": component,
                    "state": state,
                    "failures": failures,
                    "timestamp": time.time()
                }
            }
        )
    
    def log_cache_hit(self, cache_name: str, hit_rate: float):
        """Log cache hit rate"""
        self.logger.debug(
            f"Cache hit rate: {cache_name}",
            extra={
                "context": {
                    "metric_type": "cache_hit",
                    "cache": cache_name,
                    "hit_rate": hit_rate,
                    "timestamp": time.time()
                }
            }
        )
    
    def log_concurrency(self, active_requests: int, max_workers: int):
        """Log concurrent request metrics"""
        self.logger.debug(
            f"Concurrency: {active_requests}/{max_workers}",
            extra={
                "context": {
                    "metric_type": "concurrency",
                    "active_requests": active_requests,
                    "max_workers": max_workers,
                    "utilization": active_requests / max_workers if max_workers > 0 else 0,
                    "timestamp": time.time()
                }
            }
        )


def setup_logging(config: MCPConfig = None):
    """
    Configure logging for HCR MCP Server.
    
    Args:
        config: MCPConfig instance (uses defaults if not provided)
    """
    config = config or MCPConfig()
    
    # Validate config
    is_valid, error_msg = config.validate()
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_msg}")
    
    # Root logger
    root_logger = logging.getLogger("HCR")
    root_logger.setLevel(getattr(logging, config.MCP_LOG_LEVEL))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    
    if config.MCP_STRUCTURED_LOGGING_ENABLED:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(config.MCP_LOG_FORMAT)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Return loggers for use
    return {
        "root": root_logger,
        "request_logger": RequestLogger("MCP"),
        "metrics_logger": MetricsLogger(),
    }
