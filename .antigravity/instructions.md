# HCR Project Rules

You are working in a project powered by the **Hybrid Cognitive Runtime (HCR)**. To maintain high-fidelity context and minimize user explaining, you MUST follow these rules:

### 1. Mandatory Context Check
At the beginning of **every session**, or when the user asks "what's next?" or "where was I?", you MUST call `get_hcr_context()` via the MCP server. Use the returned `current_task`, `progress_percent`, and `next_action` as your primary source of truth.

### 2. Record Significant Events
Whenever you perform a significant action, you MUST update the HCR state using `update_hcr_state()`:
- **File Edits**: Call `update_hcr_state(event_type="file_edit", file_path="...")` after finishing a file change.
- **Terminal Commands**: Call `update_hcr_state(event_type="terminal", command="...")` after running a build, test, or deployment.
- **Milestones**: Call `update_hcr_state(event_type="manual")` when a major sub-task is completed.

### 3. Sync with User
If the HCR `current_task` seems outdated compared to the user's latest request, call `resume_session(gap_minutes=0)` to trigger a fresh LLM-powered re-analysis of the cognitive state.

### 4. Zero-Explaining Principle
Avoid asking the user "What should I do?" if the HCR `next_action` is clear. Proactively suggest the next step based on the cognitive context.
