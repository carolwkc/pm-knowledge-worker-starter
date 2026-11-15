"""Authentication is mandatory even when the database is unavailable."""

import pytest
from fastapi.testclient import TestClient

from pmknowledge.config import Settings
from pmknowledge.main import create_app


@pytest.mark.parametrize("authorization", [None, "Basic forged", "Bearer", "Bearer bad token"])
def test_missing_or_malformed_credentials_are_rejected_before_database_access(authorization):
    app = create_app(Settings(database_url="postgresql+psycopg://unused@127.0.0.1:1/unused"))
    headers = {"Authorization": authorization} if authorization else {}
    with TestClient(app) as client:
        response = client.post("/api/v1/workspaces", json={"name": "Synthetic"}, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing credentials"}


def test_openapi_declares_bearer_security_for_every_api_operation():
    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            if path.startswith("/api/v1"):
                assert operation["security"] == [{"HTTPBearer": []}]
            else:
                assert "security" not in operation
