<div align="center">
  <img src="../assets/images/logo.png" alt="HCR Logo" width="150"/>
  <h1>Architecture</h1>
</div>


## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hybrid Cognitive Runtime             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  Input State │─────▶│  HCO Engine  │               │
│  │     (S_in)   │      │              │               │
│  └──────────────┘      └──────┬───────┘               │
│                                │                       │
│                                ▼                       │
│                        ┌──────────────┐               │
│                        │  Policy (Π)  │               │
│                        └──────┬───────┘               │
│                               │                       │
│              ┌────────────────┼────────────────┐      │
│              ▼                ▼                ▼      │
│        ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│        │ Neural   │    │Symbolic  │    │ Causal   │   │
│        │  (Φ_n)   │    │  (Φ_s)   │    │  (Φ_c)   │   │
│        └────┬─────┘    └────┬─────┘    └────┬─────┘   │
│             │              │              │          │
│             └──────────────┼──────────────┘          │
│                            │                         │
│                            ▼                         │
│                      ┌──────────┐                   │
│                      │ ΔS (State │                   │
│                      │Transition)│                   │
│                      └────┬─────┘                   │
│                           │                         │
│                           ▼                         │
│                  ┌──────────────┐                  │
│                  │ Output State │                  │
│                  │   (S_next)   │                  │
│                  └──────────────┘                  │
│                                                 │
├─────────────────────────────────────────────────┤
│              Operator Registry & Storage          │
├─────────────────────────────────────────────────┤
│  • HCO Catalog        • State History            │
│  • Operator Sequences • Learning Metrics         │
│  • Performance Data   • Feedback Loops           │
└─────────────────────────────────────────────────┘
```

## Component Map

### Core Components

#### 1. State Module (`src/state/`)
- `cognitive_state.py` - State representation
- `state_transition.py` - ΔS implementation
- `state_history.py` - State evolution tracking

#### 2. Operators Module (`src/operators/`)
- `base_operator.py` - Abstract HCO interface
- `neural_operator.py` - Φ_n implementation (LLM-powered)
- `symbolic_operator.py` - Φ_s implementation
- `causal_operator.py` - Φ_c implementation
- `policy_selector.py` - Π implementation

#### 3. Core Engine (`src/core/`)
- `hco_engine.py` - Main reasoning engine
- `operator_registry.py` - HCO catalog
- `execution_context.py` - Execution management
- `learning_loop.py` - Feedback integration

#### 4. LLM Module (`src/llm/`)
- `provider.py` - LLM provider abstraction
- `groq_provider.py` - Groq integration
- `google_provider.py` - Google Gemini integration
- `ollama_provider.py` - Local Ollama support

#### 5. Engine API (`src/`)
- `engine_api.py` - High-level product API
- `config.py` - Layered configuration system

### Product Components

#### 1. State Capture (`product/state_capture/`)
- `git_tracker.py` - Git state monitoring
- `file_watcher.py` - File system tracking
- `terminal_monitor.py` - Terminal output capture

#### 2. Storage (`product/storage/`)
- `state_persistence.py` - JSON/YAML persistence with git-like versioning

#### 3. HCO Wrappers (`product/hco_wrappers/`)
- `dev_context_ops.py` - Developer context HCOs

#### 4. CLI (`product/cli/`)
- `main.py` - Professional CLI (hcr init, resume, status, dashboard)
- `resume.py` - Resume command implementation

#### 5. Integrations (`product/integrations/`)
- `mcp_server.py` - MCP server for IDE integration (Windsurf, Claude, Cursor)

### Data Flow

```
Input → State Parser → HCO Engine → Operator Selection → 
Execution → State Transition → Output → Storage → Learning
```

## State Representation

### Latent State
- Compressed vector representation
- Dimensionality: n (configurable)
- Storage: NumPy arrays or similar

### Symbolic State
- Facts: Atomic truths
- Rules: Logical constraints
- Constraints: Hard/soft limits

### Causal State
- Dependencies: What affects what
- Effects: Consequences of actions

### Meta State
- Confidence: 0.0-1.0
- Uncertainty: 0.0-1.0
- Timestamp: Execution time

## Operator Registry

### Structure
- Unique identifier per HCO
- Version tracking
- Input/output state schemas
- Performance metrics
- Usage statistics

### Persistence
- File-based storage (JSON/YAML)
- Version control integration
- Backup and restore

## Learning System

### Feedback Types
- Success reinforcement
- Failure adjustment
- Irrelevant decay

### Metrics
- Success rate
- Token efficiency
- Execution time
- State convergence

## Cross-Model Compatibility

### Abstraction Layer
- Model-agnostic state representation
- Standardized operator interface
- No model-specific dependencies

### Portability
- Pure Python implementation
- No embedding dependencies
- Minimal external libraries

## Extension Points

### Custom Operators
- Inherit from base HCO
- Implement state transition logic
- Register in catalog

### Custom Policies
- Implement policy selector interface
- Define selection criteria
- Integrate with learning loop

### State Serializers
- Implement state persistence
- Support different formats
- Handle version migration
