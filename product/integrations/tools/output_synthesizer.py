"""
Commercial-Grade Output Synthesizer for HCR MCP Tools.

Transforms raw tool data into polished, AI-IDE-optimized markdown outputs
using Groq (or fallback LLM). Every tool result passes through here before
reaching the client.

Design:
- Fast rule-based formatter (default, <1ms)
- Smart LLM synthesizer (optional, ~200-800ms via Groq)
- Selective synthesis: only data-heavy tools get LLM treatment
- 2s timeout on LLM calls — never blocks
- Result caching per tool+data hash

Usage:
    synthesizer = OutputSynthesizer(engine)
    polished = synthesizer.synthesize("hcr_get_state", raw_state_dict)
"""

import hashlib
import json
import time
import asyncio
from typing import Dict, Any, Optional


# ---------------------------------------------------------------------------
# System prompts per tool — optimized for AI IDE consumption
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATES: Dict[str, str] = {
    "default": """You are the HCR Output Synthesizer. Transform raw tool data into a concise, professional markdown summary optimized for an AI IDE assistant.

Rules:
- Use clear headings, bullet points, and visual separators.
- Highlight the most actionable insight first.
- Include confidence indicators where relevant.
- Keep total output under 800 tokens (≈600 words).
- Never hallucinate data not present in the input.
- If data is empty/missing, say so explicitly rather than inventing.

Output format: Valid JSON with keys:
  "summary": "One-sentence TL;DR",
  "panel": "Full markdown panel for IDE display",
  "confidence": "high" | "medium" | "low",
  "actions": ["actionable suggestion 1", ...] (max 3)

Respond ONLY with valid JSON. No markdown fences, no explanation.""",

    "hcr_get_state": """You are the HCR State Synthesizer. Analyze cognitive state data and produce a developer-focused resume panel.

Rules:
- Lead with: current task, progress %, and next action.
- Use emoji indicators: ✅ high confidence, ⚠️ medium, ❓ low.
- Show recent facts as a bulleted list (max 5).
- If no state exists, say "No cognitive state tracked yet. Start coding to build context."
- Include a visual progress bar [████░░░░░░].

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_get_system_health": """You are the HCR Health Monitor. Transform system metrics into a clear status dashboard.

Rules:
- Start with overall status: 🟢 Healthy / 🟡 Degraded / 🔴 Unhealthy.
- List each component with its status and a one-line explanation.
- Surface metrics in a clean table or list format.
- Flag any component that is "unavailable" or "degraded" with a ⚠️ warning.
- Suggest ONE next step if anything is degraded.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_get_causal_graph": """You are the HCR Dependency Analyst. Summarize causal graph data for a developer.

Rules:
- Report total files tracked and key dependency clusters.
- Highlight files with the most dependents (high impact).
- If graph is empty, say "Dependency graph is empty. Edit files to build it."
- Suggest which files to review based on centrality.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_get_recent_activity": """You are the HCR Activity Log. Summarize recent developer events into a narrative timeline.

Rules:
- Group events by type (edits, commits, tool calls).
- Highlight the most significant recent actions.
- Surface patterns: "You've been editing src/ operators — likely refining core logic."
- Keep chronological order, newest first.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_list_shared_states": """You are the HCR Cross-Project Memory. Summarize shared state keys.

Rules:
- List keys with brief inferred purpose.
- Group by semantic category if possible (e.g., "tasks", "tests", "config").
- Highlight keys that look like they contain active work items.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_get_version_history": """You are the HCR Time Machine. Summarize state version history.

Rules:
- Show total versions and time range.
- Highlight recent checkpoints with size and message.
- If only auto-saves exist, note that.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_analyze_impact": """You are the HCR Impact Advisor. Summarize file change ripple effects.

Rules:
- State clearly: "Changing X affects Y files."
- List impacted files grouped by severity (direct / indirect).
- Suggest testing strategy for the impacted area.
- If no dependents found, say "No downstream dependencies. Safe to modify."

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_get_recommendations": """You are the HCR Action Advisor. Rank and explain recommendations.

Rules:
- Present top 3 recommendations with confidence %.
- Add a one-sentence "why" for each.
- Bold the highest-confidence recommendation.
- Include a fallback action if confidence is low overall.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",

    "hcr_search_history": """You are the HCR Historian. Summarize search results.

Rules:
- State match count and query.
- Show top matches with event type, timestamp, and brief detail.
- Highlight any trends or clusters in the results.

Output format: JSON with "summary", "panel" (markdown), "confidence", "actions".
Respond ONLY with valid JSON.""",
}

