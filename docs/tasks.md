# Tasks

## Current Project Status: Product Development Phase 1 ✅

The core HCR architecture is implemented. LLM Connectors are now integrated and being refined.

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
- [x] MCP Server verified (12/12 tools working, context updates working)
