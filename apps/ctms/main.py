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
    InvestigatorGrant,
    BudgetLineItem,
    PaymentMilestone,
    InvestigatorPayable,
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


# --- Financial Pydantic Models ---

class InvestigatorGrantCreate(BaseModel):
    investigator_id: str = Field(..., description="Investigator unique ID")
    site_id: str = Field(..., description="Site ID associated with the grant")
    study_id: str = Field(..., description="Study ID associated with the grant")
    total_budget: float = Field(..., description="Planned total budget for investigator grant")
    currency: Optional[str] = Field("USD", description="Currency of the budget")
    status: Optional[str] = Field("DRAFT", description="Status of the investigator grant")


class InvestigatorGrantUpdate(BaseModel):
    investigator_id: Optional[str] = None
    site_id: Optional[str] = None
    study_id: Optional[str] = None
    total_budget: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class InvestigatorGrantResponse(BaseModel):
    id: str
    investigator_id: str
    site_id: str
    study_id: str
    total_budget: float
    currency: str
    status: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class BudgetLineItemCreate(BaseModel):
    grant_id: str = Field(..., description="Grant ID associated with the budget item")
    category: str = Field(..., description="Budget category (e.g. Travel, Subject Fee)")
    planned_amount: float = Field(..., description="Planned amount for this category")
    actual_amount: Optional[float] = Field(0.0, description="Actual spent amount")


class BudgetLineItemUpdate(BaseModel):
    category: Optional[str] = None
    planned_amount: Optional[float] = None
    actual_amount: Optional[float] = None


class BudgetLineItemResponse(BaseModel):
    id: str
    grant_id: str
    category: str
    planned_amount: float
    actual_amount: float
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class PaymentMilestoneCreate(BaseModel):
    description: str = Field(..., description="Milestone description")
    trigger_type: str = Field(..., description="Trigger type (e.g. VISIT_COMPLETED, STUDY_APPROVED, MANUAL)")
    trigger_condition: Optional[str] = Field(None, description="Trigger condition argument (e.g. visit type 'IMV')")
    amount: float = Field(..., description="Milestone payout amount")


class PaymentMilestoneResponse(BaseModel):
    id: str
    grant_id: str
    description: str
    trigger_type: str
    trigger_condition: Optional[str]
    amount: float
    trigger_date: Optional[str]
    payment_status: str
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class InvestigatorPayableResponse(BaseModel):
    id: str
    milestone_id: str
    grant_id: str
    amount: float
    currency: str
    status: str
    payment_date: Optional[str]
    created_at: str
    created_by: str
    reason_for_change: str
    version_index: int


class MilestoneEvaluationResponse(BaseModel):
    triggered: bool
    message: str
    milestone: PaymentMilestoneResponse
    payable: Optional[InvestigatorPayableResponse] = None


class PaymentStatusResponse(BaseModel):
    grant_id: str
    milestones: List[PaymentMilestoneResponse]
    payables: List[InvestigatorPayableResponse]


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


# --- Financial Helper Functions & Endpoints ---

async def check_grant_locked(session: AsyncSession, grant_id: str) -> None:
    """
    Enforces the lock on an APPROVED investigator grant.
    """
    stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    res = await session.execute(stmt)
    grant = res.scalars().first()
    if not grant:
        raise HTTPException(status_code=404, detail="Investigator grant not found")
    if grant.status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Cannot modify or configure an approved investigator grant (locked)"
        )


async def evaluate_milestone_condition(
    session: AsyncSession,
    grant: InvestigatorGrant,
    milestone: PaymentMilestone
) -> bool:
    """
    Evaluates known milestone conditions. Returns True if triggered, False otherwise.
    """
    if milestone.trigger_type == "VISIT_COMPLETED":
        # Check if there's any completed/signed-off monitoring visit of the specified type
        # for the study_id and site_id of the grant.
        visit_type = milestone.trigger_condition
        stmt = select(MonitoringVisit).where(
            MonitoringVisit.study_id == grant.study_id,
            MonitoringVisit.site_id == grant.site_id,
            MonitoringVisit.visit_type == visit_type,
            MonitoringVisit.status.in_(["COMPLETED", "SIGNED_OFF"])
        )
        res = await session.execute(stmt)
        visit = res.scalars().first()
        return visit is not None

    elif milestone.trigger_type == "STUDY_APPROVED":
        # Check if study is active
        stmt = select(CTMSStudy).where(
            CTMSStudy.study_id == grant.study_id,
            CTMSStudy.status == "ACTIVE"
        )
        res = await session.execute(stmt)
        study = res.scalars().first()
        return study is not None

    elif milestone.trigger_type == "MANUAL":
        # Manual trigger can be evaluated as True if it's evaluated/triggered explicitly
        return True

    return False


