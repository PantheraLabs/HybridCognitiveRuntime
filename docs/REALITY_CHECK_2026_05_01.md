# HCR Reality Check - May 1, 2026

**Date:** May 1, 2026  
**Context:** Post-architecture-review alignment session  
**Status:** Hard pivot to V1 scope reduction

---

## Executive Summary

After a brutal but necessary critique, HCR is pivoting from "V3-level architecture" to "V1 MVP that actually works." The core problem: we've built infrastructure for a product that hasn't proven value yet.

**Grade:** Documentation A+, Implementation B-, Reality Check: Needed

---

## The 12 Hard Questions (Answered)

### 1. Memory Unit
**Answer:** Structured Cognitive State (not raw messages)

```python
MemoryUnit = {
    "facts": [
        {
            "id": "uuid",
            "content": "User is fixing auth middleware",
            "source": "explicit" | "git_commit" | "file_edit",
            "created": "2026-05-01",
            "pinned": false
        }
    ],
    "dependencies": {
        "src/auth/middleware.ts": ["src/routes/protected.ts"]
    },
    "current_task": {
        "description": "Fix auth bug",
        "files": ["src/auth/middleware.ts"],
        "started": "2026-05-01"
    }
}
```

**CUT FOR V1:** Remove "latent" (unclear computation), remove "causal inference" (too complex), simplify symbolic to just facts + constraints.

### 2. Extraction Strategy
**Answer:** Hybrid with explicit/implicit distinction

| Source | Method | Store? |
|--------|--------|--------|
| Explicit user statement | Direct | ✅ Yes |
| Git commit | Pattern match + LLM fallback | ✅ Yes |
| File save | Filtered (git diff OR open file) | ✅ Yes |
| Every prompt | ❌ | No |

**Fix when wrong:** Version + decay ranking. Manual override: `hcr forget`, `hcr pin`.

### 3. Write Triggers
**Answer:** Event-driven, filtered

| Event | Filter | Store? |
|-------|--------|--------|
| Git commit | Message contains issue/feat/fix | ✅ Yes |
| File save | File in git diff OR open in IDE | ✅ Yes |
| Terminal error | Error contains file path | ✅ Yes |
| Idle 5 min | Recent activity exists | ✅ Yes (heartbeat) |
| Random file save | Not in git, not open | ❌ No |

### 4. Garbage Prevention
**Answer:** Immutable versions + decay + manual control

- **Not overwritten:** New versions supersede old
- **Conflict resolution:** Causal graph shows contradictions
- **Noise control:** `relevance = f(recency, access_count, confidence)`
- **Manual:** `hcr forget <id>`, `hcr pin <fact>`, `hcr reset`

### 5. Retrieval
**Answer:** Multi-signal ranking (this part is actually sharp)

```
1. Current task (highest - explicit)
2. Files open in IDE (proximity)
3. Causal graph: file dependencies
4. Semantic: task description match
5. Recency: last 24h weighted higher

Hard limit: 200 tokens max
```

### 6. Where It Runs
**Answer:** Local daemon + MCP server

- **Primary:** Local daemon (file watching, state persistence)
- **IDE:** MCP server (stdio + HTTP)
- **CLI:** `hcr resume`, `hcr status`

**NOT:** Cloud-first. Local-first by design.

### 7. Latency Budget
**Answer:** <100ms for retrieval

| Component | Time |
|-----------|------|
| State load | 10ms (local JSON) |
| Causal graph query | 20ms |
| Ranking + injection | 50ms |
| **Total** | **<100ms** |

**BUT:** Unproven at scale. May need SQLite + partial loading.

### 8. "Holy Sh*t" Moment
**Answer:** Resume after 3 days with zero re-explanation

```
User: "continue"
AI: "You're fixing the auth middleware bug. 
     Last: Added JWT validation to routes/auth.ts.
     Next: Test the middleware with npm test.
     Run it?"
```

**3 days later. Different AI model. Zero re-explanation.**

This is the ONLY metric that matters.

### 9. Defensibility
**Answer:** Cross-model state layer, NOT feature play

