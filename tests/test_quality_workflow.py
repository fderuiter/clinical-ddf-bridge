import time

import pytest
from fastapi.testclient import TestClient

from apps.gateway.main import generate_signature
from apps.quality.database import db_manager
from apps.quality.main import app
from apps.quality.models import (
    Base,
)


@pytest.fixture(autouse=True)
async def setup_quality_db():
    """
    Setup in-memory Quality database for workflow tests.
    """
    db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


def get_auth_headers(roles: str = "admin", change_reason: str = "Compliance change justification") -> dict:
    """
    Helper to generate valid gateway V2 signed headers for testing.
    """
    timestamp = str(time.time())
    user_id = "quality_test_user"
    sig = generate_signature(
        user_id, roles, timestamp, version="2", change_reason=change_reason
    )
    headers = {
        "X-User-Id": user_id,
        "X-User-Roles": roles,
        "X-Gateway-Timestamp": timestamp,
        "X-Gateway-Signature": sig,
        "X-Signature-Version": "2",
        "X-Change-Reason": change_reason,
    }
    return headers


def test_create_and_list_deviations():
    """
    Verify that a deviation can be created and retrieved via API.
    """
    # @req:PRD-SYS-001
    client = TestClient(app)
    headers = get_auth_headers(change_reason="Reporting protocol deviation")
    payload = {
        "study_id": "study_123",
        "site_id": "site_abc",
        "title": "Informed consent missing signature",
        "description": "The subject signed the form but did not date it.",
        "severity": "MAJOR",
        "type": "INFORMED_CONSENT",
        "is_protocol_violation": True
    }
    response = client.post("/api/v1/quality/deviations", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["study_id"] == "study_123"
    assert data["site_id"] == "site_abc"
    assert data["title"] == "Informed consent missing signature"
    assert data["status"] == "REPORTED"
    assert data["version_index"] == 1
    assert data["reason_for_change"] == "Reporting protocol deviation"

    # List deviations with filters
    response_list = client.get("/api/v1/quality/deviations?study_id=study_123", headers=headers)
    assert response_list.status_code == 200
    list_data = response_list.json()
    assert len(list_data) == 1
    assert list_data[0]["id"] == data["id"]

    # View deviation
    response_view = client.get(f"/api/v1/quality/deviations/{data['id']}", headers=headers)
    assert response_view.status_code == 200
    assert response_view.json()["id"] == data["id"]


def test_create_and_update_rca():
    """
    Verify that an RCA can be created or updated for an existing deviation.
    """
    # @req:PRD-SYS-001
    client = TestClient(app)
    headers = get_auth_headers(change_reason="Create deviation for RCA test")

    # 1. Create Deviation
    dev_payload = {
        "study_id": "study_123",
        "title": "Temp excursion",
        "description": "IP storage excursion",
        "severity": "CRITICAL",
        "type": "IP_MANAGEMENT",
        "is_protocol_violation": False
    }
    dev_res = client.post("/api/v1/quality/deviations", json=dev_payload, headers=headers)
    dev_id = dev_res.json()["id"]

    # 2. Attach RCA
    rca_headers = get_auth_headers(change_reason="Perform initial RCA investigation")
    rca_payload = {
        "methodology": "5 Whys",
        "investigation_details": "Power went down in facility",
        "root_cause_summary": "Backup generator failed"
    }
    rca_res = client.post(f"/api/v1/quality/deviations/{dev_id}/rca", json=rca_payload, headers=rca_headers)
    assert rca_res.status_code == 200
    rca_data = rca_res.json()
    assert rca_data["deviation_id"] == dev_id
    assert rca_data["methodology"] == "5 Whys"
    assert rca_data["version_index"] == 1

    # Verify parent deviation transitioned to RCA_COMPLETE
    dev_view = client.get(f"/api/v1/quality/deviations/{dev_id}", headers=rca_headers)
    assert dev_view.json()["status"] == "RCA_COMPLETE"
    assert dev_view.json()["version_index"] == 2

    # 3. Update RCA with optimistic lock check
    update_headers = get_auth_headers(change_reason="Update RCA with details")
    rca_payload_update = {
        "methodology": "Fishbone Diagram",
        "investigation_details": "Updated investigation details",
        "root_cause_summary": "Updated root cause summary",
        "version_index": 1
    }
    rca_update_res = client.put(f"/api/v1/quality/deviations/{dev_id}/rca", json=rca_payload_update, headers=update_headers)
    assert rca_update_res.status_code == 200
    assert rca_update_res.json()["version_index"] == 2
    assert rca_update_res.json()["methodology"] == "Fishbone Diagram"

    # 4. Trigger version conflict
    conflict_payload = {
        "methodology": "Fishbone Diagram",
        "investigation_details": "Conflict",
        "root_cause_summary": "Conflict",
        "version_index": 1  # Stale version index
    }
    conflict_res = client.put(f"/api/v1/quality/deviations/{dev_id}/rca", json=conflict_payload, headers=update_headers)
    assert conflict_res.status_code == 409
    assert "Version conflict" in conflict_res.json()["detail"]


def test_capa_creation_validations():
    """
    Verify that CAPA creation validates parent records and statuses.
    """
    # @req:PRD-SUB-001
    client = TestClient(app)
    headers = get_auth_headers(change_reason="Create deviation for CAPA validations")

    # 1. Non-existent deviation
    capa_payload = {
        "deviation_id": "non-existent-id",
        "capa_type": "CORRECTIVE",
        "action_plan": "Testing"
    }
    res = client.post("/api/v1/quality/capas", json=capa_payload, headers=headers)
    assert res.status_code == 422
    assert "Parent deviation" in res.json()["detail"]

    # 2. Create valid deviation
    dev_payload = {
        "study_id": "study_123",
        "title": "Temp excursion",
        "description": "IP storage excursion",
        "severity": "CRITICAL",
        "type": "IP_MANAGEMENT"
    }
    dev_res = client.post("/api/v1/quality/deviations", json=dev_payload, headers=headers)
    dev_id = dev_res.json()["id"]

    # 3. Supply invalid/mismatched RCA ID
    capa_payload_invalid_rca = {
        "deviation_id": dev_id,
        "rca_id": "non-existent-rca-id",
        "capa_type": "CORRECTIVE",
        "action_plan": "Testing"
    }
    res_rca = client.post("/api/v1/quality/capas", json=capa_payload_invalid_rca, headers=headers)
    assert res_rca.status_code == 422
    assert "RCA with ID" in res_rca.json()["detail"]


def test_capa_lifecycle_transitions():
    """
    Verify legal and illegal CAPA status transitions.
    """
    # @req:PRD-SUB-001
    client = TestClient(app)
    headers = get_auth_headers(change_reason="CAPA lifecycle testing")

    # 1. Create deviation and CAPA
    dev_payload = {
        "study_id": "study_123",
        "title": "Protocol violation",
        "description": "Protocol violation desc",
        "severity": "MAJOR",
        "type": "ELIGIBILITY"
    }
    dev_res = client.post("/api/v1/quality/deviations", json=dev_payload, headers=headers)
    dev_id = dev_res.json()["id"]

    capa_payload = {
        "deviation_id": dev_id,
        "capa_type": "CORRECTIVE",
        "action_plan": "Do training on eligibility"
    }
    capa_res = client.post("/api/v1/quality/capas", json=capa_payload, headers=headers)
    assert capa_res.status_code == 201
    capa_id = capa_res.json()["id"]
    assert capa_res.json()["status"] == "INITIATED"
    assert capa_res.json()["version_index"] == 1

    # Verify deviation status is CAPA_INITIATED
    dev_view = client.get(f"/api/v1/quality/deviations/{dev_id}", headers=headers)
    assert dev_view.json()["status"] == "CAPA_INITIATED"

    # 2. Transition: INITIATED -> UNDER_REVIEW (Legal)
    trans_res1 = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "UNDER_REVIEW", "version_index": 1},
        headers=headers
    )
    assert trans_res1.status_code == 200
    assert trans_res1.json()["status"] == "UNDER_REVIEW"
    assert trans_res1.json()["version_index"] == 2

    # 3. Transition: UNDER_REVIEW -> EFFECTIVENESS_CHECK (Illegal - bypasses IMPLEMENTATION)
    trans_res_illegal = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "EFFECTIVENESS_CHECK", "version_index": 2},
        headers=headers
    )
    assert trans_res_illegal.status_code == 422
    assert "Invalid transition" in trans_res_illegal.json()["detail"]

    # 4. Transition: UNDER_REVIEW -> IMPLEMENTATION (Legal)
    trans_res2 = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "IMPLEMENTATION", "version_index": 2},
        headers=headers
    )
    assert trans_res2.status_code == 200
    assert trans_res2.json()["status"] == "IMPLEMENTATION"
    assert trans_res2.json()["version_index"] == 3

    # 5. Transition: IMPLEMENTATION -> EFFECTIVENESS_CHECK (Legal)
    trans_res3 = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "EFFECTIVENESS_CHECK", "version_index": 3},
        headers=headers
    )
    assert trans_res3.status_code == 200
    assert trans_res3.json()["status"] == "EFFECTIVENESS_CHECK"
    assert trans_res3.json()["version_index"] == 4

    # 6. Transition: EFFECTIVENESS_CHECK -> CLOSED (Legal)
    trans_res4 = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "CLOSED", "version_index": 4},
        headers=headers
    )
    assert trans_res4.status_code == 200
    assert trans_res4.json()["status"] == "CLOSED"
    assert trans_res4.json()["version_index"] == 5

    # Verify deviation is CLOSED following CAPA closure
    dev_view2 = client.get(f"/api/v1/quality/deviations/{dev_id}", headers=headers)
    assert dev_view2.json()["status"] == "CLOSED"
    assert dev_view2.json()["version_index"] > 1

    # 7. Try to transition out of terminal state (Illegal)
    trans_terminal = client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "UNDER_REVIEW", "version_index": 5},
        headers=headers
    )
    assert trans_terminal.status_code == 422
    assert "terminal state" in trans_terminal.json()["detail"]