@app.post(
    "/api/v1/ctms/grants",
    response_model=InvestigatorGrantResponse,
    status_code=201,
)
async def create_investigator_grant(
    request: Request,
    payload: InvestigatorGrantCreate,
    session: AsyncSession = Depends(get_db_session),
) -> InvestigatorGrantResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    grant = InvestigatorGrant(
        investigator_id=payload.investigator_id,
        site_id=payload.site_id,
        study_id=payload.study_id,
        total_budget=payload.total_budget,
        currency=payload.currency or "USD",
        status=payload.status or "DRAFT",
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(grant)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_GRANT",
        details=f"Created investigator grant '{grant.id}' for study '{payload.study_id}', site '{payload.site_id}'. Reason: {change_reason}",
    )

    return InvestigatorGrantResponse(
        id=grant.id,
        investigator_id=grant.investigator_id,
        site_id=grant.site_id,
        study_id=grant.study_id,
        total_budget=grant.total_budget,
        currency=grant.currency,
        status=grant.status,
        created_at=grant.created_at.isoformat(),
        created_by=grant.created_by,
        reason_for_change=grant.reason_for_change,
        version_index=grant.version_index,
    )


@app.get(
    "/api/v1/ctms/grants",
    response_model=List[InvestigatorGrantResponse],
)
async def list_investigator_grants(
    request: Request,
    study_id: Optional[str] = None,
    site_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> List[InvestigatorGrantResponse]:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["grants manager", "sponsor admin", "monitor", "cra", "auditor", "admin", "system"],
    )

    stmt = select(InvestigatorGrant)
    if study_id:
        stmt = stmt.where(InvestigatorGrant.study_id == study_id)
    if site_id:
        stmt = stmt.where(InvestigatorGrant.site_id == site_id)

    stmt = stmt.order_by(InvestigatorGrant.created_at.desc())
    result = await session.execute(stmt)
    grants = result.scalars().all()

    return [
        InvestigatorGrantResponse(
            id=g.id,
            investigator_id=g.investigator_id,
            site_id=g.site_id,
            study_id=g.study_id,
            total_budget=g.total_budget,
            currency=g.currency,
            status=g.status,
            created_at=g.created_at.isoformat(),
            created_by=g.created_by,
            reason_for_change=g.reason_for_change,
            version_index=g.version_index,
        )
        for g in grants
    ]


@app.get(
    "/api/v1/ctms/grants/{grant_id}",
    response_model=InvestigatorGrantResponse,
)
async def get_investigator_grant(
    grant_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> InvestigatorGrantResponse:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["grants manager", "sponsor admin", "monitor", "cra", "auditor", "admin", "system"],
    )

    stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    result = await session.execute(stmt)
    grant = result.scalars().first()
    if not grant:
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    return InvestigatorGrantResponse(
        id=grant.id,
        investigator_id=grant.investigator_id,
        site_id=grant.site_id,
        study_id=grant.study_id,
        total_budget=grant.total_budget,
        currency=grant.currency,
        status=grant.status,
        created_at=grant.created_at.isoformat(),
        created_by=grant.created_by,
        reason_for_change=grant.reason_for_change,
        version_index=grant.version_index,
    )


