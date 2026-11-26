"""Unit tests for yt_intel.config."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from yt_intel.config import Settings, get_settings, validate_settings

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.unit
def test_settings_defaults(tmp_path: Path) -> None:
    """Settings should use safe dev defaults without creating data_dir on disk."""
    target = tmp_path / "does_not_exist"
    settings = Settings(_env_file=None, data_dir=target)

    assert settings.environment == "dev"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.quota_common_daily_cap == 2000
    assert settings.quota_search_daily_cap == 20
    assert settings.max_concurrent_workflows_per_principal == 2
    assert settings.max_workflow_starts_per_minute == 5
    assert settings.live_youtube_enabled is False
    assert settings.database_url == f"sqlite:///{(target / 'yt_intel.db').as_posix()}"
    assert not target.exists()


@pytest.mark.unit
def test_settings_env_override(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """YT_INTEL_* environment variables should override defaults."""
    monkeypatch.setenv("YT_INTEL_ENVIRONMENT", "test")
    monkeypatch.setenv("YT_INTEL_PORT", "9001")
    monkeypatch.setenv("YT_INTEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YT_INTEL_QUOTA_COMMON_DAILY_CAP", "1500")
    monkeypatch.setenv("YT_INTEL_QUOTA_SEARCH_DAILY_CAP", "10")

    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.environment == "test"
        assert settings.port == 9001
        assert settings.data_dir == tmp_path
        assert settings.quota_common_daily_cap == 1500
        assert settings.quota_search_daily_cap == 10
    finally:
        get_settings.cache_clear()


@pytest.mark.unit
def test_validate_settings_accepts_valid_dev_config() -> None:
    """Valid dev settings should pass validation."""
    settings = Settings(_env_file=None)
    validate_settings(settings)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("quota_common_daily_cap", 0),
        ("quota_common_daily_cap", -10),
        ("quota_search_daily_cap", 0),
        ("max_concurrent_workflows_per_principal", 0),
        ("max_workflow_starts_per_minute", 0),
        ("port", 0),
        ("port", 70000),
    ],
)
def test_validate_settings_rejects_non_positive_caps_and_invalid_ports(
    field_name: str,
    value: int,
) -> None:
    """Caps <= 0 and out-of-range ports should fail validation."""
    settings = Settings(_env_file=None, **{field_name: value})
    with pytest.raises(ValueError):
        validate_settings(settings)


@pytest.mark.unit
def test_validate_settings_rejects_relative_data_dir_in_prod() -> None:
    """Prod environment requires an absolute data_dir."""
    settings = Settings(_env_file=None, environment="prod", data_dir=Path("var"))
    with pytest.raises(ValueError, match="absolute"):
        validate_settings(settings)


@pytest.mark.unit
def test_validate_settings_accepts_absolute_data_dir_in_prod(tmp_path: Path) -> None:
    """Prod environment with absolute data_dir and valid origins passes."""
    settings = Settings(
        _env_file=None,
        environment="prod",
        data_dir=tmp_path.resolve(),
        allowed_origins=["https://example.com"],
    )
    validate_settings(settings)


@pytest.mark.unit
@pytest.mark.parametrize(
    "origins",
    [
        ["*"],
        ["https://*.example.com"],
        ["not-a-url"],
        ["ftp://example.com"],
        ["https://example.com/path"],
    ],
)
def test_validate_settings_rejects_bad_origins(origins: list[str]) -> None:
    """Wildcard and malformed origins must be rejected."""
    settings = Settings(
        _env_file=None, environment="prod", data_dir=Path("/var/data"), allowed_origins=origins
    )
    with pytest.raises(ValueError):
        validate_settings(settings)


@pytest.mark.unit
@pytest.mark.security
def test_validate_settings_rejects_live_youtube_in_phase2() -> None:
    """live_youtube_enabled=True must be rejected in Phase 2."""
    settings = Settings(_env_file=None, live_youtube_enabled=True)
    with pytest.raises(ValueError, match="live_youtube_enabled"):
        validate_settings(settings)


@pytest.mark.unit
@pytest.mark.security
def test_repr_never_leaks_secret_str() -> None:
    """Subclassing Settings with a SecretStr field must redact its value in repr()."""

    class ExtendedSettings(Settings):
        api_token: SecretStr = SecretStr("super-secret-value-12345")

    extended = ExtendedSettings(_env_file=None)
    rendered = repr(extended)
    assert "super-secret-value-12345" not in rendered
    assert "SecretStr" in rendered
