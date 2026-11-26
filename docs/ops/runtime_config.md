# Runtime Configuration

All runtime settings are defined in `yt_intel.config.Settings` using `pydantic-settings` with the `YT_INTEL_` environment variable prefix. Local development reads `.env` if present.

## Variables

| Variable | Type | Default | Description | Who reads it |
|---|---|---|---|---|
| `YT_INTEL_ENVIRONMENT` | `"dev" \| "test" \| "prod"` | `"dev"` | Runtime environment mode | `server`, `config` |
| `YT_INTEL_HOST` | `str` | `"127.0.0.1"` | Bind host | `server` |
| `YT_INTEL_PORT` | `int` | `8000` | Bind port (1–65535) | `server` |
| `YT_INTEL_ALLOWED_ORIGINS` | `list[str]` | `["http://localhost:8000", "http://127.0.0.1:8000"]` | Exact-match Origin allow-list (TBC for Claude Desktop) | `server` |
| `YT_INTEL_LOG_LEVEL` | `str` | `"INFO"` | Logging level | `server`, `common` |
| `YT_INTEL_DATA_DIR` | `Path` | `./var` | Directory for persistent SQLite DB (`/var/data` in `prod`) | `storage` |
| `YT_INTEL_DATABASE_URL` | `str` | `sqlite:///<data_dir>/yt_intel.db` | SQLAlchemy DB URL (derived from `data_dir` if empty) | `storage` |
| `YT_INTEL_FIXTURES_DIR` | `Path \| None` | `None` | Directory containing synthetic fixtures | `provider` |
| `YT_INTEL_QUOTA_COMMON_DAILY_CAP` | `int` | `2000` | Daily common YouTube quota cap (SRS §6.1, 20% cap) | `quota` |
| `YT_INTEL_QUOTA_SEARCH_DAILY_CAP` | `int` | `20` | Daily `search.list` call cap (SRS §6.1) | `quota` |
| `YT_INTEL_MAX_CONCURRENT_WORKFLOWS_PER_PRINCIPAL` | `int` | `2` | Max active workflows per principal (ADR-09) | `storage` / workflow |
| `YT_INTEL_MAX_WORKFLOW_STARTS_PER_MINUTE` | `int` | `5` | Max workflow starts per minute per principal (ADR-09) | `storage` / workflow |
| `YT_INTEL_LIVE_YOUTUBE_ENABLED` | `bool` | `False` | Fail-closed live API gate (must be `False` in Phase 2) | `provider`, `config` |

## Startup Validation

`validate_settings(settings)` is called at startup and fails fast if:
- `port` is outside `1..65535`
- Any quota or concurrency/rate cap is `<= 0`
- `environment == "prod"` and `data_dir` is relative (must be absolute, e.g. `/var/data`)
- Any entry in `allowed_origins` contains a wildcard (`*`) or is not a valid `http`/`https` origin
- `live_youtube_enabled` is `True` (prohibited in Phase 2)