@app.put(
    "/api/v1/ctms/grants/{grant_id}",
    response_model=InvestigatorGrantResponse,
)
async def update_investigator_grant(
    grant_id: str,
    request: Request,
    payload: InvestigatorGrantUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> InvestigatorGrantResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    result = await session.execute(stmt)
    grant = result.scalars().first()
    if not grant:
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    if grant.status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Cannot modify an approved investigator grant (locked)"
        )

    if payload.investigator_id is not None:
        grant.investigator_id = payload.investigator_id
    if payload.site_id is not None:
        grant.site_id = payload.site_id
    if payload.study_id is not None:
        grant.study_id = payload.study_id
    if payload.total_budget is not None:
        grant.total_budget = payload.total_budget
    if payload.currency is not None:
        grant.currency = payload.currency
    if payload.status is not None:
        grant.status = payload.status

    grant.version_index += 1
    grant.reason_for_change = change_reason
    session.add(grant)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="UPDATE_GRANT",
        details=f"Updated investigator grant '{grant.id}' to version {grant.version_index}. Reason: {change_reason}",
    )

    return InvestigatorGrantResponse(
        id=grant.id,
        investigator_id=grant.investigator_id,
        site_id=grant.site_id,
        study_id=grant.study_id,
        total_budget=grant.total_budget,
        currency=grant.currency,
        status=grant.status,
        created_at=grant.created_at.isoformat(),
        created_by=grant.created_by,
        reason_for_change=grant.reason_for_change,
        version_index=grant.version_index,
    )


@app.post(
    "/api/v1/ctms/budgets/line-items",
    response_model=BudgetLineItemResponse,
    status_code=201,
)
async def create_budget_line_item(
    request: Request,
    payload: BudgetLineItemCreate,
    session: AsyncSession = Depends(get_db_session),
) -> BudgetLineItemResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    await check_grant_locked(session, payload.grant_id)

    item = BudgetLineItem(
        grant_id=payload.grant_id,
        category=payload.category,
        planned_amount=payload.planned_amount,
        actual_amount=payload.actual_amount or 0.0,
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(item)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_BUDGET_ITEM",
        details=f"Created budget line item '{item.id}' under grant '{payload.grant_id}' in category '{payload.category}'. Reason: {change_reason}",
    )

    return BudgetLineItemResponse(
        id=item.id,
        grant_id=item.grant_id,
        category=item.category,
        planned_amount=item.planned_amount,
        actual_amount=item.actual_amount,
        created_at=item.created_at.isoformat(),
        created_by=item.created_by,
        reason_for_change=item.reason_for_change,
        version_index=item.version_index,
    )


@app.get(
    "/api/v1/ctms/budgets/line-items",
    response_model=List[BudgetLineItemResponse],
)
async def list_budget_line_items(
    request: Request,
    grant_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> List[BudgetLineItemResponse]:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["grants manager", "sponsor admin", "monitor", "cra", "auditor", "admin", "system"],
    )

    stmt = select(BudgetLineItem)
    if grant_id:
        stmt = stmt.where(BudgetLineItem.grant_id == grant_id)

    stmt = stmt.order_by(BudgetLineItem.created_at.desc())
    result = await session.execute(stmt)
    items = result.scalars().all()

    return [
        BudgetLineItemResponse(
            id=item.id,
            grant_id=item.grant_id,
            category=item.category,
            planned_amount=item.planned_amount,
            actual_amount=item.actual_amount,
            created_at=item.created_at.isoformat(),
            created_by=item.created_by,
            reason_for_change=item.reason_for_change,
            version_index=item.version_index,
        )
        for item in items
    ]


@app.put(
    "/api/v1/ctms/budgets/line-items/{item_id}",
    response_model=BudgetLineItemResponse,
)
async def update_budget_line_item(
    item_id: str,
    request: Request,
    payload: BudgetLineItemUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> BudgetLineItemResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    stmt = select(BudgetLineItem).where(BudgetLineItem.id == item_id)
    result = await session.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Budget line item not found")

    await check_grant_locked(session, item.grant_id)

    if payload.category is not None:
        item.category = payload.category
    if payload.planned_amount is not None:
        item.planned_amount = payload.planned_amount
    if payload.actual_amount is not None:
        item.actual_amount = payload.actual_amount

    item.version_index += 1
    item.reason_for_change = change_reason
    session.add(item)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="UPDATE_BUDGET_ITEM",
        details=f"Updated budget line item '{item.id}' to version {item.version_index}. Reason: {change_reason}",
    )

    return BudgetLineItemResponse(
        id=item.id,
        grant_id=item.grant_id,
        category=item.category,
        planned_amount=item.planned_amount,
        actual_amount=item.actual_amount,
        created_at=item.created_at.isoformat(),
        created_by=item.created_by,
        reason_for_change=item.reason_for_change,
        version_index=item.version_index,
    )


