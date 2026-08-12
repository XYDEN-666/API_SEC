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
rate limiting scanner, dashboard analytics, scan scheduling, resume scans,
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

## Git workflow — follow this for every task
1. Check the current branch: `git rev-parse --abbrev-ref HEAD`.
   - If it's `main`, create a task branch first: `git checkout -b task-X.X-short-name`
     (infer X.X and the short name from the task description itself — e.g. "Task 2.3 —
     Register & login endpoints" becomes `task-2.3-register-login`).
   - If already on a `task-*` branch, stay on it.
2. Implement the task.
3. Run the acceptance check described in the prompt yourself (pytest, curl, alembic
   upgrade head, whatever applies) and confirm it actually passes. Do not commit on the
   assumption it works — run the check first.
4. Stage and commit with message format: `task X.X: <short description>`. One commit
   per task, not several.
5. Stop there. Do NOT merge into main, do NOT push, and do NOT delete the branch —
   those stay manual, they're the review checkpoint.

## When blocked
Stop and summarize what's blocking you rather than guessing at scope or
silently implementing a Deferred feature to make something "work."
