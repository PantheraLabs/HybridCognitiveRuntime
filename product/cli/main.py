"""
HCR CLI - Professional Developer Tool

Usage:
    hcr init              Initialize HCR in current project
    hcr resume            Resume session with context
    hcr daemon            Start background context capture
    hcr dashboard         Launch web dashboard
    hcr status            Check HCR engine status
    hcr setup-ide         Configure IDE integrations

Examples:
    # One-command setup (like docker init)
    hcr init --auto
    
    # Start background service
    hcr daemon install && hcr daemon start
    
    # Resume with full context
    hcr resume
"""

import sys
import os
import json
import argparse
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine_api import HCREngine
from src.engine_server import start_server, get_engine_status


@dataclass
class ProjectType:
    name: str
    indicators: List[str]
    rules: List[str]


# Auto-detection patterns
PROJECT_TYPES = [
    ProjectType("react", ["package.json", "vite.config", "next.config"], ["components/", "hooks/", "pages/"]),
    ProjectType("python", ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"], ["src/", "tests/"]),
    ProjectType("rust", ["Cargo.toml"], ["src/"]),
    ProjectType("go", ["go.mod"], ["cmd/", "pkg/"]),
    ProjectType("node", ["package.json"], ["node_modules/"]),
    ProjectType("generic", [], []),
]


def detect_project_type(project_path: str) -> ProjectType:
    """Detect project type from file signatures"""
    path = Path(project_path)
    
    for ptype in PROJECT_TYPES:
        for indicator in ptype.indicators:
            if list(path.glob(indicator)) or list(path.glob(f"**/{indicator}")):
                return ptype
    
    return PROJECT_TYPES[-1]  # generic


def print_banner():
    """Print HCR banner"""
    print("""
╭─────────────────────────────────────╮
│  HCR - Hybrid Cognitive Runtime       │
│  State-based developer context        │
╰─────────────────────────────────────╯
""")


def get_hcr_dir(project_path: str) -> Path:
    """Get .hcr directory path"""
    return Path(project_path) / ".hcr"


def get_mcp_config_paths() -> Dict[str, Path]:
    """Get MCP config paths for different IDEs"""
    home = Path.home()
    
    paths = {
        "windsurf": home / ".codeium" / "windsurf" / "mcp_config.json",
        "claude": None,  # Platform dependent
        "cursor": home / ".cursor" / "mcp.json",
    }
    
    # Claude Desktop paths (platform specific)
    if sys.platform == "darwin":
        paths["claude"] = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        paths["claude"] = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    else:
        paths["claude"] = home / ".config" / "Claude" / "claude_desktop_config.json"
    
    return {k: v for k, v in paths.items() if v}


def install_mcp_config(ide: str, project_path: str, mcp_server_path: str):
    """Install MCP config for a specific IDE"""
    paths = get_mcp_config_paths()
    
    if ide not in paths:
        print(f"  [Warning] Unknown IDE: {ide}")
        return False
    
    config_path = paths[ide]
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing or create new
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except:
            config = {}
    else:
        config = {}
    
    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add HCR server
    config["mcpServers"]["hcr"] = {
        "command": sys.executable,
        "args": ["-u", mcp_server_path, "--project", project_path],
        "env": {
            "HCR_PROJECT": project_path
        }
    }
    
    # Write config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"  [OK] {ide}: {config_path}")
    return True


def detect_installed_ides() -> List[str]:
    """Detect which IDEs are installed"""
    ides = []
    paths = get_mcp_config_paths()
    
    # Check if config directories exist (rough heuristic)
    for ide, path in paths.items():
        if path and path.parent.exists():
            ides.append(ide)
    
    # Additional checks
    if sys.platform == "darwin":
        # Check Applications folder
        apps = Path("/Applications")
        if (apps / "Windsurf.app").exists():
            if "windsurf" not in ides:
                ides.append("windsurf")
        if (apps / "Claude.app").exists():
            if "claude" not in ides:
                ides.append("claude")
    
    return ides


def launch_background_python(module_args: List[str]):
    """Launch a detached background Python process across platforms."""
    popen_kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        creationflags = 0
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen([sys.executable, *module_args], **popen_kwargs)


def cmd_init(args):
    """Initialize HCR in project - like 'docker init' or 'npm init'"""
    print_banner()
    
    project_path = Path(args.project).resolve()
    hcr_dir = get_hcr_dir(project_path)
    
    print(f"📁 Project: {project_path}")
    
    # Check if already initialized
    if hcr_dir.exists() and not args.force:
        print(f"\n[Warning] HCR already initialized (use --force to reinitialize)")
        print(f"   Config: {hcr_dir / 'config.yaml'}")
        return
    
    # Create .hcr directory
    hcr_dir.mkdir(exist_ok=True)
    print(f"\n📂 Created: {hcr_dir}")
    
    # Detect project type
    ptype = detect_project_type(project_path)
    print(f"🔍 Detected: {ptype.name} project")
    
    # Create config
    config = {
        "project": {
            "name": project_path.name,
            "path": str(project_path),
            "type": ptype.name,
        },
        "hcr": {
            "version": "0.1.0",
            "initialized": True,
        },
        "daemon": {
            "enabled": args.daemon,
            "watch_patterns": ["*.py", "*.ts", "*.js", "*.json"],
            "ignore_patterns": ["node_modules/", ".git/", "__pycache__/", ".hcr/"],
        },
        "mcp": {
            "enabled": True,
            "ides": [],
        }
    }
    
    config_path = hcr_dir / "config.yaml"
    with open(config_path, 'w') as f:
        import yaml
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"⚙️  Config: {config_path}")
    
    # Setup IDE integrations
    if args.setup_ide or args.auto:
        print("\n🖥️  Setting up IDE integrations...")
        
        mcp_server = Path(__file__).parent.parent.parent / "mcp_server_wrapper.py"
        
        if args.auto:
            # Auto-detect installed IDEs
            ides = detect_installed_ides()
            if ides:
                print(f"   Detected: {', '.join(ides)}")
                for ide in ides:
                    install_mcp_config(ide, str(project_path), str(mcp_server))
            else:
                print("   No IDEs auto-detected")
                print("   Run 'hcr setup-ide --ide <name>' manually")
        else:
            # Install specific IDE
            install_mcp_config(args.setup_ide, str(project_path), str(mcp_server))
    
    # Start daemon if requested
    if args.daemon:
        print("\n🚀 Starting background daemon...")
        from product.daemon.hcr_daemon import HCRDaemon
        daemon = HCRDaemon(str(project_path))
        if daemon.is_already_running():
            print("   [OK] Daemon already running")
        else:
            launch_background_python(["-m", "product.daemon.hcr_daemon", "start", "--project", str(project_path)])
            print("   [OK] Daemon started in background")
    
    # Initial state capture
    print("\n📊 Capturing initial state...")
    engine = HCREngine(str(project_path))
    
    # Create init event
    from src.engine_api import EngineEvent
    from datetime import datetime
    event = EngineEvent(
        event_type='manual',
        timestamp=datetime.now(),
        data={'init': True}
    )
    engine.update_from_environment(event)
    engine.save_state()
    print("   [OK] State captured")
    
    print(f"\n[Success] HCR initialized! Try:")
    print(f"   hcr resume          - Resume session")
    print(f"   hcr dashboard       - Open web dashboard")
    print(f"   hcr status          - Check engine status")
    
    if args.setup_ide or args.auto:
        print(f"\n📝 Restart your IDE to load HCR integration")


