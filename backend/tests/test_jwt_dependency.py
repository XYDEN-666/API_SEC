"""JWT auth dependency tests: protected route access control."""

from app.core.security import create_access_token


def _register_and_login(client, unique_email):
    password = "CorrectHorse42!"
    register = client.post(
        "/auth/register", json={"email": unique_email, "password": password}
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login", json={"email": unique_email, "password": password}
    )
    assert login.status_code == 200
    return register.json(), login.json()


def test_protected_route_returns_401_without_token(client) -> None:
    response = client.get("/users/me")
    assert response.status_code == 401


def test_protected_route_returns_401_with_invalid_token(client) -> None:
    response = client.get(
        "/users/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401


def test_protected_route_returns_200_with_valid_token(
    client, unique_email
) -> None:
    user, login = _register_and_login(client, unique_email)
    token = login["access_token"]

    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["email"] == unique_email


def test_protected_route_returns_401_with_expired_token(
    client, unique_email
) -> None:
    user, _ = _register_and_login(client, unique_email)
    expired = create_access_token(user["id"], expires_minutes=-1)

    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401
