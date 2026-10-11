"""Credentials are forwarded on the scanners' HTTP requests.

Before this, only the IDOR scanner used the credential it was handed: the
headers, CORS, HTTP-methods and JWT scanners sent anonymous requests, so
authenticated targets were assessed as a logged-out client.
"""

import asyncio

from app.core.crypto import encrypt_value
from app.models import Credential
from app.scanners.cors import CORSScanner
from app.scanners.headers import HeaderScanner
from app.scanners.http_methods import HTTPMethodScanner
from app.scanners.jwt_config import JWTScanner
from tests.scanner_harness import run_scanner_against_target

AUTHENTICATED_SCANNERS = (
    HeaderScanner,
    CORSScanner,
    HTTPMethodScanner,
    JWTScanner,
)


def _credential(auth_type: str, value: str) -> Credential:
    return Credential(
        target_id=1,
        identity_name="ci-bot",
        auth_type=auth_type,
        encrypted_value=encrypt_value(value),
    )


def test_api_key_credential_is_sent_by_every_scanner(
    http_recording_target,
) -> None:
    base_url, hits = http_recording_target()
    credential = _credential("api_key", "secret-key")

    for scanner_cls in AUTHENTICATED_SCANNERS:
        hits.clear()
        asyncio.run(
            run_scanner_against_target(
                scanner_cls(), base_url, credentials=credential
            )
        )
        assert hits, f"{scanner_cls.name} made no request"
        assert all(hit.get("x-api-key") == "secret-key" for hit in hits), (
            f"{scanner_cls.name} did not send the credential: {hits}"
        )


def test_bearer_credential_becomes_authorization_header(
    http_recording_target,
) -> None:
    base_url, hits = http_recording_target()

    asyncio.run(
        run_scanner_against_target(
            JWTScanner(),
            base_url,
            credentials=_credential("bearer", "token-123"),
        )
    )

    assert hits
    assert all(
        hit.get("authorization") == "Bearer token-123" for hit in hits
    )


def test_no_credential_means_no_auth_header(http_recording_target) -> None:
    base_url, hits = http_recording_target()

    asyncio.run(run_scanner_against_target(HeaderScanner(), base_url))

    assert hits
    for hit in hits:
        assert "authorization" not in hit
        assert "x-api-key" not in hit
