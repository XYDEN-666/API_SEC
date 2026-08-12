# IDORScanner — IDOR / BOLA (multi-identity replay)

**Code**: `backend/app/scanners/idor_bola.py`

**OWASP mapping**: `api1:2023` — Broken Object Level Authorization

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

For endpoints with an object identifier in the path (e.g. `/users/{user_id}`),
the scanner replays the same request once per configured identity/credential
and compares the outcomes:

- Identities receive different status codes for the same object, or
- A lower-privileged identity receives the same 2xx data with overlapping
  values in sensitive fields (`email`, `ssn`, `account_number`, `token`, …).

Both responses are captured as evidence for the finding.

## Noise filtering

A configurable ignore-list excludes known-noisy fields from the comparison
(`timestamp`, `created_at`, `updated_at`, cursors, request/trace IDs), so a
response that differs only in a timestamp does not produce a false positive.

## Findings

- Severity: `medium`
- Confidence: `medium` (status-code anomalies) / `high` (sensitive-data overlap)
- Example title: `Access-control anomaly detected (IDOR/BOLA)`

## OWASP rationale

Exposing an object to an unauthorized identity is broken object-level
authorization, which is **API1:2023 Broken Object Level Authorization** in the
OWASP API Top 10 (2023).
