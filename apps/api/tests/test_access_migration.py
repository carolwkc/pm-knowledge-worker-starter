"""Upgrade an isolated 0002 schema containing evidence, never the shared test schema."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import ROOT
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.integration
EVIDENCE_SQL = text("""
    SELECT d.id, d.workspace_id, v.id, v.sha256, v.plain_text, c.id, c.text,
           c.start_char, c.end_char, e.embedding::text
    FROM source_document d
    JOIN document_version v ON v.source_document_id=d.id
    JOIN source_chunk c ON c.document_version_id=v.id
    JOIN chunk_embedding e ON e.chunk_id=c.id
""")


def test_upgrade_preserves_existing_evidence_and_grants_no_implicit_access(database):
    schema = "migration_" + uuid4().hex
    ids = {key: uuid4() for key in ("workspace", "source", "version", "chunk")}
    evidence = "Original synthetic evidence."
    with database.begin() as connection:
        connection.execute(CreateSchema(schema))
        try:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            # Prevent Alembic from discovering the public schema's version table.
            connection.execute(
                text("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)")
            )
            cfg = Config(str(ROOT / "alembic.ini"))
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "0002")
            connection.execute(
                text("INSERT INTO workspace (id, name) VALUES (:workspace, 'Legacy synthetic')"),
                ids,
            )
            connection.execute(
                text(
                    "INSERT INTO source_document (id, workspace_id, title) "
                    "VALUES (:source, :workspace, 'Preserved synthetic')"
                ),
                ids,
            )
            connection.execute(
                text(
                    "INSERT INTO document_version "
                    "(id, source_document_id, version_number, sha256, plain_text) "
                    "VALUES (:version, :source, 1, :hash, :evidence)"
                ),
                {**ids, "hash": "a" * 64, "evidence": evidence},
            )
            connection.execute(
                text(
                    "INSERT INTO source_chunk "
                    "(id, document_version_id, ordinal, text, start_char, end_char) "
                    "VALUES (:chunk, :version, 0, :evidence, 0, :end)"
                ),
                {**ids, "evidence": evidence, "end": len(evidence)},
            )
            connection.execute(
                text(
                    "INSERT INTO chunk_embedding (chunk_id, model_id, embedding) "
                    "VALUES (:chunk, 'synthetic-model', CAST(:vector AS vector))"
                ),
                {**ids, "vector": str([1.0] + [0.0] * 383)},
            )
            snapshot = connection.execute(EVIDENCE_SQL).all()
            assert len(snapshot) == 1
            command.upgrade(cfg, "head")
            assert connection.execute(EVIDENCE_SQL).all() == snapshot
            assert connection.scalar(text("SELECT count(*) FROM app_user")) == 0
            assert connection.scalar(text("SELECT count(*) FROM api_token")) == 0
            assert connection.scalar(text("SELECT count(*) FROM workspace_membership")) == 0
            # Downgrading removes access metadata only; original evidence survives.
            command.downgrade(cfg, "0002")
            assert (
                connection.scalar(
                    text("SELECT plain_text FROM document_version WHERE id=:version"), ids
                )
                == evidence
            )
        finally:
            connection.execute(text("SET LOCAL search_path TO public"))
            connection.execute(DropSchema(schema, cascade=True))
