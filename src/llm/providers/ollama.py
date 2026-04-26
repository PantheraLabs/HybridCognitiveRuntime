"""
Ollama LLM Provider

Local model inference via Ollama HTTP API.
No API key needed, fully offline, no SDK dependency.

Default model: llama3.2
Requires: Ollama installed and running (https://ollama.com)
"""

import json
import urllib.request
import urllib.error
from typing import Optional

from ..llm_provider import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider — free, offline, private"""

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        api_key: str = "",  # unused, kept for interface compat
        **kwargs
    ):
        super().__init__(model=model, api_key="", **kwargs)
        self.host = host.rstrip("/")

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate completion via Ollama HTTP API"""

        # Build request payload (Ollama uses /api/chat for chat models)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result.get("message", {}).get("content", "")

            # Ollama provides eval_count and prompt_eval_count
            usage = {}
            if "eval_count" in result:
                usage = {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                }

            return LLMResponse(
                content=content,
                model=self.model,
                provider="ollama",
                usage=usage,
                raw=result,
            )

        except urllib.error.URLError as e:
            return LLMResponse(
                content=f"[LLM Error] Ollama not reachable at {self.host}: {str(e)}",
                model=self.model,
                provider="ollama",
                usage={},
            )
        except Exception as e:
            return LLMResponse(
                content=f"[LLM Error] Ollama: {str(e)}",
                model=self.model,
                provider="ollama",
                usage={},
            )

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available"""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # Check if our model is available
            models = [m.get("name", "").split(":")[0] for m in result.get("models", [])]
            return self.model.split(":")[0] in models

        except Exception:
            return False

    def list_models(self) -> list:
        """List available models in Ollama"""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            return [m.get("name", "") for m in result.get("models", [])]

        except Exception:
            return []
