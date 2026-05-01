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
import subprocess
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


def _ensure_daemon_running(project_path: str):
    """Auto-start daemon if not running - ensures background tracking"""
    try:
        from product.daemon.hcr_daemon import HCRDaemon
        daemon = HCRDaemon(project_path)
        
        if not daemon.is_already_running():
            popen_kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if creationflags:
                    popen_kwargs["creationflags"] = creationflags
            else:
                popen_kwargs["start_new_session"] = True
            try:
                subprocess.Popen(
                    [sys.executable, "-m", "product.daemon.hcr_daemon", "start", "--project", project_path],
                    **popen_kwargs
                )
            except OSError:
                popen_kwargs.pop("creationflags", None)
                popen_kwargs.pop("start_new_session", None)
                subprocess.Popen(
                    [sys.executable, "-m", "product.daemon.hcr_daemon", "start", "--project", project_path],
                    **popen_kwargs
                )
    except Exception:
        # Continue without daemon
        pass


def run_resume(project_path: str, output_format: str = "text") -> str:
    """
    Run resume using Engine API directly.
    
    Args:
        project_path: Path to project
        output_format: 'text' or 'json'
        
    Returns:
        Formatted output string
    """
    # Auto-start daemon for background tracking
    _ensure_daemon_running(project_path)
    
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


def _get_api_data(endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
    """Helper to get data from running engine server"""
    import requests
    try:
        url = f"http://localhost:8733{endpoint}"
        if method == "GET":
            r = requests.get(url, timeout=2)
        else:
            r = requests.post(url, json=data, timeout=2)
        
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def show_graph(project_path: str):
    """Visualize the causal graph using rich"""
    from rich.console import Console
    from rich.tree import Tree
    from rich.panel import Panel
    
    console = Console()
    
    # Try to get data from server
    data = _get_api_data("/causal_graph")
    
    if not data:
        # Fallback to local engine
        engine = HCREngine(project_path)
        engine.load_state()
        data = {
            "forward": {k: list(v) for k, v in engine.dependency_graph.forward_edges.items()},
            "reverse": {k: list(v) for k, v in engine.dependency_graph.reverse_edges.items()}
        }
    
    console.print(Panel("[bold cyan]Temporal Causal Graph[/bold cyan]", expand=False))
    
    if not data["forward"]:
        console.print("[yellow]Graph is empty. Edit some files to populate it![/yellow]")
        return
        
    # Build a tree visualization
    root_tree = Tree("[bold blue]Project Dependencies[/bold blue]")
    
    for node, deps in data["forward"].items():
        node_tree = root_tree.add(f"[green]{node}[/green]")
        for dep in deps:
            node_tree.add(f"[white]{dep}[/white]")
            
    console.print(root_tree)
    console.print("\n[bold blue]Impact Map (Reverse Edges):[/bold blue]")
    for node, impacts in data["reverse"].items():
        if impacts:
            console.print(f"  [cyan]{node}[/cyan] impacts -> [yellow]{', '.join(impacts)}[/yellow]")


def show_impact(project_path: str, file_path: str):
    """Show predicted impact of a change using rich"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    # Try to get data from server
    data = _get_api_data("/impact", method="POST", data={"file_path": file_path})
    
    if not data:
        # Fallback to local engine
        engine = HCREngine(project_path)
        engine.load_state()
        impacted = engine.impact_analyzer.predict_impact(file_path)
    else:
        impacted = data.get("impacted_files", [])
        
    console.print(Panel(f"[bold red]Impact Analysis: {file_path}[/bold red]", expand=False))
    
    if not impacted:
        console.print(f"[green]No immediate ripple effects predicted for {file_path}.[/green]")
        return
        
    table = Table(title="Predicted Affected Files")
    table.add_column("File Path", style="cyan")
    table.add_column("Relationship", style="magenta")
    
    for imp in impacted:
        table.add_row(imp, "Dependent")
        
    console.print(table)
    console.print(f"\n[bold yellow]Advice:[/bold yellow] Modifying [bold cyan]{file_path}[/bold cyan] might require updates to the [bold]{len(impacted)}[/bold] files listed above.")


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
    
    parser.add_argument(
        "--port",
        type=int,
        default=8733,
        help="HTTP server port when using --server"
    )
    
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Visualize the Temporal Causal Graph"
    )
    
    parser.add_argument(
        "--impact",
        metavar="FILE",
        help="Show predicted impact of modifying a specific file"
    )
    
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the visual Causal Dashboard in your browser"
    )
    
    args = parser.parse_args()
    
    try:
        if args.server:
            # Start HTTP server
            print(f"[HCR] Starting engine server for: {args.project}")
            start_server(args.project, args.port)
        elif args.dashboard:
            from src.web.dashboard import launch_dashboard
            launch_dashboard()
        elif args.graph:
            show_graph(args.project)
        elif args.impact:
            show_impact(args.project, args.impact)
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
