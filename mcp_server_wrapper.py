#!/usr/bin/env python3
"""Wrapper to ensure fresh module loading for MCP server."""
import sys
from pathlib import Path

# Always use the latest on-disk code
sys.path.insert(0, str(Path(__file__).parent))

from product.integrations.mcp_server import main

if __name__ == "__main__":
    main()
