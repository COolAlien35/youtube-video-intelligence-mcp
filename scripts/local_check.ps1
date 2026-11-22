# ── local_check.ps1 ──────────────────────────────────────────────────────────
# PowerShell equivalent of local_check.sh.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1
# ─────────────────────────────────────────────────────────────────────────────
$ErrorActionPreference = "Stop"

function Pass($name) { Write-Host "  ✔ $name passed" -ForegroundColor Green }
function Fail($name) {
    Write-Host "  ✘ $name FAILED" -ForegroundColor Red
    exit 1
}
function Skip($name, $reason) { Write-Host "  ⊘ $name skipped: $reason" -ForegroundColor Yellow }

Write-Host "═══════════════════════════════════════════════════════"
Write-Host " Local checks"
Write-Host "═══════════════════════════════════════════════════════"

# 0. Lock check
Write-Host ""
Write-Host "▶ Checking lockfile…"
uv sync --locked
if ($LASTEXITCODE -ne 0) { Fail "uv sync --locked (lockfile may be stale — run 'uv lock')" }
Pass "lockfile"

# 1. Lint
Write-Host ""
Write-Host "▶ Linting…"
uv run ruff check .
if ($LASTEXITCODE -ne 0) { Fail "ruff check" }
Pass "ruff check"

# 2. Format
Write-Host ""
Write-Host "▶ Format check…"
uv run ruff format --check .
if ($LASTEXITCODE -ne 0) { Fail "ruff format --check" }
Pass "ruff format"

# 3. Type check
Write-Host ""
Write-Host "▶ Type checking…"
uv run mypy src scripts
if ($LASTEXITCODE -ne 0) { Fail "mypy" }
Pass "mypy"

# 4. Tests
Write-Host ""
Write-Host "▶ Running tests…"
uv run pytest
if ($LASTEXITCODE -ne 0) { Fail "pytest" }
Pass "pytest"

# 5. Secrets (optional locally)
Write-Host ""
$gitleaksPath = Get-Command gitleaks -ErrorAction SilentlyContinue
if ($gitleaksPath) {
    Write-Host "▶ Scanning for secrets…"
    gitleaks git --redact --no-banner
    if ($LASTEXITCODE -ne 0) { Fail "gitleaks" }
    Pass "gitleaks"
} else {
    Skip "gitleaks" "not installed (CI always scans)"
}

# Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════"
Write-Host " All local checks passed." -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════"
