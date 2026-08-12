# HTTPMethodScanner — HTTP Methods

**Code**: `backend/app/scanners/http_methods.py`

**OWASP mapping**: `api8:2023` — Security Misconfiguration

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

Probes each endpoint with `OPTIONS`, `TRACE`, `PUT`, and `DELETE`. A method is
considered enabled when the server responds with anything other than
`404`/`405`/`501`:

| Finding | Severity |
| --- | --- |
| `TRACE` enabled (XST risk) | high |
| `PUT` / `DELETE` enabled | medium |
| `OPTIONS` advertises dangerous methods (`TRACE`, `PUT`, `DELETE`, `PATCH`, `DEBUG`) | medium |

## Findings

- Confidence: `high`
- Example title: `TRACE method enabled`

## OWASP rationale

Unexpectedly enabled HTTP methods are a server misconfiguration, mapped to
**API8:2023 Security Misconfiguration**.
