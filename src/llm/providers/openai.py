"""
OpenAI LLM Provider

Implements the LLMProvider interface using the official openai SDK.
Supports structured JSON output and token usage extraction.
"""

import os
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "", **kwargs):
        super().__init__(model=model, api_key=api_key, **kwargs)

        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY", "")

        self._client = None

    def _get_client(self):
        """Lazy-init the OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI SDK not installed. Run: pip install openai"
                )

            if not self.api_key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or pass api_key to the provider."
                )

            self._client = OpenAI(api_key=self.api_key)

        return self._client

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via OpenAI API"""
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
                # We do not use response_format={"type": "json_object"} here by default 
                # because the base complete() might be used for free text.
                # The structured_complete() method in the base class relies on 
                # prompt engineering and parsing.
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
                provider="openai",
                usage=usage,
                raw=response,
            )

        except Exception as e:
            return LLMResponse(
                content=f"[LLM Error] OpenAI: {str(e)}",
                model=self.model,
                provider="openai",
                usage={},
            )

    def is_available(self) -> bool:
        """Check if OpenAI is reachable"""
        try:
            client = self._get_client()
            response = client.models.list()
            return bool(response.data)
        except Exception:
            return False
