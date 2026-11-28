"""Offline documentation checker: links, tool names, settings env vars, and stray markers."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_DOC_GLOBS = (
    "README.md",
    "RELEASE_NOTES.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "docs/**/*.md",
    "skills/**/*.md",
    "second-brain/**/*.md",
)

# Historical planning/baseline docs that intentionally retain exploratory TBC markers.
_MARKER_EXEMPT_PREFIXES = (
    "docs/plan.md",
    "docs/phase1_person_A.md",
    "docs/Architecture_Decision_Records_v1.0.md",
    "docs/Engineering_Governance_Specification_v1.0.md",
    "docs/architecture/",
    "docs/stage_reviews/",
    "docs/testing/",
    "docs/ops/",
    "docs/quota/",
    "second-brain/",
)

# Planned Phase 7 env vars (Phase 7 §Settings) tracked ahead of A's config PR.
_TRACKED_FUTURE_ENV_VARS = frozenset(
    {
        "YT_INTEL_RETENTION_INTERVAL_SECONDS",
        "YT_INTEL_DB_PATH",
        "YT_INTEL_RECOVERY_ON_START",
    }
)

_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_ENV_VAR_RE = re.compile(r"\bYT_INTEL_([A-Z0-9_]+)\b")
_MARKER_RE = re.compile(r"\b(TODO|TBC)\b")
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def registry_tool_names(root: Path = ROOT) -> set[str]:
    """Extract registered MCP tool names from ``src/yt_intel/tools/registry.py``."""
    tree = ast.parse((root / "src/yt_intel/tools/registry.py").read_text(encoding="utf8"))
    names: set[str] = {"disconnect"}  # explicit alias in register_tools()
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "TOOLS" for t in node.targets)
            and isinstance(node.value, ast.Tuple)
        ):
            for entry in node.value.elts:
                if isinstance(entry, ast.Name):
                    names.add(entry.id)
    return names


def settings_env_vars(root: Path = ROOT) -> set[str]:
    """Extract ``YT_INTEL_*`` environment variable names from ``Settings``."""
    tree = ast.parse((root / "src/yt_intel/config/settings.py").read_text(encoding="utf8"))
    env_vars: set[str] = set(_TRACKED_FUTURE_ENV_VARS)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if name != "model_config":
                        env_vars.add(f"YT_INTEL_{name.upper()}")
    return env_vars


def _iter_markdown_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in _DOC_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return files


def check_docs(root: Path = ROOT) -> list[str]:
    """Return a list of documentation validation errors (empty means passing)."""
    errors: list[str] = []
    known_env = settings_env_vars(root)
    _ = registry_tool_names(root)  # verify registry parses cleanly

    for md_path in _iter_markdown_files(root):
        rel = md_path.relative_to(root).as_posix()
        text = md_path.read_text(encoding="utf8")
        stripped = _FENCE_RE.sub("", text)

        # 1. Relative Markdown link check
        for match in _LINK_RE.finditer(stripped):
            target = match.group(1).strip()
            if (
                not target
                or target.startswith(("http://", "https://", "mailto:", "#"))
                or "://" in target
            ):
                continue
            target_path = target.split("#", 1)[0].split("?", 1)[0]
            if not target_path:
                continue
            resolved = (md_path.parent / target_path).resolve()
            if not resolved.exists():
                errors.append(f"{rel}: broken link '{target}'")

        # 2. Environment variable check (YT_INTEL_*)
        for match in _ENV_VAR_RE.finditer(text):
            full = f"YT_INTEL_{match.group(1)}"
            if full not in known_env:
                errors.append(f"{rel}: unknown setting '{full}'")

        # 3. Unresolved TODO / TBC markers outside tracked historical docs
        if not rel.startswith(_MARKER_EXEMPT_PREFIXES):
            for match in _MARKER_RE.finditer(stripped):
                errors.append(f"{rel}: unresolved marker '{match.group(1)}'")

    return errors


def main() -> int:
    errors = check_docs(ROOT)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
