#!/usr/bin/env python3
"""
env_check.py

PRE-LAUNCH ENVIRONMENT VALIDATOR — SmokeSentinel
=================================================

Validates that everything is in place before launching the SentinelMCP agent.
Run this once before `python agent/sentinel.py` to catch all blocking issues
upfront instead of discovering them mid-run.

Checks performed (in order):
    ✔ .env file exists and is readable
    ✔ All required environment variables are present
    ✔ Variable formats are valid (API key patterns, URL shapes, email…)
    ✔ Optional variables are present (warns if missing, does not block)
    ✔ External services are reachable (Anthropic, GitHub, Jira, Slack…)
    ✔ Python version meets the minimum requirement
    ✔ Required Python packages are installed at the expected versions
    ✔ Docker is available and the daemon is running
    ✔ Playwright browsers are installed
    ✔ No sensitive values are accidentally set to their placeholder defaults

Exits with code 0 if all required checks pass (warnings are allowed).
Exits with code 1 if any required check fails — safe to use in CI/CD.

Usage:
    python env_check.py                        # checks .env in current dir
    python env_check.py --env /path/to/.env    # explicit .env path
    python env_check.py --strict               # treat warnings as errors
    python env_check.py --ci                   # compact output for CI logs
    python env_check.py --fix                  # auto-create .env from .env.example
"""

import os
import re
import sys
import socket
import argparse
import importlib
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Configuration — edit this section to match your project
# ─────────────────────────────────────────────────────────────────────────────

# Minimum Python version required by SmokeSentinel
MIN_PYTHON = (3, 11)

# Required env variables: key → (description, validator_name or None)
# validator_name refers to a function in VALIDATORS dict below
REQUIRED_VARS: dict[str, tuple[str, Optional[str]]] = {
    "ANTHROPIC_API_KEY":  ("Anthropic Claude API key",          "anthropic_key"),
    "JIRA_BASE_URL":      ("Jira instance base URL",             "url"),
    "JIRA_PROJECT_KEY":   ("Jira project key (e.g. PROJ)",       "jira_key"),
    "JIRA_TOKEN":         ("Jira Personal Access Token",          "non_empty"),
    "JIRA_EMAIL":         ("Jira account email",                  "email"),
    "PLAYWRIGHT_MCP_URL": ("Playwright MCP server URL",           "url"),
}

# Optional env variables: key → (description, validator_name or None)
OPTIONAL_VARS: dict[str, tuple[str, Optional[str]]] = {
    "SLACK_WEBHOOK_URL":   ("Slack incoming webhook URL",         "slack_url"),
    "TEAMS_WEBHOOK_URL":   ("Microsoft Teams webhook URL",        "url"),
    "OPENAI_API_KEY":      ("OpenAI API key (fallback LLM)",      "openai_key"),
    "LANGCHAIN_API_KEY":   ("LangSmith tracing key",              "non_empty"),
    "LANGCHAIN_PROJECT":   ("LangSmith project name",             "non_empty"),
    "REPORT_OUTPUT_DIR":   ("Directory for test reports",         "non_empty"),
    "LOG_LEVEL":           ("Log verbosity (DEBUG/INFO/WARNING)", "log_level"),
    "MAX_RETRIES":         ("Max agent retry attempts",           "positive_int"),
    "TIMEOUT_SECONDS":     ("HTTP timeout in seconds",            "positive_int"),
}

# Placeholder values that indicate the user forgot to fill in the .env
PLACEHOLDER_PATTERNS = [
    r"^<.+>$",           # <YOUR_KEY_HERE>
    r"^your[_-]",        # your_api_key
    r"^REPLACE",         # REPLACE_ME
    r"^xxx+$",           # xxx or xxxx
    r"^changeme$",       # changeme
    r"^todo$",           # todo
    r"^placeholder",     # placeholder_value
]

# External services to ping: name → (host, port, description)
SERVICES: dict[str, tuple[str, int, str]] = {
    "Anthropic API":   ("api.anthropic.com",  443, "Claude LLM backend"),
    "GitHub":          ("github.com",         443, "Source control"),
    "PyPI":            ("pypi.org",           443, "Python package registry"),
}

