# Product Roadmap: HCR (Transitioning from Engine to Product)

This document outlines the strategic plan to evolve the **Hybrid Cognitive Runtime (HCR)** from a technical architecture into a complete, market-ready product.

## Phase 1: Real Intelligence Integration (The "Brain" Upgrade)
**Goal:** Replace simulated logic with actual machine intelligence.

- [ ] **LLM Connector Service:** Implement a robust integration layer for Claude (Anthropic), Gemini (Google), and GPT-4 (OpenAI).
- [ ] **Local Model Support:** Integrate Ollama/Llama.cpp for privacy-focused local reasoning.
- [ ] **Neural Operator (Φ_n) Realization:** Update `NeuralOperator` to use real embeddings and completions instead of simulated vector math.
- [ ] **Vector Database Integration:** Add support for ChromaDB or Pinecone to handle the `latent` state persistence at scale.

## Phase 2: Autonomous Context Extraction (The "Awareness" Upgrade)
**Goal:** Automatically capture context from the developer's ecosystem.

- [ ] **GitHub/GitLab Integrations:** Automatically pull PR descriptions, issue comments, and commit history into the cognitive state.
- [ ] **Communication Hooks:** Connect to Slack/Discord to capture "tribal knowledge" shared in chat.
- [ ] **Documentation Parser:** Implement a background worker that indexers project docs, wikis, and READMEs into the `symbolic` and `causal` states.
- [ ] **Terminal Awareness:** Capture command history and build-failure logs to update the `causal` state automatically.

## Phase 3: Cognitive Dashboard (The "Interface" Upgrade)
**Goal:** Provide a high-fidelity visual window into the HCR state.

- [ ] **Web-based Dashboard:** A React/Next.js interface that visualizes:
    - **The Causal Graph:** A node-link diagram showing how tasks and facts are related.
    - **State Timeline:** A "Time Machine" to scrub back through cognitive state transitions.
    - **Confidence Heatmap:** Visual indicators of where the system is uncertain.
- [ ] **Enhanced VS Code View:** A dedicated sidebar panel (beyond just the status bar) for real-time task tracking.

## Phase 4: Streamlined Onboarding (The "Growth" Upgrade)
**Goal:** Reduce "Time-to-Value" to under 5 minutes.

- [ ] **Unified Installer:** A single command (e.g., `curl -sSL hcr.sh | sh`) that sets up the engine, CLI, and IDE extensions.
- [ ] **Zero-Config Defaults:** Smart auto-detection of project type (React, Python, Rust) to populate initial symbolic rules.
- [ ] **Configuration UI:** A user-friendly settings page to manage API keys and ports without editing JSON.

## Phase 5: Enterprise & Team Features (The "Scale" Upgrade)
**Goal:** Enable HCR to work across teams and devices.

- [ ] **State Sync Service:** Encrypted cloud backup to sync cognitive state across multiple machines.
- [ ] **Shared Team State:** Allow teams to share a "Global Cognitive State" for a repository, ensuring everyone stays in sync.
- [ ] **HCO Marketplace:** A registry for sharing custom Symbolic rules and Causal templates for specific frameworks.

---

## Strategy: "Engine-First, Product-Second"
We maintain the **Engine-First** philosophy. Every "Product" feature must be an API endpoint in the HCR Engine before it is implemented in the UI. 

**Core Mantra:** The UI is just a lens; the Engine is the truth.