def cmd_resume(args):
    """Resume HCR session"""
    from product.cli.resume import run_resume, format_output_text, format_output_json
    
    project_path = args.project or str(Path.cwd())
    
    hcr_dir = get_hcr_dir(project_path)
    hcr_dir.mkdir(exist_ok=True)

    if args.server:
        from product.cli.resume import start_server
        print(f"[HCR] Starting engine server for: {project_path}")
        start_server(project_path, args.port)
        return 0
    
    output = run_resume(project_path, args.format)
    print(output)


def cmd_status(args):
    """Check HCR engine status"""
    print_banner()
    
    project_path = Path(args.project or Path.cwd()).resolve()
    
    # Check if initialized
    hcr_dir = get_hcr_dir(project_path)
    print(f"📁 Project: {project_path}")
    print(f".hcr directory: {'[OK]' if hcr_dir.exists() else '[Missing]'}")
    
    # Check engine status
    if get_engine_status():
        print("Engine: Running on localhost:8733")
    else:
        print("Engine: Not running")
        print("   Start with: hcr resume --server")
    
    # Check state
    state_file = hcr_dir / "session_state.json"
    if state_file.exists():
        import json
        with open(state_file) as f:
            state = json.load(f)
        print(f"💾 State: {state.get('current_task', 'Unknown')}")
        print(f"📊 Progress: {state.get('progress_percent', 0)}%")
    else:
        print("💾 State: None (run hcr resume to create)")


