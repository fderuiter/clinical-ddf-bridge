
import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from packages.security.rbac import (
    AUDITOR,
    CRA,
    CRC,
    INVESTIGATOR,
    SPONSOR_DM,
    SPONSOR_STATISTICIAN,
    SUBJECT,
    SYSADMIN,
    Principal,
    can_access_site,
    get_principal,
    has_permission,
    mask_payload,
    normalize_role,
    require_permission,
    require_permission_imperative,
)


# A mock Request class for testing
class MockRequest:
    def __init__(self, headers=None, state_attrs=None):
        self.headers = headers or {}
        self.state = type("State", (), state_attrs or {})()

def test_role_normalization():
    # Test case-insensitivity and formatting
    assert normalize_role("Admin") == SYSADMIN
    assert normalize_role("SYSTEM") == SYSADMIN
    assert normalize_role("sponsor-designer") == "sponsor_designer"
    assert normalize_role("SPONSOR STUDY DESIGNER") == "sponsor_designer"
    assert normalize_role("sponsor_dm_role") == SPONSOR_DM
    assert normalize_role("grants_manager") == SPONSOR_DM
    assert normalize_role("Grants Manager") == SPONSOR_DM
    assert normalize_role("PI") == INVESTIGATOR
    assert normalize_role("site investigator") == INVESTIGATOR
    assert normalize_role("clinical research coordinator") == CRC
    assert normalize_role("Site Coordinator") == CRC
    assert normalize_role("CRA") == CRA
    assert normalize_role("monitor") == CRA
    assert normalize_role("patient") == SUBJECT
    assert normalize_role("epro") == SUBJECT
    assert normalize_role("Inspector") == AUDITOR
    assert normalize_role("regulatory_inspector") == AUDITOR
    assert normalize_role("unknown_role") == "unknown role"

def test_principal_instantiation():
    principal = Principal(
        user_id="user_123",
        roles=[SYSADMIN, SPONSOR_DM],
        assigned_sites=["site_A", "site_B"],
        unblinded_status=True,
        change_reason="Operational audit"
    )
    assert principal.user_id == "user_123"
    assert principal.roles == [SYSADMIN, SPONSOR_DM]
    assert principal.assigned_sites == ["site_A", "site_B"]
    assert principal.unblinded_status is True
    assert principal.change_reason == "Operational audit"

def test_permission_matrix_validation():
    # Check permissions for SysAdmin
    p_admin = Principal(user_id="admin", roles=[SYSADMIN])
    assert has_permission(p_admin, "study_design:read") is True
    assert has_permission(p_admin, "study_design:create") is False
    assert has_permission(p_admin, "subject_enrollment:read") is False
    assert has_permission(p_admin, "export_masked:read") is True

    # Check Sponsor DM permissions
    p_dm = Principal(user_id="dm", roles=[SPONSOR_DM])
    assert has_permission(p_dm, "query_lifecycle:create") is True
    assert has_permission(p_dm, "query_lifecycle:delete") is True
    assert has_permission(p_dm, "sdv:read") is False
    assert has_permission(p_dm, "export_masked:create") is True

    # Check Investigator permissions
    p_inv = Principal(user_id="inv", roles=[INVESTIGATOR])
    assert has_permission(p_inv, "subject_enrollment:create") is True
    assert has_permission(p_inv, "ecrf_data_entry:update") is True
    assert has_permission(p_inv, "query_lifecycle:read") is True
    assert has_permission(p_inv, "query_lifecycle:update") is True
    assert has_permission(p_inv, "query_lifecycle:delete") is False

    # Check Patient permissions
    p_sub = Principal(user_id="sub", roles=[SUBJECT])
    assert has_permission(p_sub, "ecrf_data_entry:create") is True
    assert has_permission(p_sub, "query_lifecycle:read") is False

def test_site_access_isolation():
    p_restricted = Principal(user_id="crc1", roles=[CRC], assigned_sites=["Site_01", "Site_02"])
    p_global = Principal(user_id="dm1", roles=[SPONSOR_DM], assigned_sites=[])

    # Restricted user tests
    assert can_access_site(p_restricted, "Site_01") is True
    assert can_access_site(p_restricted, "site_02") is True
    assert can_access_site(p_restricted, "Site_03") is False

    # Global user tests
    assert can_access_site(p_global, "Site_01") is True
    assert can_access_site(p_global, "Site_03") is True

