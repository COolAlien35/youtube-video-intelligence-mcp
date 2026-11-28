import json

import pytest

from scripts.check_skill_traces import EVALS, check


@pytest.mark.parametrize("path", sorted((EVALS / "traces").glob("*.json")), ids=lambda p: p.stem)
def test_trace(path):
    trace = json.loads(path.read_text())
    if path.name.startswith("bad_"):
        with pytest.raises(ValueError):
            check(trace)
    else:
        check(trace)
