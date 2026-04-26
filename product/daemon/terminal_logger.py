"""
HCR Terminal Logger

Generates shell snippets for various shells (bash, zsh, powershell)
to automatically log commands to the HCR engine.
"""

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

def get_snippet(shell_type: str) -> str:
    if shell_type in ["bash", "zsh"]:
        return BASH_ZSH_SNIPPET
    elif shell_type == "powershell":
        return POWERSHELL_SNIPPET
    else:
        return f"# Unsupported shell: {shell_type}"

if __name__ == "__main__":
    import sys
    shell = sys.argv[1] if len(sys.argv) > 1 else "bash"
    print(get_snippet(shell))
