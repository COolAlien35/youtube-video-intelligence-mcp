# Infrastructure Prerequisites

> **Phase 1 status:** This is a **checklist only**. Nothing is created yet. No API keys exist and the YouTube Data API is **not** enabled in Phase 1.

## Render Web Service

- [ ] Web service created on [Render](https://render.com)
- [ ] **Persistent disk** mounted at `/var/data`
  - ⚠️ Persistent disks require a **paid instance type** (not available on free tier)
  - Confirm the plan and price before provisioning
  - Single-instance behaviour: only one instance can mount a persistent disk at a time
- [ ] Environment variables configured (see Secrets section below)

## Supabase

- [ ] Project created in **`ap-southeast-1`** region
- [ ] Connection string and keys stored securely (see Secrets section)

## Google Cloud

- [ ] Exactly **one** Google Cloud project (ADR-05)
  - ❌ Extra projects for additional quota are **prohibited**
- [ ] YouTube Data API v3: **not enabled** in Phase 1
- [ ] No API keys created in Phase 1

## Secrets — Where Each One Lives

| Secret | Location | Never in git |
|---|---|---|
| `YOUTUBE_API_KEY` | Render environment variable | ✅ |
| `SUPABASE_URL` | Render environment variable | ✅ |
| `SUPABASE_ANON_KEY` | Render environment variable | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Render environment variable | ✅ |
| `DATABASE_URL` | Render environment variable | ✅ |
| `SECRET_KEY` | Render environment variable | ✅ |
| CI-only secrets | GitHub Secrets | ✅ |

> **Rule:** Secrets live in Render environment variables or GitHub Secrets. They are **never** committed to git.

## Account Ownership

| Account / Service | Owner |
|---|---|
| GitHub repo (`COolAlien35/youtube-video-intelligence-mcp`) | A (COolAlien35) |
| Render | TBD |
| Supabase | TBD |
| Google Cloud project | TBD |

## Phase 1 Explicit Statements

- ❌ No API keys are created in Phase 1
- ❌ The YouTube Data API is **not** enabled in Phase 1
- ❌ No runtime dependencies are added in Phase 1
- ❌ No live API calls are made in Phase 1
