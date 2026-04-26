import sys
import argparse
from pathlib import Path
from .hcr_daemon import HCRDaemon

def main():
    parser = argparse.ArgumentParser(description="HCR Daemon Management")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"])
    parser.add_argument("--project", default=".")
    
    args = parser.parse_args()
    daemon = HCRDaemon(args.project)
    
    if args.action == "start":
        daemon.start()
    elif args.action == "stop":
        daemon.stop()
    elif args.action == "status":
        daemon.status()
    elif args.action == "restart":
        daemon.stop()
        daemon.start()

if __name__ == "__main__":
    main()
