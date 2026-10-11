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

Frontend (from `frontend/`):

```bash
npm run dev        # Vite dev server on :5173
npm run build      # type-check + production bundle
npm test           # unit tests for the domain/formatting helpers
npm run test:ui    # headless-Chrome smoke test of the full user journey
npm run dev:mock   # fixture API on :8001 for previewing the UI without Docker
npm run preview:mock  # fixture API + dev server in one command
```

`npm run dev` finds the backend by itself: it probes `http://localhost:8000`
(the Docker backend) and then `http://localhost:8001` (the fixture API) and
uses the first one that answers, printing which it picked. Set
`VITE_API_BASE_URL` to override that, and note the value is baked in at build
time for `npm run build`.

So the full stack is just:

```bash
docker compose up -d --build     # terminal 1
cd frontend && npm run dev       # terminal 2
```

To preview the UI without PostgreSQL, Redis or Docker, run one command:

```bash
npm run preview:mock
```

It starts the fixture API on `:8001` and the dev server on `:5173`, then open
<http://localhost:5173> — sign in with any email and an 8+ character password.
Ctrl+C stops both. `npm run dev:mock` starts only the fixture API if you would
rather run the two halves yourself.

If neither backend is reachable the dev server says so and the UI loads with
API calls failing, rather than silently pointing somewhere unexpected.

`scripts/mock-api.mjs` is a development fixture only — in-memory data, no
encryption, every token accepted. Never use it as a real backend.

Migrations run automatically on backend startup, so the manual `alembic`
command is only needed when you want to apply schema changes without
restarting the container.

## Running the backend without Docker (native)

Docker is only needed for PostgreSQL and Redis. The backend, worker and tests
can all run straight from a virtualenv, which is much faster to iterate on
(no image rebuild per change) and works without the WeasyPrint system
libraries that only the image ships.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Point the app at your PostgreSQL/Redis. If you keep the compose data
# services, expose them first:  docker compose up -d postgres redis
$env:DATABASE_URL = "postgresql+asyncpg://apishield:apishield@localhost:5432/apishield"
$env:REDIS_URL     = "redis://localhost:6379/0"

cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# in a second terminal, same env vars and working directory:
..\.venv\Scripts\python.exe -m celery -A app.core.celery_app.celery_app worker --pool=solo --loglevel=info
```

Then run the frontend as usual (`cd frontend && npm run dev`).

Notes:

- **Windows needs `--pool=solo`.** Celery's default prefork pool is not usable
  on Windows, so the worker will not pick up scans without it.
- **PDF export needs WeasyPrint's native libraries** (GTK/Pango). They are in
  the Docker image but not on a stock machine. Without them the API and every
  other route run normally; only `/scans/{id}/report.pdf` reports a clear
  error. Use the container for PDF export, or install the libraries.
- **Run the tests natively** with `cd backend` then
  `..\.venv\Scripts\python.exe -m pytest -q`. The PDF module skips itself when
  the native libraries are missing, so the suite stays green either way.
- **Only one worker per queue.** If the compose `worker` container is still
  running it shares the same Redis queue, so it may pick up scans instead of
  your native worker. Stop it (`docker compose stop worker`) or set a
  different `REDIS_URL` (e.g. `redis://localhost:6379/1`) for both the API and
  the worker.

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
  src/
    api/        typed API client (JWT kept in memory only)
    components/ app shell, page header, design-system components (ui/)
    hooks/      data loading, theme and document-title hooks
    lib/        pure domain + formatting helpers (unit tested)
    pages/      Dashboard, Projects, ProjectDetail, TargetDetail, ScanResults
    styles/     design tokens, base, layout and component CSS
  scripts/      fixture API + headless UI smoke test
  tests/        node:test unit tests for src/lib
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
