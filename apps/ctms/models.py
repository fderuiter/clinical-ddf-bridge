import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Float, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CTMSAuditLog(Base):
    """
    Represents an immutable, chronological record of all actions performed
    on the CTMS platform, in compliance with 21 CFR Part 11.
    """

    __tablename__ = "ctms_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_role: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str] = mapped_column(String(1000), nullable=False)


class CTMSStudy(Base):
    """
    Example CTMS domain model representing a clinical trial metadata boundary
    with mandatory Part 11 audit fields.
    """

    __tablename__ = "ctms_studies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    study_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class MonitoringVisit(Base):
    """
    Represents a clinical trial site monitoring visit report (MVR) lifecycle.
    """

    __tablename__ = "ctms_monitoring_visits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    study_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cra_id: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED", nullable=False)

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class MonitoringVisitFinding(Base):
    """
    Represents an individual monitoring visit finding or action item.
    """

    __tablename__ = "ctms_monitoring_visit_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    visit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MINOR, MAJOR, CRITICAL
    resolution_status: Mapped[str] = mapped_column(
        String(50), default="OPEN", nullable=False
    )  # OPEN, RESOLVED

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class GeneratedLetter(Base):
    """
    Represents a persisted confirmation or follow-up letter generated for a monitoring visit.
    Ensures that letters can be retrieved without re-rendering previously issued content.
    """

    __tablename__ = "ctms_generated_letters"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    visit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    letter_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # CONFIRMATION, FOLLOW_UP
    rendered_content: Mapped[str] = mapped_column(String(100000), nullable=False)

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


async def write_audit_log(
    session: AsyncSession,
    user_id: str,
    user_role: str,
    action: str,
    details: str,
) -> None:
    """
    Utility helper to write to the append-only CTMSAuditLog.
    """
    log_entry = CTMSAuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        details=details,
    )
    session.add(log_entry)
    await session.flush()


class InvestigatorGrant(Base):
    """
    Represents an investigator grant associated with a trial site, study, and investigator.
    Tracks total budget, currency, status, and complies with Part 11 requirements.
    """
    __tablename__ = "ctms_investigator_grants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    investigator_id: Mapped[str] = mapped_column(String(255), nullable=False)
    site_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    study_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)  # DRAFT, APPROVED

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class BudgetLineItem(Base):
    """
    Represents an itemized budget line item within an investigator grant.
    """
    __tablename__ = "ctms_budget_line_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    grant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PaymentMilestone(Base):
    """
    Represents a planned payment milestone tied to specific conditions or triggers.
    """
    __tablename__ = "ctms_payment_milestones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    grant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. VISIT_COMPLETED, STUDY_APPROVED, MANUAL
    trigger_condition: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # e.g. "IMV"
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    trigger_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, TRIGGERED, PAID

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class InvestigatorPayable(Base):
    """
    A payable ledger record generated upon triggering of a milestone.
    """
    __tablename__ = "ctms_investigator_payables"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    milestone_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, unique=True)
    grant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="UNPAID", nullable=False)  # UNPAID, PAID
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Standard Part 11 Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
