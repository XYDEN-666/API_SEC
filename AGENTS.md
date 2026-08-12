# APIShield — Agent Operating Contract

## Project
API Security Assessment Platform. Stack: FastAPI (Python) backend, React + Vite
frontend, PostgreSQL, Redis, Docker Compose. Async background workers (Celery/RQ)
handle scanning.

## Scope — read this before touching anything
Included: user auth, project/target management, authorization gate, OpenAPI 3.x
import, multi-identity credential management, scan orchestrator, scanners
(Headers, CORS, HTTP Methods, JWT, SQLi indicators, IDOR/BOLA), findings engine,
OWASP API Top 10 mapping, HTML/PDF/JSON reports, in-app report viewer, Docker
deployment.

Deferred — do NOT build these even if it seems convenient: Swagger 2.0 import,
Postman import, OAuth refresh flows, time-based SQLi, advanced JWT analysis,
rate limiting scanner, scan scheduling, resume scans,
plugin ecosystem. If a task seems to require one of these, stop and flag it
instead of implementing it.

## Commands
<!-- fill these in with your actual commands, adjust as needed -->
- Backend dev server: `docker compose up backend`
- Backend tests: `docker compose exec backend pytest -v`
- Migrations: `docker compose exec backend alembic upgrade head`
- Frontend dev: `docker compose up frontend`
- Full stack: `docker compose up`

## Conventions
- Every task's acceptance criterion is a test. Write that test alongside the
  implementation — don't just implement and claim it works.
- Never return decrypted credential values from any API response — only from
  internal service calls.
- All new tables need an Alembic migration, not just a SQLAlchemy model.
- Scanners implement `BaseScanner.scan()` only — don't reach into orchestrator
  internals from inside a scanner.

## Definition of done
A task is done when: the acceptance test (see prompt) passes, `alembic upgrade
head` runs clean if a migration was added, and no Deferred-scope feature was
touched.

## When blocked
Stop and summarize what's blocking you rather than guessing at scope or
silently implementing a Deferred feature to make something "work."