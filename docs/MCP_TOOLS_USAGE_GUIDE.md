# HCR MCP Tools - AI IDE Global Rules

**Version:** 1.0.0  
**Last Updated:** 2026-05-01  
**Purpose:** System rules for AI IDEs (Cursor, Windsurf/Cascade, Claude Desktop) to use HCR MCP tools

---

## CORE RULES (Apply to All Conversations)

### Conversation Start Workflow
```
1. Call hcr_capture_full_context(include_diffs=false, use_llm=false)
   - If timeout/error: Retry once with use_llm=false
   - If still fails: Check if HCR server is available (hcr_get_system_health)
   - If server unavailable: Fallback to asking user for context
2. Call hcr_get_current_task(use_llm=false)
   - If timeout/error: Retry once
   - If still fails: Fallback to analyzing git history and recent files
3. Call hcr_get_next_action(use_llm=false)
   - If timeout/error: Retry once
   - If still fails: Proceed with user's request without suggestion
4. If HCR tools succeeded: Display context summary to user
5. If HCR tools completely unavailable: Inform user "HCR unavailable, working without context" but proceed normally
```

### File Edit Workflow
```
After EVERY file edit:
1. Call hcr_record_file_edit(filepath, old_content, change_summary)
2. Provide old_content for AST analysis if available
3. If old_content unavailable, provide functions_changed and imports_changed manually
4. This is CRITICAL - never skip this step
```

### General Principles
- State-first: Always check HCR state before making assumptions
- Non-blocking: Most tools timeout at 3-5s - never wait longer
- Session-aware: Use session_id for multi-pane IDE scenarios
- Incremental: Build context gradually; don't fetch everything at once
- Cache-aware: Respect cache durations to avoid redundant calls
- **HCR-priority:** Always prefer HCR context over inference. Retry failed tools once before fallback. Only fallback if tool unavailable or repeated failures.

---

## TOOL-SPECIFIC RULES

### State Management Tools

#### hcr_get_state
**When to call:** Conversation start, after major changes, debugging context
**Parameters:** include_history=false (default), session_id (optional for multi-pane)
**Timeout:** 5s
**Cache:** 60s
**Priority:** HIGH

#### hcr_get_causal_graph
**When to call:** Before refactoring, architecture analysis, dependency visualization
**Parameters:** graph_name="main" (default)
**Timeout:** 5s
**Cache:** 60s
**Priority:** MEDIUM

#### hcr_get_recent_activity
**When to call:** Resume after break, activity summaries, understanding recent changes
**Parameters:** limit=10 (default), session_id (optional)
**Timeout:** 5s
**Cache:** 30s
**Priority:** MEDIUM

---

### Task & Action Tools

#### hcr_get_current_task
**When to call:** Conversation start, user asks "what was I doing?", resume workflows
**Parameters:** use_llm=false (default for speed), session_id (optional)
**Timeout:** 3s (use_llm=false), 10s (use_llm=true)
**Cache:** 30s
**Priority:** HIGH

#### hcr_get_next_action
**When to call:** User asks "what should I do next?", after task completion, workflow suggestions
**Parameters:** use_llm=false (default), session_id (optional)
**Timeout:** 3s (use_llm=false), 10s (use_llm=true)
**Cache:** 30s
**Priority:** MEDIUM

---

### Session Management Tools

#### hcr_create_session
**When to call:** New IDE pane/context creation, parallel task isolation
**Parameters:** session_id (required), tag="untitled" (default), clone_from="" (default), use_llm=false (default)
**Timeout:** 3s (use_llm=false), 10s (use_llm=true)
**Cache:** None
**Priority:** MEDIUM

#### hcr_set_session_note
**When to call:** Remember session-specific context, temporary notes before merge
**Parameters:** session_id (required), note (required)
**Timeout:** 2s
**Cache:** None
**Priority:** LOW

#### hcr_merge_session
**When to call:** Session close, pane close, persisting session insights
**Parameters:** session_id (required), preserve_notes=true (default)
**Timeout:** 5s
**Cache:** None
**Priority:** MEDIUM

#### hcr_list_sessions
**When to call:** Multi-pane scenario management, debugging session issues
**Parameters:** none
**Timeout:** 2s
**Cache:** None
**Priority:** MEDIUM

---

### Shared State Tools

#### hcr_share_state
**When to call:** Share configuration across projects, setup integrations
**Parameters:** key (required), value (required, any JSON type)
**Timeout:** 5s
**Cache:** None
**Priority:** LOW

#### hcr_get_shared_state
**When to call:** Access cross-project configuration, integration setup
**Parameters:** key (required)
**Timeout:** 5s
**Cache:** None
**Priority:** LOW

