"""
HCR LLM Provider Package

Abstracts away LLM provider differences behind a unified interface.
"""

from .llm_provider import LLMProvider, LLMResponse, get_provider

__all__ = ["LLMProvider", "LLMResponse", "get_provider"]
