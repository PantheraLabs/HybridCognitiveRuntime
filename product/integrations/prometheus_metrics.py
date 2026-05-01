"""
Prometheus Metrics - Production monitoring and observability.

Exposes metrics for:
- Tool execution latency (histogram)
- Tool success/error rates (counter)
- Circuit breaker state (gauge)
- Cache hit rates (gauge)
- Connection pool status (gauge)
- Request throughput (counter)
"""

import time
import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque


logger = logging.getLogger("HCR.Metrics")


class MetricCounter:
    """Simple counter metric"""
    
    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help_text = help_text
        self.value = 0
    
    def inc(self, amount: float = 1.0):
        """Increment counter"""
        self.value += amount
    
    def get_value(self) -> float:
        """Get current value"""
        return self.value


class MetricGauge:
    """Gauge metric (can increase or decrease)"""
    
    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help_text = help_text
        self.value = 0
    
    def set(self, value: float):
        """Set gauge value"""
        self.value = value
    
    def inc(self, amount: float = 1.0):
        """Increment gauge"""
        self.value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge"""
        self.value -= amount
    
    def get_value(self) -> float:
        """Get current value"""
        return self.value


class MetricHistogram:
    """Histogram metric (tracks distribution of values)"""
    
    def __init__(self, name: str, help_text: str, buckets: Optional[List[float]] = None):
        self.name = name
        self.help_text = help_text
        self.buckets = buckets or [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        self.bucket_counts = {b: 0 for b in self.buckets}
        self.sum = 0
        self.count = 0
    
    def observe(self, value: float):
        """Record observation"""
        self.sum += value
        self.count += 1
        
        # Find appropriate bucket
        for bucket in sorted(self.buckets):
            if value <= bucket:
                self.bucket_counts[bucket] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get histogram statistics"""
        return {
            "sum": self.sum,
            "count": self.count,
            "average": self.sum / (self.count or 1),
            "buckets": dict(self.bucket_counts)
        }


