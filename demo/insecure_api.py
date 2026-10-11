"""Deliberately insecure API used as a demo scan target for APIShield.

Every weakness in this file is intentional. It exists so that a single scan
lights up all six built-in scanners at once, with a spread of severities and
OWASP categories:

=====================  ==========  ==========================
Scanner                Severity    OWASP API Top 10 (2023)
=====================  ==========  ==========================
headers                medium      API8:2023
cors                   high        API8:2023
http_methods           high/medium API8:2023
jwt                    high/medium API2:2023
idor_bola              medium      API1:2023
sqli_indicators        high        API10:2023
=====================  ==========  ==========================

This is a demo fixture, NOT part of the product. Never deploy it.

Run it on the compose network so the scan worker can reach it::

    docker run --rm -d --name apishield-demo-target \
      --network mini_project_api_default -p 8765:8765 \
      -v "$PWD/demo:/app:ro" -w /app \
      mini_project_api-backend:latest \
      uvicorn insecure_api:app --host 0.0.0.0 --port 8765

Then point a target at ``http://apishield-demo-target:8765`` and import that
target's own OpenAPI document (``http://localhost:8765/openapi.json``).
"""

from __future__ import annotations

import base64
import json

import jwt
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse, Response

app = FastAPI(title="Insecure Demo API", version="1.0.0")

#: Error text returned for injection payloads. Chosen to trip the error-based
#: signatures the SQLi scanner looks for.
SQL_ERROR = (
    'psycopg.errors.SyntaxError: syntax error at or near "OR"\n'
    "LINE 1: SELECT * FROM records WHERE id = ' OR 1=1--\n"
    "SQLSTATE[42601]"
)

_VICTIM_RECORD = {
    "id": 1,
    "email": "victim@example.com",
    "ssn": "078-05-1120",
    "account_number": "4111111111111111",
}


def _b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _weak_secret_token() -> str:
    """HS256 signed with a well-known secret, with a valid ``exp``."""
    return jwt.encode(
        {"sub": "1", "exp": 2000000000}, "changeme", algorithm="HS256"
    )


def _alg_none_token() -> str:
    """Unsigned token advertising ``alg: none``."""
    return (
        f"{_b64url({'alg': 'none', 'typ': 'JWT'})}"
        f".{_b64url({'sub': '1', 'exp': 2000000000})}."
    )


def _no_expiry_token() -> str:
    """Signed with a strong secret, but no ``exp`` claim."""
    return jwt.encode(
        {"sub": "1"},
        "a-strong-secret-that-is-not-in-any-wordlist-4f9c2a",
        algorithm="HS256",
    )


@app.get("/public/feed")
def public_feed() -> Response:
    """Wildcard CORS *with* credentials -> HIGH."""
    return JSONResponse(
        {"items": [{"id": 1, "title": "hello"}]},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.options("/public/feed", include_in_schema=False)
def public_feed_preflight() -> Response:
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Allow": "GET, OPTIONS",
        },
    )


@app.get("/auth/token")
def issue_token() -> dict[str, str]:
    """Hands out three differently-broken JWTs -> 2 HIGH, 1 MEDIUM."""
    return {
        "access_token": _weak_secret_token(),
        "legacy_token": _alg_none_token(),
        "refresh_token": _no_expiry_token(),
    }


@app.get("/users/{user_id}")
def get_user(user_id: str) -> Response:
    """Ignores the caller's identity -> IDOR/BOLA, and leaks SQL errors."""
    if not user_id.isdigit():
        return PlainTextResponse(SQL_ERROR, status_code=500)
    return JSONResponse(dict(_VICTIM_RECORD))


@app.get("/search")
def search(q: str = "") -> Response:
    """Reflects a database error for injection payloads -> SQLi indicator."""
    if not q.isalnum():
        return PlainTextResponse(SQL_ERROR, status_code=500)
    return JSONResponse({"results": [], "query": q})


@app.get("/admin/settings")
def admin_settings() -> dict[str, bool]:
    """Read-only in the spec, but TRACE/PUT/DELETE are enabled server-side."""
    return {"debug": True}


@app.put("/admin/settings", include_in_schema=False)
def replace_settings() -> dict[str, str]:
    return {"status": "replaced"}


@app.delete("/admin/settings", include_in_schema=False)
def delete_settings() -> dict[str, str]:
    return {"status": "deleted"}


@app.trace("/admin/settings", include_in_schema=False)
def trace_settings() -> Response:
    """The classic cross-site tracing (XST) exposure -> HIGH."""
    return PlainTextResponse("TRACE /admin/settings")


@app.options("/admin/settings", include_in_schema=False)
def settings_options() -> Response:
    return Response(
        status_code=204,
        headers={"Allow": "GET, PUT, DELETE, TRACE, OPTIONS"},
    )
