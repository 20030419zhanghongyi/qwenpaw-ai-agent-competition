# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"澳迹同行 · Macau StoryWalk" — a full-stack AI tour-guide app for Macau (千模百炼 AI 竞赛 team project). React frontend (routes, map, narration, postcards) + FastAPI backend (orchestration, guardrails, fallbacks) + QwenPaw agents (intent understanding, route adjustment, cultural narration, photo recognition, content review, image generation).

Dev runs as **three processes**:
1. QwenPaw on the host at `127.0.0.1:8088` (`qwenpaw app`; containers reach it via `host.docker.internal:8088`)
2. Backend + database via Docker Compose at `:8000`
3. Vite frontend at `:5173`

Config comes from the repo-root `.env` (copied from `.env.example`); both backend and frontend (`envDir: ".."` in vite.config.ts) read it. Never commit `.env`.

## Commands

Run from the repo root unless noted.

```bash
docker compose up -d --build            # start PostGIS/pgvector db, seed (migrations + data), backend
docker compose ps                       # db should be healthy, backend running
docker compose run --rm rag-seed        # optional: embed RAG vectors (needs DASHSCOPE key), then set PGVECTOR_ENABLED=true and rebuild

cd backend && python -m pytest -q -p no:cacheprovider          # backend tests
cd backend && python -m pytest tests/test_routes_database.py -q            # one file
cd backend && python -m pytest tests/test_users.py -k <name> -q            # one test
cd backend && ruff check app tests      # lint (line length 100)

cd frontend && npm run dev              # Vite dev server, proxies /api → localhost:8000
cd frontend && npm run build            # tsc --noEmit + vite build (this is the type check)
```

Local backend without Compose: install `backend[dev]`, then from `backend/` run `python -m alembic upgrade head` and `python -m uvicorn app.main:app --reload`.

Some integration tests need the Compose database running. Docker images bake in the code — after adding an Alembic migration or changing seed data, re-run `docker compose up -d --build` so the seed container picks it up.

Verify: `curl http://127.0.0.1:8000/api/v1/health` (API returns 200 even when the db is down, with `database_status=unavailable`), OpenAPI at `http://localhost:8000/docs`.

## Architecture

### Backend (`backend/app/`)

Strict layering: **API → Service → Repository → PostgreSQL/PostGIS**. API layers never touch the database directly.

- `features/<domain>/` — one package per domain (routes, trips, users, profile, pois, guide, intent, postcards, stories, review), each keeping the `models.py` / `repository.py` / `service.py` / `api.py` split. Preserve this layout when adding a domain.
- `agents/` — wrappers for QwenPaw agents (`route_agent`, `intent_agent`, `guide_agent`, `photo_agent`, `reviewer_agent`, `preference_guide_agent`) over a shared `qwenpaw_client.py` that talks HTTP to QwenPaw at `QWENPAW_BASE_URL`. Each agent is gated by an `.env` flag (`ROUTE_AGENT_ENABLED` etc., default off); when off or when QwenPaw fails, endpoints degrade to rule-based/local fallbacks instead of erroring. Keep that degradation path working.
- `core/config.py` — pydantic-settings; `core/security.py` — JWT auth (register/login/me/preferences contract).
- `guardrails/` — rate limiting, audit, PII masking. `tests/conftest.py` resets the rate limiter between tests.
- `api/router.py` — assembles feature routers; `orchestrator/` — cross-feature orchestration endpoints.
- `alembic/versions/` — migrations. The Compose `seed` service runs `scripts/seed.sh` (migrations + POI/route-template import, idempotent).
- `tools/qwen-image/` — vendored QwenPaw plugin providing `generate_image_qwen` / `edit_image_qwen` for the postcard flow.

Database: PostgreSQL 16 + PostGIS (POI points, GiST index, nearby queries) + optional pgvector for RAG. `rag/ingest.py` / `rag/retrieve.py` handle embedding and semantic retrieval for guide narration; without pgvector the guide falls back to keyword retrieval.

### QwenPaw runtime contract

Six agent IDs are part of the backend contract and must not be renamed: `route`, `intent`, `guide`, `photo`, `scene`, `reviewer` (plus the `default` agent). Skill *source of truth* lives in `skills/` (business: route-adjust, requirement-understand, macau-guide, photo-recognize, postcard-scene) and `ethics/qwenpaw-skills/` (fairness-gate, source-attribution, anti-sycophancy, content-safety-review); they are copied into QwenPaw's `skill_pool` and mounted per-agent — full setup scripts are in the root `README.md`. `photo` and `scene` need a vision-capable model; `photo` needs the built-in `view_image` tool enabled. All project agents share the ethics baseline from `ethics/prompts/_ethics_base.md`.

### Frontend (`frontend/src/`)

React 18 + Vite + TypeScript + Tailwind 4 + react-router 7. HTTP calls go through `src/api/client.ts` (relative `/api` paths, proxied in dev); keep API types beside `src/api/`. Map is AMap (高德) via `@amap/amap-jsapi-loader` — needs `VITE_AMAP_API_KEY` + `VITE_AMAP_SECURITY_CODE`. i18n strings in `src/i18n.ts` (four languages). `@` aliases `src/`.

### Other top-level directories

- `data/` — canonical POI / route-template / weights JSON. Treat as **read-only** unless the task is explicitly a data update (see `data/HOW_TO_EDIT_POIS.md`).
- `harness/` — evaluation datasets, rubrics, and reports for competition evidence. Do not commit `harness/results/traces/traces.jsonl` or generated caches.
- `ethics/` — safety prompts and skills. Only `SKILL.md` files are mounted; the standalone `prompt.md` files there are intentionally not injected anywhere.

## Conventions

- Python 3.10+, four-space indent, type annotations on public interfaces, Ruff 100-char limit. `snake_case` for functions/modules/JSON fields, `PascalCase` for classes and Pydantic/SQLAlchemy models.
- TypeScript: `PascalCase` components (`RouteCard.tsx`), `camelCase` values.
- Tests: `tests/test_<area>.py`, functions `test_<expected_behavior>`; cover API contracts as well as service/repository behavior.
- Commits: Conventional Commit style (`feat(routes): …`, `fix(api): …`), small and focused. PRs list verification commands and include screenshots for UI changes.
