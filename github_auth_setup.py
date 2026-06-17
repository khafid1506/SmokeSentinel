#!/usr/bin/env python3
"""
github_auth_setup.py

EDUCATIONAL ADMIN SCRIPT
=========================

Purpose:
    Help fix the following Git error when pushing to GitHub over HTTPS:

        remote: Invalid username or token. Password authentication is not supported
        fatal: Authentication failed for 'https://github.com/...'

Why this error happens:
    GitHub removed support for password authentication on Git operations
    (HTTPS push/pull). You now need either:
        1. A Personal Access Token (PAT) used INSTEAD of a password, or
        2. SSH key-based authentication (no password/token needed at all)

This script walks through BOTH solutions, step by step, with comments
explaining what each line does and why it's needed.

Usage:
    python github_auth_setup.py
"""

# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------

# 'os' lets us check the operating system (Windows vs Linux/Mac) and
# interact with environment-related things like file permissions.
import os

# 'subprocess' lets Python run external shell commands (git, ssh, etc.)
# exactly as if you typed them in a terminal.
import subprocess

# 'sys' is used here to exit the script with a specific status code
# (e.g. sys.exit(1) means "exit with an error").
import sys

# 'Path' (from pathlib) is a modern, cross-platform way to handle
# file and folder paths instead of manually concatenating strings.
from pathlib import Path


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def run(cmd, check=True, capture=False):
    """
    Run a shell command (given as a list of strings, e.g. ["git", "push"]).

    Parameters:
        cmd     -> list of command parts, e.g. ["git", "remote", "-v"]
        check   -> if True, stop the script if the command fails
        capture -> if True, capture the command's output instead of
                   printing it directly to the terminal

    Returns:
        The subprocess.CompletedProcess result object, so the caller
        can inspect stdout/stderr if needed.
    """
    # Print the command before running it, so the user can see exactly
    # what is being executed (transparency = good practice for admin scripts).
    print(f"\n$ {' '.join(cmd)}")

    # subprocess.run() actually executes the command.
    # text=True means stdout/stderr will be returned as strings, not bytes.
    result = subprocess.run(
        cmd,
        check=False,        # we handle errors manually below
        capture_output=capture,
        text=True,
    )

    # If we captured the output, print it so the user can read it.
    if capture:
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

    # If 'check' is True and the command failed (non-zero exit code),
    # stop the whole script — continuing would likely cause more errors.
    if check and result.returncode != 0:
        print(f"Error while running: {' '.join(cmd)}")
        sys.exit(result.returncode)

    return result


def get_remote_url():
    """
    Return the list of Git remotes configured for the current repository
    (equivalent to running 'git remote -v' manually).
    """
    # capture=True so we get the output back instead of it being printed
    # twice; check=False because this command should never crash the script
    # even if there's no remote configured yet.
    result = run(["git", "remote", "-v"], capture=True, check=False)
    return result.stdout


# ----------------------------------------------------------------------
# SOLUTION 1: Personal Access Token (PAT)
# ----------------------------------------------------------------------

