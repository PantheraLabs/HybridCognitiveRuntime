#!/usr/bin/env python3
"""
HCR MCP Server Diagnostic Report
Run: python diagnostic_report.py
"""
import sys
import os
import json
from pathlib import Path

REPORT = []
def log(msg): 
    print(msg)
    REPORT.append(msg)

log("=" * 60)
log("HCR MCP SERVER DIAGNOSTIC REPORT")
log("=" * 60)

# 1. Python environment
log(f"\n[1] PYTHON ENVIRONMENT")
log(f"  Executable: {sys.executable}")
log(f"  Version: {sys.version}")
log(f"  CWD: {os.getcwd()}")

# 2. Module paths
log(f"\n[2] MODULE PATHS (first 5)")
for p in sys.path[:5]:
    log(f"  {p}")

# 3. Check if product module loads from repo
log(f"\n[3] MODULE ORIGIN")
sys.path.insert(0, str(Path(__file__).parent))
try:
    import product
    log(f"  product module: {product.__file__}")
except Exception as e:
    log(f"  ERROR importing product: {e}")

# 4. Check .env and API key
log(f"\n[4] ENVIRONMENT & API KEY")
env_file = Path(__file__).parent / ".env"
log(f"  .env exists: {env_file.exists()}")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.startswith("GROQ_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            log(f"  GROQ_API_KEY found: {key[:15]}...")
            os.environ["GROQ_API_KEY"] = key
            break
    else:
        log("  GROQ_API_KEY NOT found in .env")
else:
    log("  .env NOT found")

# 5. Test Groq directly
log(f"\n[5] GROQ DIRECT API TEST")
try:
    import urllib.request
    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "Say pong"}],
        "max_tokens": 5,
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HCR-Diagnostic/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        log(f"  SUCCESS: '{content.strip()}'")
except Exception as e:
    log(f"  FAILED: {type(e).__name__}: {e}")

# 6. Test engine initialization
log(f"\n[6] HCR ENGINE INITIALIZATION")
try:
    from src.engine_api import HCREngine
    engine = HCREngine(str(Path(__file__).parent))
    log(f"  Engine created: {type(engine).__name__}")
    log(f"  Current state: {engine._current_state}")
except Exception as e:
    log(f"  FAILED: {type(e).__name__}: {e}")
    import traceback
    log(f"  {traceback.format_exc()[:500]}")

# 7. Test MCP Responder constructor
log(f"\n[7] MCP RESPONDER CONSTRUCTOR")
try:
    from product.integrations.mcp_server import HCRMCPResponder
    responder = HCRMCPResponder()
    log(f"  Responder created: {type(responder).__name__}")
    log(f"  Project path: {responder.project_path}")
    log(f"  Engine is None: {responder.engine is None}")
    if responder.engine:
        log(f"  Engine state: {responder.engine._current_state}")
    log(f"  Synthesizer: {type(responder._synthesizer).__name__}")
except Exception as e:
    log(f"  FAILED: {type(e).__name__}: {e}")
    import traceback
    log(f"  {traceback.format_exc()[:500]}")

# Save report
report_file = Path(__file__).parent / "diagnostic_output.txt"
report_file.write_text("\n".join(REPORT))
log(f"\n[8] Report saved to: {report_file}")