# Required Python packages: package_name → (import_name, min_version or None)
REQUIRED_PACKAGES: dict[str, tuple[str, Optional[str]]] = {
    "langchain":       ("langchain",          "0.1.0"),
    "anthropic":       ("anthropic",          "0.20.0"),
    "playwright":      ("playwright",         "1.40.0"),
    "python-dotenv":   ("dotenv",             None),
    "requests":        ("requests",           "2.28.0"),
    "jinja2":          ("jinja2",             None),
    "pytest":          ("pytest",             "7.0.0"),
}

# ANSI color codes
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"
    MAGENTA = "\033[95m"


# ─────────────────────────────────────────────────────────────────────────────
# Result tracking
# ─────────────────────────────────────────────────────────────────────────────

class CheckResult:
    """
    Accumulates check results throughout the script.
    Provides a final summary and overall pass/fail status.
    """
    def __init__(self) -> None:
        self.passed:   list[str] = []
        self.warnings: list[str] = []
        self.failed:   list[str] = []

    def ok(self, msg: str)   -> None: self.passed.append(msg)
    def warn(self, msg: str) -> None: self.warnings.append(msg)
    def fail(self, msg: str) -> None: self.failed.append(msg)

    @property
    def has_failures(self) -> bool:
        return len(self.failed) > 0

    @property
    def score(self) -> str:
        total = len(self.passed) + len(self.warnings) + len(self.failed)
        return f"{len(self.passed)}/{total}"


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

CI_MODE = False  # set by --ci flag

def header(title: str) -> None:
    if CI_MODE:
        print(f"\n[{title}]")
        return
    bar = "─" * 60
    print(f"\n{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  {title}{C.RESET}")
    print(f"{C.CYAN}{bar}{C.RESET}")

def ok(msg: str) -> None:
    prefix = "  [OK]  " if CI_MODE else f"{C.GREEN}  ✔  {C.RESET}"
    print(f"{prefix}{msg}")

def warn(msg: str) -> None:
    prefix = "  [WARN]" if CI_MODE else f"{C.YELLOW}  ⚠  {C.RESET}"
    print(f"{prefix}{msg}")

def fail(msg: str) -> None:
    prefix = "  [FAIL]" if CI_MODE else f"{C.RED}  ✖  {C.RESET}"
    print(f"{prefix}{msg}")

def info(msg: str) -> None:
    prefix = "  [INFO]" if CI_MODE else f"{C.CYAN}  ℹ  {C.RESET}"
    print(f"{prefix}{msg}")

