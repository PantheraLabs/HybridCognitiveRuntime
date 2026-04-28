<div align="center">
  <img src="../assets/images/logo.png" alt="HCR Logo" width="150"/>
  <h1>Product Roadmap</h1>
  <p>Transitioning from Engine to Product</p>
</div>

---

**License**: Proprietary - See [LICENSE](../LICENSE) | **Author**: Rishi Praseeth Krishnan

This document outlines the strategic plan to evolve the **Hybrid Cognitive Runtime (HCR)** from a technical architecture into a complete, market-ready product.

## Phase 1: Real Intelligence Integration (The "Brain" Upgrade) ✅
**Goal:** Replace simulated logic with actual machine intelligence.

- [x] **LLM Connector Service:** Implemented unified provider abstraction with Groq (free, default), Google Gemini (free fallback), and Ollama (local/offline).
- [x] **Local Model Support:** Integrated Ollama with zero-dependency HTTP adapter for privacy-focused local reasoning.
- [x] **Neural Operator (Φ_n) Realization:** Rewrote `NeuralOperator` with real LLM calls, structured JSON prompting, and heuristic fallback.
- [ ] **Vector Database Integration:** Add support for ChromaDB or Pinecone to handle the `latent` state persistence at scale. *(Deferred — current JSON persistence is sufficient for now)*

## Phase 2: Autonomous Context Extraction (The "Awareness" Upgrade)
**Goal:** Make HCR a silent background daemon that watches your work — no manual input required.  
**Detailed Plan:** See [`docs/phase2_plan.md`](./phase2_plan.md)

- [x] **HCR Daemon:** A long-running background process that manages all watchers with start/stop/restart CLI. ✅
- [x] **Real-Time File Watcher:** Uses `watchdog` (OS-level inotify/FSEvents) to feed file edits to the engine at < 0.1% CPU. ✅
- [x] **Git Hook Installer:** Lightweight shell hooks for `post-commit`, `post-checkout`, `post-merge` that fire engine events automatically. ✅
- [x] **Terminal Logger:** Shell snippet injected into `.bashrc`/`.zshrc` to capture commands and exit codes into cognitive state. ✅
- [ ] **VS Code Extension Upgrade:** Window focus heartbeat, active tab tracking, and live status bar showing `[HCR: 65% → Commit changes]`.
- [ ] **VS Code Extension Upgrade:** Window focus heartbeat, active tab tracking, and live status bar showing `[HCR: 65% → Commit changes]`.

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
