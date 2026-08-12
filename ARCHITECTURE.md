# APIShield Architecture

## System overview

APIShield is a containerized web platform with five services:

```text
┌────────────┐     HTTP      ┌───────────────────────────────┐
│  Browser   │ ────────────► │  frontend (React + Vite)      │
└────────────┘               └───────────────┬───────────────┘
                                             │ JSON API (JWT bearer)
                                             ▼
┌──────────────────────────────────────────────────────────────┐
│  backend (FastAPI + uvicorn)                                 │
│  routers → schemas → services → models (SQLAlchemy async)    │
└───────┬──────────────────────────┬───────────────────────────┘
        │                          │ Celery task enqueue
        ▼                          ▼
┌───────────────┐          ┌──────────────────────┐
│  postgres     │          │  worker (Celery)     │
│  (persistence)│          │  ScanOrchestrator    │
└───────────────┘          │  + scanners          │
        ▲                  └──────────┬───────────┘
        │                             │ HTTP probes
        │                        ┌────┴────────────┐
        │                        │  target API     │
        └──────────┬─────────────┴─────────────────┘
                   ▼
            ┌────────────┐
            │  redis     │  (Celery broker)
            └────────────┘
```

The **backend** owns all business logic and persistence. The **frontend** is a
thin SPA that talks to the backend API. The **worker** executes scans
asynchronously so the API returns immediately when a scan is triggered.
**PostgreSQL** stores everything; **Redis** is the Celery broker.

## Backend components

### Core (`backend/app/core/`)

- `config.py` — pydantic-settings `Settings`, loaded from environment (see
  [.env.example](.env.example)).
- `db.py` — async SQLAlchemy engine/session; the app fails fast at startup if
  PostgreSQL is unreachable.
- `cache.py` — Redis connection with the same fail-fast startup check.
- `security.py` — bcrypt password hashing and JWT encode/decode.
- `crypto.py` — Fernet encryption for stored credentials.
- `deps.py` — FastAPI dependencies: `get_current_user` (JWT bearer) and
  `require_role`.
- `celery_app.py` — Celery application using Redis as broker.

### Routers (`backend/app/routers/`)

| Router | Endpoints |
| --- | --- |
| `auth` | register, login, me |
| `users` | current-user info |
| `projects` | project CRUD (owner-scoped) |
| `targets` | target CRUD, OpenAPI import, endpoints, credentials |
| `authorization_records` | authorization record CRUD |
| `scans` | trigger scans, list scans per target |
| `findings` | list findings for a scan |
| `reports` | `report.html`, `report.pdf`, `report.json` |

All resource routes enforce ownership through the authenticated user's
projects (non-owners get 404).

### Scan pipeline (`backend/app/services/orchestrator.py`)

1. `POST /targets/{id}/scans` enqueues a Celery task and returns immediately.
2. The worker loads the target's endpoints and (decrypted) credentials and
   runs the registered scanners per endpoint, each under a timeout.
3. One scanner failure or timeout never aborts the whole scan; the scan ends
   `completed` or `completed_with_errors`.
4. Raw scanner findings are **deduplicated** on `(scan, endpoint, scanner,
   normalized signature)` and persisted as `findings` rows linked to
   `evidence` rows.
5. Reports read the persisted rows through a single data-assembly path
   (`services/reports/data.py`), so HTML, PDF, and JSON always agree.

### Scanners (`backend/app/scanners/`)

Each scanner subclasses `BaseScanner` and implements only `scan()`. Default
set and OWASP API Top 10 (2023) mapping (single source of truth in
`services/owasp_mapping.py`):

| Scanner | Checks | OWASP category |
| --- | --- | --- |
| `headers` | missing/misconfigured security response headers | API8 Security Misconfiguration |
| `cors` | overly permissive CORS | API8 Security Misconfiguration |
| `http_methods` | unexpectedly enabled HTTP methods | API8 Security Misconfiguration |
| `jwt` | JWT configuration weaknesses | API2 Broken Authentication |
| `sqli_indicators` | error-based SQL injection indicators | API10 Unsafe Consumption of APIs |
| `idor_bola` | IDOR/BOLA via multi-identity replay | API1 Broken Object Level Authorization |

Details per scanner: [docs/scanners/](docs/scanners/).

## Frontend components (`frontend/src/`)

- `api/client.ts` — typed API client; the JWT is kept in module memory only
  (never `localStorage`) and attached to every request.
- `auth/AuthContext.tsx` — login/register/logout state.
- `pages/` — Home, Projects, ProjectDetail (targets/import/credentials),
  ReportViewer (findings + downloads).
- `components/` — layout and protected-route wrappers.

The report viewer fetches `GET /scans/{id}/report.json` and renders findings
severity-sorted with OWASP badges and expandable evidence; the HTML/PDF/JSON
download buttons fetch the corresponding report endpoints with the JWT and
save them as blobs.

## Data model (key tables)

```text
users ──< projects ──< targets ──< endpoints
                        │
                        ├──< credentials       (encrypted secrets)
                        └──< scans ──< evidence
                                └──< findings   (severity, owasp_category,
                                                 confidence, evidence link)
```

`findings` rows are created only after a scan run completes; every finding has
a non-null `owasp_category` (enforced at the DB level and by the orchestrator
fallback).

## Key design decisions

- **One data-assembly path for reports**: HTML, PDF, and JSON all derive from
  `build_report_data()`, so the formats cannot drift.
- **PDF reuses the HTML template** (WeasyPrint) — no second template.
- **Deduplication is keyed per endpoint**: the same issue on three endpoints
  stays three findings; the same issue observed repeatedly on one endpoint
  collapses to one.
- **Risk scoring** (0–10): severity weight × confidence multiplier, mapped to
  Low/Medium/High/Critical bands with inclusive lower bounds.
- **OWASP 2023**: the API Top 10 was last revised in 2023; injection is no
  longer a standalone category and maps to API10 (Unsafe Consumption of APIs)
  — see `services/owasp_mapping.py` for the rationale.
- **Credentials are never decrypted in API responses**; masking happens at
  the router layer and decryption is internal to scan services.
- **Memory-only JWT on the frontend**: required by the auth design; a page
  reload requires re-login.

## Deployment notes

- Docker Compose runs migrations automatically on backend startup
  (`alembic upgrade head`), so `docker compose up -d --build` from a clean
  clone is the only command needed.
- Every service has a health check and `restart: unless-stopped`.
- Overrides via `.env` (see [.env.example](.env.example)); production should
  set strong `SECRET_KEY` / `ENCRYPTION_KEY` values.
