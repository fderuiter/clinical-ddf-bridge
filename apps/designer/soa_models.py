from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class SoAAuditMetadata(BaseModel):
    """
    Reusable Pydantic v2 audit metadata matching standard Designer and regulatory conventions.
    Aligns with GxP and 21 CFR Part 11 expectations.
    """
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="High-precision UTC timestamp of creation"
    )
    created_by: str = Field(
        ...,
        description="Deterministic user identity (OIDC Subject UUID or username) who created the record"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="High-precision UTC timestamp of the last update"
    )
    updated_by: Optional[str] = Field(
        None,
        description="User identity (OIDC Subject UUID or username) who performed the last update"
    )
    reason_for_change: Optional[str] = Field(
        None,
        description="Mandatory justification detailing the reason for mutation (used on update)"
    )
    version: str = Field(
        "1.0.0",
        description="Semantic version of this record or schema"
    )


# --- Core Domain Models with Audit Metadata ---

class TimingWindow(BaseModel):
    """
    Represents an advanced Timing Window model extending visit_window_days.
    """
    id: str = Field(..., description="Unique timing window identifier")
    name: str = Field(..., description="Descriptive name of the timing window")
    target_day: int = Field(..., description="Target study day relative to baseline")
    window_back: int = Field(..., description="Backward tolerance range")
    window_forward: int = Field(..., description="Forward tolerance range")
    time_unit: str = Field("DAYS", description="Unit of time (e.g., DAYS, WEEKS, HOURS)")
    description: Optional[str] = Field(None, description="Detailed explanation of the timing window")
    audit: SoAAuditMetadata = Field(..., description="Compliance audit metadata")


class StudyArm(BaseModel):
    """
    Represents a branch or treatment group within the study design.
    """
    id: str = Field(..., description="Unique arm identifier")
    name: str = Field(..., description="Name of the study arm")
    arm_type: str = Field(..., description="Type of treatment arm (e.g., TREATMENT, PLACEBO, CONTROL)")
    type_concept_id: Optional[str] = Field(None, description="Terminology concept ID for the arm type")
    description: Optional[str] = Field(None, description="Optional narrative description")
    audit: SoAAuditMetadata = Field(..., description="Compliance audit metadata")


class Epoch(BaseModel):
    """
    Represents a major phase of the study (e.g., Screening, Treatment, Follow-up).
    """
    id: str = Field(..., description="Unique epoch identifier")
    name: str = Field(..., description="Descriptive name of the epoch")
    sequence_order: int = Field(..., description="Temporal sequence of this epoch in the study")
    description: Optional[str] = Field(None, description="Optional narrative description")
    audit: SoAAuditMetadata = Field(..., description="Compliance audit metadata")


class Visit(BaseModel):
    """
    Represents a scheduled clinical visit/encounter.
    """
    id: str = Field(..., description="Unique visit identifier")
    name: str = Field(..., description="Descriptive name of the visit")
    visit_window_days: Optional[int] = Field(None, description="Legacy/simplified visit window days")
    timing_window_id: Optional[str] = Field(None, description="Reference to a detailed TimingWindow node")
    description: Optional[str] = Field(None, description="Optional narrative description")
    audit: SoAAuditMetadata = Field(..., description="Compliance audit metadata")


class ProcedureActivity(BaseModel):
    """
    Represents a defined procedure or activity conducted during visits.
    """
    id: str = Field(..., description="Unique procedure/activity identifier")
    name: str = Field(..., description="Descriptive name of the procedure/activity")
    code: Optional[str] = Field(None, description="Standard dictionary terminology code (e.g., LOINC, SNOMED)")
    description: Optional[str] = Field(None, description="Optional narrative description")
    audit: SoAAuditMetadata = Field(..., description="Compliance audit metadata")


# --- Mutation Contracts (Create / Update Requests) ---

