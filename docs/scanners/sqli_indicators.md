# SQLiScanner — SQL Injection Indicators (error-based)

**Code**: `backend/app/scanners/sqli_indicators.py`

**OWASP mapping**: `api10:2023` — Unsafe Consumption of APIs

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

Sends common injection payloads (`'`, `' OR 1=1--`, `' UNION SELECT NULL--`,
etc.) to parameterized endpoints (path and query parameters from the OpenAPI
spec) and inspects responses for database error signatures:

`SQLSTATE`, `syntax error near`, `syntax error at or near`, SQL driver stack
traces (`psycopg`, `sqlalchemy.exc`, `sqlite3`), `postgresql`, `ODBC`, etc.

This is **error-based indicator detection only**. Time-based SQL injection is
explicitly Deferred scope and is not built.

## Findings

- Severity: `high`
- Confidence: `high`
- Example title: `SQL injection indicator via query parameter`

## OWASP mapping note

The current OWASP API Security Top 10 (2023) no longer has a standalone
Injection category (it was API8:2019). OWASP's 2023 series records injection
as subsumed into **API10:2023 Unsafe Consumption of APIs**, so the scanner
maps there. See `backend/app/services/owasp_mapping.py` for the rationale.
