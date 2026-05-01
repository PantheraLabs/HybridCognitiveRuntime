"""
Configuration Management for HCR MCP Server

Consolidates all environment-based configuration instead of hardcoded values.
Replaces Phase 1-2 magic numbers with configurable settings.

Phase 3 Enhancement: Environment variable configuration
"""

import os
from typing import Optional


class MCPConfig:
    """MCP Server configuration from environment variables"""
    
    # Thread pool configuration
    MCP_THREAD_POOL_SIZE: int = int(os.getenv("MCP_THREAD_POOL_SIZE", "16"))
    MCP_THREAD_POOL_PREFIX: str = os.getenv("MCP_THREAD_POOL_PREFIX", "hcr-mcp")
    
    # Timeout configuration
    MCP_DEFAULT_TIMEOUT: float = float(os.getenv("MCP_DEFAULT_TIMEOUT", "5.0"))
    MCP_CONTEXT_INFERENCE_TIMEOUT: float = float(os.getenv("MCP_CONTEXT_INFERENCE_TIMEOUT", "3.0"))
    MCP_IO_TIMEOUT: float = float(os.getenv("MCP_IO_TIMEOUT", "5.0"))
    MCP_LLM_TIMEOUT: float = float(os.getenv("MCP_LLM_TIMEOUT", "3.0"))
    MCP_GIT_TIMEOUT: float = float(os.getenv("MCP_GIT_TIMEOUT", "5.0"))
    MCP_FILE_TIMEOUT: float = float(os.getenv("MCP_FILE_TIMEOUT", "5.0"))
    
    # Cache configuration
    MCP_CACHE_TTL: float = float(os.getenv("MCP_CACHE_TTL", "60.0"))
    MCP_MAX_CACHE_ENTRIES: int = int(os.getenv("MCP_MAX_CACHE_ENTRIES", "100"))
    
    # Rate limiting configuration
    MCP_RATE_LIMIT_CALLS_PER_MINUTE: int = int(os.getenv("MCP_RATE_LIMIT_CALLS_PER_MINUTE", "30"))
    MCP_RATE_LIMIT_ENABLED: bool = os.getenv("MCP_RATE_LIMIT_ENABLED", "true").lower() == "true"
    
    # Circuit breaker configuration
    MCP_CIRCUIT_BREAKER_ENABLED: bool = os.getenv("MCP_CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    MCP_CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("MCP_CIRCUIT_BREAKER_THRESHOLD", "5"))
    MCP_CIRCUIT_BREAKER_RESET_TIME: float = float(os.getenv("MCP_CIRCUIT_BREAKER_RESET_TIME", "30.0"))
    
    # Request tracing configuration
    MCP_REQUEST_TRACING_ENABLED: bool = os.getenv("MCP_REQUEST_TRACING_ENABLED", "true").lower() == "true"
    MCP_MAX_ACTIVE_REQUESTS_HISTORY: int = int(os.getenv("MCP_MAX_ACTIVE_REQUESTS_HISTORY", "100"))
    
    # Logging configuration
    MCP_LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")
    MCP_LOG_FORMAT: str = os.getenv("MCP_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    MCP_STRUCTURED_LOGGING_ENABLED: bool = os.getenv("MCP_STRUCTURED_LOGGING_ENABLED", "false").lower() == "true"
    
    # State management configuration
    MCP_STATE_CACHE_ENABLED: bool = os.getenv("MCP_STATE_CACHE_ENABLED", "true").lower() == "true"
    MCP_STATE_PRELOAD_ENABLED: bool = os.getenv("MCP_STATE_PRELOAD_ENABLED", "true").lower() == "true"
    
    # Context capture configuration
    MCP_CAPTURE_GIT_STATE: bool = os.getenv("MCP_CAPTURE_GIT_STATE", "true").lower() == "true"
    MCP_CAPTURE_FILE_STATE: bool = os.getenv("MCP_CAPTURE_FILE_STATE", "true").lower() == "true"
    MCP_CAPTURE_CONTEXT_INFERENCE: bool = os.getenv("MCP_CAPTURE_CONTEXT_INFERENCE", "true").lower() == "true"
    MCP_CAPTURE_INCLUDE_DIFFS: bool = os.getenv("MCP_CAPTURE_INCLUDE_DIFFS", "false").lower() == "true"
    MCP_MAX_DIFF_FILES: int = int(os.getenv("MCP_MAX_DIFF_FILES", "5"))
    
    # LLM provider configuration
    MCP_LLM_PROVIDER: str = os.getenv("MCP_LLM_PROVIDER", "groq")
    MCP_LLM_MODEL: str = os.getenv("MCP_LLM_MODEL", "llama-3.1-8b-instant")
    MCP_LLM_CONNECTION_POOL_SIZE: int = int(os.getenv("MCP_LLM_CONNECTION_POOL_SIZE", "5"))
    
    # Observability configuration
    MCP_PROMETHEUS_ENABLED: bool = os.getenv("MCP_PROMETHEUS_ENABLED", "false").lower() == "true"
    MCP_PROMETHEUS_PORT: int = int(os.getenv("MCP_PROMETHEUS_PORT", "8000"))
    MCP_TRACING_ENABLED: bool = os.getenv("MCP_TRACING_ENABLED", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """
        Validate configuration values for consistency.
        
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        errors = []
        
        if cls.MCP_THREAD_POOL_SIZE < 1:
            errors.append(f"MCP_THREAD_POOL_SIZE must be >= 1, got {cls.MCP_THREAD_POOL_SIZE}")
        
        if cls.MCP_DEFAULT_TIMEOUT <= 0:
            errors.append(f"MCP_DEFAULT_TIMEOUT must be > 0, got {cls.MCP_DEFAULT_TIMEOUT}")
        
        if cls.MCP_CACHE_TTL <= 0:
            errors.append(f"MCP_CACHE_TTL must be > 0, got {cls.MCP_CACHE_TTL}")
        
        if cls.MCP_RATE_LIMIT_CALLS_PER_MINUTE < 1:
            errors.append(f"MCP_RATE_LIMIT_CALLS_PER_MINUTE must be >= 1")
        
        if cls.MCP_CIRCUIT_BREAKER_THRESHOLD < 1:
            errors.append(f"MCP_CIRCUIT_BREAKER_THRESHOLD must be >= 1")
        
        if errors:
            return False, "\n".join(errors)
        
        return True, None
    
    @classmethod
    def summary(cls) -> str:
        """Return human-readable configuration summary"""
        return f"""
HCR MCP Server Configuration
============================

Thread Pool:
  - Size: {cls.MCP_THREAD_POOL_SIZE} workers
  - Prefix: {cls.MCP_THREAD_POOL_PREFIX}

Timeouts:
  - Default: {cls.MCP_DEFAULT_TIMEOUT}s
  - Context Inference: {cls.MCP_CONTEXT_INFERENCE_TIMEOUT}s
  - I/O Operations: {cls.MCP_IO_TIMEOUT}s
  - LLM Calls: {cls.MCP_LLM_TIMEOUT}s

Caching:
  - TTL: {cls.MCP_CACHE_TTL}s
  - Max Entries: {cls.MCP_MAX_CACHE_ENTRIES}

Rate Limiting:
  - Enabled: {cls.MCP_RATE_LIMIT_ENABLED}
  - Limit: {cls.MCP_RATE_LIMIT_CALLS_PER_MINUTE} calls/minute

Circuit Breaker:
  - Enabled: {cls.MCP_CIRCUIT_BREAKER_ENABLED}
  - Threshold: {cls.MCP_CIRCUIT_BREAKER_THRESHOLD} failures
  - Reset Time: {cls.MCP_CIRCUIT_BREAKER_RESET_TIME}s

Request Tracing:
  - Enabled: {cls.MCP_REQUEST_TRACING_ENABLED}
  - Max History: {cls.MCP_MAX_ACTIVE_REQUESTS_HISTORY} requests

Logging:
  - Level: {cls.MCP_LOG_LEVEL}
  - Structured: {cls.MCP_STRUCTURED_LOGGING_ENABLED}

LLM:
  - Provider: {cls.MCP_LLM_PROVIDER}
  - Model: {cls.MCP_LLM_MODEL}
  - Connection Pool Size: {cls.MCP_LLM_CONNECTION_POOL_SIZE}

Observability:
  - Prometheus Metrics: {cls.MCP_PROMETHEUS_ENABLED} (port {cls.MCP_PROMETHEUS_PORT})
  - Distributed Tracing: {cls.MCP_TRACING_ENABLED}

Phase 3d Features:
  - LLM Connection Pooling: {cls.MCP_LLM_CONNECTION_POOL_SIZE} concurrent connections
  - Prometheus Metrics: {cls.MCP_PROMETHEUS_ENABLED}
"""
