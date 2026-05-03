#!/usr/bin/env python3
"""Wrapper to ensure fresh module loading for MCP server."""
import sys
from pathlib import Path

# NUCLEAR: never use stale .pyc, always re-import from disk
sys.dont_write_bytecode = True

# Purge any previously-loaded HCR modules so we get fresh code
# (critical when the MCP server process restarts but .pyc was stale)
for name in list(sys.modules.keys()):
    if name.startswith(("product.", "src.", "core.")) or name in ("product", "src", "core"):
        del sys.modules[name]

# Always use the latest on-disk code
sys.path.insert(0, str(Path(__file__).parent))

from product.integrations.mcp_server import main

if __name__ == "__main__":
    main()