| Big Players | HCR |
|-------------|-----|
| Closed ecosystem | Model-agnostic (GPT/Claude/Gemini) |
| Chat history-based | Structured state (causal graphs) |
| Per-product | Cross-tool layer |
| Token-heavy | 10-100x token reduction |

**Real moat:** Developer control + transparency + local-first

### 10. What We DON'T Do
**Answer:** Codebases only

| Not Doing | Why |
|-----------|-----|
| Personal life memory | Privacy nightmare |
| General chat memory | Focus on code context |
| Long-term knowledge base | That's RAG, different problem |
| All AI memory problems | **Only developer workflow continuity** |

### 11. Integration
**Answer:** 2-minute setup

```bash
pip install hcr-cli
hcr init --auto   # Detects IDE, sets up everything
```

**Friction:** Need demo/GIF/video BEFORE install.

### 12. Failure Modes
**Answer:** Subtly wrong context is the killer

| Failure | Mitigation |
|---------|------------|
| Wrong context | `hcr explain` shows what's injected |
| Stale state | Auto-detect git branch switch |
| Hallucination | Require causal validation |
| Subtly wrong | **Hard to detect - this is the risk** |

---

## Critical Feedback Applied

### ❌ What Was Cut

| Cut | Why |
|-----|-----|
| "Latent" state | Unclear computation, unclear value, sounds cool = distraction |
| "Causal inference" | Too complex for MVP. Keep simple dependency tracking only |
| Confidence scoring | Fake precision. Use explicit/implicit distinction instead |
| Advanced causal graphs | Just track imports/file relationships |

### ✅ What Survived

| Feature | Status |
|---------|--------|
| Structured facts | ✅ Core |
| Simple dependencies | ✅ Core |
| Current task tracking | ✅ Core |
| Git extraction | ✅ Core |
| File watching | ✅ Core |
| `hcr resume` | ✅ The hook |
| `hcr explain` | ✅ Trust builder |
| `hcr pin/forget` | ✅ Manual control |

---

## V1 Build Order (Non-Negotiable)

### Week 1: Git Fact Extractor
- Parse commit messages
- Extract 1-3 facts per commit
- Store in `.hcr/facts.json`

### Week 2: Simple Injection
- Load `current_task` + recent facts
- Inject into MCP context
- Hard limit: 200 tokens

### Week 3: `hcr explain` (Critical)
- Show what's injected
- Show why
- Build trust

### Week 4: `hcr resume` MVP
- Git log analysis
- File state detection
- One-line context summary

### Week 5: Manual Controls
- `hcr pin/forget/reset`

**End of Week 5 Deliverable:**
```bash
$ hcr resume

[HCR] Last: "feat: add JWT validation to auth middleware"
      Files: src/auth/middleware.ts (modified, unsaved)
      Next: Complete middleware tests?
      
      Run `hcr explain` to see what I know.
      Run `hcr forget` if this is wrong.
```

**If this doesn't create "holy sh*t" → everything else is wasted.**

---

## Current State vs Documentation Gap

| Document Claims | Reality |
|-----------------|---------|
| "19 tools verified" | 18 issues, 5 critical in audit |
| "Production Ready" | MCP tools hang, 8-15s latency |
| "Zero sync I/O" | User confirms "still not working perfectly" |
| "Terminal Logger ✅" | CODE_REVIEW: "incomplete" |
| "Cached + fast" | 3-8s for simple `hcr_get_state` |

**Conclusion:** Docs describe intended state, not actual state.

---

## Critical Issues (From CODE_REVIEW)

### P0: Must Fix

| Issue | File | Impact |
|-------|------|--------|
| CLI-daemon disconnect | `product/cli/main.py:245-342` | CLI can't control daemon |
| File watcher crashes | `product/daemon/file_watcher_service.py` | Daemon stability |
| State corruption risk | `src/engine_api.py:224-242` | Non-atomic writes |

### P1: Before Production

| Issue | Impact |
|-------|--------|
| No config validation | Runtime failures |
| No health checks | Silent failures |
| No metrics | Can't optimize |
| Security not integrated | Enterprise can't adopt |
| Cross-project state broken | "Resume anywhere" doesn't work |
| AST parser single-threaded | File watcher stutter |
| No state compression | Slow load/save |