def cmd_daemon(args):
    """Control HCR background daemon"""
    from product.daemon.hcr_daemon import HCRDaemon
    
    project_path = args.project or str(Path.cwd())
    daemon = HCRDaemon(project_path)
    
    if args.daemon_command == "install":
        print("📦 Installing daemon...")
        print("   Daemon runs as user process (no system install needed)")
        print(f"   Run 'hcr daemon start' to start daemon for {project_path}")
    
    elif args.daemon_command == "start":
        print("🚀 Starting daemon...")
        if daemon.is_already_running():
            print("   [OK] Daemon is already running")
            daemon.status()
        else:
            # Start in background subprocess
            launch_background_python(["-m", "product.daemon.hcr_daemon", "start", "--project", project_path])
            print("   [OK] Daemon started in background")
            time.sleep(1)  # Brief wait for startup
            daemon.status()
    
    elif args.daemon_command == "stop":
        print("� Stopping daemon...")
        daemon.stop()
    
    elif args.daemon_command == "status":
        daemon.status()


def cmd_dashboard(args):
    """Launch web dashboard"""
    from src.web.dashboard import launch_dashboard
    print("🌐 Launching dashboard...")
    launch_dashboard()


def cmd_setup_ide(args):
    """Setup IDE integration"""
    print("🖥️  Setting up IDE integration...")
    
    project_path = args.project or str(Path.cwd())
    mcp_server = Path(__file__).parent.parent.parent / "mcp_server_wrapper.py"
    
    if args.ide:
        install_mcp_config(args.ide, project_path, str(mcp_server))
    elif args.auto:
        ides = detect_installed_ides()
        if ides:
            print(f"Detected: {', '.join(ides)}")
            for ide in ides:
                install_mcp_config(ide, project_path, str(mcp_server))
        else:
            print("No IDEs auto-detected")
    else:
        print("Use --ide <name> or --auto")
        print(f"Supported: {', '.join(get_mcp_config_paths().keys())}")


def cmd_explain(args):
    """Show what context HCR injects and why"""
    from product.cli.explain import run_explain
    project_path = args.project or str(Path.cwd())
    output = run_explain(project_path, full=args.full)
    print(output)


def cmd_memory(args):
    """Manual memory management: pin, forget, reset, list"""
    from product.cli.commands import cmd_pin, cmd_forget, cmd_reset, cmd_list_facts
    project_path = args.project or str(Path.cwd())
    
    if args.action == "pin":
        if not args.value:
            print("[Error] Provide fact to pin: hcr memory pin 'Use FastAPI'")
            return
        print(cmd_pin(project_path, args.value))
    elif args.action == "forget":
        if not args.value:
            print("[Error] Provide index or text: hcr memory forget 3")
            return
        print(cmd_forget(project_path, args.value))
    elif args.action == "reset":
        print(cmd_reset(project_path, force=args.force))
    elif args.action == "list":
        print(cmd_list_facts(project_path))


