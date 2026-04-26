# Phase 2 Plan: Autonomous Context Extraction (The "Awareness" Upgrade)

**Status:** Planning  
**Goal:** Make HCR a silent background daemon that watches your work in real time — no manual input required.

---

## The Problem We Are Solving

After Phase 1, HCR can reason brilliantly — but only when it is told what happened. This is like hiring a genius assistant who only knows what you choose to tell them.

Phase 2 gives HCR its **senses**. It will watch your file system, terminal, and editor autonomously and continuously update the cognitive state without any user action.

Once Phase 2 ships, the UX loop becomes:
1. You open your editor
2. HCR is already running in the background (started at login or by the IDE)
3. You work normally — save files, run tests, commit code
4. HCR's state evolves in real time
5. When you (or your AI assistant) asks "where am I?" — the answer is already there

---

## Architecture: The Daemon Model

```
┌─────────────────────────────────────────────────────────────┐
│                      HCR DAEMON                             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ File Watcher │  │ Git Monitor  │  │ Terminal Logger  │  │
│  │  (watchdog)  │  │  (git hooks) │  │  (shell hooks)   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         └─────────────────▼────────────────────┘            │
│                    Engine API (HTTP)                         │
│                 POST /event  →  state update                 │
└─────────────────────────────────────────────────────────────┘
```

All watchers communicate with the existing engine API via `POST /event`. The daemon has **no business logic** — it only translates OS events into structured HCR events. This follows the Engine-First rule strictly.

---

## Components

### 1. HCR Daemon (`product/daemon/hcr_daemon.py`)
The long-running process that manages all watchers. Responsibilities:
- Start/stop all watchers
- Handle crashes gracefully (watcher restart on failure)
- Accept signals: `SIGTERM` (graceful shutdown), `SIGHUP` (reload config)
- Write a PID file to `.hcr/daemon.pid`
- Auto-start on system login (via OS-specific startup mechanism)

Command: `python -m product.daemon start --project .`

### 2. File System Watcher (`product/daemon/file_watcher_service.py`)
Wraps the existing `product/state_capture/file_watcher.py` with `watchdog` for real-time events (instead of polling). 

Event translation:
- `FileModifiedEvent` → `POST /event {"type": "file_edit", "data": {"path": "..."}}`
- `FileCreatedEvent` → `POST /event {"type": "file_create", "data": {"path": "..."}}`
- `FileDeletedEvent` → `POST /event {"type": "file_delete", "data": {"path": "..."}}`

Debounced at 500ms (rapid saves don't spam the engine).

### 3. Git Hook Installer (`product/daemon/git_hooks.py`)
Installs lightweight shell scripts into `.git/hooks/`. The hooks fire automatically on git operations and call the engine API.

Hooks to install:
- `post-commit` → `POST /event {"type": "git_commit", "data": {"message": "..."}}`
- `post-checkout` → `POST /event {"type": "git_checkout", "data": {"branch": "..."}}`
- `post-merge` → `POST /event {"type": "git_merge"}`

Installation command: `hcr setup --project .`

### 4. Terminal Logger (`product/daemon/terminal_logger.py`)
A shell function that wraps the user's terminal to log commands to HCR. Appended to `.bashrc` / `.zshrc` during setup.

```bash
# Injected by HCR setup
_hcr_log_cmd() {
    local cmd="$1"
    local exit_code="$2"
    curl -s -X POST http://localhost:8733/event \
         -d "{\"type\":\"terminal\",\"data\":{\"command\":\"$cmd\",\"success\":$([[ $exit_code == 0 ]] && echo true || echo false)}}" &
}
```

### 5. IDE Extension Heartbeat (`product/vscode-extension/`)
The existing VS Code extension skeleton gets upgraded with:
- **Heartbeat on focus**: When the window gains focus, calculate time gap and fire `POST /event {"type": "window_focus", "data": {"gap_minutes": N}}`
- **Active file tracking**: When the user switches tabs, fire a `file_edit` event.
- **HCR Status Bar**: Show `[HCR: 65% → Commit changes]` in the VS Code status bar, updated every 30s.

---

## Implementation Plan

### Step 1: Daemon Core
- [ ] `product/daemon/__init__.py`
- [ ] `product/daemon/hcr_daemon.py` — process manager with PID file
- [ ] `product/daemon/__main__.py` — CLI entry (`python -m product.daemon start`)
- [ ] Daemon CLI: `start`, `stop`, `status`, `restart`

### Step 2: Real-Time File Watcher
- [ ] `product/daemon/file_watcher_service.py` — `watchdog` observer
- [ ] Debounce logic (500ms window)
- [ ] Ignore patterns (`.git`, `__pycache__`, `node_modules`, etc.)
- [ ] Wire to engine via `POST /event`

### Step 3: Git Hooks
- [ ] `product/daemon/git_hooks.py` — installer/uninstaller
- [ ] Shell scripts for `post-commit`, `post-checkout`, `post-merge`
- [ ] `hcr setup` command in CLI

### Step 4: Shell Integration
- [ ] `product/daemon/terminal_logger.py` — generates shell snippet
- [ ] `hcr setup` appends to `.bashrc` / `.zshrc` / `config.fish`

### Step 5: VS Code Extension Upgrade
- [ ] Heartbeat on window focus
- [ ] Active tab tracking
- [ ] Status bar item (task + progress)

### Step 6: Engine API Additions
These endpoints are needed to support the daemon:
- [ ] `GET /health` (already exists) — daemon checks this before sending events
- [ ] `GET /status` — returns daemon connection info
- [ ] Engine handles rapid event bursts gracefully (event queue)

### Step 7: Tests & Docs
- [ ] Unit tests for file watcher debounce logic
- [ ] Integration test: simulate file saves, verify state updates
- [ ] Update README with daemon start instructions

---

## Setup UX (Target)

After Phase 2, getting started looks like this:

```bash
# One-time setup
pip install hcr
hcr setup --project /path/to/project

# Starts the daemon, installs git hooks, patches shell
# Done. Now just work normally.
```

---

## Dependencies

| Dependency | Purpose | Already Installed? |
|---|---|---|
| `watchdog>=4.0.0` | Real-time file system events | No |
| `requests>=2.28.0` | Daemon → Engine HTTP calls | Yes |

No new LLM dependencies — the daemon is intentionally "dumb". It only observes and reports. The intelligence stays in the Engine.

---

## Design Principles

1. **Silent by default**: The daemon must never interrupt the user. No pop-ups, no logs to stdout.
2. **Zero data leakage**: File *names* and git *messages* are captured — never file *contents*.
3. **Fault tolerant**: If the engine is not running, the daemon queues events and retries. It never crashes.
4. **Low overhead**: The file watcher uses OS-level inotify/FSEvents (not polling). CPU usage target: < 0.1% idle.
