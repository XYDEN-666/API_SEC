"""Authentication endpoint tests: register and login."""

import jwt

from app.core.config import settings


def test_register_then_login_returns_valid_jwt(client, unique_email) -> None:
    email = unique_email
    password = "CorrectHorse42!"

    register = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register.status_code == 201
    user = register.json()
    assert user["email"] == email
    assert "hashed_password" not in user

    login = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == str(user["id"])
    assert payload["exp"] > payload["iat"]


def test_login_with_wrong_password_returns_401(client, unique_email) -> None:
    email = unique_email
    password = "CorrectHorse42!"
    client.post(
        "/auth/register", json={"email": email, "password": password}
    )

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPass99!"},
    )
    assert response.status_code == 401


def test_register_duplicate_email_returns_409(client, unique_email) -> None:
    email = unique_email
    assert (
        client.post(
            "/auth/register",
            json={"email": email, "password": "CorrectHorse42!"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/auth/register",
            json={"email": email, "password": "OtherPass123!"},
        ).status_code
        == 409
    )


def test_login_with_unknown_email_returns_401(client, unique_email) -> None:
    response = client.post(
        "/auth/login",
        json={"email": unique_email, "password": "Whatever123!"},
    )
    assert response.status_code == 401
