"""
Organization Directory and Delegation of Authority (DOA) domain models.

This module provides the shared Pydantic v2 domain models and controlled
vocabularies (enums) for organization types, clinical staff roles, and
delegatable significant trial-related duties in compliance with 21 CFR Part 11,
EU Annex 11, and ICH E6(R2).
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OrganizationType(str, Enum):
    """
    Standard organization types involved in clinical trials.
    """

    SPONSOR = "sponsor"
    CRO = "CRO"
    IRB_IEC = "IRB/IEC"
    CENTRAL_LABORATORY = "central laboratory"
    SITE = "site"


class ClinicalStaffRole(str, Enum):
    """
    Standard clinical staff role vocabulary from docs/SDLC/05_Security_Compliance_Audit_Spec.md,
    reused across organization directory and delegation of authority records.
    """

    PRINCIPAL_INVESTIGATOR = "Principal Investigator"
    SUB_INVESTIGATOR = "Sub-Investigator"
    CRC = "CRC"
    CRA_MONITOR = "CRA/Monitor"


class TrialDuty(str, Enum):
    """
    Controlled vocabulary of delegatable significant trial-related duties aligned with ICH E6(R2).
    """

    INFORMED_CONSENT = "Informed Consent Process"
    ELIGIBILITY_ASSESSMENT = "Subject Recruitment & Eligibility Assessment"
    RANDOMIZATION = "Randomization & Interactive Response Technology Management"
    IP_MANAGEMENT = "Investigational Product (IP) Management & Dispensation"
    CRF_COMPLETION = "CRF Completion & Data Entry"
    QUERY_RESOLUTION = "Clinical Query & Discrepancy Resolution"
    MEDICAL_ASSESSMENT = "Medical Assessments & Safety Evaluations"
    LAB_SAMPLE_MANAGEMENT = "Laboratory Sample Handling, Processing & Shipment"
    SAFETY_REPORTING = "Adverse Event (AE) & Serious Adverse Event (SAE) Reporting"
    TRIAL_OVERSIGHT = "Trial Oversight & Principal Investigator Duties"


class AuditFields(BaseModel):
    """
    A reusable Pydantic v2 model/mixin containing standard 21 CFR Part 11
    compliant audit and metadata fields.
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Chronological UTC timestamp when the record was created.",
    )
    created_by: str = Field(
        ...,
        description="Unique identifier (e.g. username/OIDC user_id) of the user who created the record.",
    )
    reason_for_change: str = Field(
        ...,
        description="Mandatory explanation or audit justification for creating or mutating this record.",
    )
    version_index: int = Field(
        default=1,
        description="Optimistic locking or row version counter, initialized to 1.",
    )

    @field_validator("reason_for_change")
    @classmethod
    def validate_reason_for_change(cls, v: str) -> str:
        """
        Validate that the reason_for_change is a non-empty, non-blank string.
        """
        if not isinstance(v, str) or not v.strip():
            raise ValueError(
                "Reason for change cannot be empty or consist only of whitespace."
            )
        return v
