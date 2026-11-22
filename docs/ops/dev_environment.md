# Development Environment Setup

## Prerequisites

### 1. uv (pinned: 0.11.32)

Every developer and CI **must** use uv **0.11.32**. Install using the versioned installer:

**macOS / Linux / Git Bash:**
```bash
curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/0.11.32/install.ps1 | iex"
```

Verify:
```bash
uv --version
# Must print: uv 0.11.32
```

### 2. Python 3.12

Python 3.12 is installed **automatically** by uv, based on the `.python-version` file in the repo root. You do not need to install Python separately.

### 3. Git

- **macOS / Linux:** Git is usually pre-installed.
- **Windows:** Install [Git for Windows](https://gitforwindows.org/). It includes **Git Bash**, which is required for running `scripts/local_check.sh`.

### 4. gitleaks (optional locally, required in CI)

gitleaks scans for secrets. CI always runs it; local installation is recommended but optional.

**macOS:**
```bash
brew install gitleaks
```

**Windows:**
```powershell
# Check the package ID first:
winget search gitleaks
# Then install:
winget install gitleaks.gitleaks
```

**Verify:**
```bash
gitleaks version
```

## Clone and Setup

```bash
git clone https://github.com/COolAlien35/youtube-video-intelligence-mcp.git
cd youtube-video-intelligence-mcp
uv sync --locked
```

### Install pre-commit hooks (once per clone)

```bash
uv run pre-commit install
```

## Running Local Checks

Run the same checks CI runs, in the same order:

**macOS / Linux / Git Bash:**
```bash
scripts/local_check.sh
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1
```

The checks are, in order:
1. `uv sync --locked` — verify lockfile matches `pyproject.toml`
2. `uv run ruff check .` — linting
3. `uv run ruff format --check .` — format check
4. `uv run mypy src scripts` — type checking (strict)
5. `uv run pytest` — test suite

## Common Problems

### `uv sync --locked` fails

The lockfile (`uv.lock`) doesn't match `pyproject.toml`. Run:
```bash
uv lock
```
Then commit the updated `uv.lock`.

### `ruff format --check` fails

Code isn't formatted. Run the formatter, then check again:
```bash
uv run ruff format .
uv run ruff format --check .
```

### mypy reports errors on an empty directory

The `scripts/__init__.py` file exists specifically to give mypy a file to check. Don't delete it.

### PowerShell refuses to run the script

Use the `-ExecutionPolicy Bypass` form:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1
```
Don't change the machine-wide execution policy.

### Executable bit on `local_check.sh`

If cloning on Windows and then running on macOS/Linux, the executable bit may be lost. Fix it with:
```bash
git update-index --chmod=+x scripts/local_check.sh
```
Verify:
```bash
git ls-files -s scripts/local_check.sh
# Must show: 100755
```

### Line endings

`.gitattributes` enforces LF line endings for shell scripts. If you see `\r` errors, run:
```bash
git ls-files --eol scripts/local_check.sh
# Must show: i/lf
```

## Windows-Specific Notes

- Install **Git for Windows** (includes Git Bash).
- Use `powershell -ExecutionPolicy Bypass -File scripts\local_check.ps1` for local checks.
- Line endings are handled by `.gitattributes` — no manual configuration needed.
- The `.gitattributes` file normalises all text files to LF on commit.
