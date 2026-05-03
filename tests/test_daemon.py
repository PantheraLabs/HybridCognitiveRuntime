#!/usr/bin/env python3
"""Test daemon startup in isolation."""
import sys
import os
import threading
import time

sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

# Remove stale PID
pid_file = r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime\.hcr\daemon.pid"
if os.path.exists(pid_file):
    os.remove(pid_file)
    print("Removed stale PID file")

from product.daemon.hcr_daemon import HCRDaemon

d = HCRDaemon(r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

print(f"is_already_running: {d.is_already_running()}")
print(f"Starting daemon from thread: {threading.current_thread().name}")

# Start daemon in background thread (same as MCP server does)
def run_daemon():
    try:
        d.start()
    except Exception as e:
        print(f"DAEMON CRASHED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

t = threading.Thread(target=run_daemon, daemon=True)
t.start()

# Wait and check
time.sleep(3)
print(f"Thread alive: {t.is_alive()}")
print(f"Daemon is_running: {d.is_running}")

# Check log
log_file = r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime\.hcr\daemon.log"
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        print(f"\nLog tail ({len(lines)} lines total):")
        for line in lines[-10:]:
            print(line.rstrip())
else:
    print("No log file found")

# Check PID file
if os.path.exists(pid_file):
    with open(pid_file) as f:
        print(f"\nPID file exists: {f.read().strip()}")
else:
    print("\nNo PID file - daemon exited")
