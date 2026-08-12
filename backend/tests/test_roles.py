"""Role field and require_role dependency tests."""

import uuid

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_role
from app.main import create_app
from tests.helpers import cleanup_test_users, create_user

PASSWORD = "CorrectHorse42!"


def _unique_email(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex}@example.com"


def _admin_app() -> FastAPI:
    """App with a demo admin-only route exercising require_role."""
    app = create_app()

    @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    async def admin_only() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_auth_me_returns_user_role(client, unique_email) -> None:
    register = client.post(
        "/auth/register", json={"email": unique_email, "password": PASSWORD}
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login", json={"email": unique_email, "password": PASSWORD}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == unique_email
    assert body["role"] == "user"


def test_auth_me_requires_token(client) -> None:
    assert client.get("/auth/me").status_code == 401


def test_require_role_allows_admin_and_blocks_others() -> None:
    admin_email = _unique_email("admin")
    user_email = _unique_email("user")
    create_user(admin_email, PASSWORD, role="admin")

    try:
        with TestClient(_admin_app()) as client:
            assert client.get("/admin-only").status_code == 401

            admin_login = client.post(
                "/auth/login",
                json={"email": admin_email, "password": PASSWORD},
            )
            admin_token = admin_login.json()["access_token"]
            admin_response = client.get(
                "/admin-only",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert admin_response.status_code == 200
            assert admin_response.json() == {"ok": True}

            register = client.post(
                "/auth/register",
                json={"email": user_email, "password": PASSWORD},
            )
            assert register.status_code == 201
            user_login = client.post(
                "/auth/login",
                json={"email": user_email, "password": PASSWORD},
            )
            user_token = user_login.json()["access_token"]
            user_response = client.get(
                "/admin-only",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert user_response.status_code == 403
    finally:
        cleanup_test_users()
