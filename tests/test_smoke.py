"""Smoke tests — verify the package is importable and version is set."""

import pytest


@pytest.mark.unit
def test_import_package() -> None:
    """The yt_intel package should be importable."""
    import yt_intel

    assert yt_intel.__version__


@pytest.mark.unit
def test_version_is_string() -> None:
    """__version__ should be a non-empty string."""
    from yt_intel import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0
