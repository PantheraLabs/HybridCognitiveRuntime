"""
Anthropic LLM Provider

Implements the LLMProvider interface using the official anthropic SDK.
"""

import os
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider"""

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str = "", **kwargs):
        super().__init__(model=model, api_key=api_key, **kwargs)

        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "Anthropic SDK not installed. Run: pip install anthropic"
                )

            if not self.api_key:
                raise ValueError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                    "or pass api_key to the provider."
                )

            self._client = Anthropic(api_key=self.api_key)

        return self._client

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via Anthropic API"""
        client = self._get_client()

        messages = [
            {"role": "user", "content": prompt}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system:
            kwargs["system"] = system

        try:
            response = client.messages.create(**kwargs)

            # Extract content from TextBlock
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                provider="anthropic",
                usage=usage,
                raw=response,
            )

        except Exception as e:
            return LLMResponse(
                content=f"[LLM Error] Anthropic: {str(e)}",
                model=self.model,
                provider="anthropic",
                usage={},
            )

    def is_available(self) -> bool:
        """Check if Anthropic is reachable"""
        try:
            # Anthropic doesn't have a simple "models list" endpoint in the python SDK that is standard,
            # so we'll do a minimal ping completion
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False
