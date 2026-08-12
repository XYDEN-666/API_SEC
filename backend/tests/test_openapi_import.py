"""OpenAPI upload endpoint tests."""

import json
import uuid

OPENAPI_3_JSON = {
    "openapi": "3.0.3",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"responses": {"200": {"description": "ok"}}}}
    },
}

OPENAPI_3_1_YAML = """
openapi: 3.1.0
info:
  title: YAML API
  version: 2.0.0
paths:
  /ping:
    get:
      responses:
        '200':
          description: pong
"""

SWAGGER_2_JSON = {
    "swagger": "2.0",
    "info": {"title": "Legacy API", "version": "1.0.0"},
    "paths": {},
}

PASSWORD = "CorrectHorse42!"


def _email(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex}@example.com"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str) -> tuple[int, str]:
    register = client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200
    return register.json()["id"], login.json()["access_token"]


def _create_project_with_target(client, token: str) -> int:
    project = client.post(
        "/projects", json={"name": "Import Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    return target.json()["id"]


def test_import_valid_openapi_3_json(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "openapi.json",
                json.dumps(OPENAPI_3_JSON).encode(),
                "application/json",
            )
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "OpenAPI 3.x document imported successfully"
    assert body["openapi"] == "3.0.3"
    assert body["title"] == "Test API"
    assert body["paths_count"] == 1


def test_import_valid_openapi_3_1_yaml(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={"file": ("openapi.yaml", OPENAPI_3_1_YAML.encode(), "application/yaml")},
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["openapi"] == "3.1.0"
    assert body["title"] == "YAML API"
    assert body["paths_count"] == 1


def test_import_rejects_swagger_2(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "swagger.json",
                json.dumps(SWAGGER_2_JSON).encode(),
                "application/json",
            )
        },
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert "Swagger 2.0" in response.json()["detail"]
    assert "Deferred" in response.json()["detail"]


def test_import_rejects_non_openapi_content(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={"file": ("random.txt", b"not a document", "text/plain")},
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert "openapi document" in response.json()["detail"].lower()


def test_import_rejects_unparseable_file(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={"file": ("broken.yaml", b"{{{{", "application/yaml")},
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert "valid JSON or YAML" in response.json()["detail"]


def test_import_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_project_with_target(client, owner_token)

    response = client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "openapi.json",
                json.dumps(OPENAPI_3_JSON).encode(),
                "application/json",
            )
        },
        headers=_auth(other_token),
    )
    assert response.status_code == 404

    assert (
        client.post(
            f"/targets/{target_id}/import-openapi",
            files={
                "file": (
                    "openapi.json",
                    json.dumps(OPENAPI_3_JSON).encode(),
                    "application/json",
                )
            },
        ).status_code
        == 401
    )