@app.post(
    "/api/v1/ctms/grants/{grant_id}/milestones",
    response_model=PaymentMilestoneResponse,
    status_code=201,
)
async def create_payment_milestone(
    grant_id: str,
    request: Request,
    payload: PaymentMilestoneCreate,
    session: AsyncSession = Depends(get_db_session),
) -> PaymentMilestoneResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    await check_grant_locked(session, grant_id)

    milestone = PaymentMilestone(
        grant_id=grant_id,
        description=payload.description,
        trigger_type=payload.trigger_type,
        trigger_condition=payload.trigger_condition,
        amount=payload.amount,
        payment_status="PENDING",
        created_by=user_id,
        reason_for_change=change_reason,
        version_index=1,
    )
    session.add(milestone)
    await session.flush()

    await write_audit_log(
        session=session,
        user_id=user_id,
        user_role=user_roles,
        action="CREATE_MILESTONE",
        details=f"Created payment milestone '{milestone.id}' under grant '{grant_id}'. Reason: {change_reason}",
    )

    return PaymentMilestoneResponse(
        id=milestone.id,
        grant_id=milestone.grant_id,
        description=milestone.description,
        trigger_type=milestone.trigger_type,
        trigger_condition=milestone.trigger_condition,
        amount=milestone.amount,
        trigger_date=None,
        payment_status=milestone.payment_status,
        created_at=milestone.created_at.isoformat(),
        created_by=milestone.created_by,
        reason_for_change=milestone.reason_for_change,
        version_index=milestone.version_index,
    )


@app.get(
    "/api/v1/ctms/grants/{grant_id}/milestones",
    response_model=List[PaymentMilestoneResponse],
)
async def list_payment_milestones(
    grant_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> List[PaymentMilestoneResponse]:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["grants manager", "sponsor admin", "monitor", "cra", "auditor", "admin", "system"],
    )

    stmt_grant = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    res_grant = await session.execute(stmt_grant)
    if not res_grant.scalars().first():
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    stmt = select(PaymentMilestone).where(PaymentMilestone.grant_id == grant_id)
    stmt = stmt.order_by(PaymentMilestone.created_at.desc())
    result = await session.execute(stmt)
    milestones = result.scalars().all()

    return [
        PaymentMilestoneResponse(
            id=milestone.id,
            grant_id=milestone.grant_id,
            description=milestone.description,
            trigger_type=milestone.trigger_type,
            trigger_condition=milestone.trigger_condition,
            amount=milestone.amount,
            trigger_date=milestone.trigger_date.isoformat() if milestone.trigger_date else None,
            payment_status=milestone.payment_status,
            created_at=milestone.created_at.isoformat(),
            created_by=milestone.created_by,
            reason_for_change=milestone.reason_for_change,
            version_index=milestone.version_index,
        )
        for milestone in milestones
    ]


