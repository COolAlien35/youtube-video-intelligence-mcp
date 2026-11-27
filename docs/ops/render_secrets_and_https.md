# Render Secrets, Token Key Rotation, and HTTPS Runbook

## 1. Secrets Management (Render Dashboard Only)

Never commit `.env` files, private keys, or live credentials to Git. All secret environment variables in `render.yaml` are marked `sync: false` and must be entered in the **Render Dashboard → Environment**:

- `YT_INTEL_TOKEN_KEYS` — JSON object mapping positive integer key versions to base64-encoded 32-byte keys, e.g. `{"1": "<base64-32-byte-key>"}`.
- `YT_INTEL_GOOGLE_CLIENT_ID` / `YT_INTEL_GOOGLE_CLIENT_SECRET` / `YT_INTEL_GOOGLE_REDIRECT_URI`
- `YT_INTEL_SUPABASE_ISSUER` / `YT_INTEL_SUPABASE_JWKS_URL`
- `YT_INTEL_ALLOWED_ORIGINS` — exact-match HTTPS origins (no wildcards).

Generate a fresh 32-byte key locally (printed to `stdout` only, never written to disk):

```sh
uv run python scripts/generate_token_key.py
```

## 2. Rotating `YT_INTEL_TOKEN_KEYS`

1. Generate a new key with `scripts/generate_token_key.py`.
2. Add the new version to `YT_INTEL_TOKEN_KEYS` alongside the existing version(s), e.g. `{"1": "<old>", "2": "<new>"}`.
3. Update `YT_INTEL_ACTIVE_TOKEN_KEY_VERSION=2` and redeploy.
4. Re-encrypt stored `GoogleGrantRecord` rows using `yt_intel.security.rotate_blob(...)` (decrypts with `blob.key_version`, re-encrypts under `active_version`).
5. Once all rows are migrated to version `2`, remove version `1` from `YT_INTEL_TOKEN_KEYS`.

## 3. HTTPS & Proxy Headers

- Render terminates TLS at the edge and forwards `X-Forwarded-Proto: https` to the application.
- `render.yaml` starts Uvicorn with `--proxy-headers` and sets `YT_INTEL_REQUIRE_HTTPS=true` and `YT_INTEL_TRUST_PROXY_HEADERS=true`.
- `validate_settings()` rejects `environment=prod` if `require_https` is `False` or if `supabase_issuer`, `supabase_jwks_url`, or `google_redirect_uri` do not use `https://`.
