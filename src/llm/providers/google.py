"""
Google Gemini LLM Provider

Free tier available via Google AI Studio.
Default model: gemini-2.0-flash

Free tier: 15 RPM, 1,500 requests/day
"""

import os
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider — free tier fallback"""

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str = "", **kwargs):
        super().__init__(model=model, api_key=api_key, **kwargs)

        # Resolve API key
        if not self.api_key:
            self.api_key = (
                os.environ.get("GOOGLE_API_KEY", "")
                or os.environ.get("GEMINI_API_KEY", "")
            )

        self._client = None

    def _get_client(self):
        """Lazy-init the Google GenAI client"""
        if self._client is None:
            try:
                from google import genai
            except ImportError:
                raise ImportError(
                    "Google GenAI SDK not installed. Run: pip install google-genai"
                )

            if not self.api_key:
                raise ValueError(
                    "Google API key not found. Set GOOGLE_API_KEY environment variable "
                    "or pass api_key to the provider.\n"
                    "Get a free key at: https://aistudio.google.com/apikey"
                )

            self._client = genai.Client(api_key=self.api_key)

        return self._client

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via Google Gemini API"""
        from google.genai import types

        client = self._get_client()

        try:
            config = types.GenerateContentConfig(
                system_instruction=system if system else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            content = response.text or ""
            usage = {}
            if response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                provider="google",
                usage=usage,
                raw=response,
            )

        except Exception as e:
            return LLMResponse(
                content=f"[LLM Error] Google: {str(e)}",
                model=self.model,
                provider="google",
                usage={},
            )

    def is_available(self) -> bool:
        """Check if Gemini is reachable"""
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model,
                contents="ping",
                config={"max_output_tokens": 5},
            )
            return bool(response.text)
        except Exception:
            return False
