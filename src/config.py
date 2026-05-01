"""
HCR Configuration System

Layered config resolution:
1. Environment variables (highest priority)
2. .hcr/config.json (project-level)
3. ~/.hcr/config.json (user-level)
4. Built-in defaults (lowest priority)
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass


@dataclass
class HCRConfig:
    """Central configuration for HCR"""

    # LLM Provider Settings
    llm_provider: str = "groq"                  # groq | google | ollama
    llm_model: str = ""                         # empty = use provider default
    llm_api_key: str = ""                       # from env: HCR_API_KEY or provider-specific
    llm_temperature: float = 0.3                # low temp for deterministic reasoning
    llm_max_tokens: int = 1024

    # Cache Settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 60                 # 1 min TTL

    # Engine Settings
    engine_port: int = 8733
    project_path: str = ""

    # Provider-specific defaults
    groq_model: str = "llama-3.3-70b-versatile"
    google_model: str = "gemini-2.0-flash"
    ollama_model: str = "llama3.2"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
    ollama_host: str = "http://localhost:11434"

    def validate(self) -> list[str]:
        """Validate configuration and return list of error messages."""
        errors = []
        
        valid_providers = {"groq", "google", "ollama", "openai", "anthropic"}
        if self.llm_provider not in valid_providers:
            errors.append(f"Invalid llm_provider '{self.llm_provider}'. Must be one of: {valid_providers}")
        
        if not (0.0 <= self.llm_temperature <= 2.0):
            errors.append(f"llm_temperature must be between 0.0 and 2.0, got {self.llm_temperature}")
        
        if self.llm_max_tokens < 1 or self.llm_max_tokens > 32000:
            errors.append(f"llm_max_tokens must be between 1 and 32000, got {self.llm_max_tokens}")
        
        if self.cache_ttl_seconds < 1:
            errors.append(f"cache_ttl_seconds must be >= 1, got {self.cache_ttl_seconds}")
        
        if self.engine_port < 1024 or self.engine_port > 65535:
            errors.append(f"engine_port must be between 1024 and 65535, got {self.engine_port}")
        
        if self.project_path and not Path(self.project_path).exists():
            errors.append(f"project_path does not exist: {self.project_path}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0
    
    def get_model(self) -> str:
        """Get the active model name, falling back to provider default"""
        if self.llm_model:
            return self.llm_model
        defaults = {
            "groq": self.groq_model,
            "google": self.google_model,
            "ollama": self.ollama_model,
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
        }
        return defaults.get(self.llm_provider, self.groq_model)

    def get_api_key(self) -> str:
        """Get API key with env var fallback chain"""
        if self.llm_api_key:
            return self.llm_api_key

        # Provider-specific env vars
        env_keys = {
            "groq": ["GROQ_API_KEY", "HCR_API_KEY"],
            "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY", "HCR_API_KEY"],
            "openai": ["OPENAI_API_KEY", "HCR_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "HCR_API_KEY"],
            "ollama": [],  # no key needed
        }

        for env_var in env_keys.get(self.llm_provider, ["HCR_API_KEY"]):
            val = os.environ.get(env_var, "")
            if val:
                return val

        return ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(project_path: Optional[str] = None) -> HCRConfig:
    """
    Load config with layered resolution.

    Priority: env vars > project .hcr/config.json > ~/.hcr/config.json > defaults
    """
    # Load .env file if it exists
    load_dotenv()
    
    config = HCRConfig()

    # Layer 1: User-level config (~/.hcr/config.json)
    user_config_path = Path.home() / ".hcr" / "config.json"
    if user_config_path.exists():
        _merge_from_file(config, user_config_path)

    # Layer 2: Project-level config (.hcr/config.json)
    if project_path:
        project_config_path = Path(project_path) / ".hcr" / "config.json"
        if project_config_path.exists():
            _merge_from_file(config, project_config_path)
        config.project_path = project_path

    # Layer 3: Environment variables (highest priority)
    _merge_from_env(config)

    return config


def _merge_from_file(config: HCRConfig, path: Path):
    """Merge config values from a JSON file"""
    try:
        with open(path, 'r') as f:
            data = json.load(f)

        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
    except (json.JSONDecodeError, IOError) as e:
        import logging
        logging.getLogger("HCRConfig").warning(f"Could not read {path}: {e}")


def _merge_from_env(config: HCRConfig):
    """Merge config values from environment variables"""
    env_map = {
        "HCR_LLM_PROVIDER": "llm_provider",
        "HCR_LLM_MODEL": "llm_model",
        "HCR_API_KEY": "llm_api_key",
        "HCR_LLM_TEMPERATURE": "llm_temperature",
        "HCR_LLM_MAX_TOKENS": "llm_max_tokens",
        "HCR_CACHE_ENABLED": "cache_enabled",
        "HCR_CACHE_TTL": "cache_ttl_seconds",
        "HCR_ENGINE_PORT": "engine_port",
        "HCR_OLLAMA_HOST": "ollama_host",
    }

    for env_var, attr_name in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Type coerce based on the default type
            current = getattr(config, attr_name)
            try:
                if isinstance(current, bool):
                    setattr(config, attr_name, value.lower() in ("true", "1", "yes"))
                elif isinstance(current, int):
                    setattr(config, attr_name, int(value))
                elif isinstance(current, float):
                    setattr(config, attr_name, float(value))
                else:
                    setattr(config, attr_name, value)
            except (ValueError, TypeError):
                pass  # Skip invalid env values silently


def save_config(config: HCRConfig, path: Path):
    """Save config to a JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Don't save API keys to disk
    data = config.to_dict()
    data.pop("llm_api_key", None)

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
