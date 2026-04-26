# Project Memory

## Project Overview

**Hybrid Cognitive Runtime (HCR)** - A state-based cognitive execution system where intelligence = state, reasoning = state transitions, and knowledge = constraints + causal relationships.

### Core Paradigm Shift

Traditional AI systems are token-based, stateless, and operate as prompt → response → forget.

HCR is:
- **State-based**: Intelligence persists as structured state
- **Persistent**: Reasoning patterns are stored and reused
- **Execution-based**: Reasoning = state transitions (not text generation)

## Core Primitive: Hybrid Cognitive Operator (HCO)

An HCO is the smallest executable unit of reasoning.

### Formal Structure

```
HCO = (
    S_in,        # input cognitive state
    Φ_n,         # neural operator (handles ambiguity)
    Φ_s,         # symbolic operator (rules / logic)
    Φ_c,         # causal operator (dependencies)
    Π,           # policy selector
    ΔS           # state transition
)
```

## Cognitive State (S)

State is NOT text. It is structured:

```
S = {
  latent: vector(n),         # compressed representation
  symbolic: {
    facts: [],
    rules: [],
    constraints: []
  },
  causal: {
    dependencies: [],
    effects: []
  },
  meta: {
    confidence: float,
    uncertainty: float,
    timestamp: t
  }
}
```

## Reasoning Mechanism

**NOT**: generate text, retrieve memory

**INSTEAD**: `S_next = ΔS(S_current, HCO_sequence)`

Where:
- reasoning = applying operators
- understanding = evolving state

## Operator Types

### 1. Neural (Φ_n)
- Handles ambiguity
- Pattern recognition

### 2. Symbolic (Φ_s)
- Rules, logic, constraints

### 3. Causal (Φ_c)
- Cause-effect reasoning

## Policy Selector (Π)

Chooses which operator to apply based on:
- Uncertainty
- Constraint violations
- Goal state

## Key Principles

### Reusable Reasoning
- Store operator sequences
- Reuse across tasks
- Improve over time

Example:
```
debug_auth = compose(
  detect_issue,
  evaluate_constraints,
  choose_solution
)
```

### Token Usage Rule
Tokens are NOT the source of intelligence.
- Minimize token usage
- Avoid replaying history
- Reconstruct only necessary context
- Target: 10-100x reduction in tokens

### Cross-Model Continuity
System must work across GPT, Claude, Gemini.
- DO NOT rely on embeddings
- DO NOT rely on chat history
- Rely ONLY on: state + operators

### Learning Loop
After each execution:
```
HCO = update(HCO, feedback)
```
- success → reinforce
- failure → adjust
- irrelevant → decay

## Success Criteria

- Tasks resume without re-explanation
- Reasoning improves over time
- Token usage decreases drastically
- System feels like it "remembers and understands"

## Technology Decisions

### Language
- Python (for initial implementation)
- Type hints for state structure
- Dataclasses for state representation

### State Storage
- JSON/YAML for persistence
- In-memory for active reasoning
- Version control for state evolution

### Operator Registry
- Centralized operator catalog
- Versioned operator sequences
- Performance metrics tracking

## Current Status

- Phase: Product Development (Phase 5 Complete)
- State: Core engine complete. **Phase 5 (The Cognitive Twin)** is fully integrated, providing:
  - **Workflow Anticipation**: Markov Chain-based prediction of next file edits.
  - **Friction Detection**: Tracking terminal failures to avoid repeating mistakes.
  - **Behavioral Profiling**: Storing strict developer style constraints in `.hcr/profile.json`.
- Next: Build real LLM connectors (OpenAI/Anthropic) and build the web-based State Visualizer.

## Product Features

### Resume Without Re-Explaining ✅ (80% Complete)
First developer-facing product that eliminates context re-explanation problem.

**Workflow:**
1. Load cognitive state from `.hcr/session_state.json`
2. Capture current reality (git + files + time gap)
3. Run HCO sequence: ingest_context → infer_intent → suggest_action
4. Output: [Current Task] [Progress %] [Next Action]

**Components:**
- `product/state_capture/git_tracker.py` - Git state monitoring
- `product/state_capture/file_watcher.py` - File system tracking
- `product/storage/state_persistence.py` - JSON state persistence
- `product/hco_wrappers/dev_context_ops.py` - Dev context HCOs
- `product/cli/resume.py` - CLI entry point
- `product/vscode-extension/` - VS Code integration skeleton

**Target Metrics:**
- Sessions resumed without typing: >80%
- Token reduction: 10-100x
- Time to first action: <10 seconds

### Web Dashboard 🚧
State visualization tool for inspecting cognitive state and causal graphs.

**Location:** `web/` (moved from `src/web/` for proper separation of concerns)

**Features:**
- Real-time engine status
- Causal graph visualization (Cytoscape.js)
- State inspection panel
- Demo mode for testing
