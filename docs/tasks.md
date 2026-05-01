# Tasks

<div align="center">
  <img src="../assets/images/logo.png" alt="HCR Logo" width="150"/>
</div>

## Current Project Status: Product Development Phase 1 ✅

The core HCR architecture is implemented. LLM Connectors are now integrated and being refined.

**License**: Proprietary - See [LICENSE](../LICENSE)

## Completed Tasks (Phase 1-5)

### Core State System ✅
- [x] Cognitive state dataclass (`src/state/cognitive_state.py`)
- [x] State transition logic (`src/state/state_transition.py`)
- [x] State persistence (`.hcr/session_state.json`)

### Operator System ✅
- [x] Base HCO interface (`src/operators/base_operator.py`)
- [x] Neural operator simulation (`src/operators/neural_operator.py`)
- [x] Symbolic operator (`src/operators/symbolic_operator.py`)
- [x] Causal operator (`src/operators/causal_operator.py`)
- [x] Policy selector (`src/operators/policy_selector.py`)

### Execution Engine ✅
- [x] HCO engine orchestration (`src/core/hco_engine.py`)
- [x] Engine API (`src/engine_api.py`)
- [x] HTTP Server (`src/engine_server.py`)

### Interfaces ✅
- [x] Professional CLI (`product/cli/main.py`) - `hcr init --auto`
- [x] Legacy CLI wrapper (`product/cli/resume.py`)
- [x] MCP Server integration (`product/integrations/mcp_server.py`) - Universal IDE support
  - [x] 12 MCP tools implemented and verified
  - [x] 3 MCP resources (state, causal-graph, task)
  - [x] 2 MCP prompts (resume_session, context_aware_coding)
  - [x] Event logging - tool calls record to event store
  - [x] Context updates - tool calls trigger state updates
- [x] VS Code Extension (deprecated in favor of MCP)

### The Cognitive Twin (Phase 5) ✅
- [x] Workflow Anticipation (Markov Chains) (`src/causal/workflow_predictor.py`)
- [x] Friction Detection (Terminal failures) (`src/symbolic/friction_detector.py`)
- [x] Behavioral Profiling (`src/symbolic/profile_manager.py`)
- [x] Engine Event Routing Fixes (Total Recall)

---

## Active Product Development (See [Product Roadmap](product_roadmap.md))

### Immediate Priorities (Next 2 Weeks)
1. **[Roadmap Phase 1]** Refine real LLM connectors (OpenAI/Anthropic). [DONE] ✅
2. **[Roadmap Phase 1]** Update Neural Operator to use real completions. [DONE] ✅
4. **[Roadmap Phase 3]** Build initial web-based State Visualizer. [DONE] ✅
5. **[Roadmap Phase 4]** Predictive Causal Simulation & Risk Heatmaps. [DONE] ✅
6. **[Roadmap Phase 5]** Neural Causal Discovery (Latent Link Inference). [NEW] ⚡

## Testing Status
- [x] 15/15 Unit tests passing
- [x] HTTP API verified (Health, Resume, Event endpoints)
- [x] Cognitive Twin inference verified
- [x] MCP Server comprehensive reliability audit & fixes applied (2026-05-01)
  - **19 tools + 3 resources + 2 prompts** audited and hardened
  - **Standardized Transport**: Migrated to line-based JSON-RPC (standard MCP) from non-standard headers
  - **Commercial Ready Architecture**: 
    - Dedicated background reader thread for non-blocking stdin
    - Asyncio producer-consumer queue for message dispatch
    - Full concurrency with `asyncio.create_task` tracking
    - Support for `notifications/cancelled` (task abortion)
    - Atomic `stdout` write synchronization with Lock
  - All sync I/O moved off asyncio event loop via `_run_blocking(..., timeout=...)`
  - **Scale**: Thread pool expanded 4→16 workers; global handler timeout 15s→5s for faster failure recovery
  - **Caching layer** added: shared_keys, learned_operators, health, version_history (60s TTL)
  - **LLM safety**: All LLM-dependent tools default `use_llm=False` with explicit opt-in
  - `_generate_smart_resume` LLM call now has 10s timeout (was raw `run_in_executor` with no timeout)
  - Event logging changed to **fire-and-forget** background executor (was sync disk write blocking every call)
  - Smart state loading now has 5s timeout (continues with stale state on timeout)
  - `capture_full_context` defaults `include_diffs=False`; per-subsystem timeouts (git 5s, files 5s, diffs 5s, inference 8s)
  - `create_session`, `get_current_task`, `get_next_action` default to LLM-free fast path
  - `restore_version` async event replay with 10s timeout; `record_file_edit` async AST/diff with 5s timeout
  - All resource reads (`_handle_resources_read`) and prompt generation (`_handle_prompts_get`) async-safe
  - Zero remaining synchronous I/O calls on the asyncio event loop
  - Syntax verified (`python -m py_compile`)
- [x] MCP Server full regression test (verified initialization and tool list via `test_standard_mcp.py`)
