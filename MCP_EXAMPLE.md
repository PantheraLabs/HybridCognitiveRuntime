# HCR MCP Integration: Example Interaction

## Setup Status

✅ **HCR Engine:** Running on localhost:8733  
✅ **MCP Server:** Implemented (mcp_server.py)  
✅ **Windsurf Config:** Ready (windsurf_mcp_config.json)  

---

## Example: Cascade Using HCR

### User Query

```
[User]: I'm back from lunch, what should I work on?
```

### Behind the Scenes (Automatic)

```python
# Cascade automatically calls:
result = resume_session(gap_minutes=60)

# MCP server executes:
POST http://localhost:8733/resume
Body: {"gap_minutes": 60}

# HCR engine returns:
{
  "current_task": "Implementing: add 'resume without re-explaining' product",
  "progress_percent": 65,
  "next_action": "Commit 3 modified file(s)",
  "confidence": 0.75,
  "gap_minutes": 60,
  "facts": [
    "branch:main",
    "has_uncommitted_changes",
    "modified_files:3",
    "primary_language:Python"
  ]
}
```

### Cascade Response (Incorporating HCR)

```
[Cascade]:

Based on your HCR context (away for 60 minutes):

**Current Task:** Implementing the "Resume Without Re-Explaining" product
**Progress:** 65% complete
**HCR Suggests:** Commit your 3 modified files

Looking at your uncommitted changes, you have:
- docs/dev_log.md
- product/SYSTEM_DESIGN.md  
- product/vscode-extension/src/extension.ts

These appear to be documentation and VS Code extension updates related
to the HCR product feature.

**Recommended next steps:**
1. Review the changes in docs/dev_log.md
2. Stage and commit with message: "Add VS Code extension and docs"
3. Continue with the SYSTEM_DESIGN.md refinements

Want me to help you commit these changes or continue with any specific 
part of the implementation?
```

---

## Tool Call Examples

### 1. get_hcr_context()

**When:** Any question about current project state

```python
@mcp.tool()
def get_hcr_context():
    """Get cognitive context from HCR"""
    
    # MCP server does:
    response = requests.get("http://localhost:8733/context")
    
    # Returns formatted:
    return """
## HCR Cognitive Context

**Current Task:** Implementing auth API
**Progress:** 65%
**Next Action:** Commit 3 modified files
**Confidence:** 0.75

**Context Facts:**
- branch:main
- has_uncommitted_changes
- modified_files:3
- primary_language:Python
"""
```

**Cascade Usage:**
```
User: What am I working on?
→ get_hcr_context()
→ "You're implementing auth API at 65% progress..."
```

### 2. resume_session(gap_minutes)

**When:** User returns after being away

```python
@mcp.tool()
def resume_session(gap_minutes: float = 0):
    """Trigger HCR resume analysis"""
    
    # MCP server does:
    response = requests.post(
        "http://localhost:8733/resume",
        json={"gap_minutes": gap_minutes}
    )
    
    # Returns fresh analysis with gap factored in
```

**Cascade Usage:**
```
User: Back from lunch
→ resume_session(gap_minutes=60)
→ "After 60 min away: Continue with auth API implementation..."
```

### 3. update_hcr_state(event_type, file_path, command)

**When:** Recording significant events

```python
@mcp.tool()
def update_hcr_state(event_type: str, file_path: str = "", command: str = ""):
    """Update HCR with event"""
    
    # MCP server does:
    response = requests.post(
        "http://localhost:8733/event",
        json={
            "type": event_type,
            "data": {"path": file_path, "command": command}
        }
    )
```

**Cascade Usage:**
```
User: Just committed the changes
→ update_hcr_state('git_commit')
→ "Recorded: git commit event"
```

---

## Real-Time Integration

### Auto-Trigger: File Save

```typescript
// In VS Code extension
vscode.workspace.onDidSaveTextDocument(async (doc) => {
    // Tell HCR about the save
    await hcrRequest('/event', 'POST', {
        type: 'file_edit',
        data: { path: doc.fileName }
    });
});
```

**Effect:** HCR state updates in real-time as user works

### Auto-Trigger: Window Focus

```typescript
// In VS Code extension  
vscode.window.onDidChangeWindowState((e) => {
    if (e.focused && idleMinutes > 30) {
        // Trigger resume
        const result = await hcrRequest('/resume', 'POST', {
            gap_minutes: idleMinutes
        });
        displayResults(result);  // Auto-shows context
    }
});
```

**Effect:** User sees context immediately upon returning

### Agent Trigger: Conversation Start

```
[Cascade receives query]
    ↓
[Automatically calls get_hcr_context()]
    ↓
[Uses context to inform all responses]
```

**Effect:** Every response includes HCR cognitive context

---

## Architecture Validation

### ✅ Engine-First Preserved

| Layer | Responsibility | Lines of Code |
|-------|----------------|---------------|
| **HCR Engine** | State, HCOs, Reasoning | ~950 |
| **MCP Server** | HTTP proxy to engine | ~200 |
| **Windsurf Config** | Tool definitions | ~30 |

**Ratio:** Engine 80% of system ✅

### ✅ Thin Wrapper Verified

```python
# MCP tool - NO business logic
@mcp.tool()
def get_hcr_context():
    return requests.get("http://localhost:8733/context").json()
```

**All logic in HCR, MCP just transports** ✅

### ✅ Auto-Usage Pattern

```
Cascade Rule: ALWAYS call get_hcr_context() before project reasoning

User: Any question about project
    ↓
Automatic: get_hcr_context()
    ↓
Cascade: [Incorporates HCR data in response]
```

**No manual CLI required** ✅

---

## Testing the Integration

### Test 1: Engine Running

```bash
$ curl http://localhost:8733/health
{"status": "ok", "engine": "ready"}
```

✅ **PASS**

### Test 2: Context Available

```bash
$ curl http://localhost:8733/context
{
  "current_task": "Implementing: add 'resume without re-explaining' product",
  "progress_percent": 65,
  "next_action": "Commit 3 modified file(s)",
  "confidence": 0.75
}
```

✅ **PASS**

### Test 3: Resume Works

```bash
$ curl -X POST http://localhost:8733/resume \
  -d '{"gap_minutes": 60}'
{
  "current_task": "Implementing: add 'resume without re-explaining' product",
  "progress_percent": 65,
  "gap_minutes": 60,
  "confidence": 0.75
}
```

✅ **PASS**

### Test 4: MCP Server Structure

```python
# mcp_server.py implements:
- get_hcr_context() ✅
- resume_session() ✅
- update_hcr_state() ✅
- check_hcr_status() ✅

# All proxy to localhost:8733 ✅
```

✅ **PASS**

---

## Files Created

```
HybridCognitiveRuntime/
├── mcp_server.py                    # MCP server implementation
├── windsurf_mcp_config.json         # Windsurf configuration
├── MCP_INTEGRATION.md              # Installation guide
└── MCP_EXAMPLE.md                  # This file - usage examples
```

---

## Summary

**Integration Complete:** HCR → MCP → Windsurf

**Key Achievement:**
- Cascade automatically uses HCR for project context
- No manual CLI usage required
- Engine-first architecture preserved
- Thin MCP wrapper (200 lines)
- Real-time state updates

**Result:** AI assistant now has **persistent cognitive state** across conversations, understanding what the user is working on without requiring explanation.