### MCP-Specific Issues

| Issue | Current | Target |
|-------|---------|--------|
| Simple query latency | 3-8s | <500ms |
| Complex query latency | 18+s | <3s |
| Concurrent requests (5x) | Timeout | Work |
| LLM timeout | Indefinite hang | <5s |
| Thread pool | 4 workers | 12-16 |

---

## What's Needed vs What's Vague

### ✅ CLEAR (What to build)

1. **Git fact extractor** - Parse commits, extract facts, store JSON
2. **Simple injection** - Load task + facts, inject 200 tokens
3. **`hcr explain`** - Show injected context, build trust
4. **`hcr resume`** MVP - Git log + file state = context summary
5. **Manual controls** - pin/forget/reset

### ⚠️ VAGUE (Needs definition)

1. **"Latent" computation** - REMOVED from V1
2. **"Causal inference"** - REMOVED from V1
3. **Confidence scoring** - REMOVED from V1
4. **State format evolution** - How do we migrate `.hcr/facts.json` schema?
5. **Cache invalidation** - When exactly do we reload from disk?
6. **Error boundaries** - What happens when file watcher crashes?

### ❌ NOT V1 (Cut)

- VS Code Extension (use MCP only)
- Web dashboard
- Cloud sync
- Team features
- HCO Marketplace
- Vector DB (ChromaDB/Pinecone)

---

## Immediate Action Items

### Today
- [ ] Cut "latent" from all memory schemas
- [ ] Simplify `MemoryUnit` to facts + dependencies + task
- [ ] Remove confidence scoring

### This Week
- [ ] Build git fact extractor
- [ ] Implement `hcr explain` command
- [ ] Test `hcr resume` manually

### Next Week
- [ ] Fix CLI-daemon connection
- [ ] Add file watcher error boundaries
- [ ] Implement atomic state writes

### Before Any More Architecture
- [ ] Validate: Does `hcr resume` create "holy sh*t" moment?
- [ ] If NO → stop, reassess
- [ ] If YES → continue with remaining V1 features

---

## Honest Assessment

| Component | Doc Claim | Reality |
|-----------|-----------|---------|
| Core engine | 90% | 80% ✅ |
| MCP server | 90% | 60% ⚠️ |
| Daemon | 80% | 70% ⚠️ |
| VS Code integration | 40% | 20% ❌ |
| Production ready | Yes | **No** |

**The pattern:** Code exists for everything. Integration is where it breaks.

---

## Success Criteria for V1

**Test:**
1. User says: "Implement user auth"
2. Works for 30 minutes
3. Closes laptop
4. Opens 2 days later
5. Types: `hcr resume`

**Pass if:** AI says "You're implementing user auth, last working on middleware.ts"

**Fail if:** Wrong context, missing context, or "what are we working on?"

**No other metrics matter until this works.**

---

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-01 | Cut "latent" state | Unclear computation, unclear value |
| 2026-05-01 | Cut confidence scoring | Fake precision, adds complexity |
| 2026-05-01 | Simplify symbolic | Just facts + constraints, no rules layer |
| 2026-05-01 | Add `hcr explain` | Invisible failures kill trust |
| 2026-05-01 | Add manual controls | User must be able to correct |
| 2026-05-01 | Local-first | Privacy + latency + no network dependency |
| 2026-05-01 | 200 token limit | Hard constraint, forces relevance |

---

## PARALLEL WORK ASSIGNMENTS

**Split for k2.5 and k2.6 concurrent execution**

### Model k2.5 Assignment (MCP Tools A + Features)

