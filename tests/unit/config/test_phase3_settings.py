"""Unit tests for Phase 3 settings and validation."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from yt_intel.config import Settings, validate_settings
from yt_intel.config.settings import parse_token_keys

pytestmark = pytest.mark.unit


def _b64_key(byte_val: int = 0x11) -> str:
    return base64.b64encode(bytes([byte_val]) * 32).decode("ascii")


def _prod_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "environment": "prod",
        "data_dir": Path("/var/lib/yt_intel").resolve(),
        "allowed_origins": ["https://app.example.com"],
        "require_https": True,
        "supabase_issuer": "https://proj.supabase.co/auth/v1",
        "supabase_jwks_url": "https://proj.supabase.co/auth/v1/.well-known/jwks.json",
        "supabase_audience": "authenticated",
        "google_client_id": "client-id.apps.googleusercontent.com",
        "google_client_secret": SecretStr("fake-google-secret"),
        "google_redirect_uri": "https://mcp.example.com/oauth/google/callback",
        "token_keys": SecretStr(json.dumps({"1": _b64_key()})),
        "active_token_key_version": 1,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_phase3_defaults_and_secrets_redacted() -> None:
    """All policy gates default to False and secrets are masked in repr()."""
    settings = Settings(_env_file=None, token_keys=SecretStr("super-secret-value"))

    for idx in range(1, 9):
        assert getattr(settings, f"pol_0{idx}_open") is False
    assert settings.require_https is False
    assert settings.trust_proxy_headers is False
    assert settings.active_token_key_version == 1
    assert "super-secret-value" not in repr(settings)


def test_validate_settings_accepts_valid_prod_config() -> None:
    """Complete prod configuration with HTTPS and 32-byte key passes validation."""
    validate_settings(_prod_settings())


@pytest.mark.parametrize(
    "missing_field",
    [
        "supabase_issuer",
        "supabase_jwks_url",
        "supabase_audience",
        "google_client_id",
        "google_redirect_uri",
    ],
)
def test_validate_settings_rejects_missing_prod_str_field(missing_field: str) -> None:
    """Prod validation fails fast when required string auth settings are missing."""
    with pytest.raises(ValueError, match=missing_field):
        validate_settings(_prod_settings(**{missing_field: ""}))


@pytest.mark.parametrize("secret_field", ["google_client_secret", "token_keys"])
def test_validate_settings_rejects_missing_prod_secret(secret_field: str) -> None:
    """Prod validation fails fast when required SecretStr settings are empty."""
    with pytest.raises(ValueError, match=secret_field):
        validate_settings(_prod_settings(**{secret_field: SecretStr("")}))


def test_validate_settings_requires_https_in_prod() -> None:
    """Plain HTTP mode and non-HTTPS URLs are rejected in prod."""
    with pytest.raises(ValueError, match="require_https"):
        validate_settings(_prod_settings(require_https=False))

    with pytest.raises(ValueError, match="google_redirect_uri"):
        validate_settings(_prod_settings(google_redirect_uri="http://mcp.example.com/callback"))


def test_parse_token_keys_validation_and_secret_safety() -> None:
    """parse_token_keys enforces JSON dict, positive int versions, and 32-byte keys."""
    short_b64 = base64.b64encode(b"too-short-secret").decode("ascii")
    with pytest.raises(ValueError, match="32 bytes") as exc_info:
        parse_token_keys(json.dumps({"1": short_b64}))
    assert short_b64 not in str(exc_info.value)

    with pytest.raises(ValueError, match="active_token_key_version"):
        validate_settings(_prod_settings(active_token_key_version=2))
