# Phase 3b Implementation Roadmap

**Status:** Architecture Ready - Tool Implementation Roadmap  
**Date:** April 29, 2026  

---

## Current State

✅ **Phase 3a Delivered:**
- BaseMCPTool base class (working)
- StateTools fully implemented (3 tools)
- TaskTools partially implemented (2 tools)
- Configuration system (39 env vars)
- Structured logging infrastructure
- All 11 tool stubs scaffolded

**Immediately Available:** 5 tools working with modular pattern

---

## Remaining Tools to Implement (11 Tools)

### Priority 1: High Impact (3-4 hours)

#### 1. SharedStateTools (3 tools)
**Source:** `mcp_server.py` lines 1266-1330

Tools:
- `hcr_list_shared_states` - List all shared project states
- `hcr_get_shared_state` - Get specific shared state
- `hcr_share_state` - Save state for cross-project access

**Implementation Steps:**
```python
# In product/integrations/tools/shared_state_tools.py
class ListSharedStatesTool(BaseMCPTool):
    async def execute(self, args):
        # Copy logic from _tool_list_shared_states
        # Use self._get_persistence() for state manager
        
class GetSharedStateTool(BaseMCPTool):
    async def execute(self, args):
        # Copy logic from _tool_get_shared_state
        
class ShareStateTool(BaseMCPTool):
    async def execute(self, args):
        # Copy logic from _tool_share_state
```

**Estimated Time:** 1 hour

---

#### 2. VersionTools (2 tools)
**Source:** `mcp_server.py` lines 1331-1425

Tools:
- `hcr_get_version_history` - Get version history with caching
- `hcr_restore_version` - Restore from a specific version

**Implementation Pattern:**
```python
class GetVersionHistoryTool(BaseMCPTool):
    async def execute(self, args):
        # Check circuit breaker for version service
        allowed, _ = self._check_circuit_breaker('version')
        if not allowed:
            return self._error_response("Version service unavailable")
        
        # Load version history
        try:
            versions = await self._run_blocking(
                lambda: self._get_persistence().get_version_history(),
                timeout=5.0
            )
            self._record_success('version')
        except Exception as e:
            self._record_failure('version')
            return self._error_response(str(e))
        
        return {"versions": versions, "count": len(versions)}

class RestoreVersionTool(BaseMCPTool):
    async def execute(self, args):
        version_hash = args.get("version_hash")
        # Validate and restore
```

**Estimated Time:** 1 hour

---

#### 3. HealthTools (1 tool)
**Source:** `mcp_server.py` lines 1464-1515

Tool:
- `hcr_get_system_health` - Health status of all components

**Pattern:**
```python
class GetSystemHealthTool(BaseMCPTool):
    async def execute(self, args):
        # Parallel health checks via asyncio.gather()
        health = await asyncio.gather(
            self._check_engine_health(),
            self._check_git_health(),
            self._check_cache_health(),
            return_exceptions=True
        )
        
        return {
            "status": "healthy",
            "components": health,
            "timestamp": time.time()
        }
    
    async def _check_engine_health(self):
        # Check if engine initializes
        engine = self._get_engine()
        return {"engine": "ok" if engine else "failed"}
```

**Estimated Time:** 1 hour

---

#### 4. SessionTools (4 tools)
**Source:** `mcp_server.py` lines 1515-1670

Tools:
- `hcr_list_sessions` - List all sessions
- `hcr_create_session` - Create new session
- `hcr_set_session_note` - Add note to session
- `hcr_merge_session` - Merge sessions

**Implementation:**
```python
class ListSessionsTool(BaseMCPTool):
    async def execute(self, args):
        # Access self.responder._session_states dict
        sessions = list(self.responder._session_states.keys()) if self.responder else []
        return {"sessions": sessions, "count": len(sessions)}

class CreateSessionTool(BaseMCPTool):
    async def execute(self, args):
        session_id = args.get("session_id")
        tag = args.get("tag", "Untitled")
        
        if self.responder:
            self.responder._session_states[session_id] = {"tag": tag, "created": time.time()}
        
        return {"session_id": session_id, "tag": tag, "success": True}

# ... similar for SetSessionNote and MergeSession
```

**Estimated Time:** 1.5 hours

