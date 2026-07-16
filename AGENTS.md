# Repository Guidelines

## Project Structure & Module Organization

- `backend/` contains the FastAPI service. Keep API → service → repository separation in `app/features/<domain>/`; put database migrations in `backend/alembic/versions/` and tests in `backend/tests/`.
- `frontend/` is the React + Vite + TypeScript MVP. Application code lives in `frontend/src/`, with HTTP calls in `src/api/client.ts`.
- `data/` holds canonical POI, route-template, and weighting JSON. Treat source data as read-only unless a data-update task explicitly requires a change.
- `rag/`, `skills/`, and `ethics/` contain retrieval utilities, QwenPaw skill prompts, and safety guidance. `harness/` contains evaluation datasets, rubrics, and generated reports.

## Build, Test, and Development Commands

Run commands from the repository root unless noted otherwise.

```bash
docker compose up -d --build       # start PostGIS, seed data, and backend
docker compose ps                  # confirm db is healthy and backend is running
cd backend && python -m pytest -q -p no:cacheprovider  # run backend tests
cd backend && ruff check app tests # lint Python code
cd frontend && npm install && npm run dev   # run Vite at localhost:5173
cd frontend && npm run build       # type-check and create a production build
```

For local backend work without Compose, install `backend[dev]`, run `python -m alembic upgrade head`, then start `python -m uvicorn app.main:app --reload` from `backend/`.

## Coding Style & Naming Conventions

Use Python 3.10+ with four-space indentation, type annotations for public interfaces, and Ruff’s 100-character line limit. Use `snake_case` for Python functions, modules, and JSON fields; use `PascalCase` for classes and Pydantic/SQLAlchemy models. Preserve the feature layout (`models.py`, `repository.py`, `service.py`, `api.py`) when adding a backend domain.

Use TypeScript with the existing Vite conventions: `PascalCase` React components (for example, `RouteCard.tsx`), `camelCase` functions and values, and keep API types beside or below `src/api/`.

## Testing Guidelines

Add or update Pytest coverage for behavior changes. Name files `test_<area>.py` and tests `test_<expected_behavior>`. Exercise API contracts as well as service/repository behavior where applicable. Integration tests may require the Compose database; do not commit generated caches or `harness/results/traces/traces.jsonl`.

## Commit & Pull Request Guidelines

Use concise Conventional Commit-style subjects seen in project history: `feat(routes): persist templates`, `fix(api): register router`, `docs(harness): update evidence`. Keep commits focused. PRs should explain the user-facing or data impact, list verification commands, link the relevant issue or plan item when available, and include screenshots for frontend/UI changes. Never commit `.env`, API keys, or local database volumes.
