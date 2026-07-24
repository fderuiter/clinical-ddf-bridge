import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ctms.database import db_manager
from apps.ctms.models import (
    Base,
    CTMSAuditLog,
    CTMSStudy,
    GeneratedLetter,
    MonitoringVisit,
    MonitoringVisitFinding,
    write_audit_log,
)
from apps.ctms.rendering import render_confirmation_letter, render_follow_up_letter
from packages.security.middleware import GatewayAuthMiddleware

DATABASE_URL = os.getenv("CTMS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle the lifespan events for the CTMS application.

    Initializes the database session manager on startup and securely
    cleans up connections on shutdown. Creates all tables if sqlite is used.
    """
    db_manager.init_db(DATABASE_URL)

    # Automatically create tables for sqlite in-memory/file databases
    if DATABASE_URL.startswith("sqlite"):
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await db_manager.close()


app = FastAPI(
    title="Cadence Clinical - CTMS",
    version="0.1.0",
    lifespan=lifespan,
)

# Enforce secure gateway authentication middleware
app.add_middleware(GatewayAuthMiddleware)


# Dependable to obtain database session
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


# Helper to check roles case-insensitively
def check_roles(roles_str: str, allowed_roles: List[str]) -> None:
    roles_list = [r.strip().lower() for r in roles_str.split(",") if r.strip()]
    if not any(r in allowed_roles for r in roles_list):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Access denied for roles: {roles_str}.",
        )


# Pydantic models for CTMS Study
class CTMSStudyCreate(BaseModel):
    study_id: str = Field(..., description="Unique clinical study ID")
    name: str = Field(..., description="Descriptive name of the clinical study")
    status: Optional[str] = Field("ACTIVE", description="Initial status of the study")


class CTMSStudyResponse(BaseModel):
    id: str
    study_id: str
    name: str
    status: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class CTMSAuditLogResponse(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_role: str
    action: str
    details: str


# Pydantic models for CTMS Monitoring Visits
class MonitoringVisitCreate(BaseModel):
    study_id: str = Field(..., description="Study ID associated with the visit")
    site_id: str = Field(..., description="Site ID where the monitoring visit occurs")
    cra_id: str = Field(..., description="CRA performing the monitoring visit")
    visit_type: str = Field(
        ..., description="Type of monitoring visit (e.g. SIV, IMV, COV)"
    )
    scheduled_date: datetime = Field(
        ..., description="Scheduled date/time of the visit"
    )


class FindingCreate(BaseModel):
    text: str = Field(..., description="The observation or action item text")
    severity: str = Field(..., description="Finding severity (MINOR, MAJOR, CRITICAL)")
    resolution_status: Optional[str] = Field("OPEN", description="Resolution status")


class MonitoringVisitComplete(BaseModel):
    actual_date: datetime = Field(
        ..., description="Actual date/time when the visit was conducted"
    )
    findings: List[FindingCreate] = Field(
        default=[], description="List of recorded findings"
    )


class MonitoringVisitResponse(BaseModel):
    id: str
    study_id: str
    site_id: str
    cra_id: str
    visit_type: str
    scheduled_date: str
    actual_date: Optional[str]
    status: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class MonitoringVisitFindingResponse(BaseModel):
    id: str
    visit_id: str
    text: str
    severity: str
    resolution_status: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class GeneratedLetterResponse(BaseModel):
    id: str
    visit_id: str
    letter_type: str
    rendered_content: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Service health check endpoint.
    """
    return {"status": "ok", "service": "ctms"}


@app.post("/api/v1/ctms/studies", response_model=CTMSStudyResponse, status_code=201)
async def create_study(
    request: Request,
    payload: CTMSStudyCreate,
    session: AsyncSession = Depends(get_db_session),
) -> CTMSStudyResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    # RBAC: Only write-privileged roles can manage CTMS studies
    check_roles(
        user_roles,
        ["monitor", "grants manager", "cra", "sponsor admin", "admin", "system"],
    )

    study = CTMSStudy(
        study_id=payload.study_id,
        name=payload.name,
        status=payload.status or "ACTIVE",
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(study)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_STUDY",
        details=f"Created CTMS study '{payload.study_id}' with name '{payload.name}'. Reason: {change_reason}",
    )

    return CTMSStudyResponse(
        id=study.id,
        study_id=study.study_id,
        name=study.name,
        status=study.status,
        created_at=study.created_at.isoformat(),
        created_by=study.created_by,
        reason_for_change=study.reason_for_change,
        version_index=study.version_index,
    )


@app.get("/api/v1/ctms/studies", response_model=List[CTMSStudyResponse])
async def list_studies(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> List[CTMSStudyResponse]:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        [
            "monitor",
            "grants manager",
            "cra",
            "site investigator",
            "sponsor admin",
            "admin",
            "auditor",
            "anonymous",
            "system",
        ],
    )

    stmt = select(CTMSStudy).order_by(CTMSStudy.created_at.desc())
    result = await session.execute(stmt)
    studies = result.scalars().all()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="LIST_STUDIES",
        details="Listed all CTMS studies.",
    )

    return [
        CTMSStudyResponse(
            id=s.id,
            study_id=s.study_id,
            name=s.name,
            status=s.status,
            created_at=s.created_at.isoformat(),
            created_by=s.created_by,
            reason_for_change=s.reason_for_change,
            version_index=s.version_index,
        )
        for s in studies
    ]