def test_capa_updates_and_concurrency():
    """
    Verify updates to CAPA records and optimistic locking behavior.
    """
    # @req:PRD-SUB-001
    client = TestClient(app)
    headers = get_auth_headers(change_reason="Concurrency testing")

    # 1. Create parent deviation and CAPA
    dev_payload = {
        "study_id": "study_123",
        "title": "IP Temp Excursion",
        "description": "IP excursion",
        "severity": "CRITICAL",
        "type": "IP_MANAGEMENT"
    }
    dev_res = client.post("/api/v1/quality/deviations", json=dev_payload, headers=headers)
    dev_id = dev_res.json()["id"]

    capa_payload = {
        "deviation_id": dev_id,
        "capa_type": "CORRECTIVE",
        "action_plan": "Initial Plan"
    }
    capa_res = client.post("/api/v1/quality/capas", json=capa_payload, headers=headers)
    capa_id = capa_res.json()["id"]

    # 2. Update CAPA details (Legal)
    update_res = client.put(
        f"/api/v1/quality/capas/{capa_id}",
        json={"action_plan": "Updated Action Plan", "version_index": 1},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["action_plan"] == "Updated Action Plan"
    assert update_res.json()["version_index"] == 2

    # 3. Update CAPA with stale version index (Illegal -> 409)
    stale_update_res = client.put(
        f"/api/v1/quality/capas/{capa_id}",
        json={"action_plan": "Stale Update Plan", "version_index": 1},
        headers=headers
    )
    assert stale_update_res.status_code == 409
    assert "Version conflict" in stale_update_res.json()["detail"]

    # 4. Update parent deviation status compatibility gate
    # Once closed, we can't create CAPA anymore
    client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "UNDER_REVIEW", "version_index": 2},
        headers=headers
    )
    client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "IMPLEMENTATION", "version_index": 3},
        headers=headers
    )
    client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "EFFECTIVENESS_CHECK", "version_index": 4},
        headers=headers
    )
    client.post(
        f"/api/v1/quality/capas/{capa_id}/transition",
        json={"to_status": "CLOSED", "version_index": 5},
        headers=headers
    )

    # 5. Try updating details of a closed CAPA (Illegal -> 422)
    closed_update = client.put(
        f"/api/v1/quality/capas/{capa_id}",
        json={"action_plan": "No changes allowed", "version_index": 6},
        headers=headers
    )
    assert closed_update.status_code == 422
    assert "terminal state" in closed_update.json()["detail"]