class PrometheusMetrics:
    """Central metrics collection for Prometheus"""
    
    def __init__(self, enable_collection: bool = True):
        """
        Initialize metrics.
        
        Args:
            enable_collection: Whether to collect metrics (can be disabled via config)
        """
        self.enabled = enable_collection
        self.start_time = time.time()
        
        # Tool metrics
        self.tool_latency = defaultdict(lambda: MetricHistogram("tool_latency_ms", ""))
        self.tool_calls = defaultdict(lambda: MetricCounter("tool_calls", ""))
        self.tool_errors = defaultdict(lambda: MetricCounter("tool_errors", ""))
        self.tool_timeouts = defaultdict(lambda: MetricCounter("tool_timeouts", ""))
        
        # Circuit breaker metrics
        self.circuit_breaker_state = defaultdict(lambda: MetricGauge("cb_state", ""))
        self.circuit_breaker_failures = defaultdict(lambda: MetricCounter("cb_failures", ""))
        
        # Cache metrics
        self.cache_hits = MetricCounter("cache_hits", "")
        self.cache_misses = MetricCounter("cache_misses", "")
        self.cache_size = MetricGauge("cache_size", "")
        
        # Request metrics
        self.active_requests = MetricGauge("active_requests", "")
        self.total_requests = MetricCounter("total_requests", "")
        
        # Connection pool metrics
        self.pool_size = MetricGauge("pool_size", "")
        self.pool_available = MetricGauge("pool_available", "")
        self.pool_errors = MetricCounter("pool_errors", "")
        
        # Request timing
        self.request_latencies = deque(maxlen=1000)  # Keep last 1000
        
        logger.info(f"Prometheus metrics initialized (enabled={enable_collection})")
    
    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool = True, timeout: bool = False):
        """Record tool execution"""
        if not self.enabled:
            return
        
        self.tool_calls[tool_name].inc()
        self.tool_latency[tool_name].observe(duration_ms)
        self.total_requests.inc()
        
        if not success:
            self.tool_errors[tool_name].inc()
        
        if timeout:
            self.tool_timeouts[tool_name].inc()
        
        # Track for aggregates
        self.request_latencies.append({
            "tool": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": time.time()
        })
    
    def record_circuit_breaker_state(self, component: str, state: str, failure_count: int = 0):
        """Record circuit breaker state change"""
        if not self.enabled:
            return
        
        # Map states to numeric values: closed=0, half_open=1, open=2
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        self.circuit_breaker_state[component].set(state_map.get(state, -1))
        self.circuit_breaker_failures[component].inc(failure_count)
    
    def record_cache_hit(self, is_hit: bool):
        """Record cache hit or miss"""
        if not self.enabled:
            return
        
        if is_hit:
            self.cache_hits.inc()
        else:
            self.cache_misses.inc()
    
    def set_cache_size(self, size: int):
        """Set current cache size"""
        if not self.enabled:
            return
        self.cache_size.set(size)
    
    def set_active_requests(self, count: int):
        """Set current active request count"""
        if not self.enabled:
            return
        self.active_requests.set(count)
    
    def set_pool_size(self, size: int, available: int):
        """Set connection pool status"""
        if not self.enabled:
            return
        self.pool_size.set(size)
        self.pool_available.set(available)
    
    def record_pool_error(self):
        """Record connection pool error"""
        if not self.enabled:
            return
        self.pool_errors.inc()
    
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        if not self.enabled:
            return {"metrics_enabled": False}
        
        # Calculate cache hit rate
        total_cache = self.cache_hits.get_value() + self.cache_misses.get_value()
        cache_hit_rate = (
            self.cache_hits.get_value() / total_cache if total_cache > 0 else 0
        )
        
        # Calculate tool statistics
        tool_stats = {}
        for tool_name in self.tool_calls.keys():
            calls = self.tool_calls[tool_name].get_value()
            errors = self.tool_errors[tool_name].get_value()
            timeouts = self.tool_timeouts[tool_name].get_value()
            latency_stats = self.tool_latency[tool_name].get_stats()
            
            tool_stats[tool_name] = {
                "calls": calls,
                "errors": errors,
                "timeouts": timeouts,
                "error_rate": errors / (calls or 1),
                "timeout_rate": timeouts / (calls or 1),
                "latency_ms": latency_stats
            }
        
        # Calculate uptime
        uptime_seconds = time.time() - self.start_time
        
        return {
            "metrics_enabled": True,
            "uptime_seconds": uptime_seconds,
            "active_requests": self.active_requests.get_value(),
            "total_requests": self.total_requests.get_value(),
            "cache": {
                "hits": self.cache_hits.get_value(),
                "misses": self.cache_misses.get_misses(),
                "hit_rate": cache_hit_rate,
                "size": self.cache_size.get_value()
            },
            "tools": tool_stats,
            "pool": {
                "size": self.pool_size.get_value(),
                "available": self.pool_available.get_value(),
                "errors": self.pool_errors.get_value()
            },
            "recent_requests": list(self.request_latencies)[-10:]  # Last 10
        }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format"""
        if not self.enabled:
            return "# Metrics disabled\n"
        
        lines = [
            "# HELP metrics Prometheus metrics for HCR MCP Server",
            "# TYPE metrics gauge",
            ""
        ]
        
        # Tool call counts
        for tool_name, counter in self.tool_calls.items():
            lines.append(f'tool_calls{{tool="{tool_name}"}} {counter.get_value()}')
        
        # Tool error counts
        for tool_name, counter in self.tool_errors.items():
            lines.append(f'tool_errors{{tool="{tool_name}"}} {counter.get_value()}')
        
        # Tool latencies
        for tool_name, histogram in self.tool_latency.items():
            stats = histogram.get_stats()
            lines.append(f'tool_latency_sum{{tool="{tool_name}"}} {stats["sum"]}')
            lines.append(f'tool_latency_count{{tool="{tool_name}"}} {stats["count"]}')
            lines.append(f'tool_latency_avg{{tool="{tool_name}"}} {stats["average"]}')
        
        # Cache metrics
        total_cache = self.cache_hits.get_value() + self.cache_misses.get_value()
        hit_rate = (
            self.cache_hits.get_value() / total_cache if total_cache > 0 else 0
        )
        lines.append(f'cache_hits {{}} {self.cache_hits.get_value()}')
        lines.append(f'cache_misses {{}} {self.cache_misses.get_value()}')
        lines.append(f'cache_hit_rate {{}} {hit_rate}')
        lines.append(f'cache_size {{}} {self.cache_size.get_value()}')
        
        # Request metrics
        lines.append(f'active_requests {{}} {self.active_requests.get_value()}')
        lines.append(f'total_requests {{}} {self.total_requests.get_value()}')
        
        # Pool metrics
        lines.append(f'pool_size {{}} {self.pool_size.get_value()}')
        lines.append(f'pool_available {{}} {self.pool_available.get_value()}')
        lines.append(f'pool_errors {{}} {self.pool_errors.get_value()}')
        
        # Uptime
        uptime = time.time() - self.start_time
        lines.append(f'uptime_seconds {{}} {uptime}')
        
        return "\n".join(lines) + "\n"


class MetricsServer:
    """Simple HTTP server for /metrics endpoint"""
    
    def __init__(self, metrics: PrometheusMetrics, port: int = 8000):
        """
        Initialize metrics server.
        
        Args:
            metrics: PrometheusMetrics instance
            port: Port for HTTP endpoint
        """
        self.metrics = metrics
        self.port = port
        self.is_running = False
    
    async def handle_metrics_request(self) -> str:
        """Handle GET /metrics request"""
        return self.metrics.export_prometheus_format()
    
    async def start(self):
        """Start metrics HTTP server"""
        try:
            from aiohttp import web
            
            app = web.Application()
            app.router.add_get('/metrics', self._handle_metrics)
            app.router.add_get('/metrics/json', self._handle_metrics_json)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '127.0.0.1', self.port)
            await site.start()
            
            self.is_running = True
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except ImportError:
            logger.warning("aiohttp not installed - metrics server unavailable")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    async def _handle_metrics(self, request) -> Any:
        """Handle /metrics endpoint"""
        from aiohttp import web
        return web.Response(text=await self.handle_metrics_request())
    
    async def _handle_metrics_json(self, request) -> Any:
        """Handle /metrics/json endpoint"""
        from aiohttp import web
        import json
        return web.Response(
            text=json.dumps(self.metrics.get_metrics_snapshot()),
            content_type='application/json'
        )


# Global metrics instance
_global_metrics: Optional[PrometheusMetrics] = None


def get_metrics(enable: bool = True) -> PrometheusMetrics:
    """Get or create global metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PrometheusMetrics(enable_collection=enable)
    return _global_metrics


def reset_metrics():
    """Reset global metrics (for testing)"""
    global _global_metrics
    _global_metrics = None
