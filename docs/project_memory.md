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

- Phase: Initialization
- State: Architecture defined, implementation pending
- Next: Implement core HCO structure and state representation
