import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from audit import AuditFields
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.econsent.database import db_manager
from apps.econsent.models import Base, ConsentAuditLog, ConsentDocument
from packages.security.middleware import GatewayAuthMiddleware


# Pydantic Schemas for eConsent API Requests/Responses
class ConsentDocumentCreate(AuditFields):
    """
    Schema for creating a new eConsent document.
    Reuses the shared 21 CFR Part 11 AuditFields base.
    """

    study_id: str = Field(..., description="Unique clinical study identifier")
    site_id: str = Field(..., description="Unique clinical site identifier")
    document_name: str = Field(
        ..., max_length=255, description="Name of the eConsent form/document"
    )
    content: str = Field(..., description="Full text/content of the consent form")


class ConsentDocumentResponse(AuditFields):
    """
    Schema for eConsent document response.
    Reuses the shared 21 CFR Part 11 AuditFields base.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique generated UUID of the document")
    study_id: str = Field(..., description="Unique clinical study identifier")
    site_id: str = Field(..., description="Unique clinical site identifier")
    document_name: str = Field(..., description="Name of the eConsent form/document")
    content: str = Field(..., description="Full text/content of the consent form")


DATABASE_URL = os.getenv("ECONSENT_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan events for the eConsent microservice.
    Initializes database manager, creates SQLite tables, and disposes resources on shutdown.
    """
    db_manager.init_db(DATABASE_URL)

    if DATABASE_URL.startswith("sqlite"):
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await db_manager.close()


app = FastAPI(
    title="Cadence Clinical - eConsent",
    version="0.1.0",
    lifespan=lifespan,
)

# Register secure API gateway authentication and context propagation middleware
app.add_middleware(GatewayAuthMiddleware)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to yield an asynchronous database session.
    """
    session_maker = db_manager.get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def write_audit_log(
    session: AsyncSession,
    actor_id: str,
    actor_role: str,
    action: str,
    document_id: Optional[str],
    details: str,
    reason_for_change: str,
) -> None:
    """
    Appends an entry to the 21 CFR Part 11 compliant ConsentAuditLog.
    """
    log_entry = ConsentAuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        document_id=document_id,
        details=details,
        reason_for_change=reason_for_change,
    )
    session.add(log_entry)
    await session.flush()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Service health check endpoint.
    Exempt from gateway authentication checks.
    """
    return {"status": "ok", "service": "econsent"}


def map_document_to_response(doc: ConsentDocument) -> ConsentDocumentResponse:
    return ConsentDocumentResponse(
        id=doc.id,
        study_id=doc.study_id,
        site_id=doc.site_id,
        document_name=doc.document_name,
        content=doc.content,
        created_at=doc.created_at,
        created_by=doc.created_by,
        reason_for_change=doc.reason_for_change,
        version_index=doc.version_index,
    )


@app.post(
    "/api/v1/econsent/documents",
    response_model=ConsentDocumentResponse,
    status_code=201,
)
async def create_consent_document(
    request: Request,
    payload: ConsentDocumentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ConsentDocumentResponse:
    """
    Create a new clinical trial eConsent document.
    Enforces Part 11 validation and logs access to the immutable audit trail.
    """
    user_id = getattr(request.state, "user_id", "system")
    user_role = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", payload.reason_for_change)

    doc = ConsentDocument(
        study_id=payload.study_id,
        site_id=payload.site_id,
        document_name=payload.document_name,
        content=payload.content,
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=payload.version_index,
    )
    session.add(doc)
    await session.flush()

    await write_audit_log(
        session=session,
        actor_id=user_id,
        actor_role=user_role,
        action="CREATE_DOCUMENT",
        document_id=doc.id,
        details=f"Created consent document '{payload.document_name}' for study '{payload.study_id}'.",
        reason_for_change=change_reason,
    )

    return map_document_to_response(doc)


@app.get("/api/v1/econsent/documents/{id}", response_model=ConsentDocumentResponse)
async def get_consent_document(
    request: Request,
    id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConsentDocumentResponse:
    """
    Retrieve an existing eConsent document by its unique identifier.
    Logs access to the audit trail.
    """
    user_id = getattr(request.state, "user_id", "system")
    user_role = getattr(request.state, "roles", "system")

    # Access reason or default change reason for reading if present
    change_reason = getattr(request.state, "change_reason", "Standard document access")

    stmt = select(ConsentDocument).where(ConsentDocument.id == id)
    result = await session.execute(stmt)
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=404, detail=f"Consent document with ID '{id}' not found."
        )

    await write_audit_log(
        session=session,
        actor_id=user_id,
        actor_role=user_role,
        action="VIEW_DOCUMENT",
        document_id=doc.id,
        details=f"Viewed consent document '{doc.document_name}' (ID: {doc.id}).",
        reason_for_change=change_reason,
    )

    return map_document_to_response(doc)
