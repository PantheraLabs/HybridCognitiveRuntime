"""
HCR Resume Command

Main entry point for "Resume Without Re-Explaining" feature.

Usage:
    python -m product.cli.resume [options]
    
    Options:
        --auto           Auto-triggered mode (suppresses interactive prompts)
        --save           Save current state after analysis
        --format FORMAT  Output format: text, json (default: text)

Examples:
    # Manual resume
    python -m product.cli.resume
    
    # Auto-triggered from VS Code on window focus
    python -m product.cli.resume --auto --format json
    
    # Save state for next session
    python -m product.cli.resume --save
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from product.storage import DevStatePersistence, get_project_root
from product.state_capture import GitTracker, FileWatcher
from product.hco_wrappers import DevContextEngine


def format_output_text(analysis: Dict[str, Any], gap_minutes: Optional[float]) -> str:
    """Format analysis output as readable text"""
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("  HCR SESSION RESUME")
    lines.append("=" * 60)
    
    # Time gap info
    if gap_minutes is not None:
        if gap_minutes < 1:
            lines.append(f"\n⏱️  Last active: Just now")
        elif gap_minutes < 60:
            lines.append(f"\n⏱️  Last active: {int(gap_minutes)} minutes ago")
        else:
            hours = int(gap_minutes / 60)
            lines.append(f"\n⏱️  Last active: {hours} hour(s) ago")
    
    # Task info
    task = analysis.get("current_task", "Unknown")
    progress = analysis.get("progress_percent", 0)
    
    lines.append(f"\n📋 Current Task:")
    lines.append(f"   {task}")
    lines.append(f"\n📊 Progress: {progress}%")
    
    # Progress bar
    filled = int(progress / 5)  # 20 segments
    bar = "█" * filled + "░" * (20 - filled)
    lines.append(f"   [{bar}]")
    
    # Next action
    next_action = analysis.get("next_action", "Continue working")
    lines.append(f"\n👉 Next Action:")
    lines.append(f"   {next_action}")
    
    # Confidence
    confidence = analysis.get("confidence", 0.5)
    if confidence > 0.7:
        lines.append(f"\n✅ High confidence in this assessment")
    elif confidence > 0.4:
        lines.append(f"\n⚠️  Moderate confidence - verify this makes sense")
    else:
        lines.append(f"\n❓ Low confidence - please clarify what you're working on")
    
    # Context details (if relevant)
    facts = analysis.get("relevant_facts", [])
    if facts:
        lines.append(f"\n📝 Context:")
        for fact in facts[:5]:  # Show top 5
            lines.append(f"   • {fact}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)


def format_output_json(analysis: Dict[str, Any], gap_minutes: Optional[float]) -> str:
    """Format analysis output as JSON"""
    import json
    
    output = {
        "session_resume": {
            "gap_minutes": gap_minutes,
            "current_task": analysis.get("current_task"),
            "progress_percent": analysis.get("progress_percent"),
            "next_action": analysis.get("next_action"),
            "confidence": analysis.get("confidence"),
            "uncertainty": analysis.get("uncertainty"),
            "context_facts": analysis.get("relevant_facts", [])[:5]
        }
    }
    
    return json.dumps(output, indent=2)


def run_resume(auto_mode: bool = False, save: bool = True, output_format: str = "text") -> Dict[str, Any]:
    """
    Main resume logic.
    
    Args:
        auto_mode: If True, suppress interactive prompts
        save: If True, save current state for future sessions
        output_format: 'text' or 'json'
        
    Returns:
        Analysis results dictionary
    """
    # Get project root
    project_path = get_project_root()
    
    # Initialize persistence
    persistence = DevStatePersistence(project_path)
    
    # Load previous state
    previous_state = persistence.load_state()
    
    # Calculate time gap
    gap_minutes = persistence.get_gap_duration()
    
    # Capture current context
    git_tracker = GitTracker(project_path)
    file_watcher = FileWatcher(project_path)
    
    git_state = git_tracker.capture_state()
    file_state = file_watcher.capture_state(lookback_minutes=120)  # Last 2 hours
    
    # Run HCR analysis
    engine = DevContextEngine()
    analysis = engine.analyze_context(git_state, file_state, previous_state)
    
    # Add gap info to analysis
    analysis["gap_minutes"] = gap_minutes
    analysis["project_path"] = str(project_path)
    
    # Save state if requested
    if save:
        state_to_save = {
            "analysis": analysis,
            "git_state": git_state,
            "file_state": file_state,
            "captured_at": analysis.get("captured_at", "")
        }
        persistence.save_state(state_to_save)
    
    return analysis, gap_minutes


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HCR Resume - Resume your development session without re-explaining",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m product.cli.resume              # Standard resume
  python -m product.cli.resume --auto       # Auto-triggered mode
  python -m product.cli.resume --format json # JSON output
        """
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-triggered mode (suppresses interactive prompts)"
    )
    
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save current state after analysis (default: True)"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    args = parser.parse_args()
    
    try:
        # Run resume
        analysis, gap_minutes = run_resume(
            auto_mode=args.auto,
            save=args.save,
            output_format=args.format
        )
        
        # Format output
        if args.format == "json":
            output = format_output_json(analysis, gap_minutes)
        else:
            output = format_output_text(analysis, gap_minutes)
        
        print(output)
        
        # Exit code based on confidence
        confidence = analysis.get("confidence", 0)
        if confidence < 0.3:
            sys.exit(2)  # Low confidence
        elif confidence < 0.6:
            sys.exit(1)  # Moderate confidence
        else:
            sys.exit(0)  # High confidence
            
    except Exception as e:
        print(f"[HCR] Error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