**MCP Tools (11 tools):**
| ID | Tool | Issue | Status |
|----|------|-------|--------|
| 1 | `hcr_get_state` | 3-8s latency, sync I/O | <500ms | Done (fast_tools skip reload) |
| 2 | `hcr_get_causal_graph` | Unoptimized graph traversal | <500ms | Done (in fast_tools) |
| 3 | `hcr_get_current_task` | Defaults to LLM, slow inference | <500ms, LLM-free default | Done (use_llm=False) |
| 4 | `hcr_get_next_action` | No proper fallback | <500ms, degraded response | Done (use_llm=False) |
| 5 | `hcr_capture_full_context` | Sequential I/O = 18+s | <3s, parallelized | Done (removed redundant load_state) |
| 13 | `hcr_get_learned_operators` | No caching | Add 60s TTL cache | Done (already cached) |
| 14 | `hcr_get_system_health` | Heavy health checks | Cached snapshot | Done (use _current_state, 2s timeout) |
| 15 | `hcr_search_history` | Verify async safety | Add timeout | Done (already 5s timeout) |
| 18 | `_handle_resources_read` | sync load_state + infer_context | Async with timeout | Done (removed redundant load_state, 2s) |
| 19 | `_handle_prompts_get` | Default use_llm=True, sync fallback | LLM-free default | Done (use_llm=False, 2s) |
| 20 | `hcr://state/current` resource | Verify async reads | Add timeout | Done (2s timeout) |

**Feature Work:**
| Feature | File | Status |
|---------|------|--------|
| `hcr explain` command | `product/cli/explain.py` | ✅ Done |
| Git fact extractor | `product/state_capture/git_extractor.py` | ✅ Done |
| Manual controls (pin/forget/reset/list) | `product/cli/commands.py` | ✅ Done |

**Definition of Done for k2.5:**
- [x] All 11 tools optimized for latency
- [x] `hcr explain` shows injected context
- [x] Git extractor extracts 1-3 facts per commit
- [x] Manual controls implemented

---

### Model k2.6 Assignment (MCP Tools B + Infrastructure Polish)

**MCP Tools (10 tools + infrastructure):**
| ID | Tool | Issue | Status |
|----|------|-------|--------|
| 6 | `hcr_create_session` | Default LLM | ✅ k2.6 |
| 7 | `hcr_set_session_note` | Async safety | ✅ k2.6 |
| 8 | `hcr_share_state` | Cache race | ✅ k2.6 |
| 9 | `hcr_get_shared_state` | Async I/O | ✅ k2.6 |
| 10 | `hcr_list_shared_states` | Async I/O | ✅ k2.6 |
| 11 | `hcr_restore_version` | Sync replay | ✅ k2.6 |
| 12 | `hcr_get_version_history` | Metadata query | ✅ k2.6 |
| 16 | `hcr_merge_session` | Sync save | ✅ k2.6 |
| 17 | `hcr_record_file_edit` | AST blocks | ✅ k2.6 |
| 21 | `hcr_resume_session` prompt | No timeout | ✅ k2.6 |

**Infrastructure Polish:**
| Task | File | Status |
|------|------|--------|
| Config validation | `src/config.py` | ✅ k2.6 |
| Health check endpoint | `product/integrations/mcp_server.py` | ✅ k2.6 |
| State compression | `src/engine_api.py` | ✅ k2.6 |
| Terminal logger complete | `product/daemon/terminal_logger.py` | ✅ k2.6 |

**Definition of Done for k2.6:**
- [x] All 10 tools have proper timeouts (3-5s on all async ops)
- [x] Cache race conditions fixed (asyncio.Lock around all cache read/write/invalidation)
- [x] Health check tool returns system status (cached, 2s timeout, component metrics)
- [x] Update this doc with ✅ when complete

---

## CROSS-MODEL COORDINATION

**Shared Files (coordinate changes):**
- `product/integrations/mcp_server.py` - Both models edit different tool handlers
- `docs/dev_log.md` - Both update progress
- `docs/REALITY_CHECK_2026_05_01.md` - Both update status

**Communication Protocol:**
1. After each tool/feature, update this doc with ✅
2. If blocked on shared file, note it in "Blockers" section below
3. Daily sync: review what's ✅ and what's remaining

**Blockers (update as needed):**
| Blocker | Blocked Model | Waiting For | Resolution |
|---------|---------------|-------------|------------|
| None yet | - | - | - |

---

## COMPLETION CHECKLIST

