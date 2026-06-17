"""
parser.py
Validates and parses raw Gherkin text returned by the LLM.
Raises GherkinValidationError with a detailed message on failure
so the generator can re-inject it into the next retry prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GherkinStep:
    keyword: str   # Given | When | Then | And | But
    text: str


@dataclass
class GherkinScenario:
    title: str
    tags: list[str] = field(default_factory=list)
    steps: list[GherkinStep] = field(default_factory=list)

    @property
    def is_happy_path(self) -> bool:
        return "@happy_path" in self.tags

    @property
    def is_error(self) -> bool:
        return "@error" in self.tags

    @property
    def is_edge_case(self) -> bool:
        return "@edge_case" in self.tags


@dataclass
class GherkinFeature:
    title: str
    description: str
    scenarios: list[GherkinScenario] = field(default_factory=list)

    @property
    def tags(self) -> list[str]:
        """Flatten all unique tags across scenarios."""
        seen: set[str] = set()
        result: list[str] = []
        for s in self.scenarios:
            for t in s.tags:
                if t not in seen:
                    seen.add(t)
                    result.append(t)
        return result


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class GherkinValidationError(Exception):
    """Raised when the LLM output does not pass Gherkin validation."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

STEP_KEYWORDS = ("Given", "When", "Then", "And", "But")
TAG_RE = re.compile(r"@[\w\-]+")


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the LLM wrapped its output."""
    text = re.sub(r"^```[^\n]*\n", "", text.strip())
    text = re.sub(r"\n```$", "", text.strip())
    return text.strip()


def parse(raw: str) -> GherkinFeature:
    """
    Parse raw Gherkin text into a GherkinFeature object.

    Args:
        raw: Raw string returned by the LLM.

    Returns:
        GherkinFeature populated with scenarios and steps.

    Raises:
        GherkinValidationError: If structure or content is invalid.
    """
    text = _strip_fences(raw)

    if not text:
        raise GherkinValidationError("LLM returned an empty response.")

    lines = text.splitlines()

    # ---- Feature line -------------------------------------------------------
    feature_title = ""
    feature_desc_lines: list[str] = []
    feature_line_idx = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("feature:"):
            feature_title = stripped[len("feature:"):].strip()
            feature_line_idx = i
            break
    else:
        raise GherkinValidationError(
            "No 'Feature:' block found. The output must start with 'Feature: <name>'."
        )

    # ---- Split into scenario blocks -----------------------------------------
    scenarios: list[GherkinScenario] = []
    current_tags: list[str] = []
    current_scenario: GherkinScenario | None = None
    in_feature_desc = True

    for line in lines[feature_line_idx + 1:]:
        stripped = line.strip()

        # Feature-level description (before first scenario/tag block)
        if in_feature_desc and stripped and not stripped.startswith("@") and not stripped.lower().startswith("scenario"):
            feature_desc_lines.append(stripped)
            continue

        # Tag line
        if stripped.startswith("@"):
            if current_scenario is not None:
                scenarios.append(current_scenario)
                current_scenario = None
            current_tags = TAG_RE.findall(stripped)
            in_feature_desc = False
            continue

        # Scenario line
        if stripped.lower().startswith("scenario:") or stripped.lower().startswith("scenario outline:"):
            in_feature_desc = False
            title = re.sub(r"^scenario( outline)?:\s*", "", stripped, flags=re.IGNORECASE)
            current_scenario = GherkinScenario(title=title, tags=list(current_tags))
            current_tags = []
            continue

        # Step line
        if current_scenario is not None and stripped:
            for kw in STEP_KEYWORDS:
                if stripped.startswith(kw + " ") or stripped == kw:
                    step_text = stripped[len(kw):].strip()
                    current_scenario.steps.append(GherkinStep(keyword=kw, text=step_text))
                    break

    # Flush last scenario
    if current_scenario is not None:
        scenarios.append(current_scenario)

    feature = GherkinFeature(
        title=feature_title,
        description=" ".join(feature_desc_lines),
        scenarios=scenarios,
    )

    _validate(feature)
    return feature


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(feature: GherkinFeature) -> None:
    errors: list[str] = []

    if not feature.title:
        errors.append("Feature title is empty.")

    if not feature.scenarios:
        errors.append("No scenarios were found in the output.")

    if len(feature.scenarios) < 3:
        errors.append(
            f"Only {len(feature.scenarios)} scenario(s) found. Expected at least 3 "
            "(1 happy path, 1 error, 1 edge case)."
        )

    has_happy = any(s.is_happy_path for s in feature.scenarios)
    has_error = any(s.is_error for s in feature.scenarios)

    if not has_happy:
        errors.append("No happy path scenario found. Tag one scenario with @happy_path.")
    if not has_error:
        errors.append("No error scenario found. Tag at least one scenario with @error.")

    for s in feature.scenarios:
        if not s.steps:
            errors.append(f"Scenario '{s.title}' has no steps.")
        if not any(step.keyword in ("Given", "When", "Then") for step in s.steps):
            errors.append(
                f"Scenario '{s.title}' must contain at least one Given, When, and Then step."
            )

    if errors:
        raise GherkinValidationError(
            "Gherkin validation failed with the following issues:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
