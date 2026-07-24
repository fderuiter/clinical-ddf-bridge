"""
Shared SDTM Foundation Models, Controlled Terminology, and Audit Metadata.

This package provides the shared strongly-typed Pydantic v2 models for
SDTM DM, AE, VS, LB, CM, and generic SUPPQUAL records, along with CDISC
controlled-terminology enums and 21 CFR Part 11 compliant audit mixins.
"""

from sdtm.enums import (
    AEOutcome,
    AERelationship,
    AESeriousness,
    AESeverity,
    NullFlavor,
    Race,
    SDTMDomain,
    Sex,
)
from sdtm.models import (
    AE,
    CM,
    DM,
    LB,
    SUPPQUAL,
    VS,
    AdverseEvent,
    AuditableModel,
    ConcomitantMedication,
    Demographics,
    Laboratory,
    SUPPQUALRecord,
    VitalSign,
)
from sdtm.terminology import (
    normalize_race,
    normalize_seriousness,
    normalize_severity,
    normalize_sex,
)

__all__ = [
    "SDTMDomain",
    "Sex",
    "Race",
    "AESeverity",
    "AESeriousness",
    "AERelationship",
    "AEOutcome",
    "NullFlavor",
    "AuditableModel",
    "DM",
    "AE",
    "VS",
    "LB",
    "CM",
    "SUPPQUAL",
    "Demographics",
    "AdverseEvent",
    "VitalSign",
    "Laboratory",
    "ConcomitantMedication",
    "SUPPQUALRecord",
    "normalize_race",
    "normalize_seriousness",
    "normalize_severity",
    "normalize_sex",
]
