#!/usr/bin/env bash
# ── local_check.sh ───────────────────────────────────────────────────────────
# Runs the same checks CI runs, in the same order. Fails fast.
# Usage: scripts/local_check.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✔ $1 passed${NC}"; }
fail() { echo -e "${RED}✘ $1 FAILED${NC}"; exit 1; }
skip() { echo -e "${YELLOW}⊘ $1 skipped: $2${NC}"; }

echo "═══════════════════════════════════════════════════════"
echo " Local checks"
echo "═══════════════════════════════════════════════════════"

# 0. Lock check ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Checking lockfile…"
uv sync --locked || fail "uv sync --locked (lockfile may be stale — run 'uv lock')"
pass "lockfile"

# 1. Lint ──────────────────────────────────────────────────────────────────────
echo ""
echo "▶ Linting…"
uv run ruff check . || fail "ruff check"
pass "ruff check"

# 2. Format ────────────────────────────────────────────────────────────────────
echo ""
echo "▶ Format check…"
uv run ruff format --check . || fail "ruff format --check"
pass "ruff format"

# 3. Type check ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Type checking…"
uv run mypy src scripts || fail "mypy"
pass "mypy"

# 4. Tests ─────────────────────────────────────────────────────────────────────
echo ""
echo "▶ Running tests…"
uv run pytest || fail "pytest"
pass "pytest"

# 5. Secrets (optional locally) ────────────────────────────────────────────────
echo ""
if command -v gitleaks &>/dev/null; then
    echo "▶ Scanning for secrets…"
    gitleaks git --redact --no-banner || fail "gitleaks"
    pass "gitleaks"
else
    skip "gitleaks" "not installed (CI always scans)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "${GREEN} All local checks passed.${NC}"
echo "═══════════════════════════════════════════════════════"
