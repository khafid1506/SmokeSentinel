#!/usr/bin/env python3
"""
scaffold.py

PROJECT SCAFFOLDER — SmokeSentinel
====================================

Creates the full SmokeSentinel directory and file structure.
Safe to run multiple times: existing files and folders are never
overwritten — only missing items are created.

Structure created:
    SmokeSentinel/
    ├── agent/
    │   ├── sentinel.py
    │   ├── tools/
    │   └── prompts/
    ├── gherkin/
    ├── reporter/
    ├── notifier/
    ├── scripts/
    │   ├── git_commit_push.py   (placeholder if absent)
    │   ├── github_auth_setup.py (placeholder if absent)
    │   └── env_check.py         (placeholder if absent)
    ├── tests/
    │   └── fixtures/
    ├── docker/
    ├── reports/
    │   └── .gitkeep
    ├── .env.example
    ├── .gitignore
    └── README.md

Usage:
    python scaffold.py                        # creates SmokeSentinel/ in current dir
    python scaffold.py --root /path/to/dir   # creates it elsewhere
    python scaffold.py --dry-run             # preview without touching the filesystem
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# ANSI colors
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"
    BLUE    = "\033[94m"


def ok(msg: str)   -> None: print(f"{C.GREEN}  ✔  {msg}{C.RESET}")
def skip(msg: str) -> None: print(f"{C.YELLOW}  ─  {msg}{C.RESET}")
def info(msg: str) -> None: print(f"{C.CYAN}  ℹ  {msg}{C.RESET}")
def dry(msg: str)  -> None: print(f"{C.BLUE}  ~  {msg}{C.RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# File contents — stubs for each source file
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: relative path (from project root) → file content string
# Folders are inferred from any path that ends with /
# Files with content "" get a minimal stub header

YEAR = datetime.now().year

FILE_CONTENTS: dict[str, str] = {

    # ── agent/ ────────────────────────────────────────────────────────── #

    "agent/__init__.py": '"""SmokeSentinel agent package."""\n',

    "agent/sentinel.py": f'''\
#!/usr/bin/env python3
"""
sentinel.py — SmokeSentinel main agent entrypoint.

Orchestrates the full smoke-testing lifecycle:
    Jira User Story → Gherkin scenarios → Playwright tests → AI diagnosis → Report & alerts

Usage:
    python agent/sentinel.py --story JIRA-1234
"""

# TODO: implement agent entrypoint
def main() -> None:
    print("SentinelMCP agent — coming soon.")

if __name__ == "__main__":
    main()
''',

    "agent/tools/__init__.py": '"""MCP tools and Playwright wrappers."""\n',

    "agent/tools/playwright_tool.py": '''\
"""
playwright_tool.py

Playwright MCP tool wrapper for the SentinelMCP agent.
Wraps Playwright MCP calls into LangChain-compatible tool objects.
"""

# TODO: implement Playwright MCP tool
''',

    "agent/tools/jira_tool.py": '''\
"""
jira_tool.py

Jira API tool for the SentinelMCP agent.
Fetches User Stories and acceptance criteria from a Jira project.
"""

# TODO: implement Jira tool
''',

    "agent/prompts/__init__.py": '"""LLM prompt templates."""\n',

    "agent/prompts/gherkin_gen.md": '''\
# Prompt — Gherkin Scenario Generator

You are a senior QA engineer. Given the following Jira User Story,
generate clean Gherkin scenarios (Feature / Scenario / Given / When / Then).

## Rules
- Cover the happy path and at least one negative case.
- Keep scenarios atomic and independent.
- Use concrete, realistic test data — no placeholders.

## User Story
{user_story}

## Output
Return only the Gherkin block, no explanation.
''',

    "agent/prompts/failure_diagnosis.md": '''\
# Prompt — AI Failure Diagnosis

You are a senior SDET. A Playwright smoke test has just failed.
Analyse the error and provide:
1. Root cause (one sentence)
2. Severity: CRITICAL / HIGH / MEDIUM / LOW
3. Suggested fix (bullet points)

## Test context
{test_context}

## Error output
{error_output}
''',

    # ── gherkin/ ──────────────────────────────────────────────────────── #

    "gherkin/__init__.py": '"""Gherkin scenario generator package."""\n',

    "gherkin/generator.py": '''\
"""
generator.py

