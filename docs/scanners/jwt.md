# JWTScanner — JWT Configuration

**Code**: `backend/app/scanners/jwt_config.py`

**OWASP mapping**: `api2:2023` — Broken Authentication

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

Sends one request per endpoint, extracts JWTs from the response body, and
checks their configuration:

| Check | Severity |
| --- | --- |
| Token accepted with `alg: none` (unsigned) | high |
| Token missing the `exp` (expiration) claim | medium |
| Token signed with a weak, well-known secret | high |

This is deliberately basic JWT *configuration* analysis. Token cracking,
algorithm-confusion exploitation, and other advanced JWT analysis are out of
scope (Deferred).

## Findings

- Confidence: `high`
- Example title: `JWT missing exp claim`

## OWASP rationale

Weak JWT configuration leads to authentication bypass, which is
**API2:2023 Broken Authentication** in the OWASP API Top 10 (2023).