**When both models finish:**
- [x] All 21 MCP tools working properly (k2.5 + k2.6 complete)
- [x] All 21 MCP tools wired to modular `product/integrations/tools/` handlers
- [x] `hcr explain` implemented (`product/cli/explain.py`)
- [x] `hcr resume` MVP working (`product/cli/resume.py`)
- [x] Manual controls working (`hcr memory pin/forget/reset/list`)
- [x] P0 infrastructure stable (daemon auto-start, atomic writes, error boundaries)
- [x] MCP stdio transport fixed (Content-Length framing, valid JSON-RPC responses)
- [x] MCP HTTP transport initialization fixed
- [x] Engine state/event persistence safe under concurrency
- [x] Cross-project shared state fallback to temp location
- [x] IDE setup uses `mcp_server_wrapper.py` + `sys.executable`
- [x] Windows daemon PID checks fixed (WinError 87)
- [x] MCP regression test: 21/21 tools passed
- [x] MCP server works as standalone stdio MCP server (not just in-process)
- [ ] Test: Resume after 2 days works (requires runtime validation)

**Success = all boxes checked above**

---

## Commercial Readiness Checklist

**Status date: 2026-05-01**

Working checklist for moving HCR from early alpha to commercial-grade product.

### Phase 1: Reliability
- [x] MCP stdio server responds correctly with framed JSON-RPC
- [x] MCP HTTP responder initializes correctly
- [ ] CLI server startup path works from supported entrypoints
- [ ] Basic diagnostics command exists: `hcr doctor`
- [x] Safer state/event persistence under concurrent access
- [ ] Daemon soak test for 24h+ on Windows/macOS/Linux
- [ ] Crash recovery verification for daemon/server restart
- [ ] State migration/version compatibility tests
- [ ] Concurrency/load tests for repeated MCP calls
- [ ] Automated regression suite in CI

### Phase 2: Installability
- [ ] setup.py includes core runtime dependencies used by the code
- [ ] VS Code extension can launch the local engine without terminal hacks
- [ ] CLI can initialize or resume a fresh workspace without manual pre-setup
- [ ] Single supported install flow documented and tested end-to-end
- [ ] pip install hcr / editable install / extension flow tested on clean machines
- [ ] Optional provider setup guide with validation steps
- [ ] Installer or bootstrap script for non-technical users

### Phase 3: Product UX
- [ ] Supportable diagnostics output exists
- [ ] Friendly remediation messages across all major failure paths
- [ ] Extension UI validated in real VS Code sessions
- [ ] Stable onboarding flow with minimal manual configuration
- [ ] `hcr explain` / `hcr doctor` surfaced clearly in docs and extension UX
- [ ] Remove stale/over-optimistic claims from README and docs

### Phase 4: Security and Operations
- [ ] Threat model for local state, daemon, and shared-state storage
- [ ] Sensitive data handling review for logs/state files
- [ ] Structured logging and support bundle strategy
- [ ] CI release process and versioning discipline
- [ ] Signed extension/release artifacts where applicable
- [ ] Backup/restore and data retention behavior defined

### Phase 5: Commercial Release Gate
- [ ] Clean install on a fresh machine succeeds without developer intervention
- [ ] Extension start/resume workflow works on supported OS targets
- [ ] LLM-enabled and heuristic-only modes both validated
- [ ] Error budget and support runbook defined
- [ ] Pricing/licensing packaging aligned with actual repo and extension metadata
- [ ] Documentation matches real product behavior

---

## Current Assessment

**HCR is now in a stronger early-alpha state:**
- MCP core is functioning
- Server launch paths are materially better
- Diagnostics exist
- VS Code integration is less brittle than before

**HCR is not yet commercial grade** because the remaining gaps are mostly in:
- Reproducibility
- Install flow
- Long-run reliability
- Release/operations discipline

...rather than core feature existence.

---

## Next Review

**Immediate Next Recommended Work:**
1. Add CI smoke coverage for `hcr doctor`, `hcr resume`, and MCP tool regression
2. Define one canonical install path and test it on a clean machine
3. Run daemon/server soak tests and fix restart/data-corruption issues
4. Remove inaccurate claims from README and extension docs

**Trigger:** Runtime validation of resume after idle period  
**Goal:** Validate the "holy sh*t" moment  
**If successful:** Proceed to polish  
**If failed:** Assign remaining issues

---

*Document created: May 1, 2026*  
*Status: Early Alpha → Commercial Readiness Planning*  
*Last Updated: 2026-05-01*