Generates Gherkin .feature files from Jira User Stories
using an LLM (Claude / OpenAI) via LangChain.
"""

# TODO: implement Gherkin generator
''',

    "gherkin/output/.gitkeep": "",

    # ── reporter/ ─────────────────────────────────────────────────────── #

    "reporter/__init__.py": '"""Test report builder package."""\n',

    "reporter/builder.py": '''\
"""
builder.py

Builds HTML and Markdown reports from SentinelMCP test run results.
"""

# TODO: implement report builder
''',

    "reporter/templates/report.html": '''\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SmokeSentinel — Test Report</title>
</head>
<body>
  <h1>🛰️ SmokeSentinel — Test Report</h1>
  <!-- TODO: Jinja2 template -->
</body>
</html>
''',

    "reporter/output/.gitkeep": "",

    # ── notifier/ ─────────────────────────────────────────────────────── #

    "notifier/__init__.py": '"""Slack & Teams alert dispatcher package."""\n',

    "notifier/slack.py": '''\
"""
slack.py

Sends Slack notifications on critical smoke test regressions
via an incoming webhook URL (SLACK_WEBHOOK_URL).
"""

# TODO: implement Slack notifier
''',

    "notifier/teams.py": '''\
"""
teams.py

Sends Microsoft Teams notifications on critical smoke test regressions
via an incoming webhook URL (TEAMS_WEBHOOK_URL).
"""

# TODO: implement Teams notifier
''',

    # ── scripts/ ──────────────────────────────────────────────────────── #
    # These are the real admin scripts — scaffold creates stubs only if
    # the file does not already exist (the real versions live here).

    "scripts/__init__.py": "",

    "scripts/git_commit_push.py": '''\
#!/usr/bin/env python3
"""
git_commit_push.py — Safe Git commit & push workflow.
See full implementation in the SmokeSentinel scripts/ folder.
"""
# TODO: paste or copy the full git_commit_push.py implementation here.
''',

    "scripts/github_auth_setup.py": '''\
#!/usr/bin/env python3
"""
github_auth_setup.py — GitHub SSH / PAT authentication setup.
See full implementation in the SmokeSentinel scripts/ folder.
"""
# TODO: paste or copy the full github_auth_setup.py implementation here.
''',

    "scripts/env_check.py": '''\
#!/usr/bin/env python3
"""
env_check.py — Pre-launch environment validator.
See full implementation in the SmokeSentinel scripts/ folder.
"""
# TODO: paste or copy the full env_check.py implementation here.
''',

    # ── tests/ ────────────────────────────────────────────────────────── #

    "tests/__init__.py": "",

    "tests/conftest.py": '''\
"""
conftest.py