---

### Priority 2: Medium Impact (2-3 hours)

#### 5. OperatorTools (1 tool)
**Source:** `mcp_server.py` lines 1427-1463

Tool:
- `hcr_get_learned_operators` - List learned operators

**Estimated Time:** 30 min

---

#### 6. FileTools (1 tool)
**Source:** `mcp_server.py` lines 1673-1795

Tool:
- `hcr_record_file_edit` - Record file edit in state

**Estimated Time:** 45 min

---

#### 7. ContextTools (1 tool)
**Source:** `mcp_server.py` lines 1796-1933

Tool:
- `hcr_capture_full_context` - Full context with parallelized I/O (Phase 2)

**Note:** Already has parallel I/O - just extract to class

**Estimated Time:** 45 min

---

### Priority 3: Advanced Features (2-3 hours)

#### 8. ImpactTools (1 tool)
**Source:** `mcp_server.py` lines 1935-1992

Tool:
- `hcr_analyze_impact` - Analyze code change impact

**Estimated Time:** 1 hour

---

#### 9. RecommendationTools (1 tool)
**Source:** `mcp_server.py` lines 1994-2092

Tool:
- `hcr_get_recommendations` - AI recommendations for next steps

**Estimated Time:** 1 hour

---

#### 10. SearchTools (1 tool)
**Source:** `mcp_server.py` lines 2094-2150

Tool:
- `hcr_search_history` - Search through event history

**Estimated Time:** 1 hour

---

## Implementation Timeline

### Batch 1 (First 2-3 hours)
1. ✅ StateTools (3 tools) - DONE
2. ✅ TaskTools (2 tools) - DONE
3. 🔲 SharedStateTools (3 tools)
4. 🔲 VersionTools (2 tools)
5. 🔲 HealthTools (1 tool)

**Result:** 11/21 tools working

### Batch 2 (Next 1.5-2 hours)
6. 🔲 SessionTools (4 tools)
7. 🔲 OperatorTools (1 tool)
8. 🔲 FileTools (1 tool)

**Result:** 19/21 tools working

### Batch 3 (Final 2-3 hours)
9. 🔲 ContextTools (1 tool)
10. 🔲 ImpactTools (1 tool)
11. 🔲 RecommendationTools (1 tool)
12. 🔲 SearchTools (1 tool)

**Result:** 21/21 tools working ✅

### Batch 4 (Integration & Testing - 2 hours)
- Update HCRMCPResponder to use modular tools
- Refactor _handle_tools_call() to dispatch to tools
- Run full test suite
- Performance benchmarks

---

## Code Extraction Process

For each tool, follow this pattern:

### Step 1: Find Source
```bash
grep -n "async def _tool_TOOLNAME" product/integrations/mcp_server.py
```

### Step 2: Copy Implementation
```python
# Copy lines from mcp_server.py
# Replace `self.` with tool-aware calls:
# - self.engine → self._get_engine()
# - self.persistence → self._get_persistence()
# - self.logger → self.logger (already available)
# - self._run_blocking → self._run_blocking (inherited)
# - self._record_session_snapshot → via responder if needed
```

### Step 3: Create Tool Class
```python
class MyTool(BaseMCPTool):
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation from mcp_server.py
        pass
```

### Step 4: Test
```bash
python -c "from product.integrations.tools.mytool import MyTool; print('OK')"
```

---

## Example Extraction: SharedStateTools

### Source from mcp_server.py
```python
async def _tool_list_shared_states(self, args: Dict[str, Any]) -> Dict[str, Any]:
    if not self.cross_project:
        return {"shared_states": [], "count": 0, "cached": False}
    
    try:
        # Check cache
        if self._cache_valid(self._shared_keys_cache_ts):
            keys = self._shared_keys_cache
            cached = True
        else:
            keys = await self._run_blocking(
                self.cross_project.list_shared_keys,
                timeout=5.0
            )
            self._shared_keys_cache = keys
            self._shared_keys_cache_ts = time.time()
            cached = False
        
        return {"shared_states": keys, "count": len(keys), "cached": cached}
    except Exception as e:
        return {"error": str(e), "shared_states": [], "count": 0}
```

