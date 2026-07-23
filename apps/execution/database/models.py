import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # INSERT, UPDATE, DELETE
    user_id: Mapped[str] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    old_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    version_index: Mapped[int] = mapped_column(Integer, default=1)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=True)


class AuditedModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)


class TranslationJob(AuditedModel):
    """Represents an asynchronous study translation job.

    Inherits from AuditedModel to maintain an immutable audit log of status changes and generated payloads.

    Attributes:
        study_id (str): The unique identifier of the source study.
        status (str): The execution status (e.g., 'PENDING', 'COMPLETED', 'FAILED').
        odm_payload (str): The generated CDISC ODM XML payload.
        openrosa_payload (str): The generated OpenRosa XML layout payload.
        error_message (str): An error message if the translation failed.
    """

    __tablename__ = "translation_jobs"

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # PENDING, COMPLETED, FAILED
    odm_payload: Mapped[str] = mapped_column(String, nullable=True)
    openrosa_payload: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)


class Subject(AuditedModel):
    """Represents a clinical subject under study.

    Maintains pseudonymized reference to the subject to prevent storing direct,
    unencrypted patient-identifying details (PII) in compliance with regulatory mandates.

    Attributes:
        study_id (str): The unique identifier of the study.
        subject_key (str): The pseudonymized unique key of the subject.
        status (str): The current enrollment status of the subject (e.g. Screening, Active).
    """

    __tablename__ = "subjects"

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Screening")


class Visit(AuditedModel):
    """Represents a clinical trial study event or visit.

    Maintains scheduled event occurrences chronologically for subjects.

    Attributes:
        study_id (str): The unique identifier of the study.
        subject_key (str): The unique key of the subject.
        visit_oid (str): The CDISC/protocol Visit OID.
        visit_name (str): The display/logical name of the visit (e.g., 'Screening Visit').
        visit_number (int): Chronological order of the visit.
        visit_date (datetime): Timestamp when the visit was recorded or conducted.
    """

    __tablename__ = "visits"

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_number: Mapped[int] = mapped_column(Integer, nullable=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.utcnow)


class Observation(AuditedModel):
    """Represents a single clinical data observation recorded in an eCRF.

    Stores the raw as well as UCUM standardized measurement value and tracks
    statistical outlier flags.

    Attributes:
        study_id (str): The unique identifier of the study.
        subject_key (str): The pseudonymized key of the subject.
        visit_oid (str): The OID of the associated visit.
        form_oid (str): The OID of the form layout.
        form_version (str): The specific protocol/form layout version.
        item_group_oid (str): The OID of the item group within the form.
        item_oid (str): The OID of the specific field or concept.
        value (str): The verbatim raw string value entered by the investigator.
        unit (str): The raw measurement unit captured (e.g., '[degF]', '[lb_av]').
        normalized_value (float): The UCUM-converted standardized numeric value.
        normalized_unit (str): The standard target unit (e.g., 'Cel', 'kg').
        is_outlier (bool): Boolean flag indicating if this observation is an outlier.
    """

    __tablename__ = "observations"

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    form_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    form_version: Mapped[str] = mapped_column(String(50), default="1.0")
    item_group_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    item_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=True)
    normalized_unit: Mapped[str] = mapped_column(String(50), nullable=True)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)


class MeasurementHistory(AuditedModel):
    """Represents the historical measurement data points for clinical subjects.

    Helps track changes and trend analysis for measurement records over time.

    Attributes:
        study_id (str): The unique identifier of the study.
        subject_key (str): The pseudonymized key of the subject.
        item_oid (str): The concept/item OID.
        value (float): The numeric value of the measurement.
        unit (str): The standard or target unit of the measurement.
        measured_at (datetime): The timestamp when the measurement took place.
    """

    __tablename__ = "measurement_histories"

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    item_oid: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

