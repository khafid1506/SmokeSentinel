"""
generator.py
Main orchestrator for the Gherkin Scenario Generator.

The LLM backend is pluggable — switch without touching this file:

    # Free local inference via Ollama
    GHERKIN_BACKEND=ollama GHERKIN_MODEL=mistral python agent/sentinel.py --story JIRA-1234

    # Anthropic Claude (cheapest model)
    GHERKIN_BACKEND=anthropic GHERKIN_MODEL=claude-haiku-4-5-20251001 python agent/sentinel.py --story JIRA-1234

    # LM Studio (local, free)
    GHERKIN_BACKEND=openai OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio ...

    # Groq (cloud, free tier, very fast)
    GHERKIN_BACKEND=openai OPENAI_BASE_URL=https://api.groq.com/openai/v1 OPENAI_API_KEY=<key> ...

Or in Python:
    from gherkin import GherkinGenerator
    from gherkin.backends import OllamaBackend

    gen = GherkinGenerator(backend=OllamaBackend(model="mistral"))
    result = gen.run(story_title="User Login", ...)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backends import LLMBackend, get_backend
from .parser import GherkinFeature, GherkinScenario, GherkinValidationError, parse
from .prompt_builder import build_user_prompt, load_system_prompt
from .writer import write

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (overridable via env vars)
# ---------------------------------------------------------------------------

DEFAULT_MAX_SCENARIOS = int(os.getenv("GHERKIN_MAX_SCENARIOS", "6"))
DEFAULT_OUTPUT_DIR    = os.getenv("GHERKIN_OUTPUT_DIR", "tests/features")
MAX_RETRIES           = 2
MAX_TOKENS            = 2048


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

@dataclass
class GeneratorResult:
    feature: GherkinFeature
    feature_file: Path
    raw_llm_output: str

    @property
    def scenarios(self) -> list[GherkinScenario]:
        return self.feature.scenarios

    @property
    def tags(self) -> list[str]:
        return self.feature.tags

    def to_json(self) -> dict[str, Any]:
        return {
            "feature": self.feature.title,
            "feature_file": str(self.feature_file),
            "scenario_count": len(self.scenarios),
            "tags": self.tags,
            "scenarios": [
                {
                    "title": s.title,
                    "tags": s.tags,
                    "steps": [{"keyword": st.keyword, "text": st.text} for st in s.steps],
                }
                for s in self.scenarios
            ],
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class GherkinGenerator:
    """
    Transforms a Jira User Story into Gherkin scenarios.

    The LLM backend is fully interchangeable:

        # Auto-select (Ollama if no ANTHROPIC_API_KEY, else Anthropic)
        gen = GherkinGenerator()

        # Explicit Ollama
        from gherkin.backends import OllamaBackend
        gen = GherkinGenerator(backend=OllamaBackend(model="mistral"))

        # Explicit Anthropic (cheapest model)
        from gherkin.backends import AnthropicBackend
        gen = GherkinGenerator(backend=AnthropicBackend(model="claude-haiku-4-5-20251001"))

        # Groq via OpenAI-compatible backend
        from gherkin.backends import OpenAIBackend
        gen = GherkinGenerator(backend=OpenAIBackend(
            base_url="https://api.groq.com/openai/v1",
            api_key="...",
            model="llama-3.1-8b-instant",
        ))
    """

    def __init__(self, backend: LLMBackend | None = None) -> None:
        self._backend = backend or get_backend()
        self._system_prompt = load_system_prompt()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        story_title: str,
        story_description: str = "",
        acceptance_criteria: list[str] | None = None,
        output_path: str | Path | None = None,
        story_id: str | None = None,
    ) -> GeneratorResult:
        """
        Generate Gherkin scenarios for a Jira story and write them to disk.

        Args:
            story_title:          Story title (required).
            story_description:    Story body / description (optional).
            acceptance_criteria:  List of AC strings (optional).
            output_path:          Destination .feature file path.
                                  Defaults to <GHERKIN_OUTPUT_DIR>/<story_id>.feature
            story_id:             Jira issue key (e.g. "JIRA-1234").

        Returns:
            GeneratorResult with the parsed feature, file path, and raw LLM output.
        """
        ac   = acceptance_criteria or []
        dest = self._resolve_output_path(output_path, story_title, story_id)

        user_prompt = build_user_prompt(story_title, story_description, ac)
        raw, feature = self._generate_with_retry(user_prompt)

        feature_file = write(feature, dest)

        meta_path = feature_file.with_suffix(".json")
        result = GeneratorResult(feature=feature, feature_file=feature_file, raw_llm_output=raw)
        meta_path.write_text(json.dumps(result.to_json(), indent=2), encoding="utf-8")

        logger.info("✔ Generated %d scenario(s) → %s", len(feature.scenarios), feature_file)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_with_retry(self, user_prompt: str) -> tuple[str, GherkinFeature]:
        last_error = ""

        for attempt in range(1, MAX_RETRIES + 2):
            prompt = user_prompt if attempt == 1 else self._build_retry_prompt(user_prompt, last_error, attempt)

            logger.debug("LLM call — attempt %d/%d", attempt, MAX_RETRIES + 1)
            raw = self._backend.complete(self._system_prompt, prompt, MAX_TOKENS)

            try:
                feature = parse(raw)
                return raw, feature
            except GherkinValidationError as exc:
                last_error = str(exc)
                logger.warning("Validation failed (attempt %d): %s", attempt, last_error)
                if attempt == MAX_RETRIES + 1:
                    raise

        raise RuntimeError("Unexpected retry loop exit")

    def _build_retry_prompt(self, original_prompt: str, error: str, attempt: int) -> str:
        return (
            f"{original_prompt}\n\n"
            f"---\n"
            f"## ⚠️ Previous attempt {attempt - 1} failed validation\n\n"
            f"Please fix the following issues and regenerate the complete Gherkin output:\n\n"
            f"{error}\n\n"
            f"Output ONLY valid Gherkin. Start directly with 'Feature:'. No explanations."
        )

    @staticmethod
    def _resolve_output_path(
        output_path: str | Path | None,
        story_title: str,
        story_id: str | None,
    ) -> Path:
        if output_path:
            return Path(output_path)
        slug = story_id or _slugify(story_title)
        return Path(DEFAULT_OUTPUT_DIR) / f"{slug}.feature"


def _slugify(text: str) -> str:
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:60]