def setup_pat():
    """
    Guide the user through creating and using a GitHub Personal Access
    Token (PAT) instead of a password for HTTPS Git operations.
    """
    print("\n=== SOLUTION 1: Personal Access Token (PAT) ===\n")

    # Step-by-step instructions for the human — the script can't create
    # a token automatically because it requires logging into GitHub's UI.
    print("1. Go to GitHub -> Settings -> Developer settings")
    print("   -> Personal access tokens -> Tokens (classic)")
    print("2. Click 'Generate new token' -> select at least the 'repo' scope")
    print("3. Copy the generated token (it will only be shown once)\n")

    # Pause the script until the user confirms they have the token ready.
    # This prevents the script from moving on before the human is ready.
    input("Press Enter once the token has been generated and copied...")

    # Remove any previously cached (and now invalid) credential helper
    # configuration. 'check=False' because this command may "fail" if
    # no credential.helper was set — that's not a real error.
    print("\nRemoving any cached Git credential helper configuration...")
    run(["git", "config", "--global", "--unset", "credential.helper"], check=False)

    # Ask the user whether they want Git to remember the token for next time,
    # so they don't have to paste it on every single push.
    use_manager = input(
        "Use a credential helper (manager / cache) to store the token "
        "persistently? [y/N]: "
    ).strip().lower()

    if use_manager == "y":
        # os.name == "nt" means the script is running on Windows.
        if os.name == "nt":
            # 'manager' uses the Git Credential Manager on Windows,
            # which securely stores credentials in Windows Credential Manager.
            run(["git", "config", "--global", "credential.helper", "manager"])
        else:
            # On Linux/Mac, 'cache' stores the credential in memory for
            # a limited time (here: 3600 seconds = 1 hour).
            run(["git", "config", "--global", "credential.helper", "cache --timeout=3600"])

        print("Credential helper configured.")

    # Final instructions: explain exactly what to type at the next git push.
    print("\nOn your next 'git push', Git will ask for credentials:")
    print("  - Username : your GitHub username")
    print("  - Password : paste the PAT you generated (NOT your GitHub password)\n")

    # Extra tip in case an old, invalid credential is still cached on Windows.
    print("Tip: to clear an old/invalid cached credential on Windows:")
    print("  Control Panel -> Credential Manager")
    print("  -> Windows Credentials -> remove the 'git:https://github.com' entry\n")


# ----------------------------------------------------------------------
# SOLUTION 2: SSH
# ----------------------------------------------------------------------

