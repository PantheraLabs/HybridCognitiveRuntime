"""
LLM Connection Pool - Efficient connection management for LLM providers.

Implements connection pooling pattern to:
- Reuse LLM client connections
- Limit concurrent connections
- Track connection state
- Auto-reconnect on failure
- Collect connection metrics
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from src.llm.llm_provider import LLMProvider


logger = logging.getLogger("HCR.LLM.Pool")


class PooledConnection:
    """Wrapper for LLM provider with connection metadata"""
    
    def __init__(self, provider: LLMProvider, connection_id: int):
        self.provider = provider
        self.connection_id = connection_id
        self.created_at = time.time()
        self.last_used_at = self.created_at
        self.request_count = 0
        self.error_count = 0
        self.is_healthy = True
    
    def mark_used(self):
        """Update last used timestamp"""
        self.last_used_at = time.time()
        self.request_count += 1
    
    def mark_error(self):
        """Mark connection as having an error"""
        self.error_count += 1
        if self.error_count > 5:  # Unhealthy after 5+ errors
            self.is_healthy = False
    
    def get_age_seconds(self) -> float:
        """Get connection age in seconds"""
        return time.time() - self.created_at
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics"""
        return {
            "connection_id": self.connection_id,
            "age_seconds": self.get_age_seconds(),
            "last_used_at": self.last_used_at,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "is_healthy": self.is_healthy
        }


class LLMConnectionPool:
    """Thread-safe pool for LLM provider connections"""
    
    def __init__(self, pool_size: int = 5, max_age_seconds: float = 3600.0):
        """
        Initialize connection pool.
        
        Args:
            pool_size: Maximum number of concurrent connections
            max_age_seconds: Maximum age before connection is recycled
        """
        self.pool_size = pool_size
        self.max_age_seconds = max_age_seconds
        self.connections: Dict[int, PooledConnection] = {}
        self.available_connections: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.connection_counter = 0
        self.lock = asyncio.Lock()
        self.metrics = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_recycled": 0,
            "total_requests": 0,
            "total_errors": 0,
            "peak_active": 0
        }
        logger.info(f"LLM Connection Pool initialized: size={pool_size}, max_age={max_age_seconds}s")
    
    async def get_connection(self) -> Optional[PooledConnection]:
        """
        Get a connection from the pool or create a new one.
        
        Returns:
            PooledConnection if successful, None if pool exhausted
        """
        try:
            # Try to get available connection
            conn = self.available_connections.get_nowait()
            
            # Check if connection is stale
            if conn.get_age_seconds() > self.max_age_seconds or not conn.is_healthy:
                logger.debug(f"Recycling stale connection {conn.connection_id}")
                self.metrics["connections_recycled"] += 1
                conn = await self._create_new_connection()
            else:
                self.metrics["connections_reused"] += 1
                logger.debug(f"Reusing connection {conn.connection_id}")
            
            conn.mark_used()
            self.metrics["total_requests"] += 1
            return conn
        except asyncio.QueueEmpty:
            # Pool is empty, create new if under limit
            if len(self.connections) < self.pool_size:
                conn = await self._create_new_connection()
                self.metrics["total_requests"] += 1
                return conn
            else:
                # Pool exhausted - wait for connection to become available
                logger.warning(f"Connection pool exhausted ({self.pool_size}), waiting...")
                try:
                    conn = await asyncio.wait_for(
                        self.available_connections.get(),
                        timeout=5.0
                    )
                    conn.mark_used()
                    self.metrics["total_requests"] += 1
                    return conn
                except asyncio.TimeoutError:
                    logger.error("Connection pool timeout - no connections available")
                    return None
    
    async def return_connection(self, conn: PooledConnection) -> None:
        """
        Return a connection to the pool.
        
        Args:
            conn: Connection to return
        """
        if conn.is_healthy:
            try:
                self.available_connections.put_nowait(conn)
                logger.debug(f"Returned connection {conn.connection_id} to pool")
            except asyncio.QueueFull:
                logger.warning(f"Pool queue full - discarding connection {conn.connection_id}")
        else:
            logger.info(f"Discarding unhealthy connection {conn.connection_id}")
            async with self.lock:
                if conn.connection_id in self.connections:
                    del self.connections[conn.connection_id]
    
    async def _create_new_connection(self) -> PooledConnection:
        """
        Create a new LLM provider connection.
        
        Returns:
            New PooledConnection
        """
        async with self.lock:
            self.connection_counter += 1
            conn_id = self.connection_counter
        
        try:
            provider = LLMProvider()
            conn = PooledConnection(provider, conn_id)
            self.connections[conn_id] = conn
            self.metrics["connections_created"] += 1
            logger.debug(f"Created new connection {conn_id}")
            return conn
        except Exception as e:
            logger.error(f"Failed to create LLM connection: {e}")
            raise
    
    def record_error(self, conn: PooledConnection) -> None:
        """Record an error for a connection"""
        conn.mark_error()
        self.metrics["total_errors"] += 1
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics"""
        return {
            **self.metrics,
            "active_connections": len(self.connections),
            "available_in_queue": self.available_connections.qsize(),
            "pool_size": self.pool_size,
            "connection_details": [
                conn.get_metrics() for conn in self.connections.values()
            ]
        }
    
    async def clear_pool(self) -> None:
        """Clear all connections from pool"""
        async with self.lock:
            self.connections.clear()
        
        # Empty the queue
        while not self.available_connections.empty():
            try:
                self.available_connections.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info("Connection pool cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check pool health status.
        
        Returns:
            Health status dictionary
        """
        healthy_conns = sum(1 for c in self.connections.values() if c.is_healthy)
        stale_conns = sum(
            1 for c in self.connections.values()
            if c.get_age_seconds() > self.max_age_seconds
        )
        
        return {
            "pool_healthy": healthy_conns == len(self.connections),
            "healthy_connections": healthy_conns,
            "total_connections": len(self.connections),
            "stale_connections": stale_conns,
            "queue_size": self.available_connections.qsize(),
            "reuse_rate": (
                self.metrics["connections_reused"] /
                (self.metrics["total_requests"] or 1)
            )
        }


class LLMConnectionPoolManager:
    """Singleton manager for LLM connection pool"""
    
    _instance = None
    _pool = None
    
    @classmethod
    def get_instance(cls, pool_size: int = 5) -> 'LLMConnectionPoolManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls(pool_size)
        return cls._instance
    
    def __init__(self, pool_size: int = 5):
        if self._pool is None:
            self._pool = LLMConnectionPool(pool_size=pool_size)
    
    async def get_connection(self) -> Optional[PooledConnection]:
        """Get connection from pool"""
        return await self._pool.get_connection()
    
    async def return_connection(self, conn: PooledConnection) -> None:
        """Return connection to pool"""
        await self._pool.return_connection(conn)
    
    def record_error(self, conn: PooledConnection) -> None:
        """Record error for connection"""
        self._pool.record_error(conn)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics"""
        return self._pool.get_pool_metrics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Get pool health"""
        return await self._pool.health_check()
    
    @classmethod
    def reset(cls):
        """Reset singleton (for testing)"""
        cls._instance = None
        cls._pool = None
