import json
import logging
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager
from time import monotonic
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pmknowledge.config import Settings
from pmknowledge.documents import ingest
from pmknowledge.models import Workspace
from pmknowledge.retrieval import ask, search
from pmknowledge.schemas import (
    AnswerRead,
    AskRequest,
    IngestRead,
    QueryText,
    SearchRead,
    WorkspaceCreate,
    WorkspaceRead,
)

logger = logging.getLogger("pmknowledge")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session, session.begin():
        yield session


Database = Annotated[Session, Depends(get_session, scope="function")]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    api = FastAPI(title="PM Knowledge Worker", version="0.1.0", lifespan=lifespan)
    api.state.engine = engine

    @api.middleware("http")
    async def log_request(
        request: Request, call_next: Callable[[Request], Coroutine[Any, Any, Response]]
    ) -> Response:
        started = monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            logger.info(
                json.dumps(
                    {
                        "event": "request_completed",
                        "method": request.method,
                        "route": getattr(route, "path", "unmatched"),
                        "status": status,
                        "duration_ms": round((monotonic() - started) * 1000, 2),
                    }
                )
            )

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo submitted document metadata or question text in error payloads/logs.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
        )

    @api.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(json.dumps({"event": "database_error", "type": type(exc).__name__}))
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @api.get("/health")
    def health() -> dict[str, str]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(503, "Database unavailable") from exc
        return {"status": "ok"}

    @api.post(
        "/api/v1/workspaces",
        response_model=WorkspaceRead,
        status_code=201,
        summary="Create a development workspace (unauthenticated)",
    )
    def create_workspace(body: WorkspaceCreate, session: Database) -> WorkspaceRead:
        workspace = Workspace(name=body.name)
        session.add(workspace)
        session.flush()
        return WorkspaceRead.model_validate(workspace)

    @api.post(
        "/api/v1/workspaces/{workspace_id}/sources", response_model=IngestRead, status_code=201
    )
    def create_source(
        workspace_id: UUID,
        session: Database,
        file: Annotated[UploadFile, File()],
        title: Annotated[str, Form(min_length=1, max_length=200)],
        external_uri: Annotated[str | None, Form(max_length=2048)] = None,
    ) -> IngestRead:
        if not title.strip() or "\x00" in title or (external_uri and "\x00" in external_uri):
            raise HTTPException(422, "Metadata must be non-empty and contain no NUL characters")
        return ingest(session, workspace_id, file, title=title.strip(), external_uri=external_uri)

    @api.post(
        "/api/v1/workspaces/{workspace_id}/sources/{source_id}/versions",
        response_model=IngestRead,
        status_code=201,
        responses={200: {"model": IngestRead, "description": "Identical version already exists"}},
    )
    def create_version(
        workspace_id: UUID,
        source_id: UUID,
        response: Response,
        session: Database,
        file: Annotated[UploadFile, File()],
    ) -> IngestRead:
        result = ingest(session, workspace_id, file, source_id=source_id)
        if result.duplicate:
            response.status_code = 200
        return result

    @api.get("/api/v1/workspaces/{workspace_id}/search", response_model=SearchRead)
    def search_sources(
        workspace_id: UUID,
        session: Database,
        q: Annotated[QueryText, Query()],
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> SearchRead:
        return SearchRead(results=search(session, workspace_id, q, limit))

    @api.post("/api/v1/workspaces/{workspace_id}/ask", response_model=AnswerRead)
    def ask_question(workspace_id: UUID, body: AskRequest, session: Database) -> AnswerRead:
        return ask(session, workspace_id, body.question, body.limit)

    return api


app = create_app()
