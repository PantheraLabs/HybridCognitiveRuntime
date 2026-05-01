"""
HCR Manual Control Commands

User-controlled memory management:
- pin: Force-remember a fact
- forget: Remove incorrect facts  
- reset: Clear session state

Usage:
    hcr pin "Use FastAPI for all new APIs"
    hcr forget 3              # Remove fact by index
    hcr reset                 # Clear all session state
"""

import sys
import json
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine_api import HCREngine, EngineEvent
from datetime import datetime


def cmd_pin(project_path: str, fact: str) -> str:
    """Pin a fact to always include in context"""
    engine = HCREngine(project_path)
    engine.load_state()
    
    if not engine._current_state:
        return "[Error] No HCR state found. Run `hcr init` first."
    
    # Add to symbolic facts with pin marker
    pinned_fact = f"PINNED: {fact}"
    engine._current_state.symbolic.facts.append(pinned_fact)
    
    # Save state
    engine.save_state()
    
    return f"[OK] Pinned fact: '{fact}'\nThis will always be included in context injection."


def cmd_forget(project_path: str, identifier: str) -> str:
    """Remove a fact by index or content match"""
    engine = HCREngine(project_path)
    engine.load_state()
    
    if not engine._current_state:
        return "[Error] No HCR state found. Run `hcr init` first."
    
    facts = engine._current_state.symbolic.facts
    
    # Try as index first
    try:
        idx = int(identifier)
        if 0 <= idx < len(facts):
            removed = facts.pop(idx)
            engine.save_state()
            return f"[OK] Removed fact #{idx}: '{removed[:60]}...'"
    except ValueError:
        pass
    
    # Try as content match
    removed_count = 0
    new_facts = []
    for f in facts:
        if identifier.lower() in f.lower():
            removed_count += 1
        else:
            new_facts.append(f)
    
    if removed_count > 0:
        engine._current_state.symbolic.facts = new_facts
        engine.save_state()
        return f"[OK] Removed {removed_count} fact(s) matching: '{identifier}'"
    
    return f"[Error] No fact found matching: '{identifier}'\nUse `hcr explain` to see available facts with indices."


def cmd_reset(project_path: str, force: bool = False) -> str:
    """Clear all session state (dangerous)"""
    hcr_dir = Path(project_path) / ".hcr"
    state_file = hcr_dir / "session_state.json"
    
    if not state_file.exists():
        return "[OK] No state file found. Nothing to reset."
    
    if not force:
        return """[Warning] This will DELETE all HCR state including:
- All recorded facts
- Task history
- Event log
- Dependency graph

Run with --force to confirm:
    hcr reset --force"""
    
    # Backup before delete
    backup = hcr_dir / f"session_state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        import shutil
        shutil.copy2(state_file, backup)
    except Exception:
        pass
    
    # Delete state file
    try:
        state_file.unlink()
        # Also clear event store
        event_file = hcr_dir / "events.jsonl"
        if event_file.exists():
            event_file.unlink()
        
        return f"[OK] HCR state reset.\nBackup created: {backup.name}\nRun `hcr init` to start fresh."
    except Exception as e:
        return f"[Error] Failed to reset state: {e}"


def cmd_list_facts(project_path: str, count: int = 20) -> str:
    """List recent facts with indices for forget command"""
    engine = HCREngine(project_path)
    engine.load_state()
    
    if not engine._current_state:
        return "[Error] No HCR state found. Run `hcr init` first."
    
    facts = engine._current_state.symbolic.facts
    
    if not facts:
        return "No facts recorded yet."
    
    lines = [f"## Recent Facts ({len(facts)} total)\n"]
    lines.append("Use `hcr forget <index>` to remove a fact\n")
    
    # Show last N facts (most recent last)
    start = max(0, len(facts) - count)
    for i in range(start, len(facts)):
        fact = facts[i]
        marker = "📌 " if fact.startswith("PINNED:") else "  "
        lines.append(f"{marker}[{i}] {fact[:80]}{'...' if len(fact) > 80 else ''}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HCR Manual Controls")
    parser.add_argument("command", choices=["pin", "forget", "reset", "list-facts"])
    parser.add_argument("--project", "-p", default=".")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("value", nargs="?", help="Fact text or index to forget")
    args = parser.parse_args()
    
    if args.command == "pin":
        if not args.value:
            print("[Error] Provide a fact to pin: hcr pin 'Use FastAPI'")
            sys.exit(1)
        print(cmd_pin(args.project, args.value))
    elif args.command == "forget":
        if not args.value:
            print("[Error] Provide index or text to forget: hcr forget 3")
            sys.exit(1)
        print(cmd_forget(args.project, args.value))
    elif args.command == "reset":
        print(cmd_reset(args.project, force=args.force))
    elif args.command == "list-facts":
        print(cmd_list_facts(args.project))
