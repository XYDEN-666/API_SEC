# CORSScanner — Cross-Origin Resource Sharing

**Code**: `backend/app/scanners/cors.py`

**OWASP mapping**: `api8:2023` — Security Misconfiguration

**Source of truth**: `backend/app/services/owasp_mapping.py`

## What it checks

Sends a request with `Origin: https://evil.example` (plus an `OPTIONS`
preflight) and inspects the `Access-Control-Allow-*` response headers:

| Configuration | Severity |
| --- | --- |
| `Access-Control-Allow-Origin: *` + `Access-Control-Allow-Credentials: true` | high |
| `Access-Control-Allow-Origin: *` alone | medium |
| `Access-Control-Allow-Origin: null` | medium |
| Reflected attacker origin + credentials allowed | high |

Properly restricted configurations (specific allowed origins, no credentials
with wildcards) produce no findings. The scanner deduplicates identical
evidence between the simple request and the preflight.

## Findings

- Confidence: `high`
- Example title: `Wildcard CORS origin combined with credentials`

## OWASP rationale

Overly permissive CORS is a server misconfiguration, mapped to
**API8:2023 Security Misconfiguration**.
