"""Normalize display text. Authorization must always come from trusted state."""

import re
import unicodedata


def sanitize_untrusted(text: str, *, max_len: int) -> str:
    if max_len < 1:
        raise ValueError("max_len must be positive")
    cleaned = "".join(
        ch for ch in text if ch in "\n\t" or unicodedata.category(ch) not in {"Cc", "Cf", "Cs"}
    )
    cleaned = unicodedata.normalize("NFC", re.sub(r"\s{4,}", " ", cleaned))
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1] + "…"
