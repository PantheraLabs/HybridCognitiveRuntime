#!/usr/bin/env python3
"""Test daemon with external engine — verbose debug."""
import sys
import os
import threading
import time
import traceback

sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

# Remove stale PID
pid_file = r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime\.hcr\daemon.pid"
if os.path.exists(pid_file):
    os.remove(pid_file)

from src.engine_api import HCREngine
from product.daemon.hcr_daemon import HCRDaemon
from product.daemon.file_watcher_service import FileWatcherService

e = HCREngine(r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")
if e.state_exists():
    e.load_state()
    print(f"Loaded state with {len(e._current_state.symbolic.facts) if e._current_state else 0} facts")
else:
    print("No state found")

# Test FileWatcherService in isolation
print("\n--- Testing FileWatcherService ---")
try:
    watcher = FileWatcherService(r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime", e)
    watcher.start()
    print("FileWatcherService started OK")
    watcher.stop()
    print("FileWatcherService stopped OK")
except Exception as ex:
    print(f"FileWatcherService FAILED: {type(ex).__name__}: {ex}")
    traceback.print_exc()

# Start daemon with external engine
print("\n--- Starting daemon ---")
d = HCRDaemon(r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime", engine=e)
print(f"is_already_running: {d.is_already_running()}")
print(f"External engine set: {d._external_engine is not None}")

daemon_exception = None

def run_daemon():
    global daemon_exception
    try:
        print("[THREAD] Calling d.start()...")
        d.start()
        print("[THREAD] d.start() returned normally — loop exited!")
    except Exception as ex:
        daemon_exception = ex
        print(f"[THREAD] DAEMON CRASHED: {type(ex).__name__}: {ex}")
        traceback.print_exc()

t = threading.Thread(target=run_daemon, daemon=True)
t.start()

time.sleep(1)
print(f"\n[MAIN] After 1s — Thread alive: {t.is_alive()}, is_running: {d.is_running}")
time.sleep(3)
print(f"[MAIN] After 4s — Thread alive: {t.is_alive()}, is_running: {d.is_running}")
if daemon_exception:
    print(f"[MAIN] Daemon exception captured: {daemon_exception}")

# Add a fact to the engine and check if daemon saves it
if e._current_state:
    e._current_state.add_fact("test:daemon_external_engine_test")
    time.sleep(3)
    e.save_state()
    print("\nManual save done")

# Check state file
from pathlib import Path
import json, gzip

f = Path(r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime\.hcr\state.json")
if f.exists():
    raw = f.read_bytes()
    try:
        data = json.loads(gzip.decompress(raw).decode())
    except:
        data = json.loads(raw.decode())
    facts = data['state']['symbolic']['facts']
    print(f"State file facts: {len(facts)}")
    print(f"Last fact: {facts[-1]}")
else:
    print("No state file")
