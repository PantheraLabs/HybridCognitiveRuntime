#!/usr/bin/env python3
"""Test engine.save_state() in a daemon-like thread."""
import sys
import threading
import time
import os

sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

from src.engine_api import HCREngine

project_path = r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime"
engine = HCREngine(project_path)
state = engine.load_state()
print(f"Loaded state with {len(state.symbolic.facts) if state else 0} facts")

# Add a test fact
if state:
    state.add_fact("test:daemon_thread_save_test")
    print("Added test fact")

# Save in a background thread (like daemon does)
def save_in_thread():
    try:
        engine.save_state()
        print("State saved successfully from thread")
        print("File mtime:", os.path.getmtime(engine.state_file))
    except Exception as e:
        print(f"ERROR saving state: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

t = threading.Thread(target=save_in_thread, daemon=True)
t.start()
t.join(timeout=5)
print("Thread finished:", not t.is_alive())
