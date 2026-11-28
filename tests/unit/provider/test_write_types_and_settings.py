"""Unit tests for Phase 6 write types, operation models, and settings."""

from __future__ import annotations

import pytest

from yt_intel.common.errors import ErrorCode
from yt_intel.config.settings import Settings, validate_settings
from yt_intel.operations import (
    ItemOutcome,
    OperationState,
    OutcomeUncertainError,
    ReconciliationAmbiguousError,
    ReconciliationOutcome,
    estimate_write_units,
)
from yt_intel.provider.write import (
    YOUTUBE_WRITE_SCOPE,
    ChannelRequiredError,
    Fault,
    WriteScopeRequiredError,
)


def test_phase6_settings_defaults_and_validation() -> None:
    s = Settings(_env_file=None)
    validate_settings(s)
    assert s.playlist_writes_enabled is False
    assert s.max_playlist_items == 10
    assert s.workflow_deadline_seconds == 120
    assert s.write_max_resumes == 2
    assert s.read_retry_attempts == 3
    assert s.approval_ttl_seconds == 300

    with pytest.raises(ValueError, match="max_playlist_items"):
        validate_settings(Settings(_env_file=None, max_playlist_items=21))
    with pytest.raises(ValueError, match="max_playlist_items"):
        validate_settings(Settings(_env_file=None, max_playlist_items=0))
    with pytest.raises(ValueError, match="workflow_deadline_seconds"):
        validate_settings(Settings(_env_file=None, workflow_deadline_seconds=0))
    with pytest.raises(ValueError, match="write_max_resumes"):
        validate_settings(Settings(_env_file=None, write_max_resumes=-1))
    with pytest.raises(ValueError, match="read_retry_attempts"):
        validate_settings(Settings(_env_file=None, read_retry_attempts=0))
    with pytest.raises(ValueError, match="approval_ttl_seconds"):
        validate_settings(Settings(_env_file=None, approval_ttl_seconds=0))


def test_estimate_write_units_and_error_types() -> None:
    assert estimate_write_units(0) == 50
    assert estimate_write_units(10) == 550
    with pytest.raises(ValueError, match="n_items"):
        estimate_write_units(-1)

    assert YOUTUBE_WRITE_SCOPE == "https://www.googleapis.com/auth/youtube"
    assert ChannelRequiredError().code is ErrorCode.CHANNEL_REQUIRED
    assert WriteScopeRequiredError().code is ErrorCode.FORBIDDEN
    assert OutcomeUncertainError("op-1").code is ErrorCode.WRITE_UNCERTAIN
    assert ReconciliationAmbiguousError("op-1", 2).code is ErrorCode.WRITE_UNCERTAIN
    assert Fault(op="create_playlist", at=1, kind="timeout_after_success").at == 1
    assert OperationState.CREATING == "CREATING"
    assert ItemOutcome.INSERTING == "INSERTING"
    assert ReconciliationOutcome.CAN_RESUME == "CAN_RESUME"
