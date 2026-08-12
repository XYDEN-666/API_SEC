"""Shared test fixtures."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import cleanup_test_users


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client
    cleanup_test_users()


@pytest.fixture
def unique_email() -> str:
    return _unique_email()
