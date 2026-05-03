"""
Groq LLM Provider

Free tier, incredibly fast (LPU inference).
Uses the OpenAI-compatible API via raw HTTP requests — no groq SDK needed.
Uses urllib from stdlib (zero external dependencies).

Default model: llama-3.3-70b-versatile
Free tier: 30 RPM, 14,400 requests/day
"""

import json
import os
import urllib.request
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    """Groq cloud LLM provider — fast & free, zero SDK dependencies, stdlib only"""

    def __init__(self, model: str = "llama-3.1-8b-instant", api_key: str = "", **kwargs):
        super().__init__(model=model, api_key=api_key, **kwargs)

        # Resolve API key
        if not self.api_key:
            self.api_key = os.environ.get("GROQ_API_KEY", "")

    def _post(self, url: str, payload: dict, timeout: int = 30) -> dict:
        """Minimal HTTP POST using urllib (stdlib) — no requests dependency."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "HCR-MCP/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via Groq API (direct HTTP via urllib)"""

        if not self.api_key:
            return LLMResponse(
                content="[LLM Error] Groq: API key not found. Set GROQ_API_KEY environment variable.",
                model=self.model,
                provider="groq",
                usage={},
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            data = self._post(
                "https://api.groq.com/openai/v1/chat/completions",
                {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=30,
            )

            content = data["choices"][0]["message"].get("content", "")
            usage = data.get("usage", {})
            usage_out = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

            return LLMResponse(
                content=content,
                model=self.model,
                provider="groq",
                usage=usage_out,
                raw=data,
            )

        except Exception as e:
            return LLMResponse(
                content=f"[LLM Error] Groq: {str(e)}",
                model=self.model,
                provider="groq",
                usage={},
            )

    def structured_complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        schema: Optional[dict] = None,
    ) -> Optional[dict]:
        """Generate a JSON-structured completion via Groq."""
        if not self.api_key:
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if schema:
            messages.append({"role": "system", "content": f"Respond ONLY with a JSON object conforming to this schema: {json.dumps(schema)}"})
        messages.append({"role": "user", "content": prompt})

        try:
            data = self._post(
                "https://api.groq.com/openai/v1/chat/completions",
                {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            content = data["choices"][0]["message"].get("content", "")
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Strip markdown fences if present
                text = content.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0]
                return json.loads(text.strip())
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if Groq is reachable"""
        if not self.api_key:
            return False
        try:
            self._post(
                "https://api.groq.com/openai/v1/chat/completions",
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
                timeout=10,
            )
            return True
        except Exception:
            return False
