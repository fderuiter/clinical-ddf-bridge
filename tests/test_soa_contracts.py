import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.designer.main import app as designer_app
from apps.designer.soa_models import (
    SoAAuditMetadata,
    TimingWindow,
    StudyArm,
    Epoch,
    Visit,
    ProcedureActivity,
    CreateTimingWindowRequest,
    UpdateTimingWindowRequest,
    CreateStudyArmRequest,
    CreateEpochRequest,
    CreateVisitRequest,
    CreateProcedureActivityRequest,
    SoACell,
    SoAMatrixProjectionResponse,
)
from tests.test_designer_differences import get_auth_headers


@pytest.fixture
def client():
    return TestClient(designer_app)


# ==========================================
# Unit Tests for Pydantic SoA Contracts
# ==========================================

# @req:PRD-MDR-001
def test_audit_metadata_defaults():
    """Verify default behavior of SoAAuditMetadata."""
    meta = SoAAuditMetadata(created_by="usr_test_123")
    assert meta.created_by == "usr_test_123"
    assert isinstance(meta.created_at, datetime)
    assert meta.version == "1.0.0"
    assert meta.updated_at is None
    assert meta.reason_for_change is None


# @req:PRD-MDR-004
def test_soa_cell_conditional_validation():
    """Verify that a conditional SoACell requires a non-empty reason."""
    # 1. Valid non-conditional cell (no reason needed)
    cell_valid_non_cond = SoACell(
        arm_id="arm_1",
        epoch_id="ep_1",
        visit_id="v_1",
        procedure_id="p_1",
        is_applicable=True,
        is_conditional=False
    )
    assert cell_valid_non_cond.is_conditional is False

    # 2. Valid conditional cell (reason is supplied)
    cell_valid_cond = SoACell(
        arm_id="arm_1",
        epoch_id="ep_1",
        visit_id="v_1",
        procedure_id="p_1",
        is_applicable=True,
        is_conditional=True,
        conditional_reason="If systolic BP is greater than 140 mmHg"
    )
    assert cell_valid_cond.is_conditional is True
    assert cell_valid_cond.conditional_reason == "If systolic BP is greater than 140 mmHg"

    # 3. Invalid conditional cell (is_conditional=True but reason is None)
    with pytest.raises(ValidationError) as exc_info:
        SoACell(
            arm_id="arm_1",
            epoch_id="ep_1",
            visit_id="v_1",
            procedure_id="p_1",
            is_applicable=True,
            is_conditional=True,
            conditional_reason=None
        )
    assert "Conditional entries must have a non-empty conditional_reason." in str(exc_info.value)

    # 4. Invalid conditional cell (is_conditional=True but reason is empty/whitespace)
    with pytest.raises(ValidationError) as exc_info_empty:
        SoACell(
            arm_id="arm_1",
            epoch_id="ep_1",
            visit_id="v_1",
            procedure_id="p_1",
            is_applicable=True,
            is_conditional=True,
            conditional_reason="   "
        )
    assert "Conditional entries must have a non-empty conditional_reason." in str(exc_info_empty.value)


# @req:PRD-MDR-004
def test_timing_window_model():
    """Verify fields and constraints of TimingWindow model."""
    meta = SoAAuditMetadata(created_by="usr_test")
    window = TimingWindow(
        id="win_1",
        name="Week 2 Window",
        target_day=14,
        window_back=2,
        window_forward=3,
        time_unit="DAYS",
        description="Timing window for visit 2",
        audit=meta
    )
    assert window.target_day == 14
    assert window.window_back == 2
    assert window.window_forward == 3
    assert window.time_unit == "DAYS"


# ==========================================
# Integration/API Tests for SoA Endpoints
# ==========================================

