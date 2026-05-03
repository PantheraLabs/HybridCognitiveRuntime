#!/usr/bin/env python3
import sys
sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

print("A: Importing HCRMCPResponder...")
from product.integrations.mcp_server import HCRMCPResponder
print("B: Import OK, instantiating...")

import signal

def timeout_handler(signum, frame):
    print("TIMEOUT: Constructor hung for >10s")
    sys.exit(2)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

try:
    r = HCRMCPResponder()
    signal.alarm(0)
    print(f"C: Init OK, engine={r.engine is not None}")
except Exception as e:
    signal.alarm(0)
    import traceback
    traceback.print_exc()
