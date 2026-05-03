#!/usr/bin/env python3
"""Direct test of HCREngine init to see why MCP server fails."""
import sys
import os
sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

project_path = r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime"

print(f"Project path: {project_path}")
print(f"Exists: {os.path.exists(project_path)}")
print(f".hcr exists: {os.path.exists(os.path.join(project_path, '.hcr'))}")

try:
    from src.engine_api import HCREngine
    print("Import OK")
    engine = HCREngine(project_path)
    print(f"Engine init OK: {engine}")
    print(f"Current state: {engine._current_state}")
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
