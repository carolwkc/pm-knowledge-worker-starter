import json
import logging
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager
from time import monotonic
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import (
    APIRouter,
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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pmknowledge.access import change_membership, require_workspace_access
from pmknowledge.auth import Principal, authenticate, invalid_credentials
from pmknowledge.config import Settings
from pmknowledge.documents import ingest
from pmknowledge.embeddings import Embedder, EmbeddingUnavailable, LocalEmbedder
from pmknowledge.models import User, Workspace, WorkspaceMembership
from pmknowledge.retrieval import ask, search
from pmknowledge.schemas import (
    AnswerRead,
    AskRequest,
    IngestRead,
    JoinedWorkspace,
    MembershipList,
    MembershipRead,
    MembershipWrite,
    QueryText,
    RetrievalMode,
    SearchRead,
    UserRead,
    WorkspaceCreate,
    WorkspaceList,
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


def get_principal(
    session: Database,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ],
) -> Principal:
    if credentials is None:
        raise invalid_credentials()
    return authenticate(session, credentials.credentials)


Identity = Annotated[Principal, Depends(get_principal, scope="function")]


def get_embedder(request: Request) -> Embedder | None:
    return cast(Embedder | None, request.app.state.embedder)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


Embedding = Annotated[Embedder | None, Depends(get_embedder)]
Configuration = Annotated[Settings, Depends(get_settings)]


def create_app(settings: Settings | None = None, *, embedder: Embedder | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    api = FastAPI(title="PM Knowledge Worker", version="0.1.0", lifespan=lifespan)
    routes = APIRouter(dependencies=[Depends(get_principal, scope="function")])
    api.state.engine = engine
    api.state.settings = settings
    api.state.embedder = (
        (embedder or LocalEmbedder(settings.embedding_cache_dir))
        if settings.embeddings_enabled
        else None
    )

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

    @api.exception_handler(EmbeddingUnavailable)
    async def embedding_error(request: Request, exc: EmbeddingUnavailable) -> JSONResponse:
        logger.error(json.dumps({"event": "embedding_unavailable"}))
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Local embeddings unavailable; enable embeddings and download the model first"
                )
            },
        )

    @api.get("/health")
    def health() -> dict[str, str]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(503, "Database unavailable") from exc
        return {"status": "ok"}

    @routes.get("/api/v1/me", response_model=UserRead)
    def me(session: Database, principal: Identity) -> UserRead:
        user = session.get(User, principal.user_id)
        if user is None:
            raise invalid_credentials()
        return UserRead.model_validate(user)

    @routes.get("/api/v1/workspaces", response_model=WorkspaceList)
    def list_workspaces(session: Database, principal: Identity) -> WorkspaceList:
        rows = session.execute(
            select(Workspace.id, Workspace.name, Workspace.created_at, WorkspaceMembership.role)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(WorkspaceMembership.user_id == principal.user_id)
            .order_by(Workspace.created_at, Workspace.id)
        ).mappings()
        return WorkspaceList(workspaces=[JoinedWorkspace.model_validate(row) for row in rows])

    @routes.post(
        "/api/v1/workspaces",
        response_model=WorkspaceRead,
        status_code=201,
        summary="Create a workspace owned by the authenticated user",
    )
    def create_workspace(
        body: WorkspaceCreate, session: Database, principal: Identity
    ) -> WorkspaceRead:
        workspace = Workspace(name=body.name)
        session.add(workspace)
        session.flush()
        session.add(
            WorkspaceMembership(workspace_id=workspace.id, user_id=principal.user_id, role="owner")
        )
        session.flush()
        return WorkspaceRead.model_validate(workspace)

    @routes.get("/api/v1/workspaces/{workspace_id}/members", response_model=MembershipList)
    def list_members(workspace_id: UUID, session: Database, principal: Identity) -> MembershipList:
        require_workspace_access(session, workspace_id, principal, "owner")
        members = session.scalars(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.user_id)
        )
        return MembershipList(members=[MembershipRead.model_validate(member) for member in members])

    @routes.put(
        "/api/v1/workspaces/{workspace_id}/members/{user_id}", response_model=MembershipRead
    )
    def put_member(
        workspace_id: UUID,
        user_id: UUID,
        body: MembershipWrite,
        session: Database,
        principal: Identity,
    ) -> MembershipRead:
        member = change_membership(session, workspace_id, principal, user_id, body.role)
        assert member is not None
        return member

    @routes.delete("/api/v1/workspaces/{workspace_id}/members/{user_id}", status_code=204)
    def delete_member(
        workspace_id: UUID, user_id: UUID, session: Database, principal: Identity
    ) -> Response:
        change_membership(session, workspace_id, principal, user_id, None)
        return Response(status_code=204)

    @routes.post(
        "/api/v1/workspaces/{workspace_id}/sources", response_model=IngestRead, status_code=201
    )
    def create_source(
        workspace_id: UUID,
        session: Database,
        principal: Identity,
        embedder: Embedding,
        file: Annotated[UploadFile, File()],
        title: Annotated[str, Form(min_length=1, max_length=200)],
        external_uri: Annotated[str | None, Form(max_length=2048)] = None,
    ) -> IngestRead:
        if not title.strip() or "\x00" in title or (external_uri and "\x00" in external_uri):
            raise HTTPException(422, "Metadata must be non-empty and contain no NUL characters")
        return ingest(
            session,
            workspace_id,
            file,
            principal=principal,
            title=title.strip(),
            external_uri=external_uri,
            embedder=embedder,
        )

    @routes.post(
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
        principal: Identity,
        embedder: Embedding,
        file: Annotated[UploadFile, File()],
    ) -> IngestRead:
        result = ingest(
            session, workspace_id, file, principal=principal, source_id=source_id, embedder=embedder
        )
        if result.duplicate:
            response.status_code = 200
        return result

    @routes.get("/api/v1/workspaces/{workspace_id}/search", response_model=SearchRead)
    def search_sources(
        workspace_id: UUID,
        session: Database,
        principal: Identity,
        settings: Configuration,
        embedder: Embedding,
        q: Annotated[QueryText, Query()],
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
        mode: RetrievalMode = "keyword",
    ) -> SearchRead:
        return SearchRead(
            results=search(
                session,
                workspace_id,
                q,
                limit,
                principal=principal,
                mode=mode,
                embedder=embedder,
                min_score=settings.semantic_min_score,
            )
        )

    @routes.post("/api/v1/workspaces/{workspace_id}/ask", response_model=AnswerRead)
    def ask_question(
        workspace_id: UUID,
        body: AskRequest,
        session: Database,
        principal: Identity,
        settings: Configuration,
        embedder: Embedding,
    ) -> AnswerRead:
        return ask(
            session,
            workspace_id,
            body.question,
            body.limit,
            principal=principal,
            mode=body.mode,
            embedder=embedder,
            min_score=settings.semantic_min_score,
        )

    api.include_router(routes)
    return api


app = create_app()
