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
pip install -e .[all]  # Install with all LLM provider dependencies
```

### Configuration

HCR supports multiple LLM providers for real intelligence. Copy the example environment file and add your keys:

```bash
cp .env.example .env
# Edit .env to add your GROQ_API_KEY or GOOGLE_API_KEY
```

Supported Providers:
- **Groq** (Default): Fast, free tier available.
- **Google Gemini**: Reliable fallback, free tier via AI Studio.
- **Ollama**: Fully local and private reasoning.

## Quick Start

### Using the Engine API

```python
from src.engine_api import HCREngine, EngineEvent

# Initialize engine
engine = HCREngine(project_path=".")

# Process an event
engine.update_from_environment(EngineEvent(
    event_type="file_edit",
    data={"path": "src/core/hco_engine.py"}
))

# Infer context using real LLM intelligence
context = engine.infer_context()
print(f"Task: {context.current_task}")
print(f"Next Action: {context.next_action}")
```

### Running the CLI

```bash
python -m product.cli.resume --project .
```

## Testing

```bash
python -m pytest tests/ -v
```

All **42/42** tests pass.

## Project Structure

```
HybridCognitiveRuntime/
├── src/
│   ├── state/              # State representation & transitions
│   ├── operators/          # HCO implementations (now LLM-powered)
│   ├── core/               # Execution engine
│   ├── llm/                # LLM Provider abstraction (Groq, Google, Ollama)
│   ├── config.py           # Layered configuration system
│   └── engine_api.py       # High-level product API
├── product/                # Product-level tools (CLI, VS Code Bridge)
├── examples/               # Usage examples
├── tests/                  # Unit tests
└── docs/                   # Documentation
```

## Key Features

- **Real Intelligence**: Integrated with Groq, Gemini, and Ollama for non-simulated reasoning.
- **State-based reasoning**: Persistent cognitive state across operations.
- **Zero-Latency Processing**: Events are processed instantly; LLM is called lazily.
- **Heuristic Fallback**: Works offline/without keys using keyword-based pattern matching.
- **Response Caching**: Hash-based caching to minimize LLM costs and latency.

## Status

**Phase**: Phase 1 (Real Intelligence Integration) Complete.
**Tests**: 42/42 passing.
**Providers**: Groq, Google Gemini, Ollama.

The HCR architecture is now a production-ready engine for cognitive developer tools.