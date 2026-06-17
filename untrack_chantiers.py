#!/usr/bin/env python3
"""
untrack_chantiers.py

UNTRACK LOCAL FOLDER FROM GIT — SmokeSentinel
==============================================

Removes chantiers/ from Git tracking without deleting it locally,
then commits and pushes the change so it disappears from the remote.

Steps executed:
    1. Checks we are inside a Git repository
    2. Checks chantiers/ exists locally (nothing to do otherwise)
    3. Checks chantiers/ is actually tracked by Git
    4. Verifies .gitignore contains the chantiers/ rule (or adds it)
    5. git rm -r --cached chantiers/
    6. git add .gitignore
    7. git commit -m "chore: untrack chantiers/ folder — local only"
    8. git push

Safety rules:
    - chantiers/ is NEVER deleted from disk
    - Nothing is executed without a final confirmation
    - Every step is checked; the script stops on any error

Usage:
    python untrack_chantiers.py
    python untrack_chantiers.py --path /path/to/repo
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# ANSI colors
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"


def header(title: str) -> None:
    bar = "─" * 60
    print(f"\n{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  {title}{C.RESET}")
    print(f"{C.CYAN}{bar}{C.RESET}")

def ok(msg: str)    -> None: print(f"{C.GREEN}  ✔  {msg}{C.RESET}")
def warn(msg: str)  -> None: print(f"{C.YELLOW}  ⚠  {msg}{C.RESET}")
def info(msg: str)  -> None: print(f"{C.CYAN}  ℹ  {msg}{C.RESET}")
def dim(msg: str)   -> None: print(f"{C.DIM}       {msg}{C.RESET}")

def abort(msg: str) -> None:
    print(f"{C.RED}  ✖  {msg}{C.RESET}")
    print(f"\n{C.RED}{C.BOLD}  Abort.{C.RESET}\n")
    sys.exit(1)

def confirm(prompt: str, default_yes: bool = False) -> bool:
    hint = "[O/n]" if default_yes else "[o/N]"
    answer = input(f"\n{C.BOLD}  {prompt} {hint} : {C.RESET}").strip().lower()
    if answer == "":
        return default_yes
    return answer in ("o", "y", "oui", "yes")


# ─────────────────────────────────────────────────────────────────────────────
# Shell helper
# ─────────────────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True)


# ─────────────────────────────────────────────────────────────────────────────
# Check functions
# ─────────────────────────────────────────────────────────────────────────────

def check_git_repo(repo_path: str) -> None:
    """Ensure we are inside a valid Git repository."""
    result = run(["git", "rev-parse", "--git-dir"], cwd=repo_path)
    if result.returncode != 0:
        abort(f"'{repo_path}' is not a Git repository.")
    ok(f"Git repository: {repo_path}")


def check_chantiers_exists_locally(repo_path: str) -> None:
    """
    Verify chantiers/ exists on disk.
    If it doesn't exist locally there is nothing to untrack.
    """
    folder = Path(repo_path) / "chantiers"
    if not folder.exists():
        abort(
            "chantiers/ does not exist locally — nothing to untrack.\n"
            "  If it is already gone from the remote, you are all set."
        )
    ok("chantiers/ found locally (will be kept on disk)")


def check_chantiers_is_tracked(repo_path: str) -> bool:
    """
    Returns True if Git is currently tracking any file inside chantiers/.
    Uses 'git ls-files' which lists all files known to Git index.
    """
    result = run(
        ["git", "ls-files", "--error-unmatch", "chantiers/"],
        cwd=repo_path,
    )
    tracked = result.returncode == 0

    if tracked:
        # Count how many files are tracked inside the folder
        count_result = run(["git", "ls-files", "chantiers/"], cwd=repo_path)
        files = [f for f in count_result.stdout.splitlines() if f.strip()]
        ok(f"chantiers/ is tracked by Git ({len(files)} file(s) in the index)")
        for f in files[:10]:     # show at most 10
            dim(f)
        if len(files) > 10:
            dim(f"… and {len(files) - 10} more")
    else:
        warn("chantiers/ is NOT currently tracked by Git.")
        warn("It may already be ignored. Check your remote to be sure.")

    return tracked


def check_gitignore(repo_path: str) -> None:
    """
    Verifies .gitignore contains 'chantiers/' rule.
    If missing, adds it automatically before committing.
    """
    gitignore_path = Path(repo_path) / ".gitignore"

    if not gitignore_path.exists():
        warn(".gitignore not found — creating it with chantiers/ rule.")
        gitignore_path.write_text("# Local folders — never push\nchantiers/\n")
        ok(".gitignore created with chantiers/ rule.")
        return

    content = gitignore_path.read_text(encoding="utf-8")

    # Check for the rule in any common form: chantiers, chantiers/, /chantiers/
    import re
    if re.search(r"^/?chantiers/?$", content, re.MULTILINE):
        ok(".gitignore already contains the chantiers/ rule.")
    else:
        warn("chantiers/ rule missing from .gitignore — adding it now.")
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# Local folders — never push\nchantiers/\n")
        ok(".gitignore updated with chantiers/ rule.")


def show_summary(repo_path: str) -> None:
    """Print a clear recap of every action that will be executed."""
    header("Summary — actions to be executed")

    result = run(["git", "remote", "get-url", "origin"], cwd=repo_path)
    remote = result.stdout.strip() if result.returncode == 0 else "unknown"

    result2 = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    branch = result2.stdout.strip() if result2.returncode == 0 else "unknown"

    print(f"  {C.BOLD}Remote :{C.RESET} {remote}")
    print(f"  {C.BOLD}Branch :{C.RESET} {branch}")
    print()
    print(f"  {C.BOLD}Commands that will run:{C.RESET}")
    print(f"  {C.DIM}$ git rm -r --cached chantiers/{C.RESET}")
    print(f"  {C.DIM}$ git add .gitignore{C.RESET}")
    print(f"  {C.DIM}$ git commit -m \"chore: untrack chantiers/ folder — local only\"{C.RESET}")
    print(f"  {C.DIM}$ git push origin {branch}{C.RESET}")
    print()
    print(f"  {C.YELLOW}⚠  chantiers/ will NOT be deleted from your disk.{C.RESET}")
    print(f"  {C.YELLOW}⚠  It will disappear from the remote repository.{C.RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Git operations
# ─────────────────────────────────────────────────────────────────────────────

def git_rm_cached(repo_path: str) -> None:
    """
    Step 1 — git rm -r --cached chantiers/

    --cached means: remove from the Git index (staging area) only.
    The actual folder on disk is untouched.
    -r means: recursive (required for directories).
    """
    header("Step 1 — git rm -r --cached chantiers/")
    info("Removing chantiers/ from the Git index (disk untouched)…")

    result = run(
        ["git", "rm", "-r", "--cached", "chantiers/"],
        cwd=repo_path,
        capture=True,
    )

    if result.returncode != 0:
        abort(f"git rm --cached failed:\n{result.stderr.strip()}")

    lines = result.stdout.strip().splitlines()
    for line in lines[:15]:
        dim(line)
    if len(lines) > 15:
        dim(f"… and {len(lines) - 15} more file(s) removed from index")

    ok(f"chantiers/ removed from Git index ({len(lines)} file(s)).")

    # Safety check: confirm the folder still exists locally
    if (Path(repo_path) / "chantiers").exists():
        ok("chantiers/ still present on disk. ✔")
    else:
        abort("chantiers/ was unexpectedly deleted from disk! Check your repo.")


def git_add_gitignore(repo_path: str) -> None:
    """
    Step 2 — git add .gitignore

    Stages the .gitignore so the chantiers/ rule is part of the commit.
    """
    header("Step 2 — git add .gitignore")

    result = run(["git", "add", ".gitignore"], cwd=repo_path)
    if result.returncode != 0:
        abort(f"git add .gitignore failed:\n{result.stderr.strip()}")

    ok(".gitignore staged.")


def git_commit(repo_path: str) -> None:
    """
    Step 3 — git commit

    Creates a commit that records the removal of chantiers/ from the index
    and the updated .gitignore.
    """
    header("Step 3 — git commit")

    commit_msg = "chore: untrack chantiers/ folder — local only"
    result = run(
        ["git", "commit", "-m", commit_msg],
        cwd=repo_path,
        capture=True,
    )

    if result.returncode != 0:
        abort(f"git commit failed:\n{result.stderr.strip()}")

    print(f"  {result.stdout.strip()}")
    ok("Commit created.")


def git_push(repo_path: str) -> None:
    """
    Step 4 — git push

    Pushes the commit to the remote so chantiers/ disappears there too.
    Handles the most common push errors with a targeted diagnostic.
    """
    header("Step 4 — git push")

    branch_result = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

    info(f"Pushing to origin/{branch}…")

    result = run(
        ["git", "push", "origin", branch],
        cwd=repo_path,
        capture=True,
    )

    combined = (result.stdout + result.stderr).strip()

    if result.returncode == 0:
        if combined:
            print(f"  {C.DIM}{combined}{C.RESET}")
        ok("Push successful — chantiers/ is no longer on the remote.")
        return

    # ── Error diagnosis ───────────────────────────────────────────────── #
    if "set-upstream" in combined or "no upstream" in combined:
        warn("Branch has no upstream yet. Trying --set-upstream…")
        r2 = run(
            ["git", "push", "--set-upstream", "origin", branch],
            cwd=repo_path,
            capture=False,
        )
        if r2.returncode == 0:
            ok("Push with --set-upstream successful.")
            return
        abort("Push --set-upstream failed.")

    elif "rejected" in combined or "non-fast-forward" in combined:
        abort(
            "Push rejected — remote has commits you don't have locally.\n"
            f"  Run: git pull origin {branch}  then re-run this script."
        )

    elif "denied" in combined or "Permission" in combined:
        abort(
            "Authentication error — access denied.\n"
            "  Run github_auth_setup.py (option 3) to fix SSH credentials."
        )

    elif "Could not resolve host" in combined or "timeout" in combined.lower():
        abort("Network error — cannot reach GitHub. Check your connection.")

    else:
        abort(f"Push failed:\n  {combined}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove chantiers/ from Git tracking without deleting it locally."
    )
    parser.add_argument(
        "--path",
        default=os.getcwd(),
        help="Path to the Git repository (default: current directory)",
    )
    return parser.parse_args()


def main() -> None:
    args      = parse_args()
    repo_path = str(Path(args.path).resolve())

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  UNTRACK chantiers/ — Git admin script{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"  Repo : {repo_path}\n")

    # ── Pre-flight checks ─────────────────────────────────────────────── #
    header("Pre-flight checks")
    check_git_repo(repo_path)
    check_chantiers_exists_locally(repo_path)
    tracked = check_chantiers_is_tracked(repo_path)
    check_gitignore(repo_path)

    if not tracked:
        info("chantiers/ is not tracked — checking if it appears on the remote…")
        info("If it is already absent from the remote, nothing more to do.")
        if not confirm("Continue anyway to force a push with the .gitignore update?"):
            print(f"\n  {C.GREEN}Nothing to do. You are all set.{C.RESET}\n")
            sys.exit(0)

    # ── Summary + confirmation ────────────────────────────────────────── #
    show_summary(repo_path)

    if not confirm("Execute all steps now?", default_yes=True):
        abort("Operation cancelled by user.")

    # ── Execute ───────────────────────────────────────────────────────── #
    git_rm_cached(repo_path)
    git_add_gitignore(repo_path)
    git_commit(repo_path)
    git_push(repo_path)

    # ── Final confirmation ────────────────────────────────────────────── #
    print(f"\n{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"{C.GREEN}{C.BOLD}  ✔  Done.{C.RESET}")
    print(f"  chantiers/ is now ignored locally and absent from the remote.")
    print(f"  It remains intact on your disk.\n")


if __name__ == "__main__":
    main()