# @req:PRD-MDR-004
def test_get_soa_matrix_endpoint(client):
    """Verify that retrieval of SoA matrix projection returns correct structures."""
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/studies/study_ oncology/versions/v2.1/soa",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    # Enforce response parsing back into Pydantic structure for complete verification
    matrix = SoAMatrixProjectionResponse(**data)
    assert matrix.study_id == "study_ oncology"
    assert matrix.study_version_id == "v2.1"
    assert len(matrix.arms) == 2
    assert len(matrix.epochs) == 1
    assert len(matrix.visits) == 2
    assert len(matrix.procedures) == 2
    assert len(matrix.timing_windows) == 2
    assert len(matrix.cells) == 3

    # Check cell values and validations
    active_blood_cell = [c for c in matrix.cells if c.procedure_id == "proc_blood" and c.arm_id == "arm_active"][0]
    assert active_blood_cell.is_applicable is True
    assert active_blood_cell.is_conditional is False

    active_ecg_cell = [c for c in matrix.cells if c.procedure_id == "proc_ecg" and c.arm_id == "arm_active"][0]
    assert active_ecg_cell.is_applicable is True
    assert active_ecg_cell.is_conditional is True
    assert active_ecg_cell.conditional_reason == "Perform only if subject reports cardiovascular discomfort."


# @req:PRD-MDR-001
def test_create_study_arm_endpoint(client):
    """Verify POST request to create a study arm."""
    payload = {
        "name": "Experimental Combo Arm",
        "arm_type": "TREATMENT",
        "type_concept_id": "C999",
        "description": "Combines Treatment A and B",
        "change_reason": "Protocol amendment v1.2"
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/arms",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    arm = StudyArm(**data)
    assert arm.name == "Experimental Combo Arm"
    assert arm.arm_type == "TREATMENT"
    assert arm.type_concept_id == "C999"
    assert arm.audit.reason_for_change == "Protocol amendment v1.2"


# @req:PRD-MDR-001
def test_create_epoch_endpoint(client):
    """Verify POST request to create an epoch."""
    payload = {
        "name": "Follow-up Phase",
        "sequence_order": 3,
        "description": "Post-treatment monitoring",
        "change_reason": "Adding mandatory 6-month safety follow-up"
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/epochs",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    epoch = Epoch(**data)
    assert epoch.name == "Follow-up Phase"
    assert epoch.sequence_order == 3
    assert epoch.audit.reason_for_change == "Adding mandatory 6-month safety follow-up"


# @req:PRD-MDR-001
def test_create_visit_endpoint(client):
    """Verify POST request to create a visit."""
    payload = {
        "name": "Visit 3 (Week 4)",
        "visit_window_days": 28,
        "timing_window_id": "win_week4",
        "description": "End of cycle evaluation",
        "change_reason": "Adding cycle 2 assessment point"
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/visits",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    visit = Visit(**data)
    assert visit.name == "Visit 3 (Week 4)"
    assert visit.visit_window_days == 28
    assert visit.timing_window_id == "win_week4"
    assert visit.audit.reason_for_change == "Adding cycle 2 assessment point"


# @req:PRD-MDR-001
def test_create_procedure_activity_endpoint(client):
    """Verify POST request to create a procedure/activity."""
    payload = {
        "name": "Echocardiogram",
        "code": "456123",
        "description": "LVEF measurement",
        "change_reason": "Enforcing safety monitor for cardiotoxicity"
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/procedures",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    proc = ProcedureActivity(**data)
    assert proc.name == "Echocardiogram"
    assert proc.code == "456123"
    assert proc.audit.reason_for_change == "Enforcing safety monitor for cardiotoxicity"


# @req:PRD-MDR-001
def test_create_timing_window_endpoint(client):
    """Verify POST request to create a timing window."""
    payload = {
        "name": "Week 4 Tolerances",
        "target_day": 28,
        "window_back": 3,
        "window_forward": 3,
        "time_unit": "DAYS",
        "description": "Allows standard 3-day visit window",
        "change_reason": "Establishing explicit timing parameters for cycle 2"
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/timing-windows",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    win = TimingWindow(**data)
    assert win.name == "Week 4 Tolerances"
    assert win.target_day == 28
    assert win.window_back == 3
    assert win.window_forward == 3
    assert win.audit.reason_for_change == "Establishing explicit timing parameters for cycle 2"


# @req:PRD-MDR-001
def test_create_request_validation_fails_on_empty_reason(client):
    """Verify that POST mutations reject requests with empty change reasons."""
    payload = {
        "name": "Experimental Combo Arm",
        "arm_type": "TREATMENT",
        "change_reason": ""  # Invalid/empty reason
    }
    response = client.post(
        "/api/v1/studies/study_ oncology/versions/v2.1/arms",
        json=payload,
        headers=get_auth_headers()
    )
    assert response.status_code == 422
