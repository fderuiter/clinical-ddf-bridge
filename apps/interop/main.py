import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.interop.auth import (
    require_staff_role,
    verify_subject_bulk_identity,
    verify_subject_identity,
)
from apps.interop.database import db_manager
from apps.interop.fhir_adapter import FHIRAdapter
from apps.interop.models import (
    Base,
    EPROSubmission,
    Instrument,
    InteropAuditLog,
    SubjectAssignment,
)
from packages.security.middleware import GatewayAuthMiddleware

DATABASE_URL = os.getenv("INTEROP_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle the lifespan events for the Interop application.

    Initializes the database session manager on startup, creates the required
    schemas, and securely cleans up connections on shutdown.
    """
    db_manager.init_db(DATABASE_URL)

    # Automatically create tables for sqlite in-memory/file databases
    if DATABASE_URL.startswith("sqlite"):
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await db_manager.close()


app = FastAPI(
    title="Cadence Clinical - FHIR / eSource & eCOA Sync Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

# Enforce secure gateway authentication middleware
app.add_middleware(GatewayAuthMiddleware)


# Dependency to obtain database session
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


# Helper to secure and log actions to the audit ledger
async def write_audit_log(
    session: AsyncSession,
    user_id: str,
    user_role: str,
    action: str,
    details: str,
) -> None:
    """
    Utility function to write to the immutable interop audit ledger.
    """
    log_entry = InteropAuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        details=details,
    )
    session.add(log_entry)
    await session.flush()


# Pydantic models for FHIR & ePRO
class FHIRPrefillRequest(BaseModel):
    """
    Payload for pre-filling CDASH fields using a FHIR bundle.
    """

    study_id: str = Field(..., description="Unique identifier of the clinical study")
    bundle: Dict[str, Any] = Field(
        ..., description="The standard FHIR Bundle JSON payload"
    )


class OfflineSyncMarkers(BaseModel):
    """
    Offline queue reconciliation and conflict resolution parameters.
    """

    sequence_number: int = Field(
        ..., description="The queue order sequence from device"
    )
    client_id: str = Field(..., description="Unique identifier for the mobile device")
    conflict_strategy: str = Field(
        "CLIENT_WINS",
        description="Conflict strategy to resolve duplicate submissions. Supported: CLIENT_WINS, SERVER_WINS, MERGE",
    )


class EPROSubmissionPayload(BaseModel):
    """
    A single participant ePRO/eCOA diary submission.
    """

    subject_id: str = Field(..., description="Pseudonymized identifier of the subject")
    diary_id: str = Field(..., description="Unique identifier for the diary or survey")
    device_timestamp: datetime = Field(
        ..., description="ISO 8601 timestamp when the entry was created on device"
    )
    answers: Dict[str, Any] = Field(
        ..., description="The questionnaire response key-values"
    )
    offline_sync_markers: OfflineSyncMarkers = Field(
        ..., description="The offline sync queue conflict tracking parameters"
    )


class BulkSyncPayload(BaseModel):
    """
    A bulk list of ePRO submissions for offline queue reconciliation.
    """

    submissions: List[EPROSubmissionPayload] = Field(
        ..., description="A list of queued ePRO submissions"
    )


# Helper to resolve ePRO submission conflicts
async def resolve_and_save_submission(
    session: AsyncSession,
    payload: EPROSubmissionPayload,
) -> Dict[str, Any]:
    """
    Save a new ePRO submission or reconcile existing ones based on conflict strategy.
    """
    # Look for an existing submission with same subject_id and diary_id
    stmt = (
        select(EPROSubmission)
        .where(EPROSubmission.subject_id == payload.subject_id)
        .where(EPROSubmission.diary_id == payload.diary_id)
    )
    result = await session.execute(stmt)
    existing: Optional[EPROSubmission] = result.scalars().first()

    strategy = payload.offline_sync_markers.conflict_strategy.upper()
    if strategy not in ("CLIENT_WINS", "SERVER_WINS", "MERGE"):
        strategy = "CLIENT_WINS"

    if not existing:
        # Easy case, no conflict
        new_sub = EPROSubmission(
            subject_id=payload.subject_id,
            diary_id=payload.diary_id,
            device_timestamp=payload.device_timestamp,
            answers=payload.answers,
            offline_sync_markers=payload.offline_sync_markers.model_dump(),
            sync_status="RESOLVED",
            version_index=1,
        )
        session.add(new_sub)
        await session.flush()
        return {
            "status": "CREATED",
            "id": new_sub.id,
            "subject_id": new_sub.subject_id,
            "diary_id": new_sub.diary_id,
            "answers": new_sub.answers,
            "sync_status": new_sub.sync_status,
            "version_index": new_sub.version_index,
        }

    # Conflict scenario!
    if strategy == "CLIENT_WINS":
        # Overwrite with incoming
        existing.answers = payload.answers
        existing.device_timestamp = payload.device_timestamp
        existing.offline_sync_markers = payload.offline_sync_markers.model_dump()
        existing.version_index += 1
        existing.sync_status = "RESOLVED"
        session.add(existing)
        await session.flush()
        return {
            "status": "UPDATED_CLIENT_WINS",
            "id": existing.id,
            "subject_id": existing.subject_id,
            "diary_id": existing.diary_id,
            "answers": existing.answers,
            "sync_status": existing.sync_status,
            "version_index": existing.version_index,
        }

    elif strategy == "SERVER_WINS":
        # Keep existing, store incoming as ignored/archived under conflict status
        conflict_sub = EPROSubmission(
            subject_id=payload.subject_id,
            diary_id=payload.diary_id,
            device_timestamp=payload.device_timestamp,
            answers=payload.answers,
            offline_sync_markers=payload.offline_sync_markers.model_dump(),
            sync_status="CONFLICT_IGNORED",
            version_index=1,
        )
        session.add(conflict_sub)
        await session.flush()
        return {
            "status": "IGNORED_SERVER_WINS",
            "id": existing.id,
            "subject_id": existing.subject_id,
            "diary_id": existing.diary_id,
            "answers": existing.answers,
            "sync_status": "RESOLVED",
            "version_index": existing.version_index,
        }

    elif strategy == "MERGE":
        # Merge dictionaries (client overrides server for identical keys)
        merged_answers = existing.answers.copy()
        merged_answers.update(payload.answers)

        existing.answers = merged_answers
        existing.device_timestamp = payload.device_timestamp
        existing.offline_sync_markers = payload.offline_sync_markers.model_dump()
        existing.version_index += 1
        existing.sync_status = "RESOLVED"
        session.add(existing)
        await session.flush()
        return {
            "status": "MERGED",
            "id": existing.id,
            "subject_id": existing.subject_id,
            "diary_id": existing.diary_id,
            "answers": existing.answers,
            "sync_status": existing.sync_status,
            "version_index": existing.version_index,
        }

    return {"status": "ERROR", "detail": "Unhandled conflict resolution state"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Service health check endpoint.
    """
    return {"status": "ok", "service": "interop"}


@app.post("/api/v1/interop/fhir/prefill")
async def fhir_prefill(
    request: Request,
    payload: FHIRPrefillRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Ingest a standard FHIR Bundle payload, pseudonymize Patient ID,
    strip all Direct Identifiers (PII), and return mapped CDASH eCRF fields.
    """
    require_staff_role(request)
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")

    # Map FHIR using adapter
    adapter = FHIRAdapter(payload.study_id)
    result = adapter.parse_bundle(payload.bundle)

    # Log action to immutable audit trail
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="FHIR_PREFILL",
        details=f"Parsed FHIR Bundle for study '{payload.study_id}'. Pseudonymized Subject: '{result['subject_pseudonym']}'.",
    )

    return result


@app.post("/api/v1/interop/epro/submit", status_code=201)
async def epro_submit(
    request: Request,
    payload: EPROSubmissionPayload,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Secure REST endpoint for mobile apps to submit a single participant diary/survey entry.
    Handles offline queue reconciliation & conflict resolution on duplicate sync requests.
    """
    verify_subject_identity(request, payload.subject_id)
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")

    # Process and resolve conflict
    resolved = await resolve_and_save_submission(session, payload)

    # Log action to immutable audit trail
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="EPRO_SUBMIT",
        details=f"Processed ePRO submission for Subject '{payload.subject_id}', Diary '{payload.diary_id}'. Result: {resolved['status']}.",
    )

    return resolved


@app.post("/api/v1/interop/epro/sync", status_code=200)
async def epro_sync(
    request: Request,
    payload: BulkSyncPayload,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Secure bulk sync endpoint for offline queues. Performs reconciliation
    and conflict resolution across multiple participant submissions.
    """
    verify_subject_bulk_identity(
        request, [sub.subject_id for sub in payload.submissions]
    )
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")

    results = []
    created_count = 0
    updated_count = 0
    ignored_count = 0

    for sub_payload in payload.submissions:
        resolved = await resolve_and_save_submission(session, sub_payload)
        results.append(resolved)
        status = resolved["status"]
        if status == "CREATED":
            created_count += 1
        elif status in ("UPDATED_CLIENT_WINS", "MERGED"):
            updated_count += 1
        elif status == "IGNORED_SERVER_WINS":
            ignored_count += 1

    # Log bulk sync to audit trail
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="EPRO_BULK_SYNC",
        details=f"Processed bulk ePRO sync containing {len(payload.submissions)} items. Created: {created_count}, Reconciled/Updated: {updated_count}, Ignored: {ignored_count}.",
    )

    return {
        "status": "success",
        "processed_count": len(payload.submissions),
        "created_count": created_count,
        "updated_count": updated_count,
        "ignored_count": ignored_count,
        "results": results,
    }


# Instrument and SubjectAssignment Pydantic Schemas
class InstrumentCreate(BaseModel):
    name: str = Field(..., description="The name of the questionnaire/diary")
    description: Optional[str] = Field(None, description="Optional description")
    items: Dict[str, Any] = Field(..., description="Items/questions")
    response_types: Dict[str, Any] = Field(
        ..., description="Response types and options"
    )
    scoring_metadata: Dict[str, Any] = Field(..., description="Scoring metadata")
    reason_for_change: str = Field(
        ..., description="21 CFR Part 11 compliant reason for change"
    )


class InstrumentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    items: Dict[str, Any]
    response_types: Dict[str, Any]
    scoring_metadata: Dict[str, Any]
    created_at: datetime
    created_by: str
    reason_for_change: str
    version_index: int


class SubjectAssignmentCreate(BaseModel):
    subject_id: str = Field(..., description="Unique subject identifier")
    instrument_id: str = Field(..., description="ID of the Instrument to assign")
    start_date: datetime = Field(..., description="Start of the due/recurrence window")
    end_date: datetime = Field(..., description="End of the due/recurrence window")
    recurrence_pattern: Optional[str] = Field(None, description="E.g., DAILY, WEEKLY")
    due_at: Optional[datetime] = Field(
        None, description="Optional specific due date/time"
    )
    reason_for_change: str = Field(
        ..., description="21 CFR Part 11 compliant reason for change"
    )


class SubjectAssignmentResponse(BaseModel):
    id: str
    subject_id: str
    instrument_id: str
    start_date: datetime
    end_date: datetime
    recurrence_pattern: Optional[str]
    due_at: Optional[datetime]
    created_at: datetime
    created_by: str
    reason_for_change: str
    version_index: int


@app.post(
    "/api/v1/interop/instruments", response_model=InstrumentResponse, status_code=201
)
async def create_instrument(
    request: Request,
    payload: InstrumentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> InstrumentResponse:
    """
    Author a new eCOA questionnaire/diary definition.
    Enforces staff role authentication and Part 11 auditing.
    """
    require_staff_role(request)
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", payload.reason_for_change)

    instrument = Instrument(
        name=payload.name,
        description=payload.description,
        items=payload.items,
        response_types=payload.response_types,
        scoring_metadata=payload.scoring_metadata,
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(instrument)
    await session.flush()

    # Log action to immutable audit trail
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_INSTRUMENT",
        details=f"Created instrument '{payload.name}' with ID '{instrument.id}'.",
    )

    return instrument


@app.post(
    "/api/v1/interop/assignments",
    response_model=SubjectAssignmentResponse,
    status_code=201,
)
async def create_subject_assignment(
    request: Request,
    payload: SubjectAssignmentCreate,
    session: AsyncSession = Depends(get_db_session),
) -> SubjectAssignmentResponse:
    """
    Assign an eCOA instrument to a subject with due/recurrence window data.
    Enforces staff role authorization, validates instrument reference, and logs audit fields.
    """
    require_staff_role(request)
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", payload.reason_for_change)

    # Validate that instrument exists
    stmt = select(Instrument).where(Instrument.id == payload.instrument_id)
    result = await session.execute(stmt)
    instrument = result.scalars().first()
    if not instrument:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument with ID '{payload.instrument_id}' not found.",
        )

    # Validate start_date <= end_date
    if payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=400,
            detail="Assignment start_date cannot be after end_date.",
        )

    assignment = SubjectAssignment(
        subject_id=payload.subject_id,
        instrument_id=payload.instrument_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        recurrence_pattern=payload.recurrence_pattern,
        due_at=payload.due_at,
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(assignment)
    await session.flush()

    # Log action to immutable audit trail
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_ASSIGNMENT",
        details=f"Assigned instrument '{instrument.name}' (ID: '{instrument.id}') to subject '{payload.subject_id}'.",
    )

    return assignment


@app.get("/api/v1/interop/instruments/{id}", response_model=InstrumentResponse)
async def get_instrument(
    request: Request,
    id: str,
    session: AsyncSession = Depends(get_db_session),
) -> InstrumentResponse:
    """
    Retrieve an Instrument definition by ID.
    """
    stmt = select(Instrument).where(Instrument.id == id)
    result = await session.execute(stmt)
    instrument = result.scalars().first()
    if not instrument:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument with ID '{id}' not found.",
        )
    return instrument


@app.get(
    "/api/v1/interop/assignments/subject/{subject_id}",
    response_model=List[SubjectAssignmentResponse],
)
async def get_subject_assignments(
    request: Request,
    subject_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> List[SubjectAssignmentResponse]:
    """
    Retrieve all assignments for a given subject.
    Enforces subject-scoped identity boundary (Subject can only view their own assignments).
    """
    verify_subject_identity(request, subject_id)
    stmt = select(SubjectAssignment).where(SubjectAssignment.subject_id == subject_id)
    result = await session.execute(stmt)
    assignments = result.scalars().all()
    return list(assignments)
