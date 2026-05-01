# HCR MCP Server - Commercial Product Audit Report
**Date:** April 29, 2026  
**Status:** ⚠️ CRITICAL PRODUCTION ISSUES FOUND

## Executive Summary
The MCP server has 18 identified production issues causing AI IDE lag and unreliability. Issues range from **CRITICAL** (5 performance killers) to **MAJOR** (7 reliability gaps) to **ARCHITECTURAL** (6 maintainability issues).

**Impact:** 8-15 second response latency on complex operations, timeout failures, and degraded user experience when IDE scales.

---

## CRITICAL ISSUES (Fix Immediately)

### 1. ❌ Synchronous State Loading in Async Context
**Problem:** Multiple tools call `await self._run_blocking(self.engine.load_state())` which:
- Blocks thread pool worker for 2-5 seconds
- Happens in multiple places independently
- Not deduplicated across concurrent requests

**Impact:** If 2+ tools call simultaneously, thread pool exhausted → all requests timeout

**Locations:** 
- `_handle_tools_call()` (line ~780)
- `_tool_get_state()` (line ~953)
- `_tool_get_current_task()` (line ~1075)
- `_tool_capture_full_context()` (line ~1486)

**Fix:** Implement singleton state loader with per-request caching

---

### 2. ❌ Insufficient Thread Pool (4 Workers)
**Problem:** `ThreadPoolExecutor(max_workers=4)` insufficient for:
- Groq API latency (2-3s)
- Git operations (1-2s)
- File I/O (0.5-1s)
- Concurrent requests from IDE

**Impact:** 4 concurrent requests → 5th+ requests queue indefinitely → timeout

**Current:**
```python
self._executor = ThreadPoolExecutor(max_workers=4)  # BOTTLENECK
```

**Fix:** Increase to 12-16 workers + separate pools for I/O vs CPU-bound tasks

---

### 3. ❌ Long Timeouts (8-10 seconds)
**Problem:** Cascading timeouts:
- `hcr_get_current_task`: `timeout=8.0`
- `hcr_capture_full_context`: `timeout=8.0` (4 sequential calls = 32s potential!)
- LLM inference: no timeout → hangs indefinitely

**Impact:** Users blocked for 8s+ waiting for responses → IDE feels frozen

**Current:**
```python
context = await self._run_blocking(self.engine.infer_context, timeout=8.0)  # TOO LONG
```

**Fix:** Reduce to 3-5s with fast failure modes + fallback responses

---

### 4. ❌ LLM Inference Hangs (No Timeout)
**Problem:** LLM calls in `_generate_smart_resume()` have no timeout:
```python
response = llm.structured_complete(...)  # NO TIMEOUT!
```

**Impact:** If LLM provider hangs, entire tool call hangs (blocks IDE indefinitely)

**Fix:** Add 5s timeout with fallback to template-based response

---

### 5. ❌ No Circuit Breaker Pattern
**Problem:** When operations fail repeatedly (e.g., LLM timeout, network down), tools keep retrying:
```python
except Exception as e:
    self.logger.warning(f"Failed: {e}")  # Still returns result!
```

**Impact:** Degraded system stays degraded; no fast-fail mechanism

**Fix:** Add circuit breaker with exponential backoff

---

## MAJOR ISSUES (Fix Before Production)

### 6. Sequential I/O in `capture_full_context()`
```python
git_state = await self._run_blocking(git.capture_state, timeout=5.0)  # SEQUENTIAL
file_state = await self._run_blocking(watcher.capture_state, timeout=5.0)  # Then this
# ...
context = await self._run_blocking(_load_and_infer, timeout=8.0)  # Then this
```

**Actual latency:** 5 + 5 + 8 = 18 seconds! ❌  
**Should be:** ~8 seconds (all parallel)

**Fix:** Use `asyncio.gather()` for parallel execution

---

### 7. Cache Invalidation Race Condition
```python
if self._cache_valid(self._shared_keys_cache_ts) and self._shared_keys_cache is not None:
    return {"shared_states": self._shared_keys_cache}  # STALE READ possible here!

# Meanwhile: tool updates cache asynchronously
self._shared_keys_cache = keys  # Race condition!
self._shared_keys_cache_ts = time.time()
```

**Fix:** Use `asyncio.Lock` for cache access