class CreateTimingWindowRequest(BaseModel):
    name: str
    target_day: int
    window_back: int
    window_forward: int
    time_unit: str = "DAYS"
    description: Optional[str] = None
    change_reason: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class UpdateTimingWindowRequest(BaseModel):
    name: Optional[str] = None
    target_day: Optional[int] = None
    window_back: Optional[int] = None
    window_forward: Optional[int] = None
    time_unit: Optional[str] = None
    description: Optional[str] = None
    reason_for_change: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class CreateStudyArmRequest(BaseModel):
    name: str
    arm_type: str
    type_concept_id: Optional[str] = None
    description: Optional[str] = None
    change_reason: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class UpdateStudyArmRequest(BaseModel):
    name: Optional[str] = None
    arm_type: Optional[str] = None
    type_concept_id: Optional[str] = None
    description: Optional[str] = None
    reason_for_change: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class CreateEpochRequest(BaseModel):
    name: str
    sequence_order: int
    description: Optional[str] = None
    change_reason: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class UpdateEpochRequest(BaseModel):
    name: Optional[str] = None
    sequence_order: Optional[int] = None
    description: Optional[str] = None
    reason_for_change: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class CreateVisitRequest(BaseModel):
    name: str
    visit_window_days: Optional[int] = None
    timing_window_id: Optional[str] = None
    description: Optional[str] = None
    change_reason: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class UpdateVisitRequest(BaseModel):
    name: Optional[str] = None
    visit_window_days: Optional[int] = None
    timing_window_id: Optional[str] = None
    description: Optional[str] = None
    reason_for_change: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class CreateProcedureActivityRequest(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    change_reason: str = Field(..., min_length=1, description="Mandatory GxP change reason")


class UpdateProcedureActivityRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    reason_for_change: str = Field(..., min_length=1, description="Mandatory GxP change reason")


# --- Schedule of Activities Matrix Projections ---

class SoACell(BaseModel):
    """
    Represents an intersection cell between an arm, epoch, visit, and procedure.
    Supports arm applicability and per-cell conditional timing.
    """
    arm_id: str = Field(..., description="Identifier of the study arm")
    epoch_id: str = Field(..., description="Identifier of the study epoch")
    visit_id: str = Field(..., description="Identifier of the clinical visit")
    procedure_id: str = Field(..., description="Identifier of the procedure or activity")
    is_applicable: bool = Field(True, description="Whether the procedure is performed at this visit for this arm")
    is_conditional: bool = Field(False, description="Whether performing it is conditional (e.g., as needed)")
    conditional_reason: Optional[str] = Field(None, description="The condition or trigger logic under which the procedure is performed")
    timing_window_id: Optional[str] = Field(None, description="Cell-level timing window override reference")
    timing_window_override: Optional[TimingWindow] = Field(None, description="Detailed inline TimingWindow if overridden")

    @model_validator(mode="after")
    def validate_conditional_reason(self) -> "SoACell":
        """
        Enforce that conditional entries have a valid, non-empty conditional reason.
        """
        if self.is_conditional:
            if not self.conditional_reason or not self.conditional_reason.strip():
                raise ValueError("Conditional entries must have a non-empty conditional_reason.")
        return self


class SoAMatrixProjectionResponse(BaseModel):
    """
    The matrix-projection response contract consumed by the Designer API and Web UI.
    Represents the full schedule (arm × epoch × visit × procedure) structure.
    """
    study_id: str = Field(..., description="Identifier of the clinical study")
    study_version_id: str = Field(..., description="Identifier of the specific study version")
    arms: List[StudyArm] = Field(..., description="Configured treatment arms")
    epochs: List[Epoch] = Field(..., description="Configured study phases/epochs")
    visits: List[Visit] = Field(..., description="Scheduled clinical visits")
    procedures: List[ProcedureActivity] = Field(..., description="Configured procedure/activity definitions")
    timing_windows: List[TimingWindow] = Field(..., description="Configured timing windows dictionary")
    cells: List[SoACell] = Field(..., description="The flat schedule grid cells")
