"""
prompt_builder.py
Builds the user-facing LLM prompt from a Jira story dict.
"""

from pathlib import Path

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "gherkin_base.txt"


def load_system_prompt() -> str:
    """Load the system prompt template from disk."""
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def build_user_prompt(
    story_title: str,
    story_description: str,
    acceptance_criteria: list[str],
) -> str:
    """
    Build the user prompt sent to the LLM.

    Args:
        story_title:          Jira story title (e.g. "User Login")
        story_description:    Full story description / body
        acceptance_criteria:  List of AC strings (e.g. ["AC1: ...", "AC2: ..."])

    Returns:
        Formatted user prompt string.
    """
    ac_block = "\n".join(f"  - {ac}" for ac in acceptance_criteria) if acceptance_criteria else "  (none provided)"

    return f"""Please generate Gherkin scenarios for the following Jira User Story.

## Story Title
{story_title}

## Description
{story_description.strip() if story_description else "(no description provided)"}

## Acceptance Criteria
{ac_block}

Generate the Gherkin scenarios now.
"""
