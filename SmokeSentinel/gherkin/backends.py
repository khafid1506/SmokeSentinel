"""
backends.py
Interchangeable LLM backends for the Gherkin Generator.

Supported backends:
    - anthropic   : Claude via Anthropic API (requires ANTHROPIC_API_KEY)
    - ollama      : Local models via Ollama REST API (free, no API key)
    - openai      : OpenAI or any OpenAI-compatible endpoint (LM Studio, vLLM, etc.)

Select via env var:
    GHERKIN_BACKEND=ollama
    GHERKIN_BACKEND=anthropic   (default)
    GHERKIN_BACKEND=openai

Quick start with Ollama (100% free, runs locally):
    1. Install  → https://ollama.com
    2. Pull     → ollama pull mistral   (or llama3, codellama, gemma2…)
    3. Run      → ollama serve          (starts on http://localhost:11434)
    4. Set env  → GHERKIN_BACKEND=ollama  GHERKIN_MODEL=mistral
    5. Launch   → python agent/sentinel.py --story JIRA-1234
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class LLMBackend(ABC):
    """All backends implement this single method."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        """Send prompts to the LLM and return the raw text response."""


# ---------------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------------

class AnthropicBackend(LLMBackend):
    """
    Claude via the official Anthropic API.
    Requires: pip install anthropic
    Env vars: ANTHROPIC_API_KEY, GHERKIN_MODEL (default: claude-haiku-4-5-20251001)

    Tip: claude-haiku-4-5-20251001 is the cheapest Claude model — good enough for Gherkin
         and ~10x cheaper than Sonnet.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install anthropic")

        self.model = model or os.getenv("GHERKIN_MODEL", "claude-haiku-4-5-20251001")
        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        logger.info("Backend: Anthropic Claude  model=%s", self.model)

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text


# ---------------------------------------------------------------------------
# Ollama  (local, free)
# ---------------------------------------------------------------------------

class OllamaBackend(LLMBackend):
    """
    Local models via Ollama — 100% free, no API key, runs on your machine.
    Requires: https://ollama.com  +  ollama pull <model>
    Env vars: OLLAMA_BASE_URL (default: http://localhost:11434)
              GHERKIN_MODEL   (default: mistral)

    Recommended models for Gherkin generation:
        mistral       — fast, good instruction following  (4 GB)
        llama3        — stronger reasoning               (5 GB)
        gemma2        — lightweight, solid quality       (5 GB)
        codellama     — code-oriented, great for BDD     (4 GB)
    """

    # Default timeout in seconds. Increase if your machine is slow or the model is large.
    # Can be overridden via OLLAMA_TIMEOUT env var.
    DEFAULT_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        try:
            import requests  # noqa: F401
        except ImportError:
            raise ImportError("Run: pip install requests")

        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("GHERKIN_MODEL", "mistral")
        self.timeout = self.DEFAULT_TIMEOUT
        logger.info("Backend: Ollama  url=%s  model=%s  timeout=%ds", self.base_url, self.model, self.timeout)

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        import requests

        # Limit max_tokens for local models to keep generation fast
        effective_tokens = min(max_tokens, int(os.getenv("OLLAMA_MAX_TOKENS", "1024")))

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "num_predict": effective_tokens,
                "temperature": 0.2,   # lower = faster + more deterministic output
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve"
            )
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                f"Ollama timed out after {self.timeout}s. "
                "Try one of the following:\n"
                "  1. Use a lighter model  →  ollama pull phi3       (2 GB, very fast)\n"
                "  2. Increase the timeout →  set OLLAMA_TIMEOUT=600\n"
                "  3. Reduce output size   →  set OLLAMA_MAX_TOKENS=512"
            )

        data = resp.json()
        return data["message"]["content"]


# ---------------------------------------------------------------------------
# OpenAI-compatible  (OpenAI, LM Studio, vLLM, Groq, Together AI…)
# ---------------------------------------------------------------------------

class OpenAIBackend(LLMBackend):
    """
    OpenAI API or any OpenAI-compatible endpoint.
    Works with: OpenAI, LM Studio (local), vLLM, Groq, Together AI, Mistral AI…

    Requires: pip install openai
    Env vars:
        OPENAI_API_KEY   — API key (use 'ollama' or 'lm-studio' for local endpoints)
        OPENAI_BASE_URL  — Override endpoint (e.g. http://localhost:1234/v1 for LM Studio)
        GHERKIN_MODEL    — Model name (e.g. gpt-4o-mini, mistral-small, llama-3.1-8b)

    LM Studio (local, free):
        1. Download → https://lmstudio.ai
        2. Load a model and start the local server (port 1234)
        3. Set GHERKIN_BACKEND=openai  OPENAI_BASE_URL=http://localhost:1234/v1
           OPENAI_API_KEY=lm-studio  GHERKIN_MODEL=<model-name-from-lmstudio>

    Groq (cloud, very fast, generous free tier):
        GHERKIN_BACKEND=openai
        OPENAI_BASE_URL=https://api.groq.com/openai/v1
        OPENAI_API_KEY=<your-groq-key>
        GHERKIN_MODEL=llama-3.1-8b-instant
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Run: pip install openai")

        from openai import OpenAI

        resolved_key = api_key or os.getenv("OPENAI_API_KEY", "no-key")
        resolved_url = base_url or os.getenv("OPENAI_BASE_URL")  # None = official OpenAI
        self.model = model or os.getenv("GHERKIN_MODEL", "gpt-4o-mini")

        self.client = OpenAI(api_key=resolved_key, base_url=resolved_url)
        logger.info(
            "Backend: OpenAI-compatible  url=%s  model=%s",
            resolved_url or "https://api.openai.com",
            self.model,
        )

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

BACKENDS: dict[str, type[LLMBackend]] = {
    "anthropic": AnthropicBackend,
    "ollama":    OllamaBackend,
    "openai":    OpenAIBackend,
}


def get_backend(name: str | None = None, **kwargs) -> LLMBackend:
    """
    Instantiate the right backend.

    Priority:
        1. `name` argument
        2. GHERKIN_BACKEND env var
        3. Falls back to 'ollama' if no Anthropic key is set, else 'anthropic'

    Args:
        name:    Backend name: 'anthropic' | 'ollama' | 'openai'
        kwargs:  Forwarded to the backend constructor.

    Returns:
        Configured LLMBackend instance.
    """
    if name is None:
        name = os.getenv("GHERKIN_BACKEND")

    if name is None:
        # Smart default: use Ollama if no Anthropic key is configured
        name = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "ollama"
        logger.info("GHERKIN_BACKEND not set — auto-selected: %s", name)

    name = name.lower()
    if name not in BACKENDS:
        raise ValueError(
            f"Unknown backend '{name}'. Choose from: {', '.join(BACKENDS)}"
        )

    return BACKENDS[name](**kwargs)
