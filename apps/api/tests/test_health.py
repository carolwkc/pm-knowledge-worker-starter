from fastapi.testclient import TestClient

from pmknowledge.config import Settings
from pmknowledge.main import create_app


def test_unavailable_database_returns_safe_service_unavailable_response():
    settings = Settings(
        database_url="postgresql+psycopg://unused:private-secret@127.0.0.1:1/unused"
    )
    with TestClient(create_app(settings)) as client:
        for method, path, body in [
            ("GET", "/health", None),
            ("POST", "/api/v1/workspaces", {"name": "synthetic"}),
        ]:
            response = client.request(
                method, path, json=body, headers={"Authorization": "Bearer " + "x" * 43}
            )
            assert response.status_code == 503
            assert response.json() == {"detail": "Database unavailable"}
            assert "private-secret" not in response.text
