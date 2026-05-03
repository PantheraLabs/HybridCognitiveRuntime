#!/usr/bin/env python3
"""Direct Groq API test — bypasses all HCR/MCP code."""
import json
import os
import urllib.request
from pathlib import Path

# Load key from .env manually (same logic as synthesizer)
env_file = Path(__file__).parent / ".env"
API_KEY = ""
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("GROQ_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not API_KEY:
    print("❌ No GROQ_API_KEY found in .env")
    exit(1)

print(f"Key loaded: {API_KEY[:15]}...")

MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
]

for model in MODELS:
    print(f"\n--- Testing model: {model} ---")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Say 'pong'"}],
        "max_tokens": 10,
        "temperature": 0,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HCR-MCP/1.0 (python-urllib; contact=hcr@local)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            print(f"✅ SUCCESS: {content[:50]}")
            print(f"   Tokens: {data.get('usage', {})}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"❌ HTTP {e.code}: {body[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
