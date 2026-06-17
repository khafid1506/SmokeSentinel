#!/usr/bin/env python3
"""
sentinel.py — SmokeSentinel main agent entrypoint.

Orchestrates the full smoke-testing lifecycle:
    Jira User Story → Gherkin scenarios → Playwright tests → AI diagnosis → Report & alerts

Usage:
    python agent/sentinel.py --story JIRA-1234
    python agent/sentinel.py --story JIRA-1234 --title "User Login" --desc "As a user..."

If no GHERKIN_BACKEND env var is set, sentinel will interactively prompt
you to choose a free LLM backend at startup.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or agent/ directory
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gherkin import GherkinGenerator
from gherkin.backends import OllamaBackend, OpenAIBackend
from gherkin.parser import GherkinValidationError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sentinel")


# ---------------------------------------------------------------------------
# Interactive LLM backend selector
# ---------------------------------------------------------------------------

def select_backend_interactively() -> GherkinGenerator:
    """
    Prompt the user to choose a free LLM backend when none is configured.
    Displayed only when GHERKIN_BACKEND env var is not set.

    Returns a configured GherkinGenerator ready to use.
    """
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        SentinelMCP — Choose your LLM backend                ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  All options below are FREE                                  ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                              ║")
    print("║  [1]  Ollama     — local models, runs on your machine       ║")
    print("║                    no internet needed after setup            ║")
    print("║                                                              ║")
    print("║  [2]  LM Studio  — local models, graphical interface        ║")
    print("║                    drag-and-drop model management            ║")
    print("║                                                              ║")
    print("║  [3]  Groq       — cloud, extremely fast, generous free tier ║")
    print("║                    requires a free API key at console.groq.com║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    while True:
        choice = input("  Enter your choice [1 / 2 / 3]: ").strip()
        if choice in ("1", "2", "3"):
            break
        print("  Please enter 1, 2, or 3.")

    print()

    # ── Option 1: Ollama ─────────────────────────────────────────────────────
    if choice == "1":
        print("  ┌─ Ollama setup ─────────────────────────────────────────────┐")
        print("  │                                                             │")
        print("  │  One-time setup (skip if already done):                    │")
        print("  │    1. Install Ollama → https://ollama.com                  │")
        print("  │    2. Pull a model  → ollama pull mistral                  │")
        print("  │         alternatives: llama3, gemma2, codellama             │")
        print("  │                                                             │")
        print("  │  Every time:                                                │")
        print("  │    3. Start the server → ollama serve  (keep it open)      │")
        print("  │                                                             │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        print("  Recommended models by speed (fastest first):")
        print("    phi3        — 2 GB — very fast, good quality  ← recommended if timeout")
        print("    mistral     — 4 GB — fast, excellent quality")
        print("    llama3      — 5 GB — best quality, slower")
        print("    gemma2      — 5 GB — good balance")
        print()
        model = input("  Model name [default: phi3]: ").strip() or "phi3"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        timeout  = os.getenv("OLLAMA_TIMEOUT", "300")

        print()
        print(f"  ✔  Using Ollama  url={base_url}  model={model}  timeout={timeout}s")
        print( "  ℹ  If you get a timeout, try: set OLLAMA_TIMEOUT=600")
        print( "     or switch to phi3 which is 2x faster than mistral")
        print()
        return GherkinGenerator(backend=OllamaBackend(model=model, base_url=base_url))

    # ── Option 2: LM Studio ──────────────────────────────────────────────────
    if choice == "2":
        print("  ┌─ LM Studio setup ──────────────────────────────────────────┐")
        print("  │                                                             │")
        print("  │  One-time setup (skip if already done):                    │")
        print("  │    1. Install LM Studio → https://lmstudio.ai              │")
        print("  │    2. Download a model inside LM Studio (e.g. Mistral)     │")
        print("  │                                                             │")
        print("  │  Every time:                                                │")
        print("  │    3. Open LM Studio → Local Server → Start Server         │")
        print("  │         (default port: 1234)                                │")
        print("  │                                                             │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        default_url = "http://localhost:1234/v1"
        base_url = input(f"  LM Studio server URL [default: {default_url}]: ").strip() or default_url
        model = input("  Model name as shown in LM Studio: ").strip()

        if not model:
            print("  ✘  Model name is required for LM Studio. Aborting.")
            sys.exit(1)

        print()
        print(f"  ✔  Using LM Studio  url={base_url}  model={model}")
        print()
        return GherkinGenerator(backend=OpenAIBackend(
            base_url=base_url,
            api_key="lm-studio",   # LM Studio accepts any non-empty string
            model=model,
        ))

    # ── Option 3: Groq ───────────────────────────────────────────────────────
    if choice == "3":
        print("  ┌─ Groq setup ───────────────────────────────────────────────┐")
        print("  │                                                             │")
        print("  │  One-time setup (skip if already done):                    │")
        print("  │    1. Create a free account → https://console.groq.com     │")
        print("  │    2. Generate an API key in the console                   │")
        print("  │                                                             │")
        print("  │  Recommended free models:                                   │")
        print("  │    llama-3.1-8b-instant   (fastest)                        │")
        print("  │    llama-3.3-70b-versatile (best quality)                  │")
        print("  │    gemma2-9b-it                                             │")
        print("  │                                                             │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        api_key = os.getenv("OPENAI_API_KEY") or input("  Groq API key: ").strip()
        if not api_key:
            print("  ✘  API key is required for Groq. Aborting.")
            sys.exit(1)

        default_model = "llama-3.1-8b-instant"
        model = input(f"  Model name [default: {default_model}]: ").strip() or default_model

        print()
        print(f"  ✔  Using Groq  model={model}")
        print()
        return GherkinGenerator(backend=OpenAIBackend(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model,
        ))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sentinel",
        description="SmokeSentinel — autonomous QA agent for AI-driven smoke testing.",
    )
    p.add_argument(
        "--story", required=True, metavar="JIRA-ID",
        help="Jira issue key (e.g. SMOKE-42). Used to name the output .feature file.",
    )
    p.add_argument(
        "--title", default="", metavar="TEXT",
        help="Story title. Falls back to the --story key if omitted.",
    )
    p.add_argument(
        "--desc", default="", metavar="TEXT",
        help="Story description / body text.",
    )
    p.add_argument(
        "--ac", nargs="*", default=[], metavar="AC",
        help="Acceptance criteria, one string per AC. Example: --ac 'AC1: ...' 'AC2: ...'",
    )
    p.add_argument(
        "--output-dir", default=os.getenv("GHERKIN_OUTPUT_DIR", "tests/features"),
        metavar="DIR",
        help="Directory where .feature files are written (default: tests/features).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print what would happen without calling the LLM.",
    )
    return p


# ---------------------------------------------------------------------------
# Steps (one function per pipeline stage — easy to extend)
# ---------------------------------------------------------------------------

def step_generate_gherkin(
    generator: GherkinGenerator,
    story_id: str,
    story_title: str,
    story_description: str,
    acceptance_criteria: list[str],
    output_dir: str,
) -> Path:
    """
    Stage 1 — Gherkin Scenario Generator.
    Calls the configured LLM backend to produce BDD scenarios from the Jira
    story data, validates the output, retries on failure, and writes the
    .feature file.

    Returns the path to the generated .feature file.
    """
    logger.info("━━━  Stage 1 / Gherkin Generation  ━━━")
    logger.info("Story : %s — %s", story_id, story_title)

    result = generator.run(
        story_title=story_title or story_id,
        story_description=story_description,
        acceptance_criteria=acceptance_criteria,
        story_id=story_id,
        output_path=Path(output_dir) / f"{story_id}.feature",
    )

    logger.info("✔  %d scenario(s) generated", len(result.scenarios))
    logger.info("✔  Feature file : %s", result.feature_file)
    logger.info("✔  Tags         : %s", ", ".join(result.tags))

    for i, scenario in enumerate(result.scenarios, 1):
        tag_str = " ".join(scenario.tags)
        logger.info("    [%d] %s  %s", i, scenario.title, tag_str)

    return result.feature_file


def step_run_playwright(feature_file: Path) -> None:
    """Stage 2 — Playwright MCP runner (not yet implemented)."""
    logger.info("━━━  Stage 2 / Playwright Execution  ━━━")
    logger.info("    Feature file : %s", feature_file)
    logger.info("    ⏳ Coming soon — Playwright MCP integration.")


def step_ai_diagnosis() -> None:
    """Stage 3 — AI failure diagnosis (not yet implemented)."""
    logger.info("━━━  Stage 3 / AI Failure Diagnosis  ━━━")
    logger.info("    ⏳ Coming soon.")


def step_report_and_alert() -> None:
    """Stage 4 — HTML report + Slack/Teams alerts (not yet implemented)."""
    logger.info("━━━  Stage 4 / Report & Alerts  ━━━")
    logger.info("    ⏳ Coming soon.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = build_parser().parse_args()

    story_id: str          = args.story
    story_title: str       = args.title or story_id
    story_description: str = args.desc
    acceptance_criteria: list[str] = args.ac
    output_dir: str        = args.output_dir
    backend_name: str      = os.getenv("GHERKIN_BACKEND", "")

    # ── Dry-run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[dry-run] Would run the following pipeline:")
        print(f"  Story ID    : {story_id}")
        print(f"  Title       : {story_title}")
        print(f"  Description : {story_description or '(none)'}")
        print(f"  AC          : {acceptance_criteria or '(none)'}")
        print(f"  Output dir  : {output_dir}")
        print(f"  Backend     : {backend_name or 'interactive selection at startup'}")
        print(f"  Stages      : Gherkin → Playwright → Diagnosis → Report\n")
        return

    logger.info("════  SentinelMCP  ════  story=%s  ════", story_id)

    # ── Backend selection ─────────────────────────────────────────────────────
    # If GHERKIN_BACKEND is set in the environment, use it silently.
    # Otherwise, show the interactive menu so the user can pick a free backend.
    if backend_name:
        # Non-interactive: backend already configured via env var
        generator = GherkinGenerator()
    else:
        # Interactive: prompt the user to choose
        generator = select_backend_interactively()

    # ── Stage 1: Gherkin generation ───────────────────────────────────────────
    try:
        feature_file = step_generate_gherkin(
            generator=generator,
            story_id=story_id,
            story_title=story_title,
            story_description=story_description,
            acceptance_criteria=acceptance_criteria,
            output_dir=output_dir,
        )
    except GherkinValidationError as exc:
        logger.error("Gherkin generation failed after retries: %s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        # Catches "Cannot reach Ollama" or similar backend connection errors
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected error during Gherkin generation: %s", exc)
        raise

    # ── Stage 2: Playwright execution ─────────────────────────────────────────
    step_run_playwright(feature_file)

    # ── Stage 3: AI diagnosis ─────────────────────────────────────────────────
    step_ai_diagnosis()

    # ── Stage 4: Report & alerts ──────────────────────────────────────────────
    step_report_and_alert()

    logger.info("════  Pipeline complete  ════")


if __name__ == "__main__":
    main()