@app.get("/api/v1/ctms/audit-logs", response_model=List[CTMSAuditLogResponse])
async def get_audit_trail(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> List[CTMSAuditLogResponse]:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["auditor", "sponsor admin", "admin", "monitor", "grants manager", "system"],
    )

    # Log view action first
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="VIEW_AUDIT_LOGS",
        details="Accessed CTMS audit logs.",
    )

    stmt = select(CTMSAuditLog).order_by(CTMSAuditLog.timestamp.desc())
    result = await session.execute(stmt)
    logs = result.scalars().all()

    return [
        CTMSAuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            user_role=log.user_role,
            action=log.action,
            details=log.details,
        )
        for log in logs
    ]


# --- Monitoring Visits Endpoints ---


@app.post(
    "/api/v1/ctms/monitoring-visits",
    response_model=MonitoringVisitResponse,
    status_code=201,
)
async def schedule_monitoring_visit(
    request: Request,
    payload: MonitoringVisitCreate,
    session: AsyncSession = Depends(get_db_session),
) -> MonitoringVisitResponse:
    """
    Schedules a clinical site monitoring visit and automatically generates/persists
    a corresponding confirmation letter.
    """
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    # RBAC: Only CRA (or admin/sponsor admin/system) can schedule/create visits
    check_roles(
        user_roles,
        ["cra", "admin", "sponsor admin", "system"],
    )

    # 1. Persist the Monitoring Visit
    visit = MonitoringVisit(
        study_id=payload.study_id,
        site_id=payload.site_id,
        cra_id=payload.cra_id,
        visit_type=payload.visit_type,
        scheduled_date=payload.scheduled_date,
        status="SCHEDULED",
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(visit)
    await session.flush()

    # 2. Render and Persist the Confirmation Letter
    rendered_content = render_confirmation_letter(
        study_id=visit.study_id,
        site_id=visit.site_id,
        cra_id=visit.cra_id,
        visit_type=visit.visit_type,
        scheduled_date=visit.scheduled_date,
        created_at=visit.created_at,
    )

    letter = GeneratedLetter(
        visit_id=visit.id,
        letter_type="CONFIRMATION",
        rendered_content=rendered_content,
        created_by=user_id,
        reason_for_change="Automated confirmation letter on visit scheduling",
        version_index=1,
    )
    session.add(letter)
    await session.flush()

    # 3. Write state-changing CTMS audit logs
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_VISIT",
        details=f"Scheduled monitoring visit '{visit.id}' of type '{visit.visit_type}' for study '{visit.study_id}' at site '{visit.site_id}'.",
    )
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="GENERATE_LETTER",
        details=f"Generated confirmation letter for visit '{visit.id}'.",
    )

    return MonitoringVisitResponse(
        id=visit.id,
        study_id=visit.study_id,
        site_id=visit.site_id,
        cra_id=visit.cra_id,
        visit_type=visit.visit_type,
        scheduled_date=visit.scheduled_date.isoformat(),
        actual_date=None,
        status=visit.status,
        created_at=visit.created_at.isoformat(),
        created_by=visit.created_by,
        reason_for_change=visit.reason_for_change,
        version_index=visit.version_index,
    )


