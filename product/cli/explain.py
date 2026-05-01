"""
HCR Explain Command

Shows what memory/context was injected and why.
This builds trust by making the invisible system visible.

Usage:
    hcr explain          # Show current context injection
    hcr explain --full   # Show all available context (not just injected)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine_api import HCREngine


def run_explain(project_path: str, full: bool = False) -> str:
    """Generate explanation of current HCR context injection"""
    engine = HCREngine(project_path)
    engine.load_state()
    
    if not engine._current_state:
        return """## HCR Explain

No state found. Run `hcr init` first."""
    
    state = engine._current_state
    
    # Build injection explanation
    lines = ["## HCR Context Injection Explanation\n"]
    
    # 1. Meta state (confidence, timestamp)
    lines.append("### What Was Injected\n")
    if hasattr(state, 'meta'):
        lines.append(f"**State Confidence:** {state.meta.confidence:.0%}")
        lines.append(f"**Last Updated:** {state.meta.timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(state.meta.timestamp, 'strftime') else str(state.meta.timestamp)[:16]}")
    else:
        lines.append("**State Confidence:** N/A")
    lines.append("")
    
    # 2. Facts (recent, pinned)
    facts = state.symbolic.facts[-10:] if state.symbolic.facts else []
    pinned = getattr(state.symbolic, 'pinned_facts', [])
    
    lines.append(f"**Facts Used:** {len(facts)} (of {len(state.symbolic.facts)} total)")
    if pinned:
        lines.append(f"**Pinned Facts:** {len(pinned)}")
    lines.append("")
    
    # 3. Files/Dependencies
    deps = state.causal.dependencies if hasattr(state.causal, 'dependencies') else []
    lines.append(f"**Dependencies Tracked:** {len(deps)}")
    lines.append("")
    
    # 4. Why these were selected
    lines.append("### Why These Were Selected\n")
    lines.append("1. **Current task** - Highest priority (explicit user intent)")
    lines.append("2. **Recent facts** - Last 10 facts (recency signal)")
    if pinned:
        lines.append("3. **Pinned facts** - User explicitly pinned (manual control)")
    lines.append(f"4. **Dependencies** - Files linked to current task (causal signal)")
    lines.append("")
    
    # 5. Token count estimate
    token_estimate = len(json.dumps(state.to_dict())) // 4  # rough estimate
    lines.append(f"**Estimated Tokens:** ~{token_estimate}")
    lines.append(f"**Token Budget:** 200 max (enforced)")
    lines.append("")
    
    # 6. What was skipped (if --full)
    if full:
        lines.append("### What Was NOT Injected (Full Context)\n")
        lines.append(f"**Total Facts Available:** {len(state.symbolic.facts)}")
        lines.append(f"**Total Events:** {len(engine.event_store.events)}")
        lines.append(f"**Total Dependencies:** {len(state.causal.dependencies) if hasattr(state.causal, 'dependencies') else 0}")
        lines.append("")
        lines.append("**Skipped (not relevant to current task):**")
        old_facts = state.symbolic.facts[:-10] if len(state.symbolic.facts) > 10 else []
        for f in old_facts[-5:]:
            lines.append(f"- {f[:80]}...")
        lines.append("")
    
    # 7. Manual control hints
    lines.append("### Manual Control\n")
    lines.append("```bash")
    lines.append("hcr pin \"Important fact to always include\"")
    lines.append("hcr forget <fact_id>      # Remove specific fact")
    lines.append("hcr reset                 # Clear session state")
    lines.append("```")
    lines.append("")
    
    # 8. If something looks wrong
    lines.append("**Something wrong?** Run `hcr forget` to remove incorrect context, or `hcr reset` to start fresh.")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HCR Explain - Show injected context")
    parser.add_argument("--project", default=".")
    parser.add_argument("--full", action="store_true", help="Show all available context")
    args = parser.parse_args()
    
    print(run_explain(args.project, args.full))