#### hcr_list_shared_states
**When to call:** Discover available shared keys, setup integrations
**Parameters:** none
**Timeout:** 5s
**Cache:** 60s
**Priority:** LOW

---

### Version Control Tools

#### hcr_get_version_history
**When to call:** Debug state corruption, audit trails, understand state evolution
**Parameters:** limit=20 (default)
**Timeout:** 5s
**Cache:** 60s
**Priority:** LOW

#### hcr_restore_version
**When to call:** UNDO state corruption, roll back problematic changes (DESTRUCTIVE)
**Parameters:** version_hash (required from hcr_get_version_history)
**Timeout:** 5s
**Cache:** None
**Priority:** CRITICAL (requires user confirmation)

---

### System & Health Tools

#### hcr_get_system_health
**When to call:** Debug HCR issues, system monitoring, verify installation
**Parameters:** none
**Timeout:** 5s
**Cache:** 60s
**Priority:** LOW

---

### File & Context Tools

#### hcr_record_file_edit
**When to call:** AFTER EVERY FILE EDIT (CRITICAL - never skip)
**Parameters:** filepath (required), old_content (optional but recommended), change_summary (optional), lines_added (default 0), lines_removed (default 0), functions_changed (default []), imports_changed (default []), session_id (optional)
**Timeout:** 5s
**Cache:** None
**Priority:** CRITICAL

#### hcr_capture_full_context
**When to call:** Conversation start (preferred over sequential calls), resume after long breaks
**Parameters:** include_diffs=false (default), use_llm=false (default), session_id (optional)
**Timeout:** 5s (parallel operations)
**Cache:** None
**Priority:** HIGH

---

### Analysis & Search Tools

#### hcr_analyze_impact
**When to call:** Before refactoring, assess change risk, dependency analysis
**Parameters:** file_path (required), max_depth=3 (default, range 1-5)
**Timeout:** 5s
**Cache:** 60s
**Priority:** MEDIUM

#### hcr_get_recommendations
**When to call:** User asks for suggestions, workflow optimization, discover improvements
**Parameters:** context (optional), use_llm=true (default)
**Timeout:** 10s (use_llm=true), 3s (use_llm=false)
**Cache:** 30s
**Priority:** LOW

#### hcr_get_learned_operators
**When to call:** Discover reasoning patterns, setup new projects, understand capabilities
**Parameters:** none
**Timeout:** 5s
**Cache:** 60s
**Priority:** LOW

#### hcr_search_history
**When to call:** Find past work on files, debug historical issues, activity audits
**Parameters:** query (required), event_type (optional), limit=20 (default)
**Timeout:** 5s
**Cache:** None
**Priority:** LOW

---

## PARAMETER REFERENCE TABLE

| Tool | Required | Optional | Defaults |
|------|----------|----------|----------|
| hcr_get_state | - | include_history, session_id | include_history=false |
| hcr_get_causal_graph | - | graph_name | graph_name="main" |
| hcr_get_recent_activity | - | limit, session_id | limit=10 |
| hcr_get_current_task | - | use_llm, session_id | use_llm=false |
| hcr_get_next_action | - | use_llm, session_id | use_llm=false |
| hcr_list_shared_states | - | - | - |
| hcr_get_shared_state | key | - | - |
| hcr_share_state | key, value | - | - |
| hcr_get_version_history | - | limit | limit=20 |
| hcr_restore_version | version_hash | - | - |
| hcr_get_learned_operators | - | - | - |
| hcr_list_sessions | - | - | - |
| hcr_create_session | session_id | tag, clone_from, use_llm | tag="untitled", clone_from="", use_llm=false |
| hcr_set_session_note | session_id, note | - | - |
| hcr_merge_session | session_id | preserve_notes | preserve_notes=true |
| hcr_get_system_health | - | - | - |
| hcr_record_file_edit | filepath | old_content, change_summary, lines_added, lines_removed, functions_changed, imports_changed, session_id | lines_added=0, lines_removed=0, functions_changed=[], imports_changed=[] |
| hcr_capture_full_context | - | include_diffs, use_llm, session_id | include_diffs=false, use_llm=false |
| hcr_analyze_impact | file_path | max_depth | max_depth=3 |
| hcr_get_recommendations | - | context, use_llm | use_llm=true |
| hcr_search_history | query | event_type, limit | event_type="", limit=20 |

---

## OUTPUT SCHEMA REFERENCE

### Success Pattern
```json
{
  "content": "markdown_string",
  "success": true,
  "...": "tool_specific"
}
```

### Error Pattern
```json
{
  "error": "message",
  "success": false
}
```

### Boolean Check
```json
{
  "exists": true/false,
  "...": "data"
}
```

### List Pattern
```json
{
  "items": [...],
  "count": N
}
```