@app.post(
    "/api/v1/ctms/monitoring-visits/{visit_id}/complete",
    response_model=MonitoringVisitResponse,
)
async def complete_monitoring_visit(
    visit_id: str,
    request: Request,
    payload: MonitoringVisitComplete,
    session: AsyncSession = Depends(get_db_session),
) -> MonitoringVisitResponse:
    """
    Completes a scheduled monitoring visit, records findings and action items,
    and automatically generates/persists a follow-up letter.
    """
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    # RBAC: Only CRA (or admin/sponsor admin/system) can record/complete visit content
    check_roles(
        user_roles,
        ["cra", "admin", "sponsor admin", "system"],
    )

    # 1. Retrieve the scheduled visit
    stmt = select(MonitoringVisit).where(MonitoringVisit.id == visit_id)
    result = await session.execute(stmt)
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(status_code=404, detail="Monitoring visit not found")

    if visit.status != "SCHEDULED":
        raise HTTPException(
            status_code=400,
            detail=f"Monitoring visit cannot be completed from state: {visit.status}",
        )

    # 2. Complete the visit
    visit.status = "COMPLETED"
    visit.actual_date = payload.actual_date
    visit.version_index += 1
    visit.reason_for_change = change_reason
    session.add(visit)

    # 3. Create and persist findings
    finding_objs = []
    for f in payload.findings:
        if f.severity.upper() not in ("MINOR", "MAJOR", "CRITICAL"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid finding severity: {f.severity}",
            )
        finding = MonitoringVisitFinding(
            visit_id=visit.id,
            text=f.text,
            severity=f.severity.upper(),
            resolution_status=f.resolution_status or "OPEN",
            created_by=user_id,
            reason_for_change=change_reason,
            version_index=1,
        )
        session.add(finding)
        finding_objs.append(finding)

    await session.flush()

    # 4. Render and persist the Follow-up Letter
    findings_list = [
        {
            "text": f.text,
            "severity": f.severity,
            "resolution_status": f.resolution_status,
        }
        for f in finding_objs
    ]

    rendered_content = render_follow_up_letter(
        study_id=visit.study_id,
        site_id=visit.site_id,
        cra_id=visit.cra_id,
        visit_type=visit.visit_type,
        actual_date=visit.actual_date,
        findings=findings_list,
        created_at=datetime.utcnow(),
    )

    letter = GeneratedLetter(
        visit_id=visit.id,
        letter_type="FOLLOW_UP",
        rendered_content=rendered_content,
        created_by=user_id,
        reason_for_change="Automated follow-up letter on visit completion",
        version_index=1,
    )
    session.add(letter)
    await session.flush()

    # 5. Write state-changing CTMS audit logs
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="COMPLETE_VISIT",
        details=f"Completed monitoring visit '{visit.id}'. Actual date: {visit.actual_date.isoformat()}.",
    )
    for f_obj in finding_objs:
        await write_audit_log(
            session=session,
            user_id=user_id,
            user_role=user_roles,
            action="CREATE_FINDING",
            details=f"Recorded {f_obj.severity} finding for visit '{visit.id}': {f_obj.text}",
        )
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="GENERATE_LETTER",
        details=f"Generated follow-up letter for visit '{visit.id}'.",
    )

    return MonitoringVisitResponse(
        id=visit.id,
        study_id=visit.study_id,
        site_id=visit.site_id,
        cra_id=visit.cra_id,
        visit_type=visit.visit_type,
        scheduled_date=visit.scheduled_date.isoformat(),
        actual_date=visit.actual_date.isoformat() if visit.actual_date else None,
        status=visit.status,
        created_at=visit.created_at.isoformat(),
        created_by=visit.created_by,
        reason_for_change=visit.reason_for_change,
        version_index=visit.version_index,
    )


@app.get(
    "/api/v1/ctms/monitoring-visits",
    response_model=List[MonitoringVisitResponse],
)
async def list_monitoring_visits(
    request: Request,
    study_id: Optional[str] = None,
    site_id: Optional[str] = None,
    cra_id: Optional[str] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> List[MonitoringVisitResponse]:
    """
    Lists and filters clinical trial site monitoring visits.
    """
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    # RBAC: Allow CRA, Monitor, Auditor, Admin, Sponsor Admin, System to list visits
    check_roles(
        user_roles,
        ["monitor", "cra", "admin", "sponsor admin", "auditor", "system"],
    )

    stmt = select(MonitoringVisit)
    if study_id:
        stmt = stmt.where(MonitoringVisit.study_id == study_id)
    if site_id:
        stmt = stmt.where(MonitoringVisit.site_id == site_id)
    if cra_id:
        stmt = stmt.where(MonitoringVisit.cra_id == cra_id)
    if status:
        stmt = stmt.where(MonitoringVisit.status == status)

    stmt = stmt.order_by(MonitoringVisit.scheduled_date.desc())
    result = await session.execute(stmt)
    visits = result.scalars().all()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="LIST_VISITS",
        details="Listed CTMS monitoring visits.",
    )

    return [
        MonitoringVisitResponse(
            id=v.id,
            study_id=v.study_id,
            site_id=v.site_id,
            cra_id=v.cra_id,
            visit_type=v.visit_type,
            scheduled_date=v.scheduled_date.isoformat(),
            actual_date=v.actual_date.isoformat() if v.actual_date else None,
            status=v.status,
            created_at=v.created_at.isoformat(),
            created_by=v.created_by,
            reason_for_change=v.reason_for_change,
            version_index=v.version_index,
        )
        for v in visits
    ]


