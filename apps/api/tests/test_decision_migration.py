"""Round-trip Task 004 in an isolated schema, preserving evidence and access."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import ROOT
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.integration


def test_decision_migration_preserves_evidence_embeddings_and_access(database):
    schema = "migration_" + uuid4().hex
    ids = {key: uuid4() for key in ("workspace", "user", "token", "source", "version", "chunk")}
    evidence = "Decision: preserve synthetic café evidence.\r\nKeep line endings."
    with database.begin() as conn:
        conn.execute(CreateSchema(schema))
        try:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            conn.execute(text("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)"))
            cfg = Config(str(ROOT / "alembic.ini"))
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "0003")
            statements = [
                "INSERT INTO workspace(id,name) VALUES (:workspace,'Synthetic legacy')",
                "INSERT INTO app_user(id,name) VALUES (:user,'Synthetic owner')",
                "INSERT INTO workspace_membership(workspace_id,user_id,role) "
                "VALUES (:workspace,:user,'owner')",
                "INSERT INTO api_token(id,user_id,token_hash,expires_at) "
                "VALUES (:token,:user,'synthetic-digest',now()+interval '1 day')",
                "INSERT INTO source_document(id,workspace_id,title) "
                "VALUES (:source,:workspace,'Synthetic decision')",
                "INSERT INTO document_version "
                "(id,source_document_id,version_number,sha256,plain_text) "
                "VALUES (:version,:source,1,:hash,:evidence)",
                "INSERT INTO source_chunk(id,document_version_id,ordinal,text,start_char,end_char) "
                "VALUES (:chunk,:version,0,:evidence,0,:end)",
                "INSERT INTO chunk_embedding(chunk_id,model_id,embedding) "
                "VALUES (:chunk,'synthetic-model',CAST(:vector AS vector))",
            ]
            params = {
                **ids,
                "evidence": evidence,
                "end": len(evidence),
                "hash": "a" * 64,
                "vector": str([1.0] + [0.0] * 383),
            }
            for statement in statements:
                conn.execute(text(statement), params)
            tables = [
                "workspace",
                "app_user",
                "api_token",
                "workspace_membership",
                "source_document",
                "document_version",
                "source_chunk",
                "chunk_embedding",
            ]

            def snapshot():
                return {
                    table: conn.execute(text(f"SELECT * FROM {table}")).all() for table in tables
                }

            before = snapshot()
            command.upgrade(cfg, "0004")
            assert snapshot() == before
            for table in ["knowledge_proposal", "review_event", "approved_decision"]:
                assert conn.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            # Downgrade removes Task 004 data only, even with a complete review present.
            proposal, event_id, decision = uuid4(), uuid4(), uuid4()
            conn.execute(
                text(
                    "INSERT INTO knowledge_proposal "
                    "(id,workspace_id,chunk_id,statement,extractor_version,created_by,status) "
                    "VALUES (:proposal,:workspace,:chunk,:evidence,"
                    "'decision-marker-v1',:user,'approved')"
                ),
                {**params, "proposal": proposal},
            )
            conn.execute(
                text(
                    "INSERT INTO review_event(id,proposal_id,reviewer_id,action) "
                    "VALUES (:event,:proposal,:user,'approve')"
                ),
                {**ids, "event": event_id, "proposal": proposal},
            )
            conn.execute(
                text(
                    "INSERT INTO approved_decision(id,workspace_id,proposal_id) "
                    "VALUES (:decision,:workspace,:proposal)"
                ),
                {**ids, "decision": decision, "proposal": proposal},
            )
            command.downgrade(cfg, "0003")
            assert snapshot() == before
            assert not {"knowledge_proposal", "review_event", "approved_decision"}.intersection(
                inspect(conn).get_table_names(schema=schema)
            )
        finally:
            conn.execute(text("SET LOCAL search_path TO public"))
            conn.execute(DropSchema(schema, cascade=True))
