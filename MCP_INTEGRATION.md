# HCR MCP Integration for Windsurf

Connects Hybrid Cognitive Runtime (HCR) to Windsurf AI agent (Cascade) via MCP.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Windsurf IDE   │────▶│   MCP Server    │────▶│   HCR Engine    │
│   (Cascade)     │     │ (mcp_server.py) │     │ (localhost:8733)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │  State File     │
                    │ (.hcr/state)    │
                    └─────────────────┘
```

**Data Flow:**
```
Cascade asks about project
    ↓
Automatically calls get_hcr_context()
    ↓
MCP server queries HCR HTTP API
    ↓
HCR returns task, progress, next_action
    ↓
Cascade uses this context in response
```

## Installation

### Step 1: Start HCR Engine Server

```bash
# In your project directory
python -m product.cli.resume --server --project .
```

Verify it's running:
```bash
curl http://localhost:8733/health
# {"status": "ok", "engine": "ready"}
```

### Step 2: Install MCP Server

```bash
# Copy MCP server to Python path
cp mcp_server.py ~/.local/lib/python3.x/site-packages/hcr_mcp_server.py

# Or create symlink
ln -s $(pwd)/mcp_server.py ~/.local/lib/python3.x/site-packages/hcr_mcp_server.py
```

### Step 3: Configure Windsurf

Edit Windsurf MCP config:
```bash
# Windows
notepad %USERPROFILE%\.codeium\windsurf\mcp_config.json

# macOS/Linux
nano ~/.codeium/windsurf/mcp_config.json
```

Add HCR configuration:
```json
{
  "mcpServers": {
    "hcr": {
      "command": "python",
      "args": ["-m", "hcr_mcp_server"],
      "transport": "stdio",
      "env": {
        "HCR_HOST": "localhost",
        "HCR_PORT": "8733"
      }
    }
  }
}
```

### Step 4: Restart Windsurf

Close and reopen Windsurf to load the MCP server.

## Available Tools

### get_hcr_context()

**Purpose:** Get current cognitive context

**Returns:**
- Current task
- Progress percentage
- Next suggested action
- Confidence score
- Context facts

**When to use:** Before answering any project-related question

**Example:**
```
User: What should I work on?
→ get_hcr_context()
← Current Task: Implementing auth API
  Progress: 65%
  Next Action: Commit 3 modified files
→ Response based on this context
```

### resume_session(gap_minutes: float)

**Purpose:** Trigger full HCR analysis

**Args:**
- `gap_minutes`: Time since last activity (affects confidence)

**Returns:** Fresh analysis after running HCOs

**When to use:**
- User returns after being away
- Context seems stale
- Need to refresh reasoning

**Example:**
```
User: I'm back from lunch
→ resume_session(gap_minutes=60)
← Fresh analysis with 60-min gap factored in
```

### update_hcr_state(event_type, file_path, command)

**Purpose:** Record events to keep state current

**Args:**
- `event_type`: 'file_edit', 'git_commit', 'terminal'
- `file_path`: File being edited (optional)
- `command`: Command being run (optional)

**When to use:**
- After significant file edits
- After git operations
- After running important commands

**Example:**
```
User: I just committed the changes
→ update_hcr_state('git_commit')
← State updated: git_commit event recorded
```

### check_hcr_status()

**Purpose:** Verify HCR is running

**Returns:** Engine status and current context summary

**When to use:** Diagnostics, initial check

## Agent Usage Guidelines

### For Cascade (Windsurf Agent)

**Rule: ALWAYS check HCR before reasoning about project state**

**Pattern:**
```
User query about project
    ↓
Call get_hcr_context()
    ↓
Incorporate into response:
    - Acknowledge current task
    - Reference progress
    - Use HCR's next_action suggestion
    - Add your own analysis on top
```

**Example Interaction:**

```
[User]: What should I work on next?

[Cascade]:
→ get_hcr_context()

[HCR Returns]:
Current Task: Implementing user authentication API
Progress: 65%
Next Action: Commit 3 modified files
Confidence: 0.85

[Cascade Response]:
Based on your HCR context, you're implementing the auth API 
at 65% progress. HCR suggests committing your 3 modified files.

Looking at the files, you have changes in:
- src/middleware/auth.ts
- src/routes/user.ts  
- tests/auth.test.ts

I recommend:
1. Review the changes in auth.ts
2. Run tests to verify
3. Commit with message: "Add JWT validation"

Want me to help with any of these steps?
```

## Validation Checklist

- [ ] HCR engine running on localhost:8733
- [ ] MCP server installed and accessible
- [ ] Windsurf config includes HCR server
- [ ] Cascade calls get_hcr_context() automatically
- [ ] Responses include HCR cognitive context
- [ ] No manual CLI usage required

## Troubleshooting

### "HCR engine not running"

**Solution:**
```bash
python -m product.cli.resume --server --project <path>
```

### "MCP server not found"

**Solution:**
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Copy mcp_server.py to one of those locations
cp mcp_server.py <path>/hcr_mcp_server.py
```

### "Connection refused"

**Solution:**
- Verify port 8733 is not blocked
- Check HCR server is actually running: `curl http://localhost:8733/health`
- Restart Windsurf after config changes

## Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server implementation |
| `windsurf_mcp_config.json` | Example Windsurf config |
| `MCP_INTEGRATION.md` | This documentation |

## Architecture Principles

1. **Engine-First:** HCR remains the core, MCP is just another interface
2. **Thin Wrapper:** MCP server only proxies to HCR HTTP API
3. **No Duplication:** All logic stays in HCR engine
4. **Auto-Usage:** Cascade automatically uses HCR for project context
5. **Stateful:** MCP doesn't maintain state - HCR does

## Next Steps

1. Install MCP server
2. Configure Windsurf
3. Restart IDE
4. Ask Cascade: "What am I working on?"
5. Verify HCR context appears in response