def test_imperative_guard():
    p_crc = Principal(user_id="crc", roles=[CRC])

    # Happy path
    require_permission_imperative(p_crc, "ecrf_data_entry:create")

    # Denial path
    with pytest.raises(HTTPException) as exc_info:
        require_permission_imperative(p_crc, "study_design:create")
    assert exc_info.value.status_code == 403

def test_fastapi_dependencies():
    # Mock FastAPI request
    req = MockRequest(
        headers={
            "X-User-Id": "user_789",
            "X-User-Roles": "pi, grants_manager",
            "X-Assigned-Sites": "Site_Alpha",
            "X-Unblinded-Access": "true",
            "X-Change-Reason": "API test call"
        }
    )

    principal = get_principal(req)
    assert principal.user_id == "user_789"
    assert INVESTIGATOR in principal.roles
    assert SPONSOR_DM in principal.roles
    assert principal.assigned_sites == ["Site_Alpha"]
    assert principal.unblinded_status is True
    assert principal.change_reason == "API test call"

    # Test Depends() guard with allowed permission
    dep = require_permission("query_lifecycle:create")
    res_principal = dep(principal)
    assert res_principal == principal

    # Test Depends() guard with denied permission
    dep_denied = require_permission("study_design:create")
    with pytest.raises(HTTPException) as exc_info:
        dep_denied(principal)
    assert exc_info.value.status_code == 403

class DemoModelPayload(BaseModel):
    initials: str
    ssn: str
    dob: str
    treatment_arm_id: str
    drug_code: str
    age: int
    unrelated_field: str

def test_schema_agnostic_masking():
    # Blinded principal
    p_blind = Principal(user_id="crc", roles=[CRC], unblinded_status=False)
    # Unblinded principal
    p_unblind = Principal(user_id="stat", roles=[SPONSOR_STATISTICIAN], unblinded_status=True)

    test_data = {
        "initials": "JD",
        "ssn": "123-45-6789",
        "dob": "1980-01-01",
        "treatment_arm_id": "ARM_A_ACTIVE",
        "drug_code": "DRUG_A",
        "age": 45,
        "unrelated_field": "Non-sensitive value",
        "nested_dict": {
            "ssn": "987-65-4321",
            "treatment_arm": "ARM_B_PLACEBO",
            "administered_drug_code": "DRUG_B"
        },
        "item_list": [
            {"dob": "1990-12-31", "ssn": "000-00-0000"},
            {"unrelated_field": "test"}
        ]
    }

    # Test dict masking for blinded
    masked_dict = mask_payload(test_data, p_blind)
    assert masked_dict["initials"] == "REDACTED"
    assert masked_dict["ssn"] == "REDACTED"
    assert masked_dict["dob"] == "REDACTED"
    assert masked_dict["treatment_arm_id"] == "BLINDED"
    assert masked_dict["drug_code"] == "Kit Number XYZ"
    assert masked_dict["age"] == 45
    assert masked_dict["unrelated_field"] == "Non-sensitive value"
    assert masked_dict["nested_dict"]["ssn"] == "REDACTED"
    assert masked_dict["nested_dict"]["treatment_arm"] == "BLINDED"
    assert masked_dict["nested_dict"]["administered_drug_code"] == "Kit Number XYZ"
    assert masked_dict["item_list"][0]["dob"] == "REDACTED"
    assert masked_dict["item_list"][0]["ssn"] == "REDACTED"
    assert masked_dict["item_list"][1]["unrelated_field"] == "test"

    # Test dict masking for unblinded (must be untouched)
    unmasked_dict = mask_payload(test_data, p_unblind)
    assert unmasked_dict == test_data

    # Test Pydantic model masking for blinded
    model_obj = DemoModelPayload(
        initials="JD",
        ssn="123-45-6789",
        dob="1980-01-01",
        treatment_arm_id="ARM_A_ACTIVE",
        drug_code="DRUG_A",
        age=45,
        unrelated_field="Non-sensitive value"
    )

    masked_model = mask_payload(model_obj, p_blind)
    assert isinstance(masked_model, DemoModelPayload)
    assert masked_model.initials == "REDACTED"
    assert masked_model.ssn == "REDACTED"
    assert masked_model.dob == "REDACTED"
    assert masked_model.treatment_arm_id == "BLINDED"
    assert masked_model.drug_code == "Kit Number XYZ"
    assert masked_model.age == 45
    assert masked_model.unrelated_field == "Non-sensitive value"

    # Test Pydantic model masking for unblinded (must be untouched)
    unmasked_model = mask_payload(model_obj, p_unblind)
    assert unmasked_model.ssn == "123-45-6789"
