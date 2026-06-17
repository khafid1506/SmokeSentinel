#!/usr/bin/env python3
"""
git_commit_push.py

SCRIPT D'ADMINISTRATION GIT — COMMIT & PUSH SÉCURISÉ
=====================================================

Automatise le cycle complet :
    git add .  →  git commit -m "<message>"  →  git push

Checks inclus (dans l'ordre d'exécution) :
    ✔ Vérifie que git est installé
    ✔ Vérifie que le dossier courant est bien un dépôt Git
    ✔ Vérifie que la remote 'origin' est configurée
    ✔ Vérifie que la branche courante est connue (protection anti-HEAD détaché)
    ✔ Alerte si la branche est 'main' ou 'master' (demande confirmation)
    ✔ Affiche les fichiers modifiés / non suivis avant l'ajout
    ✔ Alerte si aucune modification n'est détectée (rien à committer)
    ✔ Alerte si des fichiers sensibles (.env, secrets, clés) sont sur le point d'être commités
    ✔ Valide que le message de commit n'est pas vide et respecte une longueur minimale
    ✔ Affiche un récapitulatif complet avant d'exécuter quoi que ce soit
    ✔ Demande confirmation finale avant le push
    ✔ Gère les erreurs SSH / token / réseau et affiche un diagnostic clair

Usage :
    python git_commit_push.py
    python git_commit_push.py --path /chemin/vers/ton/repo
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Constantes de configuration
# ─────────────────────────────────────────────────────────────────────────────

# Branches qui méritent une confirmation explicite avant tout push
PROTECTED_BRANCHES = {"main", "master", "production", "prod", "release"}

# Patterns de fichiers considérés comme sensibles
SENSITIVE_PATTERNS = [
    r"\.env(\..+)?$",          # .env, .env.local, .env.production …
    r"\.pem$",                  # certificats privés
    r"\.key$",                  # clés privées
    r"secrets?\.(json|ya?ml|toml)$",
    r"credentials?\.(json|ya?ml)$",
    r"id_rsa",                  # clés SSH privées
    r"id_ed25519$",
    r"\.p12$",                  # keystores
    r"\.pfx$",
    r"config\.ya?ml$",          # fichiers de config potentiellement sensibles
    r"database\.ya?ml$",
]

# Longueur minimale acceptable pour un message de commit
MIN_COMMIT_MSG_LENGTH = 10

# Couleurs ANSI pour le terminal
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires d'affichage
# ─────────────────────────────────────────────────────────────────────────────

def header(title: str) -> None:
    """Affiche un séparateur de section lisible."""
    bar = "─" * 60
    print(f"\n{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  {title}{C.RESET}")
    print(f"{C.CYAN}{bar}{C.RESET}")


def ok(msg: str) -> None:
    print(f"{C.GREEN}  ✔  {msg}{C.RESET}")


def warn(msg: str) -> None:
    print(f"{C.YELLOW}  ⚠  {msg}{C.RESET}")


def error(msg: str) -> None:
    print(f"{C.RED}  ✖  {msg}{C.RESET}")


def info(msg: str) -> None:
    print(f"{C.CYAN}  ℹ  {msg}{C.RESET}")


def abort(msg: str) -> None:
    """Affiche une erreur fatale et quitte le script."""
    error(msg)
    print(f"\n{C.RED}{C.BOLD}  Abandon.{C.RESET}\n")
    sys.exit(1)


def confirm(prompt: str, default_yes: bool = False) -> bool:
    """
    Demande une confirmation y/n à l'utilisateur.
    default_yes=True → Entrée seule compte comme 'oui'.
    """
    hint = "[O/n]" if default_yes else "[o/N]"
    answer = input(f"\n{C.BOLD}  {prompt} {hint} : {C.RESET}").strip().lower()
    if answer == "":
        return default_yes
    return answer in ("o", "y", "oui", "yes")


# ─────────────────────────────────────────────────────────────────────────────
# Exécution de commandes shell
# ─────────────────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str = None, capture: bool = True,
        check: bool = False) -> subprocess.CompletedProcess:
    """
    Exécute une commande shell.

    Paramètres :
        cmd     -> liste des arguments, ex. ["git", "status", "--short"]
        cwd     -> répertoire de travail (None = répertoire courant)
        capture -> si True, récupère stdout/stderr au lieu de les afficher
        check   -> si True, lève une exception si le code de retour ≠ 0

    Retourne :
        L'objet CompletedProcess avec .returncode, .stdout, .stderr
    """
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        check=check,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Checks préliminaires
# ─────────────────────────────────────────────────────────────────────────────

def check_git_installed() -> None:
    """Vérifie que la commande 'git' est disponible sur le système."""
    result = run(["git", "--version"])
    if result.returncode != 0:
        abort("Git n'est pas installé ou n'est pas dans le PATH.")
    ok(f"Git détecté : {result.stdout.strip()}")


def check_is_git_repo(repo_path: str) -> None:
    """
    Vérifie que repo_path (ou le dossier courant) est bien à l'intérieur
    d'un dépôt Git.  'git rev-parse --git-dir' échoue si ce n'est pas le cas.
    """
    result = run(["git", "rev-parse", "--git-dir"], cwd=repo_path)
    if result.returncode != 0:
        abort(
            f"'{repo_path}' n'est pas un dépôt Git.\n"
            "  Lancez d'abord : git init"
        )
    ok(f"Dépôt Git valide : {repo_path}")


def check_remote(repo_path: str) -> str:
    """
    Vérifie qu'une remote 'origin' est configurée et retourne son URL.
    Sans remote, git push ne sait pas où envoyer les commits.
    """
    result = run(["git", "remote", "get-url", "origin"], cwd=repo_path)
    if result.returncode != 0:
        abort(
            "Aucune remote 'origin' configurée.\n"
            "  Exemple : git remote add origin git@github.com:user/repo.git"
        )
    url = result.stdout.strip()
    ok(f"Remote 'origin' : {url}")
    return url


def check_branch(repo_path: str) -> str:
    """
    Récupère la branche courante.
    Alerte si on est en mode HEAD détaché (dangereux pour les pushs).
    """
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    if result.returncode != 0:
        abort("Impossible de déterminer la branche courante.")

    branch = result.stdout.strip()

    if branch == "HEAD":
        # Mode HEAD détaché : les commits ne sont rattachés à aucune branche.
        # Un push dans cet état est souvent une erreur.
        abort(
            "Vous êtes en mode HEAD détaché (detached HEAD).\n"
            "  Créez ou basculez sur une branche avant de committer :\n"
            "  git checkout -b ma-branche"
        )

    ok(f"Branche courante : {C.BOLD}{branch}{C.RESET}")
    return branch


def check_protected_branch(branch: str) -> None:
    """
    Affiche un avertissement explicite si la branche est protégée
    (main, master, production…) et demande confirmation.
    Pousse sur main directement est souvent une mauvaise pratique.
    """
    if branch in PROTECTED_BRANCHES:
        warn(
            f"Vous êtes sur la branche protégée '{C.BOLD}{branch}{C.RESET}{C.YELLOW}'.\n"
            f"  Pousser directement sur '{branch}' est risqué en équipe.\n"
            "  Préférez une branche de feature + Pull Request."
        )
        if not confirm(f"Continuer quand même sur '{branch}' ?", default_yes=False):
            abort("Push annulé par l'utilisateur.")


# ─────────────────────────────────────────────────────────────────────────────
# Analyse des fichiers modifiés
# ─────────────────────────────────────────────────────────────────────────────

def get_status(repo_path: str) -> list[tuple[str, str]]:
    """
    Retourne la liste des fichiers modifiés sous forme de tuples (code, chemin).
    'git status --porcelain' produit une sortie stable et scriptable :
       M  fichier.py   -> modifié
       ??  nouveau.txt  -> non suivi (untracked)
       D  supprimé.go  -> supprimé
       etc.
    """
    result = run(["git", "status", "--porcelain"], cwd=repo_path)
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    parsed = []
    for line in lines:
        # Les deux premiers caractères = code de statut, le reste = chemin
        code = line[:2].strip()
        path = line[3:].strip()
        parsed.append((code, path))
    return parsed


def display_status(files: list[tuple[str, str]]) -> None:
    """Affiche la liste des fichiers avec une couleur selon leur statut."""
    code_labels = {
        "M":  (C.YELLOW, "modifié "),
        "MM": (C.YELLOW, "modifié "),
        "A":  (C.GREEN,  "ajouté  "),
        "D":  (C.RED,    "supprimé"),
        "R":  (C.CYAN,   "renommé "),
        "C":  (C.CYAN,   "copié   "),
        "??": (C.DIM,    "nouveau "),
        "UU": (C.RED,    "conflit "),
    }
    for code, path in files:
        color, label = code_labels.get(code, (C.WHITE, code.ljust(8)))
        print(f"    {color}{label}{C.RESET}  {path}")


def check_no_changes(files: list[tuple[str, str]]) -> None:
    """
    Arrête le script si aucune modification n'est détectée.
    Évite de créer un commit vide, ce qui polluerait l'historique.
    """
    if not files:
        abort(
            "Aucune modification détectée.\n"
            "  L'arbre de travail est propre — rien à committer."
        )


def check_merge_conflicts(files: list[tuple[str, str]]) -> None:
    """
    Détecte les fichiers en conflit de merge non résolus (code 'UU', 'AA'…).
    Un commit avec des marqueurs de conflit (<<<<<<<) est toujours une erreur.
    """
    conflict_codes = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
    conflicts = [(c, p) for c, p in files if c in conflict_codes]
    if conflicts:
        error("Conflits de merge non résolus :")
        for code, path in conflicts:
            print(f"    {C.RED}{code}  {path}{C.RESET}")
        abort(
            "Résolvez les conflits avant de committer.\n"
            "  Utilisez : git mergetool  ou éditez les fichiers manuellement,\n"
            "  puis : git add <fichier>"
        )


def check_sensitive_files(files: list[tuple[str, str]]) -> None:
    """
    Détecte les fichiers potentiellement sensibles sur le point d'être commités
    (.env, clés SSH, secrets…).  Propose d'abandonner ou de continuer.
    Ne bloque pas définitivement — l'utilisateur peut choisir de continuer
    s'il sait ce qu'il fait (ex: .env.example sans vraies valeurs).
    """
    flagged = []
    for _, path in files:
        filename = Path(path).name
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                flagged.append(path)
                break  # un seul match suffit par fichier

    if flagged:
        warn("Fichiers potentiellement sensibles détectés :")
        for path in flagged:
            print(f"    {C.YELLOW}⚠  {path}{C.RESET}")
        print(
            f"\n  {C.DIM}Ces fichiers contiennent peut-être des mots de passe,\n"
            f"  clés API ou secrets. Vérifiez qu'ils appartiennent bien au\n"
            f"  commit et ne figurent pas dans .gitignore.{C.RESET}"
        )
        if not confirm("Inclure quand même ces fichiers ?", default_yes=False):
            abort(
                "Push annulé.\n"
                "  Ajoutez les fichiers sensibles à .gitignore, puis relancez."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Message de commit
# ─────────────────────────────────────────────────────────────────────────────

def ask_commit_message() -> str:
    """
    Invite l'utilisateur à saisir un message de commit.
    Valide :
        - message non vide
        - longueur minimale (MIN_COMMIT_MSG_LENGTH caractères)
        - pas uniquement des espaces / caractères spéciaux

    Affiche des conseils de style Conventional Commits si l'utilisateur
    semble écrire un message générique.
    """
    header("Message de commit")

    print(
        f"  {C.DIM}Conseils — Conventional Commits :\n"
        f"    feat: ajoute une nouvelle fonctionnalité\n"
        f"    fix:  corrige un bug\n"
        f"    docs: modifie la documentation\n"
        f"    refactor: restructuration sans changement de comportement\n"
        f"    chore: tâche de maintenance (deps, CI…){C.RESET}\n"
    )

    generic_messages = {
        "update", "fix", "commit", "changes", "wip",
        "test", "modif", "modifs", "maj", "misc",
    }

    while True:
        msg = input(f"  {C.BOLD}Message de commit : {C.RESET}").strip()

        if not msg:
            warn("Le message de commit ne peut pas être vide.")
            continue

        if len(msg) < MIN_COMMIT_MSG_LENGTH:
            warn(
                f"Message trop court ({len(msg)} caractères).\n"
                f"  Minimum requis : {MIN_COMMIT_MSG_LENGTH} caractères.\n"
                f"  Soyez descriptif — ce message vivra dans l'historique Git."
            )
            continue

        # Alerte sur les messages trop génériques
        first_word = msg.split()[0].rstrip(":").lower()
        if first_word in generic_messages and len(msg.split()) <= 2:
            warn(
                f"Le message '{msg}' est très générique.\n"
                "  Un bon message répond à : 'Ce commit fait quoi exactement ?'\n"
                "  Exemple : 'fix: corrige le crash au démarrage sur Windows'"
            )
            if not confirm("Garder ce message quand même ?", default_yes=False):
                continue

        ok(f"Message validé : \"{msg}\"")
        return msg


# ─────────────────────────────────────────────────────────────────────────────
# Récapitulatif et confirmation finale
# ─────────────────────────────────────────────────────────────────────────────

def show_summary(branch: str, remote_url: str,
                 files: list[tuple[str, str]], commit_msg: str) -> None:
    """
    Affiche un récapitulatif complet de ce qui va être exécuté.
    L'utilisateur voit exactement ce qui va se passer AVANT que cela se passe.
    """
    header("Récapitulatif — ce qui va être exécuté")

    print(f"  {C.BOLD}Remote  :{C.RESET} {remote_url}")
    print(f"  {C.BOLD}Branche :{C.RESET} {branch}")
    print(f"  {C.BOLD}Commit  :{C.RESET} \"{commit_msg}\"")
    print(f"\n  {C.BOLD}Fichiers inclus ({len(files)}) :{C.RESET}")
    display_status(files)

    print(f"\n  {C.BOLD}Commandes qui vont être lancées :{C.RESET}")
    print(f"  {C.DIM}$ git add .{C.RESET}")
    print(f"  {C.DIM}$ git commit -m \"{commit_msg}\"{C.RESET}")
    print(f"  {C.DIM}$ git push origin {branch}{C.RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Exécution Git
# ─────────────────────────────────────────────────────────────────────────────

def git_add(repo_path: str) -> None:
    """
    Exécute 'git add .' pour stager tous les fichiers modifiés.
    """
    header("git add .")
    result = run(["git", "add", "."], cwd=repo_path, capture=False)
    if result.returncode != 0:
        abort("Échec de 'git add .'.")
    ok("Tous les fichiers ont été stagés.")


def git_commit(repo_path: str, commit_msg: str) -> None:
    """
    Exécute 'git commit -m <message>'.
    Affiche le hash court du commit créé pour traçabilité.
    """
    header("git commit")
    result = run(
        ["git", "commit", "-m", commit_msg],
        cwd=repo_path,
        capture=True,
    )
    if result.returncode != 0:
        error("Échec de 'git commit'.")
        print(result.stderr.strip())
        abort("Vérifiez la configuration git (user.name, user.email).")

    # Affiche la sortie de git commit (contient le hash du commit)
    print(f"  {result.stdout.strip()}")
    ok("Commit créé avec succès.")


def git_push(repo_path: str, branch: str) -> None:
    """
    Exécute 'git push origin <branche>'.

    Gestion des erreurs courantes :
        - Branche non existante sur le remote → propose --set-upstream
        - Rejet (remote ahead)               → propose git pull
        - Erreur d'authentification SSH/HTTPS → diagnostic ciblé
        - Timeout réseau                      → message clair
    """
    header("git push")
    info(f"Push vers origin/{branch} en cours…")

    result = run(
        ["git", "push", "origin", branch],
        cwd=repo_path,
        capture=True,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    combined = stdout + "\n" + stderr

    if result.returncode == 0:
        if stdout:
            print(f"  {stdout}")
        if stderr:
            print(f"  {C.DIM}{stderr}{C.RESET}")
        ok("Push réussi !")
        return

    # ── Diagnostic d'erreurs connus ──────────────────────────────────── #

    error("Échec du push. Analyse de l'erreur…\n")

    if "set-upstream" in combined or "no upstream branch" in combined:
        warn(
            "La branche n'existe pas encore sur le remote.\n"
            f"  Lancez : git push --set-upstream origin {branch}"
        )
        if confirm("Exécuter git push --set-upstream maintenant ?", default_yes=True):
            r2 = run(
                ["git", "push", "--set-upstream", "origin", branch],
                cwd=repo_path,
                capture=False,
            )
            if r2.returncode == 0:
                ok("Push avec upstream réussi !")
                return
            else:
                abort("Échec du push --set-upstream.")
        else:
            abort("Push annulé.")

    elif "rejected" in combined or "non-fast-forward" in combined:
        warn(
            "Le remote contient des commits que vous n'avez pas localement.\n"
            "  Le push a été rejeté pour éviter d'écraser le travail des autres.\n"
            "  Solution : récupérez d'abord les changements distants :\n"
            f"    git pull origin {branch}\n"
            "  Puis relancez ce script."
        )
        abort("Push rejeté — faites un git pull d'abord.")

    elif "denied" in combined or "Permission" in combined:
        warn(
            "Erreur d'authentification / permissions refusées.\n"
            "  Causes possibles :\n"
            "    1. Mauvais compte SSH actif → lancez github_auth_setup.py option 3\n"
            "    2. Token PAT expiré         → générez-en un nouveau sur GitHub\n"
            "    3. Vous n'êtes pas collaborateur de ce dépôt\n"
            f"  Sortie Git : {stderr}"
        )
        abort("Accès refusé.")

    elif "Could not resolve host" in combined or "timeout" in combined.lower():
        warn(
            "Problème réseau — impossible de joindre GitHub.\n"
            "  Vérifiez votre connexion internet et réessayez."
        )
        abort("Erreur réseau.")

    else:
        # Erreur inconnue : on affiche la sortie brute pour diagnostiquer
        error("Erreur non reconnue :")
        print(f"  {C.RED}{stderr or stdout}{C.RESET}")
        abort("Push échoué.")


# ─────────────────────────────────────────────────────────────────────────────
# Vérification post-push
# ─────────────────────────────────────────────────────────────────────────────

def post_push_info(repo_path: str, branch: str, remote_url: str) -> None:
    """
    Affiche des informations utiles après un push réussi :
        - Hash du dernier commit
        - Lien direct vers le commit sur GitHub (si remote GitHub détecté)
    """
    header("Résumé post-push")

    # Récupère le hash court du commit qui vient d'être poussé
    result = run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_path,
        capture=True,
    )
    commit_hash = result.stdout.strip() if result.returncode == 0 else "???"

    ok(f"Dernier commit poussé : {C.BOLD}{commit_hash}{C.RESET}")
    info(f"Branche : {branch}")

    # Construit le lien GitHub si l'URL de remote est reconnue
    github_match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url)
    if github_match:
        repo_slug = github_match.group(1)
        commit_url  = f"https://github.com/{repo_slug}/commit/{commit_hash}"
        branch_url  = f"https://github.com/{repo_slug}/tree/{branch}"
        info(f"Voir le commit  : {commit_url}")
        info(f"Voir la branche : {branch_url}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """
    Analyse les arguments de la ligne de commande.
    --path permet de cibler un dépôt différent du dossier courant.
    """
    parser = argparse.ArgumentParser(
        description="Commit & push Git sécurisé avec checks et alertes."
    )
    parser.add_argument(
        "--path",
        default=os.getcwd(),
        help="Chemin vers le dépôt Git (défaut : dossier courant)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_path = str(Path(args.path).resolve())

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}   GIT COMMIT & PUSH — Script d'administration{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"  Dépôt : {repo_path}\n")

    # ── Phase 1 : Checks préliminaires ───────────────────────────────── #
    header("Vérifications préliminaires")

    check_git_installed()
    check_is_git_repo(repo_path)
    remote_url = check_remote(repo_path)
    branch     = check_branch(repo_path)
    check_protected_branch(branch)

    # ── Phase 2 : Analyse des modifications ──────────────────────────── #
    header("Fichiers modifiés")

    files = get_status(repo_path)
    check_no_changes(files)
    check_merge_conflicts(files)

    print(f"  {len(files)} fichier(s) détecté(s) :\n")
    display_status(files)

    check_sensitive_files(files)

    # ── Phase 3 : Message de commit ───────────────────────────────────── #
    commit_msg = ask_commit_message()

    # ── Phase 4 : Récapitulatif et confirmation ───────────────────────── #
    show_summary(branch, remote_url, files, commit_msg)

    if not confirm(
        f"\n  Tout semble correct. Lancer add → commit → push ?",
        default_yes=True
    ):
        abort("Opération annulée par l'utilisateur.")

    # ── Phase 5 : Exécution ───────────────────────────────────────────── #
    git_add(repo_path)
    git_commit(repo_path, commit_msg)
    git_push(repo_path, branch)

    # ── Phase 6 : Résumé final ────────────────────────────────────────── #
    post_push_info(repo_path, branch, remote_url)

    print(f"{C.GREEN}{C.BOLD}  ✔  Tout s'est bien passé !{C.RESET}\n")


if __name__ == "__main__":
    main()
