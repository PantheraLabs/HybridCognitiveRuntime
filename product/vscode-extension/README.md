# HCR Resume - Never Re-Explain Your Code

**Resume development sessions with full cognitive context intact.**

HCR (Hybrid Cognitive Runtime) eliminates the #1 developer pain point: **context loss between AI sessions**. While traditional AI tools make you spend 10+ minutes re-explaining your work, HCR remembers everything.

## Features

### 🧠 Smart Session Resume
- Automatic context restoration when returning to projects
- AI-inferred current task and progress tracking
- Suggested next actions based on cognitive state

### 📊 Real-time State Tracking
- File change monitoring with automatic state updates
- Git integration (commits, branches, uncommitted changes)
- Active editor tracking for precise context

### 🎯 Intelligent Recommendations
- AI-powered next action suggestions
- Confidence scoring for context inference
- Causal impact analysis (predict ripple effects of changes)

### ⚡ Token Efficiency
- **10-100x reduction** in context rebuilding tokens
- Persistent cognitive state across sessions
- Works across GPT, Claude, Gemini without re-explanation

## Quick Start

1. Install the extension
2. Install the local HCR Python package or set `hcr.pythonPath`
3. Open a project folder
4. HCR auto-starts the local engine server for that workspace
5. Use `Ctrl+Shift+P` → "HCR: Resume Session" anytime

## Commands

| Command | Description |
|---------|-------------|
| `HCR: Resume Session` | Resume with full context |
| `HCR: Show Current State` | View current cognitive state |
| `HCR: Clear Session State` | Reset HCR state |
| `HCR: Start Engine Server` | Manually start HCR engine |

## Configuration

```json
{
  "hcr.autoResume": true,        // Auto-resume on window focus
  "hcr.idleThreshold": 30,         // Minutes before auto-resume (default: 30)
  "hcr.outputFormat": "text",      // Output format: text, json
  "hcr.commandPath": "",           // Optional path to hcr CLI
  "hcr.pythonPath": "",            // Optional Python executable for local launch
  "hcr.serverPort": 8733            // Local engine server port
}
```

## How It Works

```
Traditional AI:          HCR Resume:
2000+ tokens             0 tokens
10 min setup             <10 seconds
Repeat context           Full memory retained
Variable success         80%+ confidence
```

HCR maintains a **cognitive state** including:
- Current development task
- Progress percentage
- Recent file changes
- Git state
- Inferred next actions

## Requirements

- Python 3.9+
- VS Code 1.74+
- Local HCR package available either as `hcr` on PATH or via `hcr.pythonPath`

## Extension Settings

This extension contributes the following settings:

* `hcr.autoResume`: Enable/disable automatic session resumption
* `hcr.idleThreshold`: Minutes of idle time before auto-resume triggers
* `hcr.outputFormat`: Format for resume output (text or json)
* `hcr.commandPath`: Path to the `hcr` executable, if not on PATH
* `hcr.pythonPath`: Python executable used to launch HCR locally
* `hcr.serverPort`: Local HTTP port used by the extension

## Known Issues

- First initialization may take 5-10 seconds
- Large projects (1000+ files) may have slower analysis
- The extension launches a local HTTP engine process; if startup fails, set `hcr.commandPath` or `hcr.pythonPath`

## Release Notes

### 0.1.0

- Initial release
- Session resume with cognitive state
- File watcher integration
- Git state tracking
- Auto-resume on window focus

## License

Proprietary. See the repository `LICENSE` file.
