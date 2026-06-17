"""
writer.py
Serialises a GherkinFeature object back to a clean .feature file.
"""

from __future__ import annotations

from pathlib import Path

from .parser import GherkinFeature, GherkinScenario


def write(feature: GherkinFeature, output_path: str | Path) -> Path:
    """
    Write a GherkinFeature to a .feature file.

    Args:
        feature:     Validated GherkinFeature object.
        output_path: Destination path (created if it doesn't exist).

    Returns:
        Resolved Path of the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append(f"Feature: {feature.title}")
    if feature.description:
        lines.append(f"  {feature.description}")
    lines.append("")

    for scenario in feature.scenarios:
        lines.append(_render_scenario(scenario))

    content = "\n".join(lines).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")
    return path.resolve()


def _render_scenario(scenario: GherkinScenario) -> str:
    parts: list[str] = []

    if scenario.tags:
        parts.append("  " + " ".join(scenario.tags))

    parts.append(f"  Scenario: {scenario.title}")

    for step in scenario.steps:
        parts.append(f"    {step.keyword} {step.text}")

    parts.append("")
    return "\n".join(parts)
