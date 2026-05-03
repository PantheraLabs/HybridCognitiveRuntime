#!/usr/bin/env python3
"""Test MCP server init to catch exact failure point."""
import sys
sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

print("Step 1: import mcp_server module")
try:
    from product.integrations.mcp_server import HCRMCPResponder
    print("  OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Step 2: instantiate HCRMCPResponder")
try:
    responder = HCRMCPResponder()
    print(f"  OK - engine={responder.engine}")
    print(f"  synthesizer={responder._synthesizer}")
except Exception as e:
    import traceback
    print(f"  FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

if responder.engine is None:
    print("WARNING: engine is None despite no exception")
else:
    print(f"  engine._current_state={responder.engine._current_state}")
