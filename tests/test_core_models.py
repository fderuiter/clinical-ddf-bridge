"""Unit tests for the centralized CDISC USDM shared validation models.

Ensures that the models in `packages/core_models` correctly validate schemas,
extend official USDM types (like Study and StudyArm), and raise standard
validation errors on malformed payloads.
"""

import pytest
from pydantic import ValidationError

from packages.core_models import USDMStudy, USDMStudyArm


def test_valid_usdm_study_instantiation():
    """Test that a fully compliant USDMStudy payload instantiates successfully."""
    payload = {
        "name": "Sponsor Protocol 101",
        "protocol": {
            "items": [
                {"id": "bp_sys", "name": "Systolic Blood Pressure", "type": "int"},
                {"id": "bp_dia", "name": "Diastolic Blood Pressure", "type": "int"},
            ]
        },
    }

    study = USDMStudy(**payload)
    assert study.name == "Sponsor Protocol 101"
    assert study.protocol.items[0].id == "bp_sys"
    assert study.protocol.items[1].name == "Diastolic Blood Pressure"
    assert study.instanceType == "USDMStudy"


def test_invalid_usdm_study_missing_protocol():
    """Test that instantiating a USDMStudy with a missing protocol raises a ValidationError."""
    payload = {
        "name": "Sponsor Protocol 101",
    }

    with pytest.raises(ValidationError) as exc_info:
        USDMStudy(**payload)

    # Ensure the error specifies the missing protocol field
    assert "protocol" in str(exc_info.value)


def test_invalid_usdm_study_malformed_items():
    """Test that instantiating a USDMStudy with malformed items raises a ValidationError."""
    payload = {
        "name": "Sponsor Protocol 101",
        "protocol": {
            "items": [
                {"id": "bp_sys"},  # Missing name and type
            ]
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        USDMStudy(**payload)

    assert "name" in str(exc_info.value)
    assert "type" in str(exc_info.value)


def test_usdm_study_arm_extension():
    """Test that USDMStudyArm properly extends the official usdm_model.StudyArm class."""
    arm = USDMStudyArm(
        id="arm_a",
        name="Treatment Arm A",
        description="Active pharmaceutical ingredient cohort",
        type={
            "id": "c1",
            "code": "API_CODE",
            "decode": "Active",
            "codeSystem": "NCI Thesaurus",
            "codeSystemVersion": "2023-12",
            "instanceType": "Code",
        },
        dataOriginDescription="EHR records",
        dataOriginType={
            "id": "c2",
            "code": "EHR",
            "decode": "Electronic Health Record",
            "codeSystem": "ISO 20301",
            "codeSystemVersion": "1.0",
            "instanceType": "Code",
        },
    )
    assert arm.id == "arm_a"
    assert arm.name == "Treatment Arm A"
    assert arm.instanceType == "USDMStudyArm"