def setup_ssh():
    """
    Guide the user through setting up SSH authentication with GitHub:
    generate a key, load it into the SSH agent, test the connection,
    and switch the Git remote from HTTPS to SSH.
    """
    print("\n=== SOLUTION 2: SSH Configuration ===\n")

    # Path.home() returns the user's home directory (cross-platform).
    # We append ".ssh" because that's the standard folder where SSH
    # keys and configuration live.
    ssh_dir = Path.home() / ".ssh"

    # This will be the path to our private key file (e.g. ~/.ssh/id_ed25519).
    key_path = ssh_dir / "id_ed25519"

    # Check if a key already exists, so we don't accidentally overwrite it.
    if key_path.exists():
        print(f"An SSH key already exists: {key_path}")
    else:
        # Ask for an email address — this is just a label/comment embedded
        # in the key, traditionally used to identify who owns it.
        email = input("Enter your GitHub email (used as a label for the key): ").strip()

        # Create the ~/.ssh directory if it doesn't exist yet.
        # mode=0o700 means "only the owner can read/write/execute this folder",
        # which is required for SSH to trust the directory.
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

        # Generate a new SSH key pair:
        #   -t ed25519   -> use the modern, secure Ed25519 algorithm
        #   -C email     -> attach the email as a comment/label
        #   -f key_path  -> save the key at this specific path
        #   -N ""        -> set an EMPTY passphrase (simpler for automation;
        #                    in a real environment, consider using a passphrase)
        run([
            "ssh-keygen",
            "-t", "ed25519",
            "-C", email,
            "-f", str(key_path),
            "-N", "",
        ])

    # The SSH agent is a background program that holds your decrypted
    # private keys in memory, so you don't have to type a passphrase
    # every time you connect.
    print("\nStarting the SSH agent...")

    # os.name != "nt" means we're NOT on Windows (so Linux/Mac).
    # On Linux/Mac, ssh-agent needs to be started explicitly in this shell.
    # On Windows, ssh-agent is usually managed as a system service instead.
    if os.name != "nt":
        run(["bash", "-c", 'eval "$(ssh-agent -s)"'], check=False)

    # Add our private key to the running SSH agent so it can be used
    # automatically for authentication.
    run(["ssh-add", str(key_path)], check=False)

    # List the keys currently loaded in the agent, as a sanity check.
    # -l means "list fingerprints of loaded keys".
    run(["ssh-add", "-l"], check=False, capture=True)

    # The public key file (the one we share with GitHub) has the same
    # name as the private key, plus a ".pub" extension.
    pub_key_path = Path(str(key_path) + ".pub")

    if pub_key_path.exists():
        # Display the public key content so the user can copy it.
        print(f"\nPublic key ({pub_key_path}):\n")
        print(pub_key_path.read_text())

        print(
            "\nAdd this public key to GitHub:\n"
            "  Settings -> SSH and GPG keys -> New SSH key\n"
        )

        # Wait for the user to confirm they've added the key on GitHub's
        # website before we try to test the connection.
        input("Press Enter once the key has been added to GitHub...")

    # Test the SSH connection to GitHub.
    # 'ssh -T git@github.com' attempts authentication WITHOUT opening
    # a shell (-T = disable pseudo-terminal allocation), which is exactly
    # what GitHub recommends for testing.
    print("\nTesting SSH connection to GitHub...")
    test = run(["ssh", "-T", "git@github.com"], check=False, capture=True)

    # Combine stdout and stderr because GitHub's success message is
    # actually sent to stderr (this is normal SSH behavior, not an error).
    output = (test.stdout or "") + (test.stderr or "")

    if "successfully authenticated" in output:
        print("\n✅ SSH connection successful!")
    else:
        # If the expected success message isn't found, give the user
        # troubleshooting hints for the most common failure causes.
        print(
            "\n⚠️ Could not automatically confirm the SSH connection.\n"
            "Check the message above. Common issues:\n"
            "  - 'Permission denied (publickey)' -> the key was not added "
            "to GitHub, or is not loaded in the agent (run ssh-add again)\n"
            "  - 'Could not open a connection to your authentication agent' "
            "-> re-run: eval \"$(ssh-agent -s)\"\n"
        )

    # Show the current remote(s) so the user can see the existing
    # (HTTPS) URL before we change it.
    print("\nCurrent remote(s):")
    print(get_remote_url())

    # Ask before making any changes to the repository configuration —
    # admin scripts should avoid silent, irreversible modifications.
    switch = input(
        "\nDo you want to switch the 'origin' remote to SSH? [y/N]: "
    ).strip().lower()

    if switch == "y":
        # Ask for the repo path in the form "username/repo-name",
        # which is the part of the URL after "github.com/".
        repo = input(
            "Enter the GitHub repo path (e.g. khafid1506/SmokeSentinel): "
        ).strip()

        # Build the SSH-style URL. SSH URLs look like:
        #   git@github.com:username/repo.git
        # (note the ':' instead of '/' after github.com)
        ssh_url = f"git@github.com:{repo}.git"

        # 'git remote set-url origin <url>' changes where 'origin' points,
        # without affecting your commit history or branches.
        run(["git", "remote", "set-url", "origin", ssh_url])

        print("\nNew remote:")
        print(get_remote_url())


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def main():
    """
    Display a menu and run the chosen solution(s).
    This is the function that runs when the script is executed directly.
    """
    print("=" * 60)
    print(" Admin script - GitHub authentication setup")
    print(" Fixes: 'Password authentication is not supported'")
    print("=" * 60)

    print("\nChoose an option:")
    print("  1 - Personal Access Token (PAT) - quick fix")
    print("  2 - SSH - recommended long-term solution")
    print("  3 - Both")
    print("  0 - Exit")

    # input() always returns a string, so we compare against string values.
    choice = input("\nYour choice: ").strip()

    if choice == "1":
        setup_pat()
    elif choice == "2":
        setup_ssh()
    elif choice == "3":
        setup_pat()
        setup_ssh()
    else:
        print("Cancelled.")
        sys.exit(0)

    print("\nSetup complete. Test it with: git push")


# This standard Python idiom means:
# "Only run main() if this file is executed directly,
#  not if it's imported as a module from another script."
if __name__ == "__main__":
    main()
