import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "audit_schema"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # INSERT, UPDATE, DELETE
    user_id: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    old_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    version_index: Mapped[int] = mapped_column(Integer, default=1)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    cryptographic_seal: Mapped[str] = mapped_column(String(64), nullable=True)


class AuditLedgerSeal(Base):
    __tablename__ = "audit_ledger_seals"
    __table_args__ = {"schema": "audit_schema"}

    block_index: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    previous_block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    sealed_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    merkle_root_hash: Mapped[str] = mapped_column(String(64), nullable=False)


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


class ClinicalSubject(AuditedModel):
    """Represents a pseudonymized clinical subject.

    This class stores subject identification details strictly without storing direct, unencrypted
    personally identifiable information (PII) to comply with HIPAA, GDPR, and GxP standards.

    Attributes:
        subject_id (str): The unique pseudonymized identifier of the subject (e.g. SUBJ-001).
        study_id (str): The identifier of the clinical trial study.
        encrypted_demographics (str): Securely encrypted demographic details if provided.
    """

    __tablename__ = "clinical_subjects"

    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_demographics: Mapped[str] = mapped_column(String, nullable=True)


class ClinicalVisit(AuditedModel):
    """Represents a scheduled clinical event/visit for a subject.

    Maintains scheduled trial encounters like Screening, Baseline, Week 4, etc.

    Attributes:
        subject_id (str): The unique identifier of the subject.
        visit_name (str): The name or description of the visit.
        visit_date (datetime): The actual datetime of the visit encounter.
        study_id (str): The identifier of the clinical trial study.
    """

    __tablename__ = "clinical_visits"

    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    study_id: Mapped[str] = mapped_column(String(255), nullable=False)


