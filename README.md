<div align="center">
  <img src="assets/images/logo.png" alt="HCR Logo" width="200"/>
  <h1>Hybrid Cognitive Runtime (HCR)</h1>
  <p><strong>State-based intelligence for persistent, context-aware reasoning</strong></p>
  <p>
    <a href="#installation"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
    <a href="#testing"><img src="https://img.shields.io/badge/tests-42%2F42%20passing-brightgreen.svg" alt="Tests"></a>
    <a href="#key-features"><img src="https://img.shields.io/badge/LLM-Groq%20%7C%20Gemini%20%7C%20Ollama-orange.svg" alt="LLM Support"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Proprietary-red.svg" alt="License: Proprietary"></a>
  </p>
</div>

---

## What is HCR?

**Intelligence = State. Reasoning = State Transitions. Knowledge = Constraints + Causal Relationships.**

Traditional AI systems are **token-based, stateless, and forgetful**: prompt → response → forget.

HCR revolutionizes this by making intelligence **persistent** and **structured**:

| Traditional AI | HCR |
|----------------|-----|
| Stateless | ✅ **State-based**: Intelligence persists as structured cognitive state |
| Forgetful | ✅ **Persistent**: Reasoning patterns are stored and reused |
| Text generation | ✅ **Execution-based**: Reasoning = state transitions |
| 2000+ tokens per context rebuild | ✅ **Zero-latency resume**: Instant context restoration |

---

## Architecture

## 🧠 Core Components

### Hybrid Cognitive Operator (HCO)
The fundamental unit of reasoning in HCR.

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
Rich, multi-modal state representation.

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

## 🚀 Installation

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

## 💡 Quick Start

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

### Diagnostics

```bash
hcr doctor
hcr doctor --format json
```

## ✅ Testing

```bash
python -m pytest tests/ -v
```

All **42/42** tests pass.

## 📁 Project Structure

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

## ✨ Key Features

- **Real Intelligence**: Integrated with Groq, Gemini, and Ollama for non-simulated reasoning.
- **State-based reasoning**: Persistent cognitive state across operations.
- **Zero-Latency Processing**: Events are processed instantly; LLM is called lazily.
- **Heuristic Fallback**: Works offline/without keys using keyword-based pattern matching.
- **Response Caching**: Hash-based caching to minimize LLM costs and latency.

## 🎯 Why HCR?

### The Problem
Developer tools today force you to **re-explain your context** every time you switch windows, devices, or conversations:
- VS Code doesn't remember what you were doing
- AI assistants start fresh every chat
- Context is lost across sessions

### The Solution
HCR captures and persists **cognitive state** — not just files, but *what you were thinking*:

```
Developer opens project
    ↓
System loads saved cognitive state from .hcr/state/
    ↓
Captures current context (git diff, open files, errors)
    ↓
Outputs: [Current Task] [Progress %] [Next Action]
```

**Result**: 80%+ sessions resumed without typing. 10-100x token reduction.

## 💼 Use Cases

| Use Case | How HCR Helps |
|----------|---------------|
| **Resume Work** | Know exactly where you left off after a break |
| **Code Review** | Track intent behind changes, not just diffs |
| **Onboarding** | New team members see the "why" not just the "what" |
| **Debugging** | Correlate errors with recent changes and intent |
| **AI Assistants** | Context persists across conversations |

## 📊 Performance & Status

| Metric | Value |
|--------|-------|
| **Phase** | Phase 1 (Real Intelligence Integration) ✅ Complete |
| **Tests** | 42/42 passing |
| **LLM Providers** | Groq, Google Gemini, Ollama |
| **Session Resume** | >80% without typing |
| **Token Reduction** | 10-100x vs traditional context rebuilding |
| **Time to First Action** | <10 seconds |

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on code style, testing, and the pull request process.

```bash
# Run tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_engine_api.py -v
```

## 📄 License

This project is licensed under a **Proprietary License**. The source code is visible for reference only.

**No license is granted for:**
- Commercial use without written consent
- Modification or derivative works
- Distribution or sublicensing

See the [LICENSE](LICENSE) file for full terms. For licensing inquiries, please contact the author.

## 🔗 Links

- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **Issues**: [GitHub Issues](https://github.com/PantheraLabs/HybridCognitiveRuntime/issues)
- **Discussions**: [GitHub Discussions](https://github.com/PantheraLabs/HybridCognitiveRuntime/discussions)

---

<div align="center">
  <p><strong>Built with ❤️ by PantheraLabs</strong></p>
  <p><em>Intelligence should persist. Context should resume.</em></p>
</div>
