from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pmknowledge.config import Settings
from pmknowledge.main import create_app


def test_optional_web_build_is_served_without_masking_api(tmp_path: Path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html><body>Synthetic web build</body></html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('synthetic');")
    with TestClient(create_app(Settings(web_dist_dir=tmp_path))) as client:
        assert "Synthetic web build" in client.get("/").text
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").json()["info"]["title"] == "PM Knowledge Worker"
        assert client.get("/api/v1/not-a-route").status_code == 404
        assert client.get("/not-a-page").status_code == 404
        assert client.get("/assets/../index.html").status_code == 404


def test_api_only_mode_leaves_root_unmapped():
    with TestClient(create_app(Settings(web_dist_dir=None))) as client:
        assert client.get("/").status_code == 404
        assert client.get("/docs").status_code == 200


def test_unexpected_api_errors_are_safe_and_not_cached(caplog):
    app = create_app(Settings(web_dist_dir=None))

    @app.get("/api/v1/synthetic-error")
    def synthetic_error():
        raise RuntimeError("synthetic-private-error-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/synthetic-error")
        assert response.status_code == 500
        assert response.headers.get("cache-control") == "no-store"
        assert "synthetic-private-error-detail" not in response.text + caplog.text


@pytest.mark.parametrize("contents", ["missing", "index-only", "assets-only"])
def test_invalid_configured_web_build_fails_clearly(tmp_path: Path, contents: str):
    if contents == "index-only":
        (tmp_path / "index.html").write_text("synthetic")
    if contents == "assets-only":
        (tmp_path / "assets").mkdir()
    with pytest.raises(ValueError, match="WEB_DIST_DIR"):
        create_app(Settings(web_dist_dir=tmp_path))
