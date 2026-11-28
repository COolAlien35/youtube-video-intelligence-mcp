"""Validate a synthetic or manually normalized MCP-client trace."""

import argparse
import json
from pathlib import Path
from typing import Any

EVALS = Path(__file__).resolve().parents[1] / "skills/video-to-playlist/evals"


def check(trace: dict[str, Any]) -> None:
    name = trace.get("scenario")
    paths = {p.stem: p for p in (EVALS / "scenarios").glob("*.json")}
    if not isinstance(name, str) or name not in paths:
        raise ValueError("Unknown scenario")
    spec = json.loads(paths[name].read_text())
    events = trace.get("events")
    if events != spec["events"]:
        raise ValueError("Unexpected call, decision, or outcome")
    approved = False
    for event in events:
        if event.split(":")[0] in spec["forbidden_before_confirmation"] and not approved:
            raise ValueError("Missing user confirmation")
        approved = event == "user:confirmed"
    report = trace.get("report")
    if not isinstance(report, dict) or not set(spec["required_fields"]) <= report.keys():
        raise ValueError("Incomplete final report")
    if report["status"] != spec["outcome"]:
        raise ValueError("Unsupported status claim")
    requested, inserted = report["requested"], report["inserted"]
    if (
        type(requested) is not int
        or requested < 0
        or (inserted is not None and (type(inserted) is not int or not 0 <= inserted <= requested))
    ):
        raise ValueError("Invalid counts")
    if report["status"] == "completed" and inserted != requested:
        raise ValueError("Incomplete write reported as complete")
    if "confirm_execute_playlist:accepted" not in events and inserted != 0:
        raise ValueError("Unapproved insert count")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    check(json.loads(parser.parse_args().trace.read_text()))
