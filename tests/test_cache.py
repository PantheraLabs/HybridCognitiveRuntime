import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cache import LLMCache
import src.cache as cache_module


def test_llm_cache_hit_miss_and_stats(monkeypatch):
    cache = LLMCache(ttl_seconds=10)
    state = {"facts": ["alpha"]}
    response = {"summary": "ok"}

    monkeypatch.setattr(cache_module.time, "time", lambda: 1000)

    assert cache.get(state) is None
    cache.put(state, response)
    assert cache.get(state) == response

    stats = cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["entries"] == 1


def test_llm_cache_expiration_and_invalidate(monkeypatch):
    cache = LLMCache(ttl_seconds=5)
    state = {"facts": ["beta"]}
    response = {"summary": "cached"}
    clock = {"now": 1000}

    def fake_time():
        return clock["now"]

    monkeypatch.setattr(cache_module.time, "time", fake_time)

    cache.put(state, response)
    assert cache.get(state) == response

    clock["now"] = 1010
    assert cache.get(state) is None

    cache.put(state, response)
    cache.invalidate()
    assert cache.get(state) is None


def test_llm_cache_prune_called_when_large(monkeypatch):
    cache = LLMCache(ttl_seconds=10)
    called = {"value": False}

    def fake_prune():
        called["value"] = True

    monkeypatch.setattr(cache, "_prune", fake_prune)

    for i in range(101):
        cache.put({"facts": [str(i)]}, {"result": i}, cache_key=f"k{i}")

    assert called["value"] is True
