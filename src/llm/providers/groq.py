"""
Groq LLM Provider

Free tier, incredibly fast (LPU inference).
Uses the OpenAI-compatible API so we use the groq SDK.

Default model: llama-3.3-70b-versatile
Free tier: 30 RPM, 14,400 requests/day
"""

import os
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    """Groq cloud LLM provider — fast & free"""

    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str = "", **kwargs):
        super().__init__(model=model, api_key=api_key, **kwargs)

        # Resolve API key
        if not self.api_key:
            self.api_key = os.environ.get("GROQ_API_KEY", "")

        self._client = None

    def _get_client(self):
        """Lazy-init the Groq client"""
        if self._client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError(
                    "Groq SDK not installed. Run: pip install groq"
                )

            if not self.api_key:
                raise ValueError(
                    "Groq API key not found. Set GROQ_API_KEY environment variable "
                    "or pass api_key to the provider.\n"
                    "Get a free key at: https://console.groq.com/keys"
                )

            self._client = Groq(api_key=self.api_key)

        return self._client

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via Groq API"""
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content or ""
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                provider="groq",
                usage=usage,
                raw=response,
            )

        except Exception as e:
            # Return error as content so the operator can handle it gracefully
            return LLMResponse(
                content=f"[LLM Error] Groq: {str(e)}",
                model=self.model,
                provider="groq",
                usage={},
            )

    def is_available(self) -> bool:
        """Check if Groq is reachable"""
        try:
            client = self._get_client()
            # Minimal call to test connectivity
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False
