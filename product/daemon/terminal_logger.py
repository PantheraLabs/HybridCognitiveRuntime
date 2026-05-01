"""
HCR Terminal Logger

Generates shell snippets for various shells (bash, zsh, powershell)
to automatically log commands to the HCR engine.

k2.6 complete: Now includes a TerminalLogger class that the daemon
can use to record terminal events directly, plus Windows batch support.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


BASH_ZSH_SNIPPET = """
# HCR Terminal Integration
_hcr_log_command() {
    local exit_code=$?
    local cmd=$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')
    if [ -n "$cmd" ]; then
        curl -s -X POST http://localhost:8733/event \\
             -H "Content-Type: application/json" \\
             -d "{\\"type\\":\\"terminal\\", \\"data\\":{\\"command\\":\\"$cmd\\", \\"success\\":$([[ $exit_code == 0 ]] && echo true || echo false)}}" &
    fi
}
# Add to PROMPT_COMMAND (bash) or precmd (zsh)
if [ -n "$BASH_VERSION" ]; then
    PROMPT_COMMAND="_hcr_log_command; $PROMPT_COMMAND"
elif [ -n "$ZSH_VERSION" ]; then
    precmd_functions+=(_hcr_log_command)
fi
"""

POWERSHELL_SNIPPET = """
# HCR Terminal Integration for PowerShell
function _hcr_log_command {
    $lastCommand = Get-History -Count 1
    if ($lastCommand) {
        $success = $?
        $body = @{
            type = "terminal"
            data = @{
                command = $lastCommand.CommandLine
                success = [bool]$success
            }
        } | ConvertTo-Json -Compress
        
        try {
            Invoke-RestMethod -Method Post -Uri "http://localhost:8733/event" `
                              -ContentType "application/json" -Body $body > $null
        } catch {}
    }
}

# Add to your prompt function
$originalPrompt = $function:prompt
function prompt {
    _hcr_log_command
    & $originalPrompt
}
"""

BATCH_SNIPPET = """
REM HCR Terminal Integration for Windows CMD
REM Add to your AutoRun registry or call manually after each command
@echo off
if defined HCR_TERMINAL_ENABLED (
    powershell -NoProfile -Command "try { $cmd=(Get-History -Count 1).CommandLine; Invoke-RestMethod -Method Post -Uri 'http://localhost:8733/event' -ContentType 'application/json' -Body ('{\"type\":\"terminal\",\"data\":{\"command\":\"' + $cmd + '\",\"success\":true}}') } catch {}" >nul 2>&1
)
"""


class TerminalLogger:
    """
    Direct terminal event logger for HCR daemon.
    
    Can be used by the daemon to record terminal events without
    relying on shell hooks (useful for IDE-integrated terminals).
    """
    
    def __init__(self, engine_port: int = 8733, project_path: Optional[str] = None):
        self.engine_port = engine_port
        self.project_path = project_path or str(Path.cwd())
        self._event_endpoint = f"http://localhost:{engine_port}/event"
    
    def log_command(self, command: str, success: bool = True, 
                     working_dir: Optional[str] = None,
                     duration_ms: Optional[int] = None) -> bool:
        """
        Log a terminal command execution to the HCR engine.
        
        Args:
            command: The executed command string
            success: Whether the command exited successfully
            working_dir: Directory where command was executed
            duration_ms: Execution time in milliseconds
            
        Returns:
            True if logged successfully, False otherwise
        """
        payload = {
            "type": "terminal",
            "data": {
                "command": command[:500],  # Truncate very long commands
                "success": success,
                "working_dir": working_dir or self.project_path,
                "timestamp": datetime.now().isoformat(),
            }
        }
        if duration_ms is not None:
            payload["data"]["duration_ms"] = duration_ms
        
        return self._send_event(payload)
    
    def log_error(self, command: str, error_output: str, 
                  exit_code: int = 1) -> bool:
        """
        Log a terminal command that failed with error output.
        
        Args:
            command: The failed command
            error_output: stderr or error message
            exit_code: Process exit code
            
        Returns:
            True if logged successfully
        """
        payload = {
            "type": "terminal",
            "data": {
                "command": command[:500],
                "success": False,
                "exit_code": exit_code,
                "error_preview": error_output[:1000],
                "timestamp": datetime.now().isoformat(),
            }
        }
        return self._send_event(payload)
    
    def _send_event(self, payload: Dict[str, Any]) -> bool:
        """Send event to HCR engine HTTP endpoint."""
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self._event_endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError):
            # Engine not running - silent fail, don't break terminal UX
            return False
        except Exception:
            return False
    
    def get_snippet(self, shell_type: str) -> str:
        """Get shell integration snippet for manual installation."""
        return get_snippet(shell_type)


def get_snippet(shell_type: str) -> str:
    """Get shell integration snippet."""
    if shell_type in ["bash", "zsh"]:
        return BASH_ZSH_SNIPPET
    elif shell_type == "powershell":
        return POWERSHELL_SNIPPET
    elif shell_type in ["cmd", "batch"]:
        return BATCH_SNIPPET
    else:
        return f"# Unsupported shell: {shell_type}"


def install_snippet(shell_type: str = "auto") -> str:
    """
    Detect shell and return appropriate snippet.
    
    Args:
        shell_type: 'auto', 'bash', 'zsh', 'powershell', 'cmd'
        
    Returns:
        Installation instructions string
    """
    if shell_type == "auto":
        import os
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            shell_type = "zsh"
        elif "bash" in shell:
            shell_type = "bash"
        elif os.name == "nt":
            shell_type = "powershell"
        else:
            shell_type = "bash"
    
    snippet = get_snippet(shell_type)
    
    instructions = f"""
# HCR Terminal Logger - {shell_type.upper()} Integration
# Paste the following into your shell config file:

{snippet}

# Then reload your config:
# {shell_type}: source ~/.{shell_type}rc  (or ~/.{shell_type}_profile)
"""
    return instructions


if __name__ == "__main__":
    import sys
    shell = sys.argv[1] if len(sys.argv) > 1 else "bash"
    print(install_snippet(shell))
