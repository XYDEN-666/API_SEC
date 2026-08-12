# HeaderScanner — Security Headers

**Code**: `backend/app/scanners/headers.py`

**OWASP mapping**: `api8:2023` — Security Misconfiguration

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

Sends one request per endpoint and checks the response for four security
headers:

| Header | Acceptable value |
| --- | --- |
| `Strict-Transport-Security` | present with `max-age` > 0 |
| `X-Content-Type-Options` | exactly `nosniff` |
| `Content-Security-Policy` | present and non-empty |
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` |

Missing or misconfigured headers produce one finding per header per endpoint.
If the target is unreachable the scanner returns no findings (and logs a
warning) rather than failing the scan.

## Findings

- Severity: `medium`
- Confidence: `high`
- Example title: `Missing Strict-Transport-Security`

## OWASP rationale

Absent or weak security headers are a classic security misconfiguration,
which is OWASP API Top 10 (2023) **API8:2023 Security Misconfiguration**.