@app.get(
    "/api/v1/ctms/monitoring-visits/{visit_id}/letters",
    response_model=List[GeneratedLetterResponse],
)
async def get_monitoring_visit_letters(
    visit_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> List[GeneratedLetterResponse]:
    """
    Retrieves all generated letters associated with a specific monitoring visit.
    Guarantees no re-rendering of previously issued letters by returning stored content.
    """
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["monitor", "cra", "admin", "sponsor admin", "auditor", "system"],
    )

    stmt = select(GeneratedLetter).where(GeneratedLetter.visit_id == visit_id)
    result = await session.execute(stmt)
    letters = result.scalars().all()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="RETRIEVE_LETTERS",
        details=f"Retrieved letters for monitoring visit '{visit_id}'.",
    )

    return [
        GeneratedLetterResponse(
            id=let.id,
            visit_id=let.visit_id,
            letter_type=let.letter_type,
            rendered_content=let.rendered_content,
            created_at=let.created_at.isoformat(),
            created_by=let.created_by,
            reason_for_change=let.reason_for_change,
            version_index=let.version_index,
        )
        for let in letters
    ]


@app.get(
    "/api/v1/ctms/monitoring-visits/{visit_id}/letters/{letter_type}",
    response_model=GeneratedLetterResponse,
)
async def get_monitoring_visit_letter_by_type(
    visit_id: str,
    letter_type: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> GeneratedLetterResponse:
    """
    Retrieves a specific letter (e.g. CONFIRMATION or FOLLOW_UP) associated with a monitoring visit.
    Guarantees no re-rendering of previously issued letters by returning stored content.
    """
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["monitor", "cra", "admin", "sponsor admin", "auditor", "system"],
    )

    stmt = select(GeneratedLetter).where(
        GeneratedLetter.visit_id == visit_id,
        GeneratedLetter.letter_type == letter_type.upper(),
    )
    result = await session.execute(stmt)
    letter = result.scalars().first()

    if not letter:
        raise HTTPException(
            status_code=404,
            detail=f"Generated letter of type '{letter_type}' not found for visit '{visit_id}'",
        )

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="RETRIEVE_LETTER",
        details=f"Retrieved letter of type '{letter_type}' for monitoring visit '{visit_id}'.",
    )

    return GeneratedLetterResponse(
        id=letter.id,
        visit_id=letter.visit_id,
        letter_type=letter.letter_type,
        rendered_content=letter.rendered_content,
        created_at=letter.created_at.isoformat(),
        created_by=letter.created_by,
        reason_for_change=letter.reason_for_change,
        version_index=letter.version_index,
    )


@app.post(
    "/api/v1/ctms/monitoring-visits/{visit_id}/sign-off",
    response_model=MonitoringVisitResponse,
)
async def sign_off_monitoring_visit(
    visit_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> MonitoringVisitResponse:
    """
    Allows a clinical Monitor to perform a supervisory sign-off on a completed monitoring visit.
    """
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    # RBAC: Only supervisory roles (Monitor, Admin, Sponsor Admin, System) can perform sign-off
    check_roles(
        user_roles,
        ["monitor", "admin", "sponsor admin", "system"],
    )

    # 1. Retrieve the visit
    stmt = select(MonitoringVisit).where(MonitoringVisit.id == visit_id)
    result = await session.execute(stmt)
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(status_code=404, detail="Monitoring visit not found")

    if visit.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Only completed monitoring visits can be signed off.",
        )

    # 2. Update visit status to SIGNED_OFF
    visit.status = "SIGNED_OFF"
    visit.version_index += 1
    visit.reason_for_change = change_reason
    session.add(visit)
    await session.flush()

    # 3. Write state-changing CTMS audit log
    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="SIGN_OFF_VISIT",
        details=f"Monitor supervisory sign-off recorded for visit '{visit.id}'.",
    )

    return MonitoringVisitResponse(
        id=visit.id,
        study_id=visit.study_id,
        site_id=visit.site_id,
        cra_id=visit.cra_id,
        visit_type=visit.visit_type,
        scheduled_date=visit.scheduled_date.isoformat(),
        actual_date=visit.actual_date.isoformat() if visit.actual_date else None,
        status=visit.status,
        created_at=visit.created_at.isoformat(),
        created_by=visit.created_by,
        reason_for_change=visit.reason_for_change,
        version_index=visit.version_index,
    )