### Extracted Tool Class
```python
class ListSharedStatesTool(BaseMCPTool):
    """List all shared states across projects"""
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cross_project = self.responder.cross_project if self.responder else None
        
        if not cross_project:
            return {"shared_states": [], "count": 0, "cached": False}
        
        try:
            # Check circuit breaker
            allowed, reason = self._check_circuit_breaker('shared_state')
            if not allowed:
                return self._error_response(reason)
            
            # Load shared keys
            keys = await self._run_blocking(
                cross_project.list_shared_keys,
                timeout=5.0
            )
            self._record_success('shared_state')
            
            return {"shared_states": keys, "count": len(keys), "cached": False}
        except Exception as e:
            self._record_failure('shared_state')
            self.logger.error(f"Failed to list shared states: {e}")
            return self._error_response(str(e))
```

---

## Quick Checklist for Each Tool

- [ ] Create class inheriting from BaseMCPTool
- [ ] Implement async execute(self, args) method
- [ ] Use self._validate_args() for input validation
- [ ] Use self._get_engine()/self._get_persistence() for access
- [ ] Use self._run_blocking() for blocking operations
- [ ] Use self._check_circuit_breaker() for resilience
- [ ] Use self._record_success()/failure() to track health
- [ ] Use self._error_response() for errors
- [ ] Use self._success_response() for success
- [ ] Add docstring with Args and Returns
- [ ] Test imports work: `python -m py_compile tools/mytool.py`

---

## Testing After Implementation

### Unit Test Template
```python
import pytest
from product.integrations.tools.state_tools import GetStateTool

@pytest.mark.asyncio
async def test_get_state_tool():
    tool = GetStateTool()
    result = await tool.execute({})
    assert "content" in result
    assert "exists" in result
```

### Integration Test
```bash
cd product/integrations
python -c "
from tools.state_tools import GetStateTool
from tools.task_tools import GetCurrentTaskTool
from tools.shared_state_tools import ListSharedStatesTool
print('✅ All tools import successfully')
"
```

### Smoke Test
```bash
python test_mcp_tools.py  # Should still pass with modular tools
```

---

## Performance Expectations

After completing Phase 3b:

| Metric | Before (Phase 2) | After (Phase 3b) | Change |
|--------|---|---|---|
| Tool latency | ~5s | ~5s | No change |
| Code maintainability | Low | High | ✅ Improved |
| Test coverage | Difficult | Easy | ✅ Improved |
| Extensibility | Hard | Easy | ✅ Improved |
| Lines per tool | 100-200 | 50-100 | ✅ Reduced |

---

## Deliverables for Phase 3b

1. ✅ All 21 tools implemented as modular classes
2. ✅ HCRMCPResponder updated to use tools
3. ✅ All 17 tests passing
4. ✅ Performance metrics same or better
5. ✅ Code reduced from 2000+ LOC to ~1500 LOC in mcp_server.py
6. ✅ Comprehensive documentation

---

## Commands for Phase 3b Completion

```bash
# 1. Verify architecture
cd c:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime
python -m py_compile product/integrations/tools/*.py

# 2. Test specific tool
python -c "from product.integrations.tools.state_tools import GetStateTool; print('OK')"

# 3. Run all tool tests
python test_mcp_tools.py

# 4. Check code reduction
wc -l product/integrations/mcp_server.py
ls -la product/integrations/tools/*.py | awk '{print $5}' | awk '{s+=$1} END {print "Total lines:", s}'
```

---

## Success Criteria

✅ Phase 3b is complete when:
1. All 21 tools working as modular classes
2. All 17 MCP tools pass tests
3. Configuration system working (env vars)
4. Logging system operational (JSON format)
5. Code organized into 13 focused tool modules
6. No performance regression
7. Comprehensive documentation
8. Zero breaking changes to tool APIs

---

## Summary

**Phase 3a Status:** ✅ COMPLETE
- Architecture established
- Infrastructure built
- 5/21 tools working (StateTools, TaskTools)
- Ready for Phase 3b

**Phase 3b Goal:** Implement remaining 16 tools
**Estimated Time:** 6-8 hours
**Complexity:** Low-Medium (mostly copy/paste with refactoring)

**By end of Phase 3b:** 21/21 tools working, fully modular, production-ready
