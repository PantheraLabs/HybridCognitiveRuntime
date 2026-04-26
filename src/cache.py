"""
LLM Response Cache

Hash-based cache to avoid redundant LLM calls when cognitive state hasn't changed.
Cache is in-memory only — cheap to regenerate, no disk I/O.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """A single cached LLM response"""
    response: Dict[str, Any]
    state_hash: str
    timestamp: float
    ttl_seconds: int

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl_seconds


class LLMCache:
    """
    Simple hash-based cache for LLM responses.

    Strategy:
    - Hash the cognitive state (facts + dependencies + effects)
    - If hash matches a cached entry and TTL hasn't expired, return cached
    - Otherwise, signal a cache miss
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, state_dict: Dict[str, Any], cache_key: str = "default") -> Optional[Dict[str, Any]]:
        """
        Try to get a cached response for the given state.

        Args:
            state_dict: The cognitive state as a dict (used for hashing)
            cache_key: Additional key to distinguish different query types

        Returns:
            Cached response dict, or None on miss
        """
        state_hash = self._hash_state(state_dict)
        full_key = f"{cache_key}:{state_hash}"

        entry = self._cache.get(full_key)
        if entry and not entry.is_expired:
            self._hits += 1
            return entry.response

        self._misses += 1
        return None

    def put(self, state_dict: Dict[str, Any], response: Dict[str, Any], cache_key: str = "default"):
        """
        Cache an LLM response for a given state.

        Args:
            state_dict: The cognitive state as a dict
            response: The LLM response to cache
            cache_key: Additional key to distinguish different query types
        """
        state_hash = self._hash_state(state_dict)
        full_key = f"{cache_key}:{state_hash}"

        self._cache[full_key] = CacheEntry(
            response=response,
            state_hash=state_hash,
            timestamp=time.time(),
            ttl_seconds=self.ttl_seconds
        )

        # Prune expired entries if cache is getting large
        if len(self._cache) > 100:
            self._prune()

    def invalidate(self):
        """Clear all cached entries"""
        self._cache.clear()

    def _hash_state(self, state_dict: Dict[str, Any]) -> str:
        """Generate a deterministic hash from state dict"""
        # Sort keys for deterministic hashing
        serialized = json.dumps(state_dict, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _prune(self):
        """Remove expired entries"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        for key in expired_keys:
            del self._cache[key]

    @property
    def stats(self) -> Dict[str, Any]:
        """Cache performance stats"""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "entries": len(self._cache),
        }