Pytest configuration and shared fixtures for SmokeSentinel smoke tests.
"""
import pytest

# TODO: add shared fixtures (Playwright browser, base URL, auth tokens…)
''',

    "tests/fixtures/__init__.py": "",

    "tests/fixtures/sample_story.json": '''\
{
  "key": "SMOKE-1",
  "summary": "User can log in with valid credentials",
  "description": "As a registered user, I want to log in so that I can access my dashboard.",
  "acceptance_criteria": [
    "Given valid credentials, the user is redirected to the dashboard.",
    "Given invalid credentials, an error message is shown.",
    "Given an empty form, the submit button is disabled."
  ]
}
''',

    # ── docker/ ───────────────────────────────────────────────────────── #

    "docker/Dockerfile": '''\
# SmokeSentinel — Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \\
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \\
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \\
    libxfixes3 libxrandr2 libgbm1 libasound2 \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

ENTRYPOINT ["python", "agent/sentinel.py"]
''',

    "docker/docker-compose.yml": '''\
version: "3.9"

services:
  sentinel:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    env_file:
      - ../.env
    volumes:
      - ../reports:/app/reports
    command: ["--story", "${JIRA_STORY_KEY:-SMOKE-1}"]
''',

    # ── reports/ ──────────────────────────────────────────────────────── #

    "reports/.gitkeep": "",

    # ── root files ────────────────────────────────────────────────────── #

    ".env.example": '''\
# ─────────────────────────────────────────────────────────────────────────────
# SmokeSentinel — Environment variables template
# Copy this file to .env and fill in the real values.
# Never commit .env to version control.
# ─────────────────────────────────────────────────────────────────────────────

# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=<your-anthropic-api-key>
OPENAI_API_KEY=<your-openai-api-key-optional>

# ── Jira ─────────────────────────────────────────────────────────────────────
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_PROJECT_KEY=SMOKE
JIRA_TOKEN=<your-jira-personal-access-token>
JIRA_EMAIL=<your-jira-account-email>

# ── Playwright MCP ───────────────────────────────────────────────────────────
PLAYWRIGHT_MCP_URL=http://localhost:3000

# ── Notifications ────────────────────────────────────────────────────────────
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/<your-webhook>
TEAMS_WEBHOOK_URL=<your-teams-webhook-url>

# ── LangSmith tracing (optional) ─────────────────────────────────────────────
LANGCHAIN_API_KEY=<your-langsmith-api-key>
LANGCHAIN_PROJECT=smokesentinel

# ── Agent settings ───────────────────────────────────────────────────────────
REPORT_OUTPUT_DIR=reports
LOG_LEVEL=INFO
MAX_RETRIES=3
TIMEOUT_SECONDS=30
''',

    ".gitignore": '''\
# SmokeSentinel — .gitignore

# Work in progress / local drafts
chantiers/

# Environment & secrets
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
secrets.json
secrets.yaml
secrets.yml
credentials.json
credentials.yaml

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg
*.egg-info/
dist/
build/
.eggs/
.venv/
venv/
env/

# Pytest / coverage
.pytest_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/

# agent/
agent/.langchain.db
agent/langchain_cache/
agent/prompts/*.local.*

# gherkin/
gherkin/output/
gherkin/*.draft.*

# reporter/
reporter/output/
reports/
!reports/.gitkeep

# notifier/
notifier/*.local.*
notifier/payloads/

# tests/
test-results/
playwright-report/
tests/screenshots/
tests/videos/
tests/traces/
tests/fixtures/*.local.*

# docker/
docker/docker-compose.override.yml
docker/*.local.*

# Logs
*.log
logs/
sentinel.log

# OS
.DS_Store
.DS_Store?
Thumbs.db
ehthumbs.db
desktop.ini

# IDE
.vscode/
.idea/
*.swp
*.swo
*.sublime-project
*.sublime-workspace
''',

    "requirements.txt": '''\
# SmokeSentinel — Python dependencies
# Pin versions once the stack is stabilised.

langchain>=0.1.0
langchain-anthropic>=0.1.0
anthropic>=0.20.0
playwright>=1.40.0
python-dotenv>=1.0.0
requests>=2.28.0
jinja2>=3.1.0
pytest>=7.0.0
pytest-playwright>=0.4.0
deepeval>=0.20.0
langsmith>=0.1.0
''',

    "README.md": """\
# 🛰️ SmokeSentinel — SentinelMCP

> Autonomous QA agent for AI-driven smoke testing.
> See the full README on GitHub: https://github.com/khafid1506/SmokeSentinel

