import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
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
    user_role: str | list[str],
    action: str,
    details: str,
) -> None:
    """
    Utility helper to write to the append-only CTMSAuditLog.
    """
    role_str = user_role
    if isinstance(user_role, list):
        role_str = ",".join(user_role)

    log_entry = CTMSAuditLog(
        user_id=user_id,
        user_role=role_str,
        action=action,
        details=details,
    )
    session.add(log_entry)
    await session.flush()
