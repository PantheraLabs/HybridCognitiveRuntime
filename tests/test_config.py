import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import HCRConfig, load_config, save_config


def test_load_config_layers(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    user_config_dir = tmp_path / ".hcr"
    user_config_dir.mkdir()
    (user_config_dir / "config.json").write_text(json.dumps({
        "llm_provider": "google",
        "cache_ttl_seconds": 10
    }))

    project_path = tmp_path / "project"
    project_path.mkdir()
    project_config_dir = project_path / ".hcr"
    project_config_dir.mkdir()
    (project_config_dir / "config.json").write_text(json.dumps({
        "llm_provider": "ollama",
        "cache_ttl_seconds": 20
    }))

    monkeypatch.setenv("HCR_LLM_PROVIDER", "openai")
    monkeypatch.setenv("HCR_CACHE_TTL", "30")
    monkeypatch.setenv("HCR_CACHE_ENABLED", "false")

    config = load_config(str(project_path))

    assert config.llm_provider == "openai"
    assert config.cache_ttl_seconds == 30
    assert config.cache_enabled is False
    assert config.project_path == str(project_path)
    assert config.get_model() == config.openai_model


def test_save_config_omits_api_key(tmp_path):
    config = HCRConfig(llm_provider="groq", llm_api_key="secret-key")
    path = tmp_path / "config.json"

    save_config(config, path)
    data = json.loads(path.read_text())

    assert "llm_api_key" not in data
    assert data["llm_provider"] == "groq"
