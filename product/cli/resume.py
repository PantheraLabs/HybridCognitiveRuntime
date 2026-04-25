"""
HCR Resume Command

Thin CLI wrapper around HCR Engine API.
NO business logic here - just calls Engine API.

Usage:
    python -m product.cli.resume [options]
    
Options:
    --format FORMAT  Output format: text, json (default: text)
    --server         Start engine server instead of one-off command

Examples:
    # One-off resume (calls engine directly)
    python -m product.cli.resume
    
    # Start engine server (for IDE integration)
    python -m product.cli.resume --server
    
    # JSON output
    python -m product.cli.resume --format json
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine_api import HCREngine, EngineEvent
from src.engine_server import start_server, get_engine_status
from datetime import datetime


def format_output_text(context) -> str:
    """Format context as readable text"""
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("  HCR SESSION RESUME")
    lines.append("=" * 60)
    
    # Time gap
    gap = context.gap_minutes
    if gap is not None:
        if gap < 1:
            lines.append(f"\n[TIME] Last active: Just now")
        elif gap < 60:
            lines.append(f"\n[TIME] Last active: {int(gap)} minutes ago")
        else:
            hours = int(gap / 60)
            lines.append(f"\n[TIME] Last active: {hours} hour(s) ago")
    
    # Task
    lines.append(f"\n[TASK] {context.current_task}")
    lines.append(f"\n[PROGRESS] {context.progress_percent}%")
    
    # Progress bar
    filled = int(context.progress_percent / 5)
    bar = "#" * filled + "-" * (20 - filled)
    lines.append(f"           [{bar}]")
    
    # Action
    lines.append(f"\n[ACTION] {context.next_action}")
    
    # Confidence
    if context.confidence > 0.7:
        lines.append(f"\n[OK] High confidence")
    elif context.confidence > 0.4:
        lines.append(f"\n[!] Moderate confidence")
    else:
        lines.append(f"\n[?] Low confidence")
    
    # Context
    if context.facts:
        lines.append(f"\n[CONTEXT]")
        for fact in context.facts[:5]:
            lines.append(f"  - {fact}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)


def format_output_json(context) -> str:
    """Format context as JSON"""
    import json
    return json.dumps(context.to_dict(), indent=2)


def run_resume(project_path: str, output_format: str = "text") -> str:
    """
    Run resume using Engine API directly.
    
    Args:
        project_path: Path to project
        output_format: 'text' or 'json'
        
    Returns:
        Formatted output string
    """
    # Initialize engine
    engine = HCREngine(project_path)
    
    # Load existing state
    engine.load_state()
    
    # Simulate window focus event
    event = EngineEvent(
        event_type='window_focus',
        timestamp=datetime.now(),
        data={'gap_minutes': 0}
    )
    
    # Update state
    engine.update_from_environment(event)
    
    # Get context
    context = engine.infer_context()
    
    # Format output
    if output_format == "json":
        return format_output_json(context)
    else:
        return format_output_text(context)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HCR Resume - Thin CLI wrapper around Engine API"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start engine HTTP server for IDE integration"
    )
    
    parser.add_argument(
        "--project",
        default=str(Path.cwd()),
        help="Project path (default: current directory)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.server:
            # Start HTTP server
            print(f"[HCR] Starting engine server for: {args.project}")
            start_server(args.project)
        else:
            # One-off resume
            output = run_resume(args.project, args.format)
            print(output)
            
    except KeyboardInterrupt:
        print("\n[HCR] Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"[HCR Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
