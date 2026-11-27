# Phase 2 Dependencies

All runtime and development dependencies are declared in [`pyproject.toml`](../../pyproject.toml) and pinned in [`uv.lock`](../../uv.lock). Only Person A edits `pyproject.toml` and `uv.lock`.

## Runtime Dependencies

| Package | Pinned Version | Licence | Purpose | Requested by |
|---|---|---|---|---|
| `mcp` | `2.3.0` | MIT | Official Model Context Protocol Python SDK (`MCPServer`, Streamable HTTP transport) | B (`docs/architecture/mcp_sdk_notes.md`) |
| `fastapi` | `0.165.0` | MIT | ASGI web framework for `/health` and mounting `/mcp` | A / B (Phase 2 baseline) |
| `uvicorn` | `0.54.0` | BSD-3-Clause | Local ASGI server for running `create_app` | A / B (Phase 2 baseline) |
| `sqlalchemy` | `2.1.9` | MIT | Typed ORM and SQLite WAL persistence layer | A (Phase 2 baseline) |
| `pydantic` | `2.14.4` | MIT | Data validation and mypy plugin | A (Phase 2 baseline) |
| `pydantic-settings` | `2.16.3` | MIT | `YT_INTEL_*` environment settings management | A (Phase 2 baseline) |
| `tzdata` | `2026.6` | Apache-2.0 | IANA time zone data (`America/Los_Angeles` on Windows) | A (Phase 2 baseline) |
| `anyio` | `4.16.0` | MIT | Async-to-sync thread offload (`anyio.to_thread.run_sync`) | A (Phase 2 baseline) |

> **Note:** `cryptography` is not declared directly in Phase 2 (`A-1`); it will be added explicitly in Phase 3 when token encryption is implemented.

## Development Dependencies

| Package | Pinned Version | Licence | Purpose | Requested by |
|---|---|---|---|---|
| `httpx` | `0.28.1` | BSD-3-Clause | Async HTTP test client for FastAPI/MCP endpoints | A / B (Phase 2 baseline) |
| `pytest` | `9.2.0` | MIT | Test runner (`--strict-markers --import-mode=importlib`) | A (Phase 1 baseline) |
| `pytest-asyncio` | `1.5.0` | Apache-2.0 | Async test support (`asyncio_mode = "auto"`) | A (Phase 2 baseline) |
| `pytest-cov` | `7.1.0` | MIT | Coverage reporting | A (Phase 1/2 baseline) |
| `ruff` | `0.17.6` | MIT | Linter and formatter | A (Phase 1 baseline) |
| `mypy` | `2.4.1` | MIT | Strict static type checker (with `pydantic.mypy` plugin) | A (Phase 1 baseline) |
| `pre-commit` | `4.7.0` | MIT | Local git hook runner | A (Phase 1 baseline) |

## Requesting a New Dependency

Comment on the pinned **"Phase 2 dependency requests"** issue with:
1. Exact PyPI package name
2. Why it is needed
3. Package licence (verified on PyPI)