@app.post(
    "/api/v1/ctms/grants/{grant_id}/milestones/{milestone_id}/evaluate",
    response_model=MilestoneEvaluationResponse,
)
async def evaluate_milestone(
    grant_id: str,
    milestone_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> MilestoneEvaluationResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    grant_stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    grant_res = await session.execute(grant_stmt)
    grant = grant_res.scalars().first()
    if not grant:
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    mil_stmt = select(PaymentMilestone).where(
        PaymentMilestone.id == milestone_id,
        PaymentMilestone.grant_id == grant_id
    )
    mil_res = await session.execute(mil_stmt)
    milestone = mil_res.scalars().first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Payment milestone not found")

    if milestone.payment_status in ("TRIGGERED", "PAID"):
        pay_stmt = select(InvestigatorPayable).where(InvestigatorPayable.milestone_id == milestone.id)
        pay_res = await session.execute(pay_stmt)
        payable = pay_res.scalars().first()
        return MilestoneEvaluationResponse(
            triggered=True,
            message="Milestone has already been triggered.",
            milestone=PaymentMilestoneResponse(
                id=milestone.id,
                grant_id=milestone.grant_id,
                description=milestone.description,
                trigger_type=milestone.trigger_type,
                trigger_condition=milestone.trigger_condition,
                amount=milestone.amount,
                trigger_date=milestone.trigger_date.isoformat() if milestone.trigger_date else None,
                payment_status=milestone.payment_status,
                created_at=milestone.created_at.isoformat(),
                created_by=milestone.created_by,
                reason_for_change=milestone.reason_for_change,
                version_index=milestone.version_index,
            ),
            payable=InvestigatorPayableResponse(
                id=payable.id,
                milestone_id=payable.milestone_id,
                grant_id=payable.grant_id,
                amount=payable.amount,
                currency=payable.currency,
                status=payable.status,
                payment_date=payable.payment_date.isoformat() if payable.payment_date else None,
                created_at=payable.created_at.isoformat(),
                created_by=payable.created_by,
                reason_for_change=payable.reason_for_change,
                version_index=payable.version_index,
            ) if payable else None
        )

    is_triggered = await evaluate_milestone_condition(session, grant, milestone)

    if is_triggered:
        now = datetime.now()
        milestone.payment_status = "TRIGGERED"
        milestone.trigger_date = now
        milestone.version_index += 1
        milestone.reason_for_change = change_reason
        session.add(milestone)

        payable = InvestigatorPayable(
            milestone_id=milestone.id,
            grant_id=grant.id,
            amount=milestone.amount,
            currency=grant.currency,
            status="UNPAID",
            created_by=user_id,
            reason_for_change=f"Automated payable generation for milestone trigger: {milestone.description}",
            version_index=1,
        )
        session.add(payable)
        await session.flush()

        await write_audit_log(
            session=session,
            user_id=user_id,
            user_role=user_roles,
            action="TRIGGER_MILESTONE",
            details=f"Milestone '{milestone.id}' triggered. Created payable '{payable.id}'. Reason: {change_reason}",
        )

        return MilestoneEvaluationResponse(
            triggered=True,
            message="Milestone successfully triggered and payable record created.",
            milestone=PaymentMilestoneResponse(
                id=milestone.id,
                grant_id=milestone.grant_id,
                description=milestone.description,
                trigger_type=milestone.trigger_type,
                trigger_condition=milestone.trigger_condition,
                amount=milestone.amount,
                trigger_date=milestone.trigger_date.isoformat(),
                payment_status=milestone.payment_status,
                created_at=milestone.created_at.isoformat(),
                created_by=milestone.created_by,
                reason_for_change=milestone.reason_for_change,
                version_index=milestone.version_index,
            ),
            payable=InvestigatorPayableResponse(
                id=payable.id,
                milestone_id=payable.milestone_id,
                grant_id=payable.grant_id,
                amount=payable.amount,
                currency=payable.currency,
                status=payable.status,
                payment_date=None,
                created_at=payable.created_at.isoformat(),
                created_by=payable.created_by,
                reason_for_change=payable.reason_for_change,
                version_index=payable.version_index,
            )
        )
    else:
        return MilestoneEvaluationResponse(
            triggered=False,
            message="Milestone trigger conditions not met.",
            milestone=PaymentMilestoneResponse(
                id=milestone.id,
                grant_id=milestone.grant_id,
                description=milestone.description,
                trigger_type=milestone.trigger_type,
                trigger_condition=milestone.trigger_condition,
                amount=milestone.amount,
                trigger_date=None,
                payment_status=milestone.payment_status,
                created_at=milestone.created_at.isoformat(),
                created_by=milestone.created_by,
                reason_for_change=milestone.reason_for_change,
                version_index=milestone.version_index,
            )
        )


@app.get(
    "/api/v1/ctms/grants/{grant_id}/payments",
    response_model=PaymentStatusResponse,
)
async def get_payment_status(
    grant_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PaymentStatusResponse:
    user_id = getattr(request.state, "user_id", "anonymous")
    user_roles = getattr(request.state, "roles", "anonymous")

    check_roles(
        user_roles,
        ["grants manager", "sponsor admin", "monitor", "cra", "auditor", "admin", "system"],
    )

    grant_stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    grant_res = await session.execute(grant_stmt)
    if not grant_res.scalars().first():
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    mil_stmt = select(PaymentMilestone).where(PaymentMilestone.grant_id == grant_id)
    mil_res = await session.execute(mil_stmt)
    milestones = mil_res.scalars().all()

    pay_stmt = select(InvestigatorPayable).where(InvestigatorPayable.grant_id == grant_id)
    pay_res = await session.execute(pay_stmt)
    payables = pay_res.scalars().all()

    return PaymentStatusResponse(
        grant_id=grant_id,
        milestones=[
            PaymentMilestoneResponse(
                id=m.id,
                grant_id=m.grant_id,
                description=m.description,
                trigger_type=m.trigger_type,
                trigger_condition=m.trigger_condition,
                amount=m.amount,
                trigger_date=m.trigger_date.isoformat() if m.trigger_date else None,
                payment_status=m.payment_status,
                created_at=m.created_at.isoformat(),
                created_by=m.created_by,
                reason_for_change=m.reason_for_change,
                version_index=m.version_index,
            )
            for m in milestones
        ],
        payables=[
            InvestigatorPayableResponse(
                id=p.id,
                milestone_id=p.milestone_id,
                grant_id=p.grant_id,
                amount=p.amount,
                currency=p.currency,
                status=p.status,
                payment_date=p.payment_date.isoformat() if p.payment_date else None,
                created_at=p.created_at.isoformat(),
                created_by=p.created_by,
                reason_for_change=p.reason_for_change,
                version_index=p.version_index,
            )
            for p in payables
        ]
    )


@app.post(
    "/api/v1/ctms/grants/{grant_id}/payables/{payable_id}/pay",
    response_model=InvestigatorPayableResponse,
)
async def pay_payable(
    grant_id: str,
    payable_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> InvestigatorPayableResponse:
    user_id = getattr(request.state, "user_id", "system")
    user_roles = getattr(request.state, "roles", "system")
    change_reason = getattr(request.state, "change_reason", "system_operation")

    check_roles(user_roles, ["grants manager", "sponsor admin", "system"])

    grant_stmt = select(InvestigatorGrant).where(InvestigatorGrant.id == grant_id)
    grant_res = await session.execute(grant_stmt)
    grant = grant_res.scalars().first()
    if not grant:
        raise HTTPException(status_code=404, detail="Investigator grant not found")

    pay_stmt = select(InvestigatorPayable).where(
        InvestigatorPayable.id == payable_id,
        InvestigatorPayable.grant_id == grant_id
    )
    pay_res = await session.execute(pay_stmt)
    payable = pay_res.scalars().first()
    if not payable:
        raise HTTPException(status_code=404, detail="Investigator payable not found")

    if payable.status == "UNPAID":
        now = datetime.now()
        payable.status = "PAID"
        payable.payment_date = now
        payable.version_index += 1
        payable.reason_for_change = change_reason
        session.add(payable)

        mil_stmt = select(PaymentMilestone).where(PaymentMilestone.id == payable.milestone_id)
        mil_res = await session.execute(mil_stmt)
        milestone = mil_res.scalars().first()
        if milestone:
            milestone.payment_status = "PAID"
            milestone.version_index += 1
            milestone.reason_for_change = change_reason
            session.add(milestone)

        budget_stmt = select(BudgetLineItem).where(BudgetLineItem.grant_id == grant_id)
        budget_res = await session.execute(budget_stmt)
        budget_items = budget_res.scalars().all()
        for item in budget_items:
            # Smart match if category is in description, description is in category,
            # or if they share any keyword of length > 2 (e.g. "imv")
            category_lower = item.category.lower()
            desc_lower = milestone.description.lower() if milestone else ""
            words = [w.strip() for w in category_lower.split() if len(w.strip()) > 2]
            if milestone and (category_lower in desc_lower or desc_lower in category_lower or any(word in desc_lower for word in words)):
                item.actual_amount += payable.amount
                item.version_index += 1
                item.reason_for_change = "Payable paid - actual amount updated"
                session.add(item)
                break

        await session.flush()

        await write_audit_log(
            session=session,
            user_id=user_id,
            user_role=user_roles,
            action="PAY_PAYABLE",
            details=f"Paid investigator payable '{payable.id}' for grant '{grant_id}'. Reason: {change_reason}",
        )

    return InvestigatorPayableResponse(
        id=payable.id,
        milestone_id=payable.milestone_id,
        grant_id=payable.grant_id,
        amount=payable.amount,
        currency=payable.currency,
        status=payable.status,
        payment_date=payable.payment_date.isoformat() if payable.payment_date else None,
        created_at=payable.created_at.isoformat(),
        created_by=payable.created_by,
        reason_for_change=payable.reason_for_change,
        version_index=payable.version_index,
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
