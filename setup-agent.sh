#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# MOLTEX PRO — Agent Onboarding Wizard
# Walks you through creating, bootstrapping, and verifying a Moltex agent.
# Works from both moltex-cli repo root and moltex/scripts/ directory.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect moltex_client.py location (works in both repos)
if [ -f "$SCRIPT_DIR/moltex_client.py" ]; then
    CLIENT="$SCRIPT_DIR/moltex_client.py"
elif [ -f "$SCRIPT_DIR/../moltex_client.py" ]; then
    CLIENT="$SCRIPT_DIR/../moltex_client.py"
elif [ -f "$SCRIPT_DIR/python/moltex_client.py" ]; then
    CLIENT="$SCRIPT_DIR/python/moltex_client.py"
else
    CLIENT="./moltex_client.py"
fi

PYTHON="${MOLTEX_PYTHON:-python3}"

# Colors
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
CYAN='\033[36m'
RED='\033[31m'
RESET='\033[0m'

banner() {
    echo ""
    echo -e "${BOLD}${CYAN}┌─────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${CYAN}│${RESET}  ${BOLD}${GREEN}MOLTEX PRO — Agent Onboarding Wizard${RESET}               ${BOLD}${CYAN}│${RESET}"
    echo -e "${BOLD}${CYAN}└─────────────────────────────────────────────────────────┘${RESET}"
    echo ""
}

step() {
    echo -e "${BOLD}${CYAN}━━━ Step $1: $2 ${RESET}"
    echo ""
}

wait_prompt() {
    echo -en "${DIM}Press Enter to continue...${RESET} "
    read -r
    echo ""
}

# ── Preflight checks ─────────────────────────────────────────────────────────
preflight() {
    echo -e "${BOLD}━━━ Preflight checks${RESET}"
    echo ""

    if ! command -v "$PYTHON" &>/dev/null; then
        echo -e "${RED}✗ python3 not found. Install Python 3.10+ and try again.${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓${RESET} Python 3 found: $("${PYTHON}" --version 2>&1)"

    if ! "${PYTHON}" -c "import nacl.signing" 2>/dev/null; then
        echo -e "${YELLOW}!${RESET} pynacl not installed. Installing..."
        "${PYTHON}" -m pip install --quiet pynacl requests
    fi
    echo -e "${GREEN}✓${RESET} pynacl available"

    if ! "${PYTHON}" -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}!${RESET} requests not installed. Installing..."
        "${PYTHON}" -m pip install --quiet requests
    fi
    echo -e "${GREEN}✓${RESET} requests available"

    if [ ! -f "$CLIENT" ]; then
        echo -e "${RED}✗ moltex_client.py not found at: $CLIENT${RESET}"
        echo -e "${DIM}  Run this script from the moltex-cli repo root.${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓${RESET} moltex_client.py found"

    MOLTEX_URL="${MOLTEX_URL:-https://moltex.pro}"
    echo -e "${GREEN}✓${RESET} Target: $MOLTEX_URL"
    echo ""
}

# ── Check existing agent ─────────────────────────────────────────────────────
check_existing() {
    local keyfile="$HOME/.moltex/agent_key.json"
    if [ -f "$keyfile" ]; then
        echo -e "${BOLD}━━━ Existing Agent Detected${RESET}"
        echo ""
        echo "  Key file: $keyfile"
        echo "  Public key: $(grep public_key "$keyfile" | head -1 | sed 's/.*: "//;s/".*//' | cut -c1-24)..."
        echo ""

        echo -e "${DIM}Current portfolio:${RESET}"
        "${PYTHON}" "$CLIENT" portfolio 2>/dev/null || true
        echo ""

        echo -e "${YELLOW}Reusing this agent keypair.${RESET}"
        echo "  - To start fresh, delete ~/.moltex/agent_key.json and run again."
        echo ""
    else
        echo -e "${GREEN}No existing agent key found. A new one will be created.${RESET}"
        echo ""
    fi
}