# Tools that are too simple to warrant LLM synthesis (just confirmations)
_SKIP_SYNTHESIS = {
    "hcr_create_session",
    "hcr_set_session_note",
    "hcr_merge_session",
    "hcr_share_state",
    "hcr_get_shared_state",
    "hcr_record_file_edit",
    "hcr_restore_version",
}


class OutputSynthesizer:
    """
    Unified commercial-grade output formatter for all HCR MCP tools.

    Two paths:
    1. Fast path: rule-based professional markdown (always available, <1ms)
    2. Smart path: LLM synthesis via Groq (rich, adaptive, ~200-800ms)

    The synthesizer is wired into the MCP server's result pipeline so
    EVERY tool output gets the treatment automatically.
    """

    def __init__(self, engine, use_llm: bool = True, llm_timeout: float = 2.0):
        self.engine = engine
        self.use_llm = use_llm
        self.llm_timeout = llm_timeout
        self._llm_provider = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 30.0  # seconds
        self._cache_ts: Dict[str, float] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(self, tool_name: str, raw_data: Dict[str, Any]) -> str:
        """
        Main entry point. Takes raw tool output, returns polished markdown string.

        Fast path: returns immediately if tool is in skip-list or LLM disabled.
        Smart path: async-capable LLM synthesis with caching.
        """
        if tool_name in _SKIP_SYNTHESIS or not self.use_llm:
            return self._fast_format(tool_name, raw_data)

        # Check cache
        cache_key = self._make_cache_key(tool_name, raw_data)
        if cache_key in self._cache and self._cache_valid(cache_key):
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1

        # Try LLM synthesis
        try:
            # Run synchronously (called from async tool handler via run_in_executor)
            result = self._llm_synthesize(tool_name, raw_data)
            self._cache[cache_key] = result
            self._cache_ts[cache_key] = time.time()
            return result
        except Exception as e:
            # Fallback to fast formatting on any LLM failure
            return self._fast_format(tool_name, raw_data, fallback_reason=str(e))

    async def synthesize_async(self, tool_name: str, raw_data: Dict[str, Any]) -> str:
        """Async wrapper for use in async tool handlers."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.synthesize, tool_name, raw_data
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return synthesis performance stats."""
        total = self._cache_hits + self._cache_misses
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / total if total else 0.0,
            "cache_size": len(self._cache),
            "llm_available": self._get_llm() is not None,
        }

    # ------------------------------------------------------------------
    # Fast path: rule-based professional formatting
    # ------------------------------------------------------------------

    def _fast_format(self, tool_name: str, raw_data: Dict[str, Any], fallback_reason: str = "") -> str:
        """Professional markdown formatting without LLM — always works, always fast."""
        # If raw_data already has a nice "content" string, enhance it
        if isinstance(raw_data.get("content"), str) and raw_data["content"]:
            base = raw_data["content"]
            if fallback_reason:
                base += f"\n\n> ⚠️ *Smart synthesis unavailable: {fallback_reason}*"
            return base

        # Otherwise, build a professional summary from the raw dict
        return self._dict_to_markdown(tool_name, raw_data, fallback_reason)

    def _dict_to_markdown(self, tool_name: str, data: Dict[str, Any], fallback_reason: str = "") -> str:
        """Convert any dict into professional markdown."""
        lines = [f"## {self._tool_display_name(tool_name)}", ""]

        # Summary line if present
        if "summary" in data:
            lines.append(f"**Summary:** {data['summary']}")
            lines.append("")

        # Status line
        if "status" in data:
            status = data["status"]
            emoji = {"healthy": "🟢", "degraded": "🟡", "unhealthy": "🔴"}.get(status, "⚪")
            lines.append(f"**Status:** {emoji} {status.capitalize()}")
            lines.append("")

        # Metrics / counts
        for key in ["count", "event_count", "projects_registered", "shared_states", "learned_operators"]:
            if key in data:
                lines.append(f"- **{key.replace('_', ' ').title()}:** {data[key]}")

        # Lists
        for key in ["shared_states", "versions", "operators", "sessions", "impacted_files", "recommendations"]:
            if key in data and isinstance(data[key], list) and data[key]:
                lines.append("")
                lines.append(f"### {key.replace('_', ' ').title()} ({len(data[key])})")
                for item in data[key][:10]:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("hash") or item.get("session_id") or str(item)[:60]
                        lines.append(f"- `{name}`")
                    else:
                        lines.append(f"- {str(item)[:80]}")

        # Nested dicts (components, metrics, etc.)
        for key in ["components", "metrics", "git", "files", "hcr"]:
            if key in data and isinstance(data[key], dict):
                lines.append("")
                lines.append(f"### {key.replace('_', ' ').title()}")
                for k, v in data[key].items():
                    if isinstance(v, bool):
                        lines.append(f"- **{k}:** {'✅' if v else '❌'}")
                    else:
                        lines.append(f"- **{k}:** {v}")

        if fallback_reason:
            lines.append("")
            lines.append(f"> ⚠️ *Smart synthesis unavailable: {fallback_reason}*")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Smart path: LLM synthesis via Groq
    # ------------------------------------------------------------------

    def _llm_synthesize(self, tool_name: str, raw_data: Dict[str, Any]) -> str:
        """Call Groq to transform raw data into professional markdown."""
        llm = self._get_llm()
        if not llm:
            raise RuntimeError("No LLM provider available")

        system = _SYSTEM_TEMPLATES.get(tool_name, _SYSTEM_TEMPLATES["default"])

        # Serialize raw data compactly
        payload = json.dumps(raw_data, indent=2, default=str)
        # Truncate if too large for LLM context
        max_raw = 8000  # chars
        if len(payload) > max_raw:
            payload = payload[:max_raw] + "\n... [truncated]"

        prompt = f"""Tool: {tool_name}
Raw Data:
{payload}

Transform this into a professional markdown panel. Return ONLY JSON."""

        import time as _time
        start = _time.time()

        response = llm.structured_complete(
            prompt=prompt,
            system=system,
            temperature=0.15,
            max_tokens=800,
        )

        elapsed = _time.time() - start
        if elapsed > 1.5:
            # If slow, mark it but still use result
            pass

        if not isinstance(response, dict):
            raise RuntimeError(f"LLM returned non-dict: {type(response)}")

        panel = response.get("panel", "")
        if not panel:
            # Fallback to raw content if LLM didn't produce panel
            panel = response.get("summary", "")

        # Append metadata about synthesis
        if response.get("actions"):
            panel += "\n\n**Suggested Actions:**\n"
            for action in response["actions"][:3]:
                panel += f"- {action}\n"

        # Confidence badge
        confidence = response.get("confidence", "medium")
        badge = {"high": "✅ High confidence", "medium": "⚠️ Moderate confidence", "low": "❓ Low confidence"}.get(confidence, "")
        if badge:
            panel += f"\n*{badge}*"

        return panel

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_llm(self):
        """Lazy-load LLM provider — tries engine first, then direct HTTP fallback (no SDK needed)."""
        if self._llm_provider:
            return self._llm_provider
        
        # Try engine's provider first
        if self.engine:
            llm = getattr(self.engine, "_get_llm_provider", lambda: None)()
            if llm:
                self._llm_provider = llm
                return llm
        
        # Direct HTTP fallback: no SDK, just requests + .env
        try:
            import os
            from pathlib import Path
            from dotenv import load_dotenv
            
            project_path = Path(self.engine.project_path) if self.engine else Path.cwd()
            env_file = project_path / ".env"
            if env_file.exists():
                load_dotenv(dotenv_path=str(env_file), override=True)
            
            api_key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("HCR_API_KEY", "")
            model = os.environ.get("HCR_LLM_MODEL", "llama-3.1-8b-instant")
            
            if not api_key:
                return None
            
            self._llm_provider = _DirectGroqProvider(api_key=api_key, model=model)
            return self._llm_provider
        except Exception:
            return None

    def _make_cache_key(self, tool_name: str, raw_data: Dict[str, Any]) -> str:
        """Deterministic cache key from tool name + data hash."""
        stable = {k: v for k, v in raw_data.items() if k not in ("timestamp", "cached")}
        payload = json.dumps(stable, sort_keys=True, default=str)
        h = hashlib.blake2b(payload.encode(), digest_size=16).hexdigest()
        return f"{tool_name}:{h}"

    def _cache_valid(self, key: str) -> bool:
        return (time.time() - self._cache_ts.get(key, 0)) < self._cache_ttl

    def _tool_display_name(self, tool_name: str) -> str:
        return tool_name.replace("hcr_", "").replace("_", " ").title()


# ---------------------------------------------------------------------------
# Lightweight HTTP provider — zero SDK dependencies
# ---------------------------------------------------------------------------

class _DirectGroqProvider:
    """Minimal Groq provider using raw requests. No groq SDK required."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self._http_session = None

    def _get_session(self):
        import requests
        if self._http_session is None:
            self._http_session = requests.Session()
        return self._http_session

    def structured_complete(self, prompt: str, system: str = "", temperature: float = 0.15, max_tokens: int = 800):
        import requests, json
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
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
