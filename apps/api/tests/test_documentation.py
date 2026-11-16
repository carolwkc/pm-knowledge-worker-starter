"""Keep docs/CAPABILITIES_AND_TESTING.md aligned with implemented capabilities.

The endpoint inventory is compared with FastAPI's OpenAPI schema rather than
``app.routes``: FastAPI 0.163 wraps included routers in an internal object, so
``app.routes`` exposes only the top-level ``/health`` route.
"""

import re
from pathlib import Path

from pmknowledge.config import Settings
from pmknowledge.main import create_app

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "CAPABILITIES_AND_TESTING.md"
TASKS = ROOT / "tasks"

TITLE = "# Capabilities and end-to-end testing"
API_ENDPOINT = re.compile(
    r"`(?P<method>GET|POST|PUT|PATCH|DELETE) (?P<path>/api/v1/[A-Za-z0-9_/{}-]+)`"
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
REQUIRED_HEADINGS = (
    "Purpose and scope",
    "Capability inventory",
    "Roles and permissions",
    "What is not built",
    "Run the stack locally",
    "Provision an identity and workspace",
    "Browser walkthrough",
    "Curl smoke test",
    "Automated tests and checks",
    "Optional semantic and hybrid mode",
    "Keeping this document current",
)


def _api_operations() -> set[tuple[str, str]]:
    app = create_app(
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
            embeddings_enabled=False,
            web_dist_dir=None,
        )
    )
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1")
        for method in operations
        if method in HTTP_METHODS
    }


def test_documentation_inventory_matches_api_routes() -> None:
    text = DOC.read_text(encoding="utf-8")
    documented = {
        (match.group("method"), match.group("path")) for match in API_ENDPOINT.finditer(text)
    }
    implemented = _api_operations()
    missing = sorted(implemented - documented)
    stale = sorted(documented - implemented)
    assert not missing and not stale, (
        "Update the 'Capability inventory' table in docs/CAPABILITIES_AND_TESTING.md "
        "so it lists every implemented endpoint as a literal `METHOD /api/v1/path`.\n"
        f"Undocumented endpoints: {missing}\n"
        f"Stale documented endpoints: {stale}"
    )


def test_documentation_has_required_sections() -> None:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    assert lines[0] == TITLE
    headings = {line for line in lines if line.startswith("## ")}
    required = {f"## {heading}" for heading in REQUIRED_HEADINGS}
    assert required <= headings, f"Missing sections: {sorted(required - headings)}"


def test_documentation_is_linked_from_readme_and_agents() -> None:
    assert DOC.is_file()
    for name in ("README.md", "AGENTS.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "docs/CAPABILITIES_AND_TESTING.md" in text, (
            f"{name} must link to docs/CAPABILITIES_AND_TESTING.md"
        )


def test_documentation_coverage_matches_latest_task() -> None:
    latest = max(int(path.name[:3]) for path in TASKS.glob("[0-9][0-9][0-9]-*.md"))
    text = DOC.read_text(encoding="utf-8")
    match = re.search(r"Coverage: Tasks 001[–-](\d{3})", text)
    assert match is not None, "Document must state 'Coverage: Tasks 001–NNN.'"
    assert int(match.group(1)) == latest, (
        f"Document covers Tasks 001–{match.group(1)} but the latest task is {latest:03d}. "
        "Update the coverage marker and the capability inventory with the new task."
    )
