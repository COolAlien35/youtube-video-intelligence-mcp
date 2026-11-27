import csv
from pathlib import Path

import pytest
from scripts.validate_traceability import BASELINE, COLUMNS, validate

pytestmark = pytest.mark.unit


def matrix(tmp_path: Path, **change: str) -> Path:
    base = dict.fromkeys(COLUMNS, "")
    base.update(req_id="TQ-1", status="Under Review", planned_phase="1", verification="TQ-1")
    base.update({"class": "D", "text_status": "stated"})
    path = tmp_path / "rtm.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(dict(base, req_id="FR-1a") | change)
        writer.writerow(base)
    return path


def test_valid_forward_reference(tmp_path: Path) -> None:
    assert validate(matrix(tmp_path)) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("req_id", ""),
        ("req_id", "ADR-01"),
        ("class", "X"),
        ("status", "Done"),
        ("planned_phase", "8"),
        ("verification", ""),
        ("verification", "TQ-2"),
        ("verification", "TQ-1-TQ-2"),
        ("text_status", "draft"),
    ],
)
def test_invalid_row(tmp_path: Path, field: str, value: str) -> None:
    assert validate(matrix(tmp_path, **{field: value}))[0].startswith("row 2:")


def test_missing_column(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"
    path.write_text("req_id,status\n", encoding="utf-8")
    assert validate(path)[0].startswith("row 1:")


def test_strict_requires_fr_test_reference(tmp_path: Path) -> None:
    path = matrix(tmp_path, verification="team review")
    assert validate(path) == []
    assert validate(path, strict=True)


@pytest.mark.skipif(not BASELINE.exists(), reason="baseline arrives in the next deliverable")
def test_repository_baseline() -> None:
    assert validate(BASELINE) == []


def test_duplicate_reports_second_occurrence(tmp_path: Path) -> None:
    assert validate(matrix(tmp_path, req_id="TQ-1")) == ["row 3: duplicate req_id 'TQ-1'"]
