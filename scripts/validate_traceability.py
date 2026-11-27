"""Check the requirements traceability matrix and report CSV line numbers."""

import argparse
import csv
import re
from pathlib import Path

BASELINE = Path(__file__).resolve().parents[1] / "docs/rtm/requirements_rtm.csv"
COLUMNS = [
    "req_id",
    "group",
    "title",
    "srs_section",
    "class",
    "planned_phase",
    "verification",
    "owner",
    "status",
    "text_status",
    "issue",
    "notes",
]
OPTIONS = {
    "class": {"M", "D", "P"},
    "status": {"Proposed", "Under Review", "Approved", "Implemented", "Verified"},
    "planned_phase": set("1234567"),
    "text_status": {"stated", "range-only"},
}
PREFIX = re.compile(r"(?:FR(?:-CROSS)?|IF|NFR|DATA|SEC|POL|SK|TQ|OPS|DEV-AI)-[0-9]+[a-z]?")
REFERENCE = re.compile(r"\bTQ-(\d+)(?:\s*[-\u2013\u2014]\s*(?:TQ-)?(\d+))?\b")


def validate(path: Path, strict: bool = False) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    references: list[tuple[int, int, int]] = []
    line = 1
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, [])
            missing = set(COLUMNS).difference(header)
            if missing or len(set(header)) != len(header):
                return [f"row 1: invalid header (missing or duplicate columns): {sorted(missing)}"]
            for fields in reader:
                line = reader.line_num
                if len(fields) != len(header):
                    errors.append(f"row {line}: expected {len(header)} fields")
                    continue
                row = dict(zip(header, (value.strip() for value in fields), strict=True))
                req = row["req_id"]
                if not PREFIX.fullmatch(req):
                    errors.append(f"row {line}: invalid req_id {req!r}")
                if req in seen:
                    errors.append(f"row {line}: duplicate req_id {req!r}")
                seen.add(req)
                for key, allowed in OPTIONS.items():
                    if row[key] not in allowed:
                        errors.append(f"row {line}: invalid {key} {row[key]!r}")
                verification = row["verification"]
                matches = REFERENCE.findall(verification)
                if not verification or (strict and req.startswith("FR-") and not matches):
                    errors.append(f"row {line}: missing verification")
                for start, end in matches:
                    references.append((line, int(start), int(end or start)))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return [f"row {line}: {exc}"]
    for line, first, last in references:
        if last < first or last - first >= len(seen):
            errors.append(f"row {line}: invalid or incomplete TQ range {first}-{last}")
        else:
            for number in range(first, last + 1):
                if f"TQ-{number}" not in seen:
                    errors.append(f"row {line}: missing verification reference TQ-{number}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=BASELINE)
    parser.add_argument("--strict", action="store_true", help="require explicit TQ links for FRs")
    args = parser.parse_args()
    errors = validate(args.path, args.strict)
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
