"""Validate the repository playlist skill and its registry references."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path("skills/video-to-playlist/SKILL.md")
STEPS = (
    "Resolve the seed",
    "Summarize the metadata",
    "Find related videos",
    "Preview and wait",
    "Execute the approved snapshot",
    "Report the outcome",
)


def validate(root: Path = ROOT) -> None:
    raw = (root / SKILL).read_text(encoding="utf8")
    header = re.match(r"\A---\nname: video-to-playlist\ndescription: [^\n]+\n---\n", raw)
    if not header or not 500 <= len(raw) <= 12000:
        raise ValueError("Invalid skill frontmatter or length")
    headings = re.findall(r"^## (\d+)\. (.+?) \(SK-\d+\)$", raw, re.M)
    if headings != [(str(i), name) for i, name in enumerate(STEPS, 1)]:
        raise ValueError("Missing or reordered workflow step")
    tree = ast.parse((root / "src/yt_intel/tools/registry.py").read_text(encoding="utf8"))
    names = {
        entry.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "TOOLS" for t in node.targets)
        and isinstance(node.value, ast.Tuple)
        for entry in node.value.elts
        if isinstance(entry, ast.Name)
    }
    referenced = set(re.findall(r"`([a-z_]+)`", raw))
    required = {
        "similar_videos",
        "propose_playlist",
        "confirm_execute_playlist",
        "operation_status",
    }
    if not required <= referenced <= names:
        raise ValueError("Unknown or missing tool")
    for phrase in (
        "Never call `confirm_execute_playlist` unless the user has just confirmed",
        "Stop without further writes on any failure, denial or timeout",
        "Claim success only when the operation status says completed",
    ):
        if phrase not in raw:
            raise ValueError("Required safety rule missing")
    if re.search(
        r"(?:skip|bypass|assume|fabricate) (?:user |the )?(?:approval|confirmation)|(?:execute|confirm) automatically",
        raw,
        re.I,
    ):
        raise ValueError("Unsafe confirmation instruction")


if __name__ == "__main__":
    validate()