def cmd_doctor(args):
    """Run install/startup diagnostics."""
    from product.cli.doctor import run_doctor
    project_path = args.project or str(Path.cwd())
    print(run_doctor(project_path, as_json=args.format == "json"))


def main():
    parser = argparse.ArgumentParser(
        description="HCR - Hybrid Cognitive Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    hcr init --auto           # Full auto-setup
    hcr resume                # Resume session
    hcr status                # Check status
    hcr dashboard             # Open web UI
    hcr explain               # Show injected context
    hcr doctor                # Diagnose install/runtime issues
    hcr memory pin "Use FastAPI"  # Pin a fact
    hcr memory list           # List facts
    hcr memory forget 3       # Remove fact #3
    hcr memory reset --force  # Clear all state
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize HCR in project")
    init_parser.add_argument("--project", "-p", default=".", help="Project path")
    init_parser.add_argument("--auto", "-a", action="store_true", help="Auto-detect and configure everything")
    init_parser.add_argument("--daemon", "-d", action="store_true", help="Enable background daemon")
    init_parser.add_argument("--setup-ide", "-i", metavar="IDE", help="Setup specific IDE (windsurf, claude, cursor)")
    init_parser.add_argument("--force", "-f", action="store_true", help="Force reinitialize")
    
    # resume command
    resume_parser = subparsers.add_parser("resume", help="Resume session with context")
    resume_parser.add_argument("--project", "-p", help="Project path")
    resume_parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    resume_parser.add_argument("--server", "-s", action="store_true", help="Start engine server")
    resume_parser.add_argument("--port", type=int, default=8733, help="HTTP server port when using --server")
    
    # explain command
    explain_parser = subparsers.add_parser("explain", help="Show what context HCR injects and why")
    explain_parser.add_argument("--project", "-p", help="Project path")
    explain_parser.add_argument("--full", action="store_true", help="Show all available context")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Check HCR status")
    status_parser.add_argument("--project", "-p", help="Project path")

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run HCR diagnostics")
    doctor_parser.add_argument("--project", "-p", help="Project path")
    doctor_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    # daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Control background daemon")
    daemon_parser.add_argument("daemon_command", choices=["install", "start", "stop", "status", "logs"], nargs="?", default="status")
    
    # dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Launch web dashboard")
    
    # setup-ide command
    setup_parser = subparsers.add_parser("setup-ide", help="Configure IDE integration")
    setup_parser.add_argument("--ide", "-i", help="IDE name (windsurf, claude, cursor)")
    setup_parser.add_argument("--auto", "-a", action="store_true", help="Auto-detect IDEs")
    setup_parser.add_argument("--project", "-p", help="Project path")
    
    # memory command (pin/forget/reset/list-facts)
    memory_parser = subparsers.add_parser("memory", help="Manage HCR memory manually")
    memory_parser.add_argument("action", choices=["pin", "forget", "reset", "list"], help="Memory action")
    memory_parser.add_argument("--project", "-p", help="Project path")
    memory_parser.add_argument("--force", "-f", action="store_true", help="Force reset without confirmation")
    memory_parser.add_argument("value", nargs="?", help="Fact text or index for pin/forget")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        if args.command == "init":
            cmd_init(args)
        elif args.command == "resume":
            cmd_resume(args)
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "daemon":
            cmd_daemon(args)
        elif args.command == "dashboard":
            cmd_dashboard(args)
        elif args.command == "setup-ide":
            cmd_setup_ide(args)
        elif args.command == "explain":
            cmd_explain(args)
        elif args.command == "memory":
            cmd_memory(args)
        elif args.command == "doctor":
            cmd_doctor(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 0
    except Exception as e:
        print(f"\n[Error]: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
