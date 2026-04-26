"""
LLM Provider Abstraction

Unified interface for all LLM providers (Groq, Google, Ollama).
Synchronous API — keeps things simple for the engine's sequential execution model.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens
    raw: Optional[Any] = None  # original provider response

    def as_json(self) -> Optional[Dict[str, Any]]:
        """
        Try to parse response content as JSON.
        Handles markdown code fences and other common LLM formatting quirks.
        """
        text = self.content.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            # Remove opening fence (with optional language tag)
            text = re.sub(r'^```\w*\n?', '', text)
            # Remove closing fence
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
    - complete(): basic text completion
    - is_available(): health check
    """

    def __init__(self, model: str, api_key: str = "", **kwargs):
        self.model = model
        self.api_key = api_key
        self._kwargs = kwargs

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Generate a completion.

        Args:
            prompt: User message / prompt
            system: System instruction
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            Standardized LLMResponse
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable and configured"""
        pass

    def structured_complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a completion and parse as JSON.

        Convenience method that wraps complete() and parses the result.
        Uses lower temperature by default for structured output.
        """
        # Append JSON instruction to system prompt
        json_system = system
        if json_system:
            json_system += "\n\n"
        json_system += "IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, no code fences."

        response = self.complete(
            prompt=prompt,
            system=json_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.as_json()

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__.replace("Provider", "").lower()


def get_provider(
    provider_name: str,
    model: str = "",
    api_key: str = "",
    **kwargs
) -> LLMProvider:
    """
    Factory function to create an LLM provider instance.

    Args:
        provider_name: "groq", "google", or "ollama"
        model: Model name (uses provider default if empty)
        api_key: API key (uses env var fallback if empty)
        **kwargs: Provider-specific options

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If provider name is unknown
        ImportError: If provider SDK is not installed
    """
    provider_name = provider_name.lower().strip()

    if provider_name == "groq":
        from .providers.groq import GroqProvider
        return GroqProvider(
            model=model or "llama-3.3-70b-versatile",
            api_key=api_key,
            **kwargs
        )
    elif provider_name == "google":
        from .providers.google import GoogleProvider
        return GoogleProvider(
            model=model or "gemini-2.0-flash",
            api_key=api_key,
            **kwargs
        )
    elif provider_name == "ollama":
        from .providers.ollama import OllamaProvider
        return OllamaProvider(
            model=model or "llama3.2",
            host=kwargs.get("host", "http://localhost:11434"),
            **kwargs
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            f"Supported: groq, google, ollama"
        )