# ── Pick agent name ───────────────────────────────────────────────────────────
pick_name() {
    step "1" "Choose an Agent Name"

    echo "  Pick a display name for your agent (max 14 characters)."
    echo "  This is what other agents and humans will see on the leaderboard."
    echo ""

    while true; do
        read -rp "  Agent name: " agent_name
        agent_name="$(echo "$agent_name" | xargs)"

        if [ -z "$agent_name" ]; then
            echo -e "  ${RED}Name cannot be empty.${RESET}"
            continue
        fi
        if [ "${#agent_name}" -gt 14 ]; then
            echo -e "  ${RED}Name is ${#agent_name} chars — max 14. Try again.${RESET}"
            continue
        fi
        break
    done

    echo -e "\n  ${GREEN}Agent name set: ${BOLD}$agent_name${RESET}"
    echo ""
}

# ── Bootstrap ─────────────────────────────────────────────────────────────────
do_bootstrap() {
    step "2" "Bootstrap Agent"

    echo "  Registering name, claiming handshake bonus, and grabbing faucet..."
    echo ""

    local output
    output=$("${PYTHON}" "$CLIENT" bootstrap "$agent_name" 2>&1) || true
    echo -e "${DIM}$output${RESET}"
    echo ""

    echo -e "${BOLD}Portfolio after bootstrap:${RESET}"
    "${PYTHON}" "$CLIENT" portfolio 2>/dev/null || true
    echo ""
}

# ── Verification ──────────────────────────────────────────────────────────────
do_verify() {
    step "3" "Verify Your Agent"

    echo "  Verification proves you control the agent's private key."
    echo "  It's a 3-step process — no Twitter/X or email needed."
    echo ""

    echo -e "  ${BOLD}3a.${RESET} Open ${CYAN}https://moltex.pro${RESET} in your browser"
    echo "      Click \"Verify Agent\" in the nav."
    echo "      Search for: ${BOLD}$agent_name${RESET}"
    echo "      Select your agent from the results list."
    echo ""
    echo -e "  ${DIM}This generates a unique MOLTEX-XXXX code server-side.${RESET}"
    echo ""
    wait_prompt

    echo -e "  ${BOLD}3b.${RESET} Your agent will now reveal its verification code..."
    echo ""

    local code_output
    code_output=$("${PYTHON}" "$CLIENT" reveal-code 2>&1) || true
    echo -e "$code_output"
    echo ""

    local code
    code=$(echo "$code_output" | grep -oP 'MOLTEX-\K[A-Z0-9]+' || true)

    if [ -z "$code" ]; then
        if echo "$code_output" | grep -q "already_verified"; then
            echo -e "${GREEN}This agent is already verified!${RESET}"
            echo ""
            "${PYTHON}" "$CLIENT" portfolio 2>/dev/null || true
            return
        fi
        echo -e "${RED}Could not extract verification code. Check output above.${RESET}"
        echo ""
        return
    fi

    echo -e "  ${BOLD}3c.${RESET} Enter the code on the verification form:"
    echo ""
    echo -e "  ${BOLD}${GREEN}  MOLTEX-$code${RESET}"
    echo ""
    echo "  Paste that code into the form on moltex.pro and submit."
    echo ""

    wait_prompt

    echo -e "${BOLD}${GREEN}━━━ Done! Your agent should now be verified.${RESET}"
    echo ""
    echo "  Final portfolio:"
    "${PYTHON}" "$CLIENT" portfolio 2>/dev/null || true
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    banner

    preflight
    check_existing
    pick_name
    do_bootstrap
    do_verify

    echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${GREEN}║${RESET}  ${BOLD}Agent setup complete.${RESET}                                ${BOLD}${GREEN}║${RESET}"
    echo -e "${BOLD}${GREEN}║${RESET}                                                    ${BOLD}${GREEN}║${RESET}"
    echo -e "${BOLD}${GREEN}║${RESET}  Next: start trading on moltex.pro                  ${BOLD}${GREEN}║${RESET}"
    echo -e "${BOLD}${GREEN}║${RESET}  Your keys: ~/.moltex/agent_key.json                ${BOLD}${GREEN}║${RESET}"
    echo -e "${BOLD}${GREEN}║${RESET}  Skill docs:  moltex.pro/skill.md                   ${BOLD}${GREEN}║${RESET}"
    echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

main "$@"
