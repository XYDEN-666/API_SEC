# APIShield — API Security Assessment Platform

APIShield scans OpenAPI-defined APIs for common security issues, maps findings
to the OWASP API Security Top 10 (2023), scores them by severity and
confidence, and exports the results as HTML, PDF, and JSON reports — all
viewable in the browser without a download.

## What it does

- OpenAPI 3.x import (JSON or YAML) — endpoints are extracted and stored per
  target.
- Six built-in scanners: security headers, CORS, HTTP methods, JWT
  configuration, SQL injection indicators (error-based), and IDOR/BOLA via
  multi-identity replay. See [Scanner docs](docs/scanners/).
- Findings persistence with deduplication, OWASP API Top 10 (2023) mapping,
  and a numeric risk score (0–10) derived from severity × confidence.
- Reports: an in-app viewer, plus `report.html`, `report.pdf`, and
  `report.json` exports for every completed scan.
- Multi-identity credentials per target, encrypted at rest (Fernet); raw
  secrets never appear in API responses.

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI (Python), SQLAlchemy 2 async, Alembic, Celery |
| Frontend | React 18 + Vite + React Router (TypeScript) |
| Data | PostgreSQL 16, Redis 7 |
| Reports | Jinja2 (HTML), WeasyPrint (PDF) |
| Runtime | Docker Compose |

## Prerequisites

- Docker with Docker Compose v2 (`docker compose version`)
- Free ports `8000` and `5173` (or override them — see Configuration)

## Quick start (from a clean clone)

```bash
git clone https://github.com/XYDEN-666/API_SEC.git
cd API_SEC
docker compose up -d --build
```

That's it — no manual seed or migration step. On first boot the backend
automatically runs `alembic upgrade head` before it starts serving.

Once the stack is up:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (health check: http://localhost:8000/health)
- API docs (Swagger UI): http://localhost:8000/docs

Check status with:

```bash
docker compose ps
```

## Demo flow (end to end)

1. Open http://localhost:5173 and **Register** (this also logs you in).
2. Create a **project**.
3. Add a **target** — point it at an API you want assessed (for a quick local
   demo, any HTTP service that responds without security headers will produce
   findings).
4. **Import** its OpenAPI 3.x spec (JSON or YAML).
5. Optionally add named **credentials** (identities) so the IDOR scanner can
   replay requests as multiple users. Secrets are stored encrypted and shown
   masked.
6. Open **View scan results** for the target and click **Run new scan**. The
   scan runs in the Celery worker; the page refreshes automatically when it
   completes.
7. Browse the severity-sorted findings, OWASP category badges, and expandable
   evidence, then download the same report as **HTML**, **PDF**, or **JSON**.

## Common commands

```bash
docker compose up -d --build              # build and start everything
docker compose ps                         # status
docker compose logs -f backend            # backend logs
docker compose exec backend pytest -v     # backend tests
docker compose exec backend alembic upgrade head   # manual migration
```

Migrations run automatically on backend startup, so the manual `alembic`
command is only needed when you want to apply schema changes without
restarting the container.

## Configuration

All environment variables are documented in [.env.example](.env.example).
Copy it to `.env` to override defaults — nothing is required for a local run:

```bash
cp .env.example .env
docker compose up -d --build
```

Production notes: replace `SECRET_KEY` (JWT signing) and `ENCRYPTION_KEY`
(credential encryption) with strong, unique values before exposing the
platform; see `.env.example` for how to generate them.

## Project layout

```text
backend/
  app/
    core/       config, DB, Redis, crypto, Celery, auth dependencies
    models/     SQLAlchemy models (users, projects, targets, scans, findings…)
    routers/    FastAPI routes (auth, projects, targets, scans, reports…)
    schemas/    Pydantic request/response schemas
    scanners/   the six built-in scanners
    services/   orchestrator, dedup, risk scoring, OWASP mapping, reports
    tasks/      Celery background scan task
  alembic/      database migrations
  tests/        backend test suite
frontend/
  src/          React app (pages, components, API client)
docs/
  scanners/     per-scanner documentation
docker-compose.yml
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component overview and
[docs/scanners/](docs/scanners/) for what each scanner checks.

## Troubleshooting

- **Ports already in use**: stop the conflicting services or override the
  published ports via `.env` (see Configuration).
- **Scans never complete**: scans run in the `worker` container — confirm it
  is up with `docker compose ps` and check `docker compose logs worker`.
- **Migrations**: the backend runs them automatically at startup; to apply
  schema changes without restarting, use
  `docker compose exec backend alembic upgrade head`.
- **Reports missing content**: reports read persisted findings — run a scan
  first, and make sure the target is reachable from the worker container
  (scanners report no findings for unreachable targets).