🚧 Work in Progress
""",

}


# ─────────────────────────────────────────────────────────────────────────────
# Scaffold engine
# ─────────────────────────────────────────────────────────────────────────────

def scaffold(root: Path, dry_run: bool) -> tuple[int, int]:
    """
    Creates all directories and files defined in FILE_CONTENTS.

    Rules:
        - Directories are created with mkdir(parents=True, exist_ok=True).
        - Files are only written if they do NOT already exist.
        - .gitkeep files are always empty.
        - Returns (created_count, skipped_count).
    """
    created = 0
    skipped = 0

    for rel_path, content in FILE_CONTENTS.items():
        target = root / rel_path

        # ── Create parent directories ──────────────────────────────────── #
        parent = target.parent
        if not parent.exists():
            if dry_run:
                dry(f"mkdir  {parent.relative_to(root.parent)}/")
            else:
                parent.mkdir(parents=True, exist_ok=True)
                ok(f"mkdir  {parent.relative_to(root.parent)}/")

        # ── Create file if missing ─────────────────────────────────────── #
        if target.exists():
            skip(f"exists {target.relative_to(root.parent)}")
            skipped += 1
        else:
            if dry_run:
                dry(f"touch  {target.relative_to(root.parent)}")
            else:
                target.write_text(content, encoding="utf-8")
                ok(f"touch  {target.relative_to(root.parent)}")
            created += 1

    return created, skipped


def print_tree(root: Path, prefix: str = "", is_last: bool = True) -> None:
    """
    Prints a visual tree of the created structure (max 2 levels deep).
    """
    connector = "└── " if is_last else "├── "
    print(f"{C.DIM}{prefix}{connector}{root.name}/{C.RESET}")
    children = sorted(p for p in root.iterdir())
    for i, child in enumerate(children):
        last = i == len(children) - 1
        extension = "    " if is_last else "│   "
        if child.is_dir():
            print_tree(child, prefix + extension, last)
        else:
            conn = "└── " if last else "├── "
            print(f"{C.DIM}{prefix}{extension}{conn}{child.name}{C.RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold the SmokeSentinel project structure."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Parent directory where SmokeSentinel/ will be created (default: current dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without touching the filesystem",
    )
    return parser.parse_args()


def main() -> None:
    args    = parse_args()
    dry_run = args.dry_run
    root    = Path(args.root).resolve() / "SmokeSentinel"

    bar = "═" * 60
    print(f"\n{C.BOLD}{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  SmokeSentinel — Project Scaffolder{C.RESET}")
    if dry_run:
        print(f"{C.YELLOW}  DRY RUN — nothing will be written{C.RESET}")
    print(f"{C.CYAN}{bar}{C.RESET}")
    print(f"  Target : {root}\n")

    # Create root dir
    if not root.exists():
        if dry_run:
            dry(f"mkdir  SmokeSentinel/")
        else:
            root.mkdir(parents=True, exist_ok=True)
            ok(f"mkdir  SmokeSentinel/")

    created, skipped = scaffold(root, dry_run=dry_run)

    # ── Summary ──────────────────────────────────────────────────────── #
    print(f"\n{C.CYAN}{bar}{C.RESET}")
    print(f"  {C.GREEN}✔  Created : {created}{C.RESET}")
    print(f"  {C.YELLOW}─  Skipped : {skipped}  (already exist){C.RESET}")

    if dry_run:
        print(f"\n  {C.YELLOW}Dry run complete — rerun without --dry-run to apply.{C.RESET}\n")
    else:
        print(f"\n  {C.GREEN}{C.BOLD}✔  SmokeSentinel project structure ready.{C.RESET}")
        print(f"\n  Next steps:")
        print(f"  {C.DIM}1.  cd SmokeSentinel{C.RESET}")
        print(f"  {C.DIM}2.  cp .env.example .env  →  fill in your credentials{C.RESET}")
        print(f"  {C.DIM}3.  python scripts/env_check.py  →  validate your environment{C.RESET}")
        print(f"  {C.DIM}4.  pip install -r requirements.txt{C.RESET}")
        print(f"  {C.DIM}5.  playwright install chromium{C.RESET}\n")

        print(f"{C.CYAN}{bar}{C.RESET}")
        print(f"{C.BOLD}  Project tree{C.RESET}")
        print(f"{C.CYAN}{bar}{C.RESET}")
        print_tree(root)
        print()


if __name__ == "__main__":
    main()
