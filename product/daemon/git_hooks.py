"""
HCR Git Hook Installer

Installs lightweight shell hooks into .git/hooks to automatically
report git operations to the HCR engine.
"""

import os
import stat
from pathlib import Path

HOOKS = {
    "post-commit": """#!/bin/sh
# HCR Git Hook: post-commit
curl -s -X POST http://localhost:8733/event \\
     -H "Content-Type: application/json" \\
     -d "{\\"type\\":\\"git_commit\\", \\"data\\":{\\"message\\":\\"$(git log -1 --pretty=%B)\\"}}" &
""",
    "post-checkout": """#!/bin/sh
# HCR Git Hook: post-checkout
curl -s -X POST http://localhost:8733/event \\
     -H "Content-Type: application/json" \\
     -d "{\\"type\\":\\"git_checkout\\", \\"data\\":{\\"branch\\":\\"$(git rev-parse --abbrev-ref HEAD)\\"}}" &
""",
    "post-merge": """#!/bin/sh
# HCR Git Hook: post-merge
curl -s -X POST http://localhost:8733/event \\
     -H "Content-Type: application/json" \\
     -d "{\\"type\\":\\"git_merge\\"}" &
"""
}

def install_hooks(project_path: str):
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        print(f"Error: No .git directory found in {project_path}")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    for name, content in HOOKS.items():
        hook_path = hooks_dir / name
        print(f"Installing hook: {name}")
        hook_path.write_text(content)
        
        # Make executable
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)

def uninstall_hooks(project_path: str):
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        return

    hooks_dir = git_dir / "hooks"
    for name in HOOKS.keys():
        hook_path = hooks_dir / name
        if hook_path.exists():
            # Only remove if it contains HCR signature
            content = hook_path.read_text()
            if "HCR Git Hook" in content:
                print(f"Uninstalling hook: {name}")
                hook_path.unlink()

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    path = sys.argv[2] if len(sys.argv) > 2 else "."
    
    if action == "install":
        install_hooks(path)
    elif action == "uninstall":
        uninstall_hooks(path)