def dim(msg: str) -> None:
    if not CI_MODE:
        print(f"{C.DIM}        {msg}{C.RESET}")
    else:
        print(f"         {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Value validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_anthropic_key(value: str) -> Optional[str]:
    """
    Anthropic API keys follow the pattern: sk-ant-api03-<base64chars>
    Returns an error message if invalid, None if valid.
    """
    if not re.match(r"^sk-ant-", value):
        return "must start with 'sk-ant-' — check your Anthropic console"
    if len(value) < 40:
        return "looks too short for a valid Anthropic API key"
    return None

def validate_openai_key(value: str) -> Optional[str]:
    """OpenAI API keys start with 'sk-'."""
    if not re.match(r"^sk-", value):
        return "must start with 'sk-' — check your OpenAI console"
    return None

def validate_url(value: str) -> Optional[str]:
    """Checks that the value is a well-formed http/https URL."""
    if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", value, re.IGNORECASE):
        return f"'{value}' does not look like a valid URL (must start with http:// or https://)"
    return None

def validate_slack_url(value: str) -> Optional[str]:
    """Slack webhook URLs must point to hooks.slack.com."""
    err = validate_url(value)
    if err:
        return err
    if "hooks.slack.com/services/" not in value:
        return "Slack webhook URL should contain 'hooks.slack.com/services/'"
    return None

def validate_email(value: str) -> Optional[str]:
    """Basic email format check."""
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        return f"'{value}' does not look like a valid email address"
    return None

def validate_jira_key(value: str) -> Optional[str]:
    """Jira project keys are typically uppercase alphanumeric (e.g. PROJ, SMOKE)."""
    if not re.match(r"^[A-Z][A-Z0-9_]{1,9}$", value):
        return f"'{value}' — expected an uppercase project key like 'PROJ' or 'QA'"
    return None

def validate_non_empty(value: str) -> Optional[str]:
    """Simply checks the value is not blank."""
    if not value.strip():
        return "value is empty"
    return None

def validate_log_level(value: str) -> Optional[str]:
    """Checks that LOG_LEVEL is one of the standard Python logging levels."""
    valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if value.upper() not in valid:
        return f"'{value}' is not a valid log level. Choose from: {', '.join(sorted(valid))}"
    return None

def validate_positive_int(value: str) -> Optional[str]:
    """Checks that the value is a positive integer."""
    try:
        n = int(value)
        if n <= 0:
            raise ValueError
    except ValueError:
        return f"'{value}' must be a positive integer"
    return None

# Registry of validator functions by name
VALIDATORS = {
    "anthropic_key": validate_anthropic_key,
    "openai_key":    validate_openai_key,
    "url":           validate_url,
    "slack_url":     validate_slack_url,
    "email":         validate_email,
    "jira_key":      validate_jira_key,
    "non_empty":     validate_non_empty,
    "log_level":     validate_log_level,
    "positive_int":  validate_positive_int,
}


# ─────────────────────────────────────────────────────────────────────────────
# Check functions
# ─────────────────────────────────────────────────────────────────────────────

def check_python_version(results: CheckResult) -> None:
    """
    Verifies the running Python interpreter meets MIN_PYTHON.
    SmokeSentinel uses match statements and modern type hints that
    require Python 3.11+.
    """
    current = sys.version_info[:2]
    version_str = f"{current[0]}.{current[1]}"
    min_str = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"

    if current >= MIN_PYTHON:
        ok(f"Python {version_str}  (minimum: {min_str})")
        results.ok(f"Python {version_str}")
    else:
        fail(f"Python {version_str} — SmokeSentinel requires {min_str}+")
        dim(f"Install a newer Python: https://python.org/downloads")
        results.fail(f"Python version {version_str} < {min_str}")


def check_env_file(env_path: Path, results: CheckResult, fix: bool) -> dict[str, str]:
    """
    Loads the .env file and returns its key/value pairs.
    If --fix is passed and no .env exists, copies .env.example automatically.
    Returns an empty dict on failure (subsequent checks will fail gracefully).
    """
    if not env_path.exists():
        example = env_path.parent / ".env.example"
        if fix and example.exists():
            import shutil
            shutil.copy(example, env_path)
            warn(f".env not found — copied from .env.example at {env_path}")
            warn("Fill in the real values before launching the agent.")
            results.warn(".env created from .env.example — values not yet filled")
        else:
            fail(f".env file not found at: {env_path}")
            if example.exists():
                dim(f"Run with --fix to auto-create from .env.example, or:")
                dim(f"  cp {example} {env_path}")
            else:
                dim("Create a .env file with the variables listed below.")
            results.fail(".env file missing")
        return {}

    # Parse the .env file manually so we don't require python-dotenv at this stage.
    # This also lets us detect syntax issues ourselves.
    env_vars: dict[str, str] = {}
    parse_errors: list[str] = []

    with open(env_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            # Skip blank lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                parse_errors.append(f"line {lineno}: '{stripped}' has no '=' sign")
                continue
            key, _, value = stripped.partition("=")
            # Strip inline comments and surrounding quotes from the value
            value = value.split("#")[0].strip().strip('"').strip("'")
            env_vars[key.strip()] = value

    if parse_errors:
        for err in parse_errors:
            warn(f".env parse issue — {err}")
            results.warn(f".env parse: {err}")

    ok(f".env file found and parsed: {env_path}  ({len(env_vars)} variables)")
    results.ok(".env file readable")

    # Also load into os.environ so subprocess-based checks can see them
    for k, v in env_vars.items():
        os.environ.setdefault(k, v)

    return env_vars


def check_placeholder_values(env_vars: dict[str, str], results: CheckResult) -> None:
    """
    Detects variables that still hold their template placeholder values.
    A common mistake: copying .env.example and forgetting to replace <YOUR_KEY>.
    """
    placeholders_found = []

    for key, value in env_vars.items():
        for pattern in PLACEHOLDER_PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                placeholders_found.append((key, value))
                break

    if not placeholders_found:
        ok("No placeholder values detected in .env")
        results.ok("No placeholder values")
        return

    for key, value in placeholders_found:
        fail(f"Placeholder not replaced: {key}={value}")
        results.fail(f"Placeholder: {key}")

    dim("Replace these values in your .env with real credentials.")


def check_required_vars(env_vars: dict[str, str], results: CheckResult) -> None:
    """
    Verifies each required variable is present and passes its validator.
    A missing required variable is always a hard failure.
    """
    for var, (description, validator_name) in REQUIRED_VARS.items():
        value = env_vars.get(var, "").strip()

        if not value:
            fail(f"{var}  — MISSING  ({description})")
            results.fail(f"Missing required: {var}")
            continue

        # Run the format validator if one is configured
        if validator_name and validator_name in VALIDATORS:
            error_msg = VALIDATORS[validator_name](value)
            if error_msg:
                fail(f"{var}  — INVALID FORMAT  {error_msg}")
                dim(f"Description: {description}")
                results.fail(f"Invalid format: {var}")
                continue

        # Mask the value in output (show only first 6 chars + ***)
        masked = value[:6] + "***" if len(value) > 6 else "***"
        ok(f"{var}  ({description})  →  {masked}")
        results.ok(f"Required var: {var}")


def check_optional_vars(env_vars: dict[str, str], results: CheckResult) -> None:
    """
    Checks optional variables. Missing = warning (not a failure).
    Present but malformed = warning.
    """
    for var, (description, validator_name) in OPTIONAL_VARS.items():
        value = env_vars.get(var, "").strip()

        if not value:
            warn(f"{var}  — not set  ({description})")
            dim("Optional — agent will run without it, but some features may be disabled.")
            results.warn(f"Optional var not set: {var}")
            continue

        if validator_name and validator_name in VALIDATORS:
            error_msg = VALIDATORS[validator_name](value)
            if error_msg:
                warn(f"{var}  — present but invalid format: {error_msg}")
                results.warn(f"Optional var format: {var}")
                continue

        masked = value[:6] + "***" if len(value) > 6 else "***"
        ok(f"{var}  ({description})  →  {masked}")
        results.ok(f"Optional var: {var}")


def check_services(results: CheckResult, timeout: int = 5) -> None:
    """
    Attempts a TCP connection to each external service.
    Uses a raw socket (no HTTP library) so this works even if requests
    is not installed yet — that's checked separately.
    A timeout or refused connection means the service is unreachable from
    this machine (firewall, VPN, or the service is down).
    """
    for name, (host, port, description) in SERVICES.items():
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            ok(f"{name}  ({host}:{port})  — reachable")
            results.ok(f"Service reachable: {name}")
        except (socket.timeout, socket.gaierror, ConnectionRefusedError) as exc:
            fail(f"{name}  ({host}:{port})  — UNREACHABLE")
            dim(f"Description : {description}")
            dim(f"Error       : {exc}")
            dim("Check your network connection or VPN.")
            results.fail(f"Service unreachable: {name}")

    # Dynamic Jira check — only if JIRA_BASE_URL is configured
    jira_url = os.environ.get("JIRA_BASE_URL", "").strip()
    if jira_url:
        try:
            # Extract host from URL for a socket check
            host_match = re.match(r"https?://([^/:]+)", jira_url)
            if host_match:
                jira_host = host_match.group(1)
                sock = socket.create_connection((jira_host, 443), timeout=timeout)
                sock.close()
                ok(f"Jira  ({jira_host})  — reachable")
                results.ok("Service reachable: Jira")
            else:
                warn(f"Cannot parse host from JIRA_BASE_URL: {jira_url}")
                results.warn("Jira host parse error")
        except Exception as exc:
            fail(f"Jira  ({jira_url})  — UNREACHABLE: {exc}")
            results.fail("Service unreachable: Jira")
    else:
        warn("JIRA_BASE_URL not set — skipping Jira connectivity check")
        results.warn("Jira connectivity skipped")


def check_python_packages(results: CheckResult) -> None:
    """
    Verifies each required Python package is importable and meets the
    minimum version if specified.
    Uses importlib.metadata for version checking (stdlib since 3.8).
    """
    from importlib.metadata import version as pkg_version, PackageNotFoundError

    for package_name, (import_name, min_version) in REQUIRED_PACKAGES.items():
        # Step 1: can we import it?
        try:
            importlib.import_module(import_name)
        except ImportError:
            fail(f"{package_name}  — NOT INSTALLED")
            dim(f"Install with: pip install {package_name}")
            results.fail(f"Package missing: {package_name}")
            continue

        # Step 2: version check (if required)
        if min_version:
            try:
                installed = pkg_version(package_name)
                # Simple tuple comparison on version strings
                inst_tuple = tuple(int(x) for x in installed.split(".")[:3])
                min_tuple  = tuple(int(x) for x in min_version.split(".")[:3])
                if inst_tuple < min_tuple:
                    warn(
                        f"{package_name}  — version {installed} "
                        f"(minimum: {min_version})"
                    )
                    dim(f"Upgrade with: pip install --upgrade {package_name}>={min_version}")
                    results.warn(f"Package outdated: {package_name} {installed}")
                else:
                    ok(f"{package_name}  v{installed}  ✔")
                    results.ok(f"Package: {package_name} {installed}")
            except PackageNotFoundError:
                # Package importable but not pip-registered (e.g. installed as .whl)
                ok(f"{package_name}  — installed (version unknown)")
                results.ok(f"Package: {package_name}")
            except ValueError:
                # Non-standard version string — don't block
                ok(f"{package_name}  — installed")
                results.ok(f"Package: {package_name}")
        else:
            ok(f"{package_name}  — installed")
            results.ok(f"Package: {package_name}")


def check_docker(results: CheckResult) -> None:
    """
    Checks that:
      1. The 'docker' binary is in PATH
      2. The Docker daemon is running (docker info succeeds)
    SmokeSentinel uses Docker to containerize test runs.
    """
    # Is docker installed?
    try:
        which = subprocess.run(["docker", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        fail("Docker — not found in PATH")
        dim("Install Docker Desktop: https://docs.docker.com/get-docker/")
        results.fail("Docker not installed")
        return

    if which.returncode != 0:
        fail("Docker — not found in PATH")
        dim("Install Docker Desktop: https://docs.docker.com/get-docker/")
        results.fail("Docker not installed")
        return

    docker_version = which.stdout.strip().split("\n")[0]
    ok(f"{docker_version}")

    # Is the daemon running?
    try:
        daemon = subprocess.run(["docker", "info"], capture_output=True, text=True)
    except FileNotFoundError:
        fail("Docker daemon — NOT running")
        dim("Start Docker Desktop, or run: sudo systemctl start docker")
        results.fail("Docker daemon not running")
        return

    if daemon.returncode != 0:
        fail("Docker daemon — NOT running")
        dim("Start Docker Desktop, or run: sudo systemctl start docker")
        results.fail("Docker daemon not running")
    else:
        ok("Docker daemon — running")
        results.ok("Docker daemon running")


def check_playwright(results: CheckResult) -> None:
    """
    Checks that Playwright browsers are installed.
    'playwright install --dry-run' lists what's installed without re-downloading.
    If no browsers are found, SmokeSentinel cannot execute any tests.
    """
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--dry-run"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        # playwright module may not be installed (caught by package check)
        fail("Playwright — could not query browser installation")
        dim("Install browsers with: playwright install chromium")
        results.fail("Playwright browsers not queryable")
        return

    combined = (result.stdout + result.stderr).lower()

    # Playwright outputs "browser is already installed" for each browser
    if "already installed" in combined or "chromium" in combined:
        ok("Playwright — browsers found")
        results.ok("Playwright browsers installed")
    else:
        warn("Playwright — no browsers detected")
        dim("Install with: playwright install chromium")
        dim("Or for all browsers: playwright install")
        results.warn("Playwright browsers missing")


# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: CheckResult, strict: bool) -> None:
    """
    Prints a structured summary with counts per category and a clear
    overall verdict.  In --strict mode, warnings also count as failures.
    """
    bar = "═" * 60

    if CI_MODE:
        print(f"\n{'=' * 60}")
        print(f"RESULTS  passed={len(results.passed)}  "
              f"warnings={len(results.warnings)}  "
              f"failed={len(results.failed)}")
    else:
        print(f"\n{C.BOLD}{C.CYAN}{bar}{C.RESET}")
        print(f"{C.BOLD}{C.WHITE}  SUMMARY{C.RESET}")
        print(f"{C.CYAN}{bar}{C.RESET}")
        print(f"  {C.GREEN}✔  Passed  : {len(results.passed)}{C.RESET}")
        print(f"  {C.YELLOW}⚠  Warnings: {len(results.warnings)}{C.RESET}")
        print(f"  {C.RED}✖  Failed  : {len(results.failed)}{C.RESET}")

    # List all failures
    if results.failed:
        print(f"\n  {'[BLOCKING ISSUES]' if CI_MODE else C.BOLD + C.RED + 'Blocking issues:' + C.RESET}")
        for item in results.failed:
            print(f"    {'  - ' if CI_MODE else C.RED + '  ✖  ' + C.RESET}{item}")

    # List all warnings
    if results.warnings:
        print(f"\n  {'[WARNINGS]' if CI_MODE else C.BOLD + C.YELLOW + 'Warnings:' + C.RESET}")
        for item in results.warnings:
            print(f"    {'  - ' if CI_MODE else C.YELLOW + '  ⚠  ' + C.RESET}{item}")

    # Verdict
    blocker = results.has_failures or (strict and results.warnings)

    if not CI_MODE:
        print(f"\n{C.CYAN}{bar}{C.RESET}")

    if blocker:
        verdict = "ENVIRONMENT NOT READY — fix the issues above before launching."
        if CI_MODE:
            print(f"\n[FAIL] {verdict}")
        else:
            print(f"\n  {C.RED}{C.BOLD}✖  {verdict}{C.RESET}\n")
        sys.exit(1)
    else:
        verdict = "Environment is ready — safe to launch SentinelMCP."
        if results.warnings:
            verdict += " (with warnings)"
        if CI_MODE:
            print(f"\n[OK] {verdict}")
        else:
            print(f"\n  {C.GREEN}{C.BOLD}✔  {verdict}{C.RESET}\n")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-launch environment validator for SmokeSentinel."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the .env file to validate (default: .env in current directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures (useful in CI/CD gates)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Compact output suitable for CI logs (no colors, no box-drawing chars)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-create .env from .env.example if .env is missing",
    )
    return parser.parse_args()


def main() -> None:
    global CI_MODE

    args   = parse_args()
    CI_MODE = args.ci

    env_path = Path(args.env).resolve()
    results  = CheckResult()

    if not CI_MODE:
        print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
        print(f"{C.BOLD}{C.WHITE}  ENV CHECK — SmokeSentinel pre-launch validator{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
        if args.strict:
            info("Strict mode ON — warnings will be treated as failures")
        print()
    else:
        print("=" * 60)
        print("ENV CHECK — SmokeSentinel pre-launch validator")
        if args.strict:
            print("[strict mode]")

    # ── 1. Python version ─────────────────────────────────────────────── #
    header("Python version")
    check_python_version(results)

    # ── 2. .env file ──────────────────────────────────────────────────── #
    header(".env file")
    env_vars = check_env_file(env_path, results, fix=args.fix)

    # ── 3. Placeholder detection ──────────────────────────────────────── #
    if env_vars:
        header("Placeholder values")
        check_placeholder_values(env_vars, results)

    # ── 4. Required variables ─────────────────────────────────────────── #
    header("Required environment variables")
    check_required_vars(env_vars, results)

    # ── 5. Optional variables ─────────────────────────────────────────── #
    header("Optional environment variables")
    check_optional_vars(env_vars, results)

    # ── 6. Network / services ─────────────────────────────────────────── #
    header("External services connectivity")
    check_services(results)

    # ── 7. Python packages ────────────────────────────────────────────── #
    header("Python packages")
    check_python_packages(results)

    # ── 8. Docker ─────────────────────────────────────────────────────── #
    header("Docker")
    check_docker(results)

    # ── 9. Playwright browsers ────────────────────────────────────────── #
    header("Playwright browsers")
    check_playwright(results)

    # ── Summary & exit ────────────────────────────────────────────────── #
    print_summary(results, strict=args.strict)


if __name__ == "__main__":
    main()
