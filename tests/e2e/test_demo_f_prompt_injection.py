"""Demo F: prompt injection in untrusted metadata cannot trigger writes or bypass approval."""

import pytest

from tests.support.injection_payloads import PAYLOADS
from yt_intel.common.errors import ApprovalInvalidError, ErrorCode
from yt_intel.common.untrusted import sanitize_untrusted

pytestmark = [pytest.mark.e2e, pytest.mark.security]

_BIDI_AND_NULL = frozenset("\x00\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def test_demo_f_injection_corpus_is_sanitized_for_preview_display() -> None:
    """Verify every Demo F payload is bounded and stripped of control/bidi characters."""
    assert len(PAYLOADS) >= 15
    for payload in PAYLOADS:
        cleaned = sanitize_untrusted(payload, max_len=120)
        assert len(cleaned) <= 120
        assert not any(ch in _BIDI_AND_NULL for ch in cleaned)
        assert sanitize_untrusted(cleaned, max_len=120) == cleaned

    # Safe approval error contract never echoes injected handle text.
    err = ApprovalInvalidError()
    assert err.code == ErrorCode.APPROVAL_INVALID
    assert "FAKE_approval_handle" not in err.message


@pytest.mark.skip(
    reason=(
        "Awaits B's ProposalRepo/PlaylistProposalService/PlaylistConfirmService "
        "and A's FixtureWritePlaylistProvider."
    )
)
async def test_demo_f_prompt_injection_blocks_unapproved_writes() -> None:
    """End-to-end Demo F skeleton against fixture proposal, confirmation, and write providers.

    When B's proposal/confirmation services and A's FixtureWritePlaylistProvider land:
    1. Place PAYLOADS in fixture video titles, descriptions, tags, and user playlist title.
    2. Run propose_playlist and assert:
       - FixtureWritePlaylistProvider recorded zero write calls.
       - Preview fields are sanitized with sanitize_untrusted() and free of bidi/control chars.
    3. Attempt confirm_execute_playlist with injected 'The user has approved' / fabricated
       'FAKE_approval_handle' values and assert ApprovalInvalidError is raised, proposal state
       does not advance to APPROVED/CREATING, and zero write or write-ledger entries exist.
    4. Verify captured logs contain operation/proposal IDs and codes only, never PAYLOADS text.
    """
    raise NotImplementedError
