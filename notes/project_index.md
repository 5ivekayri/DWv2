# Dark Weather v2 Repository Reconnaissance

## Tree Overview
- Root contents: `.git/`, `README.md`, `notes/` (added during analysis).
- Expected key directories (`backend/`, `frontend/`, `docs/`, `infra/`, `docker/`, `scripts/`) are absent in the current snapshot.

## Architecture Findings
- `README.md` highlights Dark Weather v2 goals: Bridge-based modular monolith, multiple weather APIs, MQTT ingestion, Core Manager admin, clothing recommendations via OpenRouter.
- Technology stack per `README.md`: Django/DRF backend with Celery, React TS frontend, MySQL, Redis, MQTT (Mosquitto), OpenRouter, Docker Compose with Traefik/Caddy, GitHub Actions.
- No `ARCHITECTURE.md` or diagrams available locally to confirm Bridge pattern, MQTT ingest flow, or recommendation architecture.

## Configuration Inventory
- Missing common configuration artefacts: `.env.example`, `docker-compose.yml`, Python dependency files (`pyproject.toml`, `requirements.txt`), JavaScript `package.json`, Django project settings, provider/service modules.
- Repository currently only stores `README.md` and this analysis note.

## Gaps vs. Described Architecture
1. **Backend modules** — No Django project/app structure, API endpoints, or Bridge pattern implementation present.
2. **Frontend SPA** — React TypeScript project not found.
3. **Documentation** — `ARCHITECTURE.md`, diagrams, and additional docs absent.
4. **Infrastructure** — Docker, CI/CD, Terraform/Ansible-like assets missing.
5. **IoT/MQTT integration** — No MQTT consumers/producers or station management code.
6. **Recommendation service** — No OpenRouter integration or service abstraction available.

## Suggested PR Plan
1. **Bootstrap Backend Skeleton**
   - **Goal:** Scaffold Django + DRF project with modular-monolith package layout and Celery boilerplate.
   - **Key Files/Dirs:** `backend/manage.py`, `backend/config/settings.py`, `backend/apps/core/`, `backend/apps/weather/`.
   - **Acceptance:** `python manage.py check` succeeds; project boots with placeholder health endpoint; Celery worker starts without runtime errors.
   - **Commands:** `poetry install`, `poetry run python manage.py check`, `poetry run celery -A config.celery_app worker --loglevel=info`.
2. **Frontend Scaffold**
   - **Goal:** Initialize Vite + React TS SPA with routing shell and Core Manager dashboard placeholder.
   - **Key Files/Dirs:** `frontend/package.json`, `frontend/src/App.tsx`, `frontend/src/pages/Dashboard.tsx`.
   - **Acceptance:** `npm run build` passes; app renders placeholder dashboard route without runtime errors in dev server.
   - **Commands:** `npm install`, `npm run lint`, `npm run build`.
3. **Documentation Drop**
   - **Goal:** Provide architecture blueprint with Bridge diagram, MQTT ingest flow, and recommendation service mapping.
   - **Key Files/Dirs:** `docs/ARCHITECTURE.md`, `docs/diagrams/*.md`, module-level READMEs.
   - **Acceptance:** Mermaid diagrams render (lint via `markdownlint`), documents describe Bridge abstraction layers, MQTT data path, and recommendation flow aligning with README promises.
   - **Commands:** `npm run lint:docs` (markdownlint), manual Mermaid preview.
4. **Infrastructure Baseline**
   - **Goal:** Ship Docker Compose stack and environment templates for MySQL, Redis, Mosquitto, backend, frontend, worker, reverse proxy.
   - **Key Files/Dirs:** `docker-compose.yml`, `.env.example`, `infra/docker/Dockerfile.backend`, `infra/docker/Dockerfile.frontend`, `infra/traefik/traefik.yml`.
   - **Acceptance:** `docker compose config` succeeds; `docker compose up` launches services with healthy status; `.env.example` documents required variables.
   - **Commands:** `docker compose config`, `docker compose up -d`, `docker compose ps`.
5. **Service Contracts**
   - **Goal:** Implement Bridge provider interfaces for weather APIs, MQTT ingest stub, and OpenRouter recommendation service contract.
   - **Key Files/Dirs:** `backend/apps/weather/providers/base.py`, `backend/apps/stations/mqtt/consumer.py`, `backend/apps/recommendations/services/openrouter.py`.
   - **Acceptance:** Unit tests for provider interfaces and recommendation service pass; MQTT consumer stub registered with Celery beat/worker entrypoint.
   - **Commands:** `poetry run pytest`, `poetry run mypy backend`.
6. **CI/CD & Tooling**
   - **Goal:** Establish lint/test workflows and local tooling (pre-commit, formatting configs).
   - **Key Files/Dirs:** `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `pyproject.toml` tool sections, `frontend/.eslintrc.cjs`.
   - **Acceptance:** GitHub Actions workflow executes lint + test suites; `pre-commit run --all-files` passes locally.
   - **Commands:** `pre-commit install`, `pre-commit run --all-files`, `npm run lint`, `poetry run pytest`.

Each PR should stay within a 300–500 LOC diff by focusing on scoped scaffolding and deferring feature-complete implementations to later iterations.