class ClinicalObservation(AuditedModel):
    """Represents a specific clinical trial measurement observation.

    Stores normalized values, original and normalized units, and outlier flags
    for individual parameters (e.g., vital signs, lab test measurements).

    Attributes:
        subject_id (str): The unique identifier of the subject.
        visit_id (str): Reference to the clinical visit ID if applicable.
        domain (str): The CDISC domain code (e.g., 'VS', 'LB').
        observation_date (datetime): The datetime when the measurement was captured.
        test_code (str): The standard CDASH/SDTM test code (e.g., 'SYSBP', 'TEMP').
        test_name (str): The full descriptive name of the test parameter.
        value (float): The raw numeric value of the observation if applicable.
        value_string (str): The raw nominal or text value of the observation.
        unit (str): The standard UCUM or clinical unit.
        normalized_value (float): The normalized numeric value in standard reference units.
        normalized_unit (str): The standard normalized UCUM unit.
        is_outlier (bool): Flag indicating if this is a statistical outlier within the cohort.
        is_sdv_verified (bool): Non-null boolean indicating if field-level SDV is verified.
        sdv_verified_by (str): Nullable identifier of the verifier/CRA.
        sdv_verified_at (datetime): Nullable timestamp of SDV verification.
        page_id (str): Nullable eCRF page/form grouping key.
    """

    __tablename__ = "clinical_observations"

    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_id: Mapped[str] = mapped_column(String(255), nullable=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    observation_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    test_code: Mapped[str] = mapped_column(String(100), nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    value_string: Mapped[str] = mapped_column(String, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=True)
    normalized_unit: Mapped[str] = mapped_column(String(50), nullable=True)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sdv_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sdv_verified_by: Mapped[str] = mapped_column(String(255), nullable=True)
    sdv_verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    page_id: Mapped[str] = mapped_column(String(255), nullable=True)


class ClinicalQuery(AuditedModel):
    """Represents a clinical query state record for GxP data discrepancy tracking.

    Inherits from AuditedModel to maintain an immutable audit log of status changes and history,
    and prevent hard deletions through automatic trigger-based protection.

    Attributes:
        study_id (str): The unique identifier of the study.
        subject_id (str): The unique identifier of the subject (target coordinate).
        visit_id (str): Reference to the clinical visit ID if applicable (target coordinate).
        domain (str): The CDISC domain code if applicable (target coordinate).
        test_code (str): The standard CDASH/SDTM test code (target coordinate).
        status (str): The query status (e.g., 'NONE', 'OPEN', 'ANSWERED', 'CLOSED', 'REOPENED').
        explanation (str): The user-inputted explanation/justification when opening the query.
        response (str): The investigator-submitted response when answering the query.
        created_at (datetime): Timestamp of query creation.
        updated_at (datetime): Timestamp of last query modification.
    """

    __tablename__ = "clinical_queries"
    __table_args__ = (
        Index(
            "idx_query_target",
            "study_id",
            "subject_id",
            "visit_id",
            "domain",
            "test_code",
        ),
    )

    study_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    visit_id: Mapped[str] = mapped_column(String(255), index=True, nullable=True)
    domain: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    test_code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="NONE", nullable=False)
    explanation: Mapped[str] = mapped_column(String(255), nullable=True)
    response: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class SDVSignOff(AuditedModel):
    """Represents an aggregate sign-off record for SDV/TSDV verification.

    Maintains page-, visit- or field-level verification signatures and drop states
    for auditing and GxP traceability.

    Attributes:
        scope (str): The verification scope (FIELD, PAGE, or VISIT).
        target_id (str): The identifier of the verified entity.
        subject_id (str): The clinical subject identifier.
        study_id (str): The clinical trial study identifier.
        is_verified (bool): Non-null boolean indicating if aggregate verification is active.
        verified_by (str): Nullable identifier of the verifier/CRA.
        verified_at (datetime): Nullable timestamp of verification.
        dropped_reason (str): Nullable reason text for dropping/rescinding verification.
        dropped_at (datetime): Nullable timestamp when verification was dropped/rescinded.
    """

    __tablename__ = "sdv_sign_offs"

    scope: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # FIELD, PAGE, or VISIT
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    dropped_reason: Mapped[str] = mapped_column(String(1000), nullable=True)
    dropped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class TSDVConfig(AuditedModel):
    """Represents the Targeted SDV (TSDV) sampling configuration for a study.

    Maintains study-specific parameters governing subject-based or field-based
    sampling models and domain-level SDV requirements.

    Attributes:
        study_id (str): Unique clinical trial study identifier.
        sampling_model (str): SUBJECT_BASED, FIELD_BASED, or COMBINED.
        initial_full_sdv_subject_count (int): Count of subjects requiring full SDV before sampling begins.
        random_sample_percentage (float): Probability percentage of standard random subject sampling.
        full_sdv_domains (list): JSON list of SDTM domain codes requiring 100% full SDV.
        safety_endpoints (list): JSON list of safety endpoint variables/domains requiring 100% full SDV.
        zero_sdv_domains (list): JSON list of SDTM domain codes needing zero (no) SDV.
        trial_random_seed (int): Integer seed value for stable, deterministic pseudo-random sampling.
    """

    __tablename__ = "tsdv_configs"

    study_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sampling_model: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SUBJECT_BASED, FIELD_BASED, or COMBINED
    initial_full_sdv_subject_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    random_sample_percentage: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    full_sdv_domains: Mapped[list] = mapped_column(JSON, nullable=True)
    safety_endpoints: Mapped[list] = mapped_column(JSON, nullable=True)
    zero_sdv_domains: Mapped[list] = mapped_column(JSON, nullable=True)
    trial_random_seed: Mapped[int] = mapped_column(Integer, nullable=True)


class DictionaryType(str, Enum):
    MEDDRA = "MEDDRA"
    WHODRUG = "WHODRUG"


class ImportState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CodingState(str, Enum):
    PENDING = "PENDING"
    CODED = "CODED"
    REJECTED = "REJECTED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class RecodingState(str, Enum):
    PENDING = "PENDING"
    RECODED = "RECODED"
    NO_CHANGE = "NO_CHANGE"


class MedDRATerm(AuditedModel):
    """Represents a MedDRA terminology term (LLT, PT, HLT, HLGT, or SOC).

    Inherits from AuditedModel for full Part 11 compliant audit trail coverage.
    """

    __tablename__ = "meddra_terms"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "level",
            "code",
            name="uq_meddra_term_version_level_code",
        ),
        Index(
            "idx_meddra_term_lookup",
            "dictionary_version",
            "term_normalized",
            "code",
        ),
        Index(
            "idx_meddra_term_display",
            "dictionary_version",
            "term",
            "code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # LLT, PT, HLT, HLGT, SOC
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    term: Mapped[str] = mapped_column(String(500), nullable=False)
    term_normalized: Mapped[str] = mapped_column(String(500), nullable=False)


class MedDRAHierarchy(AuditedModel):
    """Represents the hierarchical relationship (mdhier) between MedDRA terms,

    including primary System Organ Class (SOC) indication.
    """

    __tablename__ = "meddra_hierarchies"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "llt_code",
            "pt_code",
            "hlt_code",
            "hlgt_code",
            "soc_code",
            name="uq_meddra_hier_version_codes",
        ),
        Index(
            "idx_meddra_hier_lookup",
            "dictionary_version",
            "llt_code",
            "pt_code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    llt_code: Mapped[str] = mapped_column(String(50), nullable=False)
    pt_code: Mapped[str] = mapped_column(String(50), nullable=False)
    hlt_code: Mapped[str] = mapped_column(String(50), nullable=False)
    hlgt_code: Mapped[str] = mapped_column(String(50), nullable=False)
    soc_code: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_soc_flag: Mapped[str] = mapped_column(
        String(1), nullable=True
    )  # 'Y' or 'N'


class WHODrugRecord(AuditedModel):
    """Represents a WHODrug drug record (Drug Dictionary/DD/Drug record)."""

    __tablename__ = "whodrug_records"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "drug_code",
            name="uq_whodrug_record_version_code",
        ),
        Index(
            "idx_whodrug_record_lookup",
            "dictionary_version",
            "drug_name_normalized",
            "drug_code",
        ),
        Index(
            "idx_whodrug_record_display",
            "dictionary_version",
            "drug_name",
            "drug_code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_code: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(500), nullable=False)
    drug_name_normalized: Mapped[str] = mapped_column(String(500), nullable=False)
    atc_code: Mapped[str] = mapped_column(String(50), nullable=True)


class WHODrugIngredient(AuditedModel):
    """Represents a WHODrug active substance/ingredient."""

    __tablename__ = "whodrug_ingredients"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "substance_code",
            name="uq_whodrug_ingredient_version_code",
        ),
        Index(
            "idx_whodrug_ingredient_lookup",
            "dictionary_version",
            "substance_name_normalized",
            "substance_code",
        ),
        Index(
            "idx_whodrug_ingredient_display",
            "dictionary_version",
            "substance_name",
            "substance_code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    substance_code: Mapped[str] = mapped_column(String(50), nullable=False)
    substance_name: Mapped[str] = mapped_column(String(500), nullable=False)
    substance_name_normalized: Mapped[str] = mapped_column(String(500), nullable=False)


class WHODrugATC(AuditedModel):
    """Represents WHODrug ATC classification and hierarchy records."""

    __tablename__ = "whodrug_atc"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "atc_code",
            name="uq_whodrug_atc_version_code",
        ),
        Index(
            "idx_whodrug_atc_lookup",
            "dictionary_version",
            "atc_text_normalized",
            "atc_code",
        ),
        Index(
            "idx_whodrug_atc_display",
            "dictionary_version",
            "atc_text",
            "atc_code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    atc_code: Mapped[str] = mapped_column(String(50), nullable=False)
    atc_text: Mapped[str] = mapped_column(String(500), nullable=False)
    atc_text_normalized: Mapped[str] = mapped_column(String(500), nullable=False)


class WHODrugDrugIngredientMap(AuditedModel):
    """Maps WHODrug drug records to their active ingredients/substances."""

    __tablename__ = "whodrug_drug_ingredient_maps"
    __table_args__ = (
        UniqueConstraint(
            "dictionary_version",
            "drug_code",
            "substance_code",
            name="uq_whodrug_drug_substance_map",
        ),
        Index(
            "idx_whodrug_drug_substance_lookup",
            "dictionary_version",
            "drug_code",
            "substance_code",
        ),
    )

    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_code: Mapped[str] = mapped_column(String(50), nullable=False)
    substance_code: Mapped[str] = mapped_column(String(50), nullable=False)


class DictionaryImportJob(AuditedModel):
    """Represents dictionary import tracking and jobs."""

    __tablename__ = "dictionary_import_jobs"

    dictionary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_encountered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[str] = mapped_column(String, nullable=True)


class ClinicalCodingAssignment(AuditedModel):
    """Represents current coded assignments mapping verbatims to dictionary terms."""

    __tablename__ = "clinical_coding_assignments"
    __table_args__ = (
        Index(
            "idx_coding_assignment_verbatim",
            "verbatim_term",
            "dictionary_type",
            "dictionary_version",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    verbatim_term: Mapped[str] = mapped_column(String(1000), nullable=False)
    dictionary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dictionary_version: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_code: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_term: Mapped[str] = mapped_column(String(1000), nullable=False)
    coding_state: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class ClinicalCodingLedgerEntry(AuditedModel):
    """Represents the historical clinical coding ledger of recoding decisions

    and version updates.
    """

    __tablename__ = "clinical_coding_ledger"
    __table_args__ = (
        Index(
            "idx_coding_ledger_assignment",
            "assignment_id",
        ),
    )

    assignment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    observation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    verbatim_term: Mapped[str] = mapped_column(String(1000), nullable=False)
    dictionary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dictionary_version_old: Mapped[str] = mapped_column(String(50), nullable=True)
    dictionary_version_new: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_code_old: Mapped[str] = mapped_column(String(50), nullable=True)
    assigned_code_new: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_term_old: Mapped[str] = mapped_column(String(1000), nullable=True)
    assigned_term_new: Mapped[str] = mapped_column(String(1000), nullable=False)
    recoding_state: Mapped[str] = mapped_column(String(50), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
