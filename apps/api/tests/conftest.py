"""Integration tests use Alembic and a separate database; cleanup is workspace-local."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def database() -> Iterator[Engine]:
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://pmknowledge:localdev@localhost:5432/pmknowledge_test",
    )
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must identify a PostgreSQL database ending in _test")
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    cfg = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def client(database: Engine) -> Iterator[TestClient]:
    from pmknowledge.config import Settings
    from pmknowledge.main import create_app

    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False),
            embeddings_enabled=False,
        )
    )
    with TestClient(app) as api:
        yield api


@pytest.fixture
def workspace(client: TestClient, database: Engine) -> Iterator[Callable[[], str]]:
    workspace_ids: list[str] = []

    def create() -> str:
        response = client.post("/api/v1/workspaces", json={"name": "Synthetic test workspace"})
        assert response.status_code == 201, response.text
        result = response.json()
        UUID(result["id"])
        workspace_ids.append(result["id"])
        return str(result["id"])

    yield create
    with database.begin() as connection:
        for workspace_id in workspace_ids:
            connection.execute(
                text("DELETE FROM workspace WHERE id = :id"), {"id": UUID(workspace_id)}
            )
