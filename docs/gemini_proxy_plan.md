# Gemini proxy — plan

Companion service for **runai**: accepts the same JSON payload `LLMClient` sends, calls Google Gemini with **your** server `GEMINI_API_KEY`, returns `{ "text": "..." }`.

## Suggested names

| Use | Name | Why |
|-----|------|-----|
| **PyPI package** | `runai-gemini-proxy` | Matches runai, obvious on `pip install`. |
| **Docker image** | `runai-gemini-proxy` | Same artifact repo family as `runai`. |
| **Git tags** | `proxy-v0.1.0` | Avoids clashing with main app `v0.1.0`. |
| **Codename** (optional) | **bridge** | Short internal label only. |

## Architecture

1. **runai** (user machine): `LLMClient` → `POST` JSON to `RUNAI_GEMINI_PROXY_URL`.
2. **Proxy** (GCP VM / Cloud Run): validate optional Bearer token → build prompt from `model` + `system` + `messages` → `google.generativeai` → JSON response.
3. **Google**: bills **your** API key only when users have **no** local `GEMINI_API_KEY`.

## MVP scope (this repo)

- [x] FastAPI app: `POST /v1/chat`, `GET /health`.
- [x] Env: `GEMINI_API_KEY` (required), `PROXY_BEARER_TOKEN` (optional; must match client `RUNAI_GEMINI_PROXY_TOKEN`), `PORT` (default 8080).
- [x] Optional `client_id` / `X-Runai-Client-Id` for your logs/metering (no storage in sample code).
- [ ] Rate limits, quotas DB — add on your side later.
- [ ] TLS termination — use Cloud Load Balancer, Caddy, or Cloud Run HTTPS.

## Security checklist

- HTTPS only in production.
- Set `PROXY_BEARER_TOKEN` and the same value as `RUNAI_GEMINI_PROXY_TOKEN` on clients.
- Do not log full request bodies in production (PII + prompt leakage).
- Firewall: only your users’ IPs or VPN if possible.

## Deploy on GCP (short)

1. Build/push image (workflow or `gcloud builds submit`).
2. **Cloud Run** (recommended): deploy container, set env vars, allow unauthenticated **off** if using Bearer check in app.
3. **Compute Engine**: Docker run with `-p 443:8080` behind LB or Caddy.

## Releases (this monorepo)

| Tag | What runs |
|-----|-----------|
| `v*.*.*` | Main **runai** → PyPI (existing workflow). |
| `proxy-v*.*.*` | **runai-gemini-proxy** → PyPI + Docker → Artifact Registry (workflows in `.github/workflows/proxy-*.yml`). |

Bump `version` in `proxy/pyproject.toml` before tagging `proxy-v…`.

## Future

- Forwarding `user_gemini_api_key` again (BYOK through proxy) when you want it.
- OpenAI mirror endpoint + `RUNAI_OPENAI_PROXY_URL` on the client.
