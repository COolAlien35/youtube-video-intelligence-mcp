"""Generate a fresh 32-byte AES-256-GCM token key and print base64 to stdout."""

from __future__ import annotations

import base64
import os


def generate_token_key() -> str:
    """Return a newly generated base64-encoded 32-byte key."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


def main() -> None:
    """Print one fresh 32-byte base64 key to stdout."""
    print(generate_token_key())


if __name__ == "__main__":
    main()