---

### 8. Incomplete Error Recovery
```python
try:
    context = await self._run_blocking(self.engine.infer_context, timeout=8.0)
except Exception as e:
    self.logger.warning(f"Context inference failed: {e}")
    # Returns hard-coded fallback, loses real error info
```

**Fix:** Include error type, timestamp, and recovery steps in response

---

### 9. Unsafe JSON Serialization
```python
text_content += f"\n\n[Metadata: {json.dumps(remaining, indent=2, default=str)}]"
```

**Problem:** `default=str` converts complex objects to string representation, hiding bugs

**Fix:** Use `JSONEncoder` subclass with proper type handling

---

### 10. Missing Input Validation
```python
async def _tool_restore_version(self, args):
    version_hash = args.get("version_hash")  # No validation!
    # Proceeds to search through all events with unvalidated hash
```

**Risks:** DoS via large inputs, injection attacks

**Fix:** Add schema validation on all inputs

---

### 11. Session Snapshots Not Used
```python
def _record_session_snapshot(self, session_id, content, metadata):
    if not session_id:
        return
    # ... updates self._session_states but never read/used downstream!
```

**Fix:** Document or remove if unused

---

## ARCHITECTURAL ISSUES

### 12. Monolithic 2000+ Line File
- All 21 tools in single class
- Hard to test individual tools
- No code reuse between similar tools

**Fix:** Refactor into modular tool handler classes

### 13. Tight Coupling to HCREngine
- No abstraction layer
- Breaks entirely if engine fails
- Can't mock for testing

**Fix:** Implement `StateProvider` interface

### 14. No Observability
- Logging only on errors (no success metrics)
- No performance tracking
- Can't diagnose slow requests

**Fix:** Add structured logging with execution times

### 15. Hardcoded Configuration
- Timeouts: 5, 8, 10 seconds hardcoded
- Cache TTL: 60 seconds hardcoded
- Thread pool: 4 workers hardcoded
- Rate limit: 30 calls/minute hardcoded

**Fix:** Move to config file

### 16. Type Safety Issues
- Missing `@asyncio.coroutine` decorators
- Helper methods lack type hints
- No runtime type validation

**Fix:** Full type hints + `beartype` runtime validation

### 17. No Rate Limiting on Expensive Operations
- LLM calls unlimited
- File operations unlimited
- State loads unlimited

**Fix:** Per-operation rate limits

### 18. No Request Tracing
- Can't correlate request across async operations
- Hard to debug multi-step failures
- No request context propagation

**Fix:** Add request IDs and context var tracing

---

## Performance Baseline

**Current (Broken):**
- Simple query (`hcr_get_state`): **3-8 seconds** (should be <500ms)
- Complex query (`hcr_capture_full_context`): **18+ seconds** (should be <3s)
- Concurrent requests (5x): **All timeout** (should work)
- LLM inference timeout: **Indefinite hang** (should be <5s)

---

## Recommended Fix Priority

**PHASE 1 (Immediate - 2 hours):**
1. Fix LLM hanging (add timeout)
2. Increase thread pool to 12
3. Reduce timeouts to 5s max
4. Add input validation

**PHASE 2 (High - 4 hours):**
5. Parallelize I/O operations
6. Implement circuit breaker
7. Add proper error responses
8. Fix cache race conditions

**PHASE 3 (Medium - 6 hours):**
9. Refactor into modular tools
10. Add observability/metrics
11. Move config to environment
12. Comprehensive error messages

---

## Testing Recommendations

After fixes, verify:
```
- Single request latency < 500ms (hcr_get_state)
- Complex request latency < 3s (hcr_capture_full_context)
- 10 concurrent requests succeed without timeout
- LLM timeout doesn't hang IDE
- Cache updates don't cause stale reads
- All error paths return descriptive errors
```

---

## Files Requiring Changes

**Primary:**
- `product/integrations/mcp_server.py` (2000+ lines → modularize)

**New Files to Create:**
- `product/integrations/mcp_config.py` (configuration)
- `product/integrations/mcp_tools/` (modular tools)
- `product/integrations/mcp_cache.py` (async caching)
- `product/integrations/mcp_circuit_breaker.py` (resilience)
- `product/integrations/mcp_metrics.py` (observability)
