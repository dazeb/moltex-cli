"""MOLTEX PRO — Skill and environment installer.

Handles installing the MOLTEX agent skill into Hermes/Codex/etc
and setting up the Python environment.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"

SKILL_REPO = "https://github.com/dazeb/agents-skill-moltex-trader"
SKILL_NAME = "moltex-pro"


def _run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command with nice output."""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def _has_npx() -> bool:
    """Check if npx is available."""
    return shutil.which("npx") is not None


def _has_pip() -> bool:
    """Check if pip is available."""
    return shutil.which("pip") is not None or shutil.which("pip3") is not None


def _pip_cmd() -> str:
    """Return the correct pip command."""
    if shutil.which("pip3"):
        return "pip3"
    return "pip"


def install_python_deps():
    """Install Python dependencies (pynacl, requests)."""
    print(f"\n{BOLD}━━━ Python Dependencies{RESET}\n")

    pkgs = ["pynacl>=1.5.0", "requests>=2.31.0"]
    pip = _pip_cmd()

    for pkg in pkgs:
        name = pkg.split(">=")[0].split("==")[0]
        try:
            __import__(name.replace("-", "_"))
            print(f"  {GREEN}✓{RESET} {name} already installed")
        except ImportError:
            print(f"  {YELLOW}!{RESET} Installing {name}...")
            _run([sys.executable, "-m", "pip", "install", "--quiet", pkg])
            print(f"  {GREEN}✓{RESET} {name} installed")


def install_skill(force: bool = False) -> bool:
    """Install the MOLTEX agent skill via npx skills add.

    Returns True if installed successfully.
    """
    print(f"\n{BOLD}━━━ Agent Skill Installation{RESET}\n")

    if not _has_npx():
        print(f"  {YELLOW}!{RESET} npx not found — skipping skill installation")
        print(f"    Install Node.js to enable automatic skill setup:")
        print(f"    {CYAN}https://nodejs.org{RESET}")
        print(f"\n    Or install manually:")
        print(f"    {CYAN}npx skills add {SKILL_REPO}{RESET}")
        return False

    # Check if skill already installed
    project_agents = Path(".agents") / "skills" / SKILL_NAME
    home_agents = Path.home() / ".agents" / "skills" / SKILL_NAME
    hermes_skills = Path.home() / ".hermes" / "skills" / SKILL_NAME
    skill_dir = project_agents if project_agents.exists() else (home_agents if home_agents.exists() else hermes_skills)
    if skill_dir.exists() and not force:
        print(f"  {GREEN}✓{RESET} Skill '{SKILL_NAME}' already installed")
        print(f"    {DIM}Location: {skill_dir}{RESET}")
        print(f"    Re-run with --force to reinstall")
        return True

    # Install via npx skills add -y (non-interactive, auto-select all agents)
    print(f"  Installing {CYAN}{SKILL_NAME}{RESET} skill...")
    print(f"  {DIM}npx skills add {SKILL_REPO} -y{RESET}\n")

    try:
        result = _run(
            ["npx", "skills", "add", SKILL_REPO, "-y"],
            check=True,
            capture=True,
        )
        # Print npx output
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
        print(f"\n  {GREEN}✓{RESET} Skill '{SKILL_NAME}' installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  {RED}✗{RESET} Skill installation failed")
        if e.stderr:
            for line in e.stderr.strip().split("\n"):
                print(f"    {RED}{line}{RESET}")
        print(f"\n  Install manually:")
        print(f"    {CYAN}npx skills add {SKILL_REPO}{RESET}")
        return False
    except FileNotFoundError:
        print(f"  {RED}✗{RESET} npx not found. Install Node.js first.")
        return False


def check_env() -> dict:
    """Check environment readiness. Returns dict of check results."""
    results = {}

    # Python
    ver = sys.version.split()[0]
    results["python"] = {
        "ok": sys.version_info >= (3, 10),
        "detail": f"Python {ver}",
    }

    # pip
    results["pip"] = {
        "ok": _has_pip(),
        "detail": _pip_cmd() if _has_pip() else "not found",
    }

    # pynacl
    try:
        import nacl
        results["pynacl"] = {"ok": True, "detail": f"v{nacl.__version__}"}
    except ImportError:
        results["pynacl"] = {"ok": False, "detail": "not installed"}

    # requests
    try:
        import requests
        results["requests"] = {"ok": True, "detail": f"v{requests.__version__}"}
    except ImportError:
        results["requests"] = {"ok": False, "detail": "not installed"}

    # npx
    results["npx"] = {
        "ok": _has_npx(),
        "detail": shutil.which("npx") or "not found",
    }

    # Existing key
    keyfile = Path.home() / ".moltex" / "agent_key.json"
    results["keypair"] = {
        "ok": keyfile.exists(),
        "detail": str(keyfile) if keyfile.exists() else "no keyfile",
    }

    # Skill installed — check both .agents/skills (npx skills) and ~/.hermes/skills
    project_agents = Path(".agents") / "skills" / SKILL_NAME
    home_agents = Path.home() / ".agents" / "skills" / SKILL_NAME
    hermes_skills = Path.home() / ".hermes" / "skills" / SKILL_NAME
    skill_found = project_agents.exists() or home_agents.exists() or hermes_skills.exists()
    skill_loc = project_agents if project_agents.exists() else (home_agents if home_agents.exists() else hermes_skills)
    results["skill"] = {
        "ok": skill_found,
        "detail": str(skill_loc) if skill_found else "not installed",
    }

    return results


def print_env_report():
    """Print a formatted environment check report."""
    print(f"\n{BOLD}━━━ Environment Check{RESET}\n")

    results = check_env()

    labels = {
        "python": "Python",
        "pip": "pip",
        "pynacl": "PyNaCl",
        "requests": "requests",
        "npx": "npx",
        "keypair": "Agent Keypair",
        "skill": "MOLTEX Skill",
    }

    all_ok = True
    for key, label in labels.items():
        r = results[key]
        icon = f"{GREEN}✓{RESET}" if r["ok"] else f"{RED}✗{RESET}"
        print(f"  {icon} {label:16s} {r['detail']}")
        if not r["ok"]:
            all_ok = False

    print()
    return all_ok


def full_install(force_skill: bool = False):
    """Run the complete installation: deps + skill."""
    print(f"\n{BOLD}{CYAN}┌─────────────────────────────────────────────────────────┐{RESET}")
    print(f"{BOLD}{CYAN}│{RESET}  {BOLD}{GREEN}MOLTEX PRO — Full Installation{RESET}                       {BOLD}{CYAN}│{RESET}")
    print(f"{BOLD}{CYAN}└─────────────────────────────────────────────────────────┘{RESET}")

    # 1. Python deps
    install_python_deps()

    # 2. Skill
    install_skill(force=force_skill)

    # 3. Summary
    print(f"\n{BOLD}━━━ Installation Complete{RESET}\n")
    print(f"  {GREEN}✓{RESET} Python client ready")
    print(f"  {GREEN}✓{RESET} Agent skill installed\n")

    print(f"  {BOLD}Next steps:{RESET}")
    print(f"    1. Set up your agent:  {CYAN}moltex setup{RESET}")
    print(f"    2. Check portfolio:    {CYAN}moltex portfolio{RESET}")
    print(f"    3. Start trading:      {CYAN}moltex state{RESET}\n")

    print(f"  {DIM}Docs: https://moltex.pro/skill.md{RESET}")
    print(f"  {DIM}Keys: ~/.moltex/agent_key.json{RESET}\n")
