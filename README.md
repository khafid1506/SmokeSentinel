# 🛰️ SmokeSentinel — SentinelMCP

> **Autonomous QA agent for AI-driven smoke testing.**
> From Jira user story to Gherkin scenarios, Playwright execution via MCP, AI failure diagnosis, and clear reporting with Slack/Teams alerts.

[![Status](https://img.shields.io/badge/status-WIP-orange?style=flat-square)](https://github.com/khafid1506/SmokeSentinel)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-agent-blueviolet?style=flat-square)](https://langchain.com)
[![Playwright](https://img.shields.io/badge/Playwright-MCP-green?style=flat-square&logo=playwright)](https://playwright.dev)
[![Claude](https://img.shields.io/badge/Claude-Anthropic-black?style=flat-square)](https://anthropic.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker)](https://docker.com)

---

## 🗺️ Table of Contents

- [Why SmokeSentinel?](#-why-smokesentinel)
- [What it does](#%EF%B8%8F-what-it-does)
- [Architecture](#-architecture)
- [Stack](#-stack)
- [Project Structure](#-project-structure)
- [Scripts](#-scripts)
  - [git_commit_push.py](#git_commit_pushpy--secure-git-commit--push)
  - [github_auth_setup.py](#github_auth_setuppy--github-authentication-setup)
  - [env_check.py](#env_checkpy--pre-launch-environment-validator)
- [Getting Started](#-getting-started)
- [Roadmap](#-roadmap)
- [Author](#-author)

---

## 💡 Why SmokeSentinel?

Before running full regression suites, E2E tests, or business validation — teams need a **fast, reliable answer** to one question:

> *"Is the application still standing after this deployment?"*

Smoke tests answer that in minutes, not hours — catching blocking regressions early and freeing QA time for deeper testing.

**SentinelMCP automates this entire first line of defense — without manual configuration.**

```
Jira User Story ──▶ Gherkin Scenarios ──▶ Playwright Tests ──▶ AI Diagnosis ──▶ Report & Alerts
```

---

## ⚙️ What It Does

| Step | Description |
|------|-------------|
| 📋 **Story parsing** | Reads a Jira User Story and generates clean Gherkin test cases |
| 🧪 **Test generation** | Produces Playwright smoke test scenarios — zero manual setup |
| 🤖 **Autonomous execution** | Runs tests via a LangChain agent through Playwright MCP |
| 🩺 **AI diagnosis** | Explains failures in plain language: root cause hints, severity level |
| 📊 **Reporting** | Produces a clear HTML/Markdown report per test run |
| 🚨 **Alerting** | Sends Slack/Teams notifications on critical regressions |
| 🐳 **CI/CD ready** | Runs anywhere via Docker — plug into any pipeline |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SentinelMCP Agent                           │
│                                                                     │
│   ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐  │
│   │  Jira Story  │────▶│ Gherkin Gen   │────▶│ Playwright Tests │  │
│   │  (input)     │     │ (LLM + Claude)│     │ (via MCP)        │  │
│   └──────────────┘     └───────────────┘     └────────┬─────────┘  │
│                                                        │            │
│   ┌──────────────┐     ┌───────────────┐     ┌────────▼─────────┐  │
│   │ Slack/Teams  │◀────│   AI Report   │◀────│ Failure Diagnosis│  │
│   │  (alerts)    │     │  (HTML + MD)  │     │ (Claude/OpenAI)  │  │
│   └──────────────┘     └───────────────┘     └──────────────────┘  │
│                                                                     │
│   🐳 Dockerized — CI/CD ready (GitHub Actions, GitLab CI…)         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧰 Stack

| Layer | Technology |
|-------|-----------|
| **Test execution** | [Playwright](https://playwright.dev) via [Playwright MCP](https://github.com/microsoft/playwright-mcp) |
| **AI orchestration** | [LangChain](https://langchain.com) agent |
| **LLM backend** | [Claude (Anthropic)](https://anthropic.com) · OpenAI |
| **Language** | Python 3.11+ |
| **Infra** | Docker · CI/CD (GitHub Actions / GitLab CI) |
| **Integrations** | Jira · Slack · Teams |

---

## 📁 Project Structure

```
SmokeSentinel/
├── agent/                    # LangChain agent core
│   ├── sentinel.py           # Main agent entrypoint
│   ├── tools/                # MCP tools & Playwright wrappers
│   └── prompts/              # LLM prompt templates
├── gherkin/                  # Gherkin scenario generator
├── reporter/                 # HTML / Markdown report builder
├── notifier/                 # Slack & Teams alert dispatcher
├── scripts/                  # Developer & admin utility scripts  ◀ see below
│   ├── git_commit_push.py    # Safe Git commit & push workflow
│   ├── github_auth_setup.py  # GitHub SSH / PAT auth setup
│   └── env_check.py          # Pre-launch environment validator
├── tests/                    # Smoke test templates & fixtures
├── docker/                   # Dockerfile & compose files
├── .env.example              # Environment variable template
└── README.md
```

---

## 🛠️ Scripts

Admin and developer scripts live in `scripts/`. They are **standalone** Python utilities — no external dependencies beyond the standard library — and can be run directly from any terminal.

> More scripts are on the way. Each one follows the same conventions: fully commented, interactive, colored output, safe-by-default.

| Script | Purpose |
|--------|---------|
| `git_commit_push.py` | Safe `add → commit → push` with pre-flight checks |
| `github_auth_setup.py` | Fix GitHub SSH / PAT authentication errors |
| `env_check.py` | Validate the full environment before launching the agent |

---

### `git_commit_push.py` — Secure Git Commit & Push

A hardened `git add . → commit → push` workflow with pre-flight checks, sensitive-file detection, and smart error diagnosis.

#### What it checks

| Phase | Check |
|-------|-------|
| **Pre-flight** | Git installed · valid repo · `origin` remote configured · branch not detached |
| **Branch safety** | Warns and requires confirmation on `main`, `master`, `production`, `release` |
| **File analysis** | Lists all modified files with status (modified / added / deleted / untracked) |
| **Conflict guard** | Blocks commit if unresolved merge conflicts are detected |
| **Secret detection** | Flags `.env`, `.pem`, `.key`, `secrets.*`, SSH private keys, etc. |
| **Commit message** | Rejects empty or too-short messages · alerts on generic messages (`fix`, `wip`, `update`…) |
| **Summary** | Displays a full recap of what will run before touching anything |
| **Confirmation** | Explicit `y/n` prompt before executing `add → commit → push` |
| **Push error diagnosis** | Handles: no upstream branch · rejected push (remote ahead) · auth denied · network timeout |
| **Post-push** | Prints commit hash + direct GitHub link to the commit and branch |

#### Usage

```bash
# From the repo root
python scripts/git_commit_push.py

# Target a different repo
python scripts/git_commit_push.py --path /path/to/your/repo
```

#### Example session

```
════════════════════════════════════════════════════
   GIT COMMIT & PUSH — Admin script
════════════════════════════════════════════════════
  Repo: /home/user/SmokeSentinel

── Pre-flight checks ───────────────────────────────
  ✔  Git detected: git version 2.43.0
  ✔  Valid Git repository
  ✔  Remote 'origin': git@github-khafid1506:khafid1506/SmokeSentinel.git
  ✔  Current branch: main
  ⚠  You are on protected branch 'main'. Continue anyway? [o/N]: o

── Modified files ───────────────────────────────────
  3 file(s) detected:
    modified   agent/sentinel.py
    added      scripts/git_commit_push.py
    untracked  .env.local
  ⚠  Sensitive file detected: .env.local — include anyway? [o/N]: n

── Commit message ───────────────────────────────────
  Message: feat: add secure git commit-push admin script

── Summary ─────────────────────────────────────────
  Remote : git@github-khafid1506:khafid1506/SmokeSentinel.git
  Branch : main
  Commit : "feat: add secure git commit-push admin script"
  Files  : 2

  Launch add → commit → push? [O/n]: O

── git add . ────────────────────────────────────────
  ✔  All files staged.
── git commit ───────────────────────────────────────
  [main a3f2c91] feat: add secure git commit-push admin script
  ✔  Commit created.
── git push ─────────────────────────────────────────
  ✔  Push successful!

── Post-push ────────────────────────────────────────
  ✔  Last pushed commit: a3f2c91
  ℹ  View commit : https://github.com/khafid1506/SmokeSentinel/commit/a3f2c91
  ℹ  View branch : https://github.com/khafid1506/SmokeSentinel/tree/main
```

---

### `github_auth_setup.py` — GitHub Authentication Setup

Interactive admin script that fixes GitHub authentication errors — both HTTPS token issues and multi-account SSH conflicts.

#### Fixes these errors

```
# HTTPS error
remote: Invalid username or token. Password authentication is not supported
fatal: Authentication failed for 'https://github.com/...'

# Multi-account SSH error
ERROR: Permission to khafid1506/SmokeSentinel.git denied to khafidmedheb.
fatal: Could not read from remote repository.
```

#### Options

| Option | Description |
|--------|-------------|
| **1 — PAT** | Guides through creating a Personal Access Token and configuring a credential helper |
| **2 — SSH (single account)** | Generates an SSH key pair, adds it to the agent, tests the connection, switches the remote to SSH |
| **3 — SSH multi-account** | Creates a **dedicated key per account**, writes a `~/.ssh/config` alias with `IdentitiesOnly yes`, tests the correct identity, updates the Git remote — fixes the "denied to wrong_user" error |
| **4 — PAT + SSH** | Runs options 1 then 2 in sequence |

#### Usage

```bash
python scripts/github_auth_setup.py
```

#### Option 3 — Multi-account SSH (step by step)

```
=== SOLUTION 3: Multi-account SSH ===

Step 1 — Secondary account info
  GitHub username : khafid1506
  Email           : khafid1506@example.com

Step 2 — Generating SSH key: ~/.ssh/id_ed25519_khafid1506

Step 3 — Loading key into SSH agent
  ✔  Key loaded.

Step 4 — Public key to add on GitHub (Settings → SSH keys):
  ssh-ed25519 AAAA... khafid1506@example.com

Step 5 — ~/.ssh/config updated:
  Host github-khafid1506
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_khafid1506
    IdentitiesOnly yes

Step 6 — Testing connection:
  Hi khafid1506! You've successfully authenticated.
  ✔  SSH connection successful!

Step 7 — Git remote updated:
  origin  git@github-khafid1506:khafid1506/SmokeSentinel.git
```

---

### `env_check.py` — Pre-launch Environment Validator

Validates that **everything is in place** before running `python agent/sentinel.py`.
Catches all blocking issues upfront — no more mid-run crashes on a missing variable or an expired token.

#### What it checks

| Phase | Check |
|-------|-------|
| **Python version** | Requires 3.11+ (match statements, modern type hints) |
| **.env file** | Present · parsable · no syntax errors · `--fix` auto-creates from `.env.example` |
| **Placeholder detection** | Flags unfilled values: `<YOUR_KEY>`, `xxx`, `changeme`, `REPLACE_ME`… |
| **Required variables** | Presence + format validation: Anthropic key pattern (`sk-ant-`), URL shape, email, Jira key… |
| **Optional variables** | Warns if Slack, Teams, OpenAI, LangSmith are absent — does not block |
| **Network connectivity** | TCP socket check: Anthropic API · GitHub · PyPI · Jira (dynamic from `JIRA_BASE_URL`) |
| **Python packages** | Import check + minimum version: `langchain`, `anthropic`, `playwright`, `requests`… |
| **Docker** | Binary in PATH · daemon running |
| **Playwright browsers** | Chromium (or others) installed via `playwright install` |

#### Usage

```bash
python scripts/env_check.py                    # standard colored output
python scripts/env_check.py --strict           # warnings = failures (CI gate)
python scripts/env_check.py --ci               # compact output for CI logs
python scripts/env_check.py --fix              # auto-create .env from .env.example
python scripts/env_check.py --env /path/.env   # explicit .env path
```

> Exit code `0` = ready to launch · Exit code `1` = blocking issues found.
> Safe to use as a CI/CD gate step before any test run.

#### Example output

```
════════════════════════════════════════════════════════════
  ENV CHECK — SmokeSentinel pre-launch validator
════════════════════════════════════════════════════════════

── Python version ──────────────────────────────────────────
  ✔  Python 3.12  (minimum: 3.11)

── .env file ───────────────────────────────────────────────
  ✔  .env file found and parsed: /home/user/SmokeSentinel/.env  (14 variables)

── Placeholder values ──────────────────────────────────────
  ✔  No placeholder values detected in .env

── Required environment variables ──────────────────────────
  ✔  ANTHROPIC_API_KEY  (Anthropic Claude API key)  →  sk-ant-***
  ✔  JIRA_BASE_URL      (Jira instance base URL)    →  https:***
  ✔  JIRA_PROJECT_KEY   (Jira project key)          →  SMOKE***
  ✔  JIRA_TOKEN         (Jira Personal Access Token) →  eyJhb***
  ✔  JIRA_EMAIL         (Jira account email)         →  khalid***
  ✔  PLAYWRIGHT_MCP_URL (Playwright MCP server URL)  →  http:/***

── Optional environment variables ──────────────────────────
  ✔  SLACK_WEBHOOK_URL  (Slack incoming webhook URL)  →  https:***
  ⚠  OPENAI_API_KEY     — not set (optional, agent will use Claude only)
  ⚠  LANGCHAIN_API_KEY  — not set (optional, LangSmith tracing disabled)

── External services connectivity ──────────────────────────
  ✔  Anthropic API  (api.anthropic.com:443)  — reachable
  ✔  GitHub         (github.com:443)         — reachable
  ✔  PyPI           (pypi.org:443)           — reachable
  ✔  Jira           (your-org.atlassian.net) — reachable

── Python packages ─────────────────────────────────────────
  ✔  langchain     v0.2.1   ✔
  ✔  anthropic     v0.25.0  ✔
  ✔  playwright    v1.44.0  ✔
  ✔  python-dotenv — installed
  ✔  requests      v2.31.0  ✔

── Docker ──────────────────────────────────────────────────
  ✔  Docker version 26.1.0
  ✔  Docker daemon — running

── Playwright browsers ─────────────────────────────────────
  ✔  Playwright — browsers found

════════════════════════════════════════════════════════════
  RESULTS  passed=22  warnings=2  failed=0

  ✔  Environment is ready — safe to launch SentinelMCP. (with warnings)
```


---

## 🚀 Getting Started

> Full setup instructions coming soon. The agent is under active development.

```bash
# Clone
git clone git@github-khafid1506:khafid1506/SmokeSentinel.git
cd SmokeSentinel

# Environment
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, JIRA_TOKEN, SLACK_WEBHOOK_URL …

# Install dependencies (coming soon)
pip install -r requirements.txt

# Run the agent (coming soon)
python agent/sentinel.py --story JIRA-1234
```

---

## 📌 Roadmap

- [x] Repository bootstrap & architecture design
- [x] Admin scripts: Git workflow & GitHub auth setup
- [x] `env_check.py` — pre-launch environment validator
- [x] Gherkin scenario generator (LLM-based)
- [ ] Playwright MCP integration & test runner
- [ ] AI failure diagnosis module
- [ ] HTML / Markdown report generator
- [ ] Slack & Teams notifier
- [ ] Docker containerization
- [ ] CI/CD pipeline templates (GitHub Actions, GitLab CI)
- [ ] Jira integration (story reader + test result sync)
- [ ] Full README with architecture diagram & live demo

⭐ Star this repo to follow the progress.

---

## 👤 Author

**Khalid Hafid-Medheb**
Senior SDET & AI Engineer — specialized in autonomous QA agents (HealthTech / BioTech)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-khalid--hafid--medheb-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/khalid-hafid-medheb-40451aa8/)
[![GitHub](https://img.shields.io/badge/GitHub-khafidmedheb-181717?style=flat-square&logo=github)](https://github.com/khafid1506)
[![Kallitests](https://img.shields.io/badge/Org-Kallitests-6e40c9?style=flat-square)](https://github.com/khafidmedheb)

---

*Built with 🧠 Claude (Anthropic) · 🎭 Playwright · 🦜 LangChain*
