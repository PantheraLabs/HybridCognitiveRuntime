#!/usr/bin/env python3
"""MCP stdio entry point — delegates to mcp_server_wrapper."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_server_wrapper import main

if __name__ == "__main__":
    main()
