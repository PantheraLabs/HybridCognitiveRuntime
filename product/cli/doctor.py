"""
HCR diagnostic command.

Provides supportable startup/install diagnostics for:
- Python/runtime availability
- Project initialization
- Config validity
- Optional provider SDK readiness
- Filesystem write access
- Local server health
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from src.config import load_config
from src.engine_api import HCREngine


def _check_server(port: int) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except OSError:
        return False


def _check_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _check_writeable_dir(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="hcr_doctor_", dir=path)
        os.close(fd)
        Path(temp_name).unlink(missing_ok=True)
        return True, "ok"
    except OSError as exc:
        return False, str(exc)


def run_doctor(project_path: str, as_json: bool = False) -> str:
    project = Path(project_path).resolve()
    hcr_dir = project / ".hcr"
    config = load_config(str(project))
    config_errors = config.validate()

    checks: List[Dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str, severity: str = "error"):
        checks.append({
            "name": name,
            "ok": ok,
            "detail": detail,
            "severity": severity,
        })

    add_check(
        "python_version",
        sys.version_info >= (3, 9),
        f"Running Python {sys.version.split()[0]}",
    )
    add_check(
        "project_exists",
        project.exists(),
        f"Project path: {project}",
    )
    add_check(
        "project_hcr_dir",
        hcr_dir.exists(),
        f"HCR directory: {hcr_dir}",
        severity="warning",
    )
    add_check(
        "config_valid",
        len(config_errors) == 0,
        "Configuration valid" if not config_errors else "; ".join(config_errors),
    )

    state_ok, state_detail = _check_writeable_dir(hcr_dir)
    add_check(
        "state_storage_writeable",
        state_ok,
        f"{hcr_dir}: {state_detail}",
    )

    temp_global = Path(tempfile.gettempdir()) / "hcr_global"
    global_ok, global_detail = _check_writeable_dir(temp_global)
    add_check(
        "global_storage_writeable",
        global_ok,
        f"{temp_global}: {global_detail}",
        severity="warning",
    )

    add_check(
        "dependency_requests",
        _check_module("requests"),
        "Python package: requests",
    )
    add_check(
        "dependency_dotenv",
        _check_module("dotenv"),
        "Python package: python-dotenv",
    )
    add_check(
        "dependency_watchdog",
        _check_module("watchdog"),
        "Python package: watchdog",
    )

    provider_modules = {
        "groq": "groq",
        "google": "google.genai",
        "openai": "openai",
        "anthropic": "anthropic",
    }
    provider = config.llm_provider
    if provider == "ollama":
        add_check(
            "llm_provider_sdk",
            True,
            f"Provider '{provider}' uses HTTP; no SDK required",
            severity="warning",
        )
    else:
        module_name = provider_modules.get(provider)
        sdk_ok = _check_module(module_name) if module_name else False
        add_check(
            "llm_provider_sdk",
            sdk_ok,
            f"Provider '{provider}' SDK module: {module_name}",
            severity="warning",
        )
        add_check(
            "llm_provider_api_key",
            bool(config.get_api_key()),
            f"Provider '{provider}' API key present: {bool(config.get_api_key())}",
            severity="warning",
        )

    engine = HCREngine(str(project))
    add_check(
        "engine_initialization",
        engine is not None,
        "Engine initialized",
    )

    server_running = _check_server(config.engine_port)
    add_check(
        "engine_server",
        server_running,
        f"Local engine server listening on 127.0.0.1:{config.engine_port}: {server_running}",
        severity="warning",
    )

    status = "healthy"
    if any((not check["ok"]) and check["severity"] == "error" for check in checks):
        status = "unhealthy"
    elif any(not check["ok"] for check in checks):
        status = "degraded"

    result = {
        "status": status,
        "project_path": str(project),
        "llm_provider": config.llm_provider,
        "engine_port": config.engine_port,
        "checks": checks,
    }

    if as_json:
        return json.dumps(result, indent=2)

    lines = [
        "HCR Doctor",
        f"Status: {status}",
        f"Project: {project}",
        f"Provider: {config.llm_provider}",
        "",
    ]

    for check in checks:
        prefix = "OK" if check["ok"] else ("WARN" if check["severity"] == "warning" else "FAIL")
        lines.append(f"[{prefix}] {check['name']}: {check['detail']}")

    lines.append("")
    lines.append("Recommended next actions:")
    if any(check["name"] == "llm_provider_sdk" and not check["ok"] for check in checks):
        lines.append(f"- Install the SDK for provider '{config.llm_provider}' or switch providers.")
    if any(check["name"] == "llm_provider_api_key" and not check["ok"] for check in checks):
        lines.append(f"- Set the API key for provider '{config.llm_provider}' in the environment or .env.")
    if any(check["name"] == "engine_server" and not check["ok"] for check in checks):
        lines.append(f"- Start the local server with `hcr resume --server --port {config.engine_port}`.")
    if any(check["name"] == "project_hcr_dir" and not check["ok"] for check in checks):
        lines.append("- Run `hcr init` or `hcr resume` once to initialize local state.")
    if not any(not check["ok"] for check in checks):
        lines.append("- No blocking issues detected.")

    return "\n".join(lines)
