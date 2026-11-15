"""Task 009 migration preserves prior knowledge and access in an isolated schema."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import ROOT
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.integration


def test_feedback_migration_round_trip_preserves_existing_data(database):
    schema = "migration_" + uuid4().hex
    ids = {
        key: uuid4()
        for key in (
            "workspace",
            "user",
            "token",
            "source",
            "version",
            "chunk",
            "proposal",
            "review",
            "decision",
        )
    }
    with database.begin() as conn:
        conn.execute(CreateSchema(schema))
        try:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            conn.execute(text("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)"))
            cfg = Config(str(ROOT / "alembic.ini"))
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "0004")
            statements = [
                "INSERT INTO workspace(id,name) VALUES (:workspace,'Synthetic legacy')",
                "INSERT INTO app_user(id,name) VALUES (:user,'Synthetic owner')",
                "INSERT INTO workspace_membership(workspace_id,user_id,role) "
                "VALUES (:workspace,:user,'owner')",
                "INSERT INTO api_token(id,user_id,token_hash,expires_at) "
                "VALUES (:token,:user,'synthetic',now()+interval '1 day')",
                "INSERT INTO source_document(id,workspace_id,title) "
                "VALUES (:source,:workspace,'Synthetic source')",
                "INSERT INTO document_version(id,source_document_id,"
                "version_number,sha256,plain_text) "
                "VALUES (:version,:source,1,:hash,:evidence)",
                "INSERT INTO source_chunk(id,document_version_id,ordinal,text,start_char,end_char) "
                "VALUES (:chunk,:version,0,:evidence,0,:end)",
                "INSERT INTO chunk_embedding(chunk_id,model_id,embedding) "
                "VALUES (:chunk,'synthetic',CAST(:vector AS vector))",
                "INSERT INTO knowledge_proposal(id,workspace_id,chunk_id,statement,"
                "extractor_version,created_by,status) VALUES "
                "(:proposal,:workspace,:chunk,:evidence,'decision-marker-v1',:user,'approved')",
                "INSERT INTO review_event(id,proposal_id,reviewer_id,action) "
                "VALUES (:review,:proposal,:user,'approve')",
                "INSERT INTO approved_decision(id,workspace_id,proposal_id) "
                "VALUES (:decision,:workspace,:proposal)",
            ]
            evidence = "Decision: preserve synthetic café.\r\n"
            params = {
                **ids,
                "hash": "a" * 64,
                "evidence": evidence,
                "end": len(evidence),
                "vector": str([1.0] + [0.0] * 383),
            }
            for statement in statements:
                conn.execute(text(statement), params)
            tables = [
                t for t in inspect(conn).get_table_names(schema=schema) if t != "alembic_version"
            ]

            def snapshot():
                return {t: conn.execute(text(f"SELECT * FROM {t}")).all() for t in tables}

            before = snapshot()
            command.upgrade(cfg, "0005")
            assert snapshot() == before
            assert conn.scalar(text("SELECT count(*) FROM answer_feedback")) == 0
            conn.execute(
                text(
                    "INSERT INTO answer_feedback(id,workspace_id,created_by,submission_id,"
                    "question,mode,rating,answer) VALUES "
                    "(:id,:workspace,:user,:submission,'Synthetic question',"
                    "'keyword','helpful','{}'::jsonb)"
                ),
                {**ids, "id": uuid4(), "submission": uuid4()},
            )
            command.downgrade(cfg, "0004")
            assert snapshot() == before
            assert "answer_feedback" not in inspect(conn).get_table_names(schema=schema)
        finally:
            conn.execute(text("SET LOCAL search_path TO public"))
            conn.execute(DropSchema(schema, cascade=True))
