# Hybrid Cognitive Runtime (HCR)

A state-based cognitive execution system where intelligence = state, reasoning = state transitions, and knowledge = constraints + causal relationships.

## Core Paradigm

Traditional AI systems are token-based, stateless, and operate as prompt → response → forget.

HCR is:
- **State-based**: Intelligence persists as structured state
- **Persistent**: Reasoning patterns are stored and reused
- **Execution-based**: Reasoning = state transitions (not text generation)

## Architecture

### Core Primitive: Hybrid Cognitive Operator (HCO)

An HCO is the smallest executable unit of reasoning.

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

### Cognitive State (S)

```python
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

## Installation

```bash
git clone https://github.com/PantheraLabs/HybridCognitiveRuntime.git
cd HybridCognitiveRuntime
```

No dependencies required - pure Python implementation.

## Quick Start

```python
from src.state.cognitive_state import CognitiveState
from src.operators.symbolic_operator import SymbolicOperator
from src.core.hco_engine import HCOEngine

# Create initial state
state = CognitiveState()
state.symbolic.facts = ["it_is_raining"]
state.symbolic.rules = ["if it_is_raining then take_umbrella"]

# Create operator
deduce = SymbolicOperator("deducer")

# Execute
result = deduce.execute(state, operation="deduce")
print(result.symbolic.facts)  # ["it_is_raining", "take_umbrella", ...]
```

## Examples

Run the reasoning examples:

```bash
python examples/simple_reasoning.py
```

## Testing

```bash
python tests/test_state.py
python tests/test_operators.py
python tests/test_engine.py
```

All 15 tests pass.

## Project Structure

```
HybridCognitiveRuntime/
├── src/
│   ├── state/              # State representation & transitions
│   │   ├── cognitive_state.py
│   │   └── state_transition.py
│   ├── operators/          # HCO implementations
│   │   ├── base_operator.py
│   │   ├── neural_operator.py
│   │   ├── symbolic_operator.py
│   │   ├── causal_operator.py
│   │   └── policy_selector.py
│   └── core/               # Execution engine
│       └── hco_engine.py
├── examples/               # Usage examples
├── tests/                  # Unit tests
└── docs/                   # Documentation
    ├── project_memory.md   # Primary source of truth
    ├── architecture.md     # System design
    ├── tasks.md            # Current tasks
    └── dev_log.md          # Development history
```

## Key Features

- **State-based reasoning**: Persistent cognitive state across operations
- **Three operator types**: Neural (Φ_n), Symbolic (Φ_s), Causal (Φ_c)
- **Policy selection**: Dynamic operator selection based on state characteristics
- **Learning loop**: Operators improve based on success/failure feedback
- **Composable**: Operators can be composed into sequences
- **Cross-model compatible**: No model-specific dependencies

## Documentation

See the `docs/` directory for detailed documentation:
- `project_memory.md` - Project overview and decisions
- `architecture.md` - System architecture and design
- `tasks.md` - Current development tasks
- `dev_log.md` - Development history and technical notes

## License

MIT License - See LICENSE file for details.

## Status

**Phase**: Core implementation complete
**Tests**: 15/15 passing
**Examples**: 4/4 working

The HCR architecture is functional and ready for extension.