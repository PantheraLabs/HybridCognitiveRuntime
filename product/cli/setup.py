"""
HCR Setup Command

Automates the installation of HCR components:
- Git Hooks
- Shell Integration
- Daemon Autostart (optional)
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from product.daemon.git_hooks import install_hooks
from product.daemon.terminal_logger import get_snippet

def run_setup(project_path: str):
    print(f"=== HCR SETUP: {project_path} ===")
    
    # 1. Install Git Hooks
    print("\n[1/2] Installing Git Hooks...")
    install_hooks(project_path)
    
    # 2. Shell Integration
    print("\n[2/2] Terminal Integration...")
    shell = "powershell" if os.name == "nt" else "bash"
    snippet = get_snippet(shell)
    
    print(f"To enable terminal awareness, add the following to your {shell} profile:")
    print("-" * 40)
    print(snippet)
    print("-" * 40)
    
    print("\nSetup complete! Start the HCR engine and daemon to begin.")
    print("Engine: python -m product.cli.resume --server")
    print("Daemon: python -m product.daemon start")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HCR Setup Utility")
    parser.add_argument("--project", default=".")
    args = parser.parse_args()
    
    run_setup(args.project)
