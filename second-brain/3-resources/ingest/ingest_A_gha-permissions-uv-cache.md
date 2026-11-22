# GitHub Actions Least-Privilege Permissions and uv Caching

## Source

GitHub official documentation: [Permissions for GITHUB_TOKEN](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication), [Caching dependencies](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows); astral-sh/setup-uv README

## Ingested by / date

Person A · 2026-11-22

## Summary

GitHub Actions workflows receive an automatic `GITHUB_TOKEN` with permissions that default to either read-write (permissive) or read-only (restricted), depending on the repository's settings. The security best practice (and the project's TQ-28 requirement) is to set the top-level `permissions` key to `contents: read` and only widen per-job where genuinely needed. This prevents accidental write access — a compromised or buggy action cannot push code, create releases, or modify issues unless explicitly granted. For uv specifically, the `astral-sh/setup-uv` action supports built-in caching via `enable-cache: true` with a cache key derived from `uv.lock`. This avoids re-downloading and re-building the entire virtual environment on every run, cutting CI time significantly. The cache is scoped to the branch and falls back to the default branch's cache on a miss.

## Key facts

- Setting `permissions: contents: read` at the workflow top level restricts every job's `GITHUB_TOKEN` to read-only by default (source: GitHub docs — Permissions for GITHUB_TOKEN)
- Individual jobs can widen their permissions with a job-level `permissions` key (source: GitHub docs)
- `persist-credentials: false` on `actions/checkout` prevents the token from being stored in the local git config, reducing attack surface (source: GitHub docs — actions/checkout)
- `astral-sh/setup-uv` with `enable-cache: true` caches the uv environment, keyed on `uv.lock` by default (source: setup-uv README)
- Cache is scoped by branch; PR branches fall back to the base branch's cache on a miss (source: GitHub docs — Caching dependencies)
- `uv sync --locked` fails if `uv.lock` doesn't match `pyproject.toml`, which enforces lockfile freshness in CI (TQ-14) (source: uv docs)
- `timeout-minutes` on each job prevents hung processes from consuming Actions minutes indefinitely (source: GitHub docs)

## Relevance

- **TQ-14**: Stale lockfile detection — `uv sync --locked` enforces this
- **TQ-28**: Least-privilege CI permissions — `permissions: contents: read`
- **SRS §9**: Security and configuration management requirements
- **A-2**: CI skeleton design and implementation

## Open questions / risks

- If a future job needs write permissions (e.g. to publish releases), it must add job-level `permissions` — document the rationale in the PR.
- Cache eviction: GitHub's cache has a 10 GB limit per repository and evicts least-recently-used entries. If the cache is frequently evicted, CI times will spike.
- Third-party actions (like gitleaks-action) may request broader permissions than expected — review each action's `action.yml` before adding it.

## Links

- [[GitHub GITHUB_TOKEN Permissions]]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- [[GitHub Caching]]: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows
- [[astral-sh/setup-uv]]: https://github.com/astral-sh/setup-uv
- [[uv sync --locked]]: https://docs.astral.sh/uv/reference/cli/#uv-sync
