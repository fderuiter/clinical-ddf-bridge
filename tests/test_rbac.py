import time

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from apps.etmf.database import db_manager as etmf_db_manager
from apps.etmf.main import app as etmf_app
from apps.etmf.models import Base as ETMFBase
from apps.execution.database.core import db_manager as exec_db_manager
from apps.execution.database.models import Base as ExecBase
from apps.execution.main import app as exec_app
from apps.gateway.main import generate_signature
from packages.security.rbac import (
    get_normalized_roles,
    verify_is_auditor,
    verify_not_auditor,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_dbs():
    """Setup in-memory SQLite databases for testing eTMF and Execution APIs."""
    etmf_db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with etmf_db_manager.engine.begin() as conn:
        await conn.run_sync(ETMFBase.metadata.create_all)

    exec_db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with exec_db_manager.engine.begin() as conn:
        await conn.run_sync(ExecBase.metadata.create_all)

    yield

    async with etmf_db_manager.engine.begin() as conn:
        await conn.run_sync(ETMFBase.metadata.drop_all)
    await etmf_db_manager.close()

    async with exec_db_manager.engine.begin() as conn:
        await conn.run_sync(ExecBase.metadata.drop_all)
    await exec_db_manager.close()


def get_auth_headers(
    roles: str = "admin", change_reason: str = "Authorized change"
) -> dict:
    """Helper to generate valid gateway V2 signed headers for testing."""
    timestamp = str(time.time())
    user_id = "test_user"
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


# ==========================================
# Unit Tests for packages/security/rbac.py
# ==========================================


def test_role_normalization_string() -> None:
    """Test get_normalized_roles with comma-separated string roles."""

    # Mocking FastAPI Request
    class MockRequest:
        def __init__(self, roles_str: str):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_str
            self.headers = {}

    request = MockRequest("Admin, CRA, Auditor")
    normalized = get_normalized_roles(request)
    assert normalized == ["admin", "cra", "auditor"]
    assert request.state.roles == ["admin", "cra", "auditor"]


def test_role_normalization_list() -> None:
    """Test get_normalized_roles with list-based roles."""

    class MockRequest:
        def __init__(self, roles_list: list):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_list
            self.headers = {}

    request = MockRequest(["Sponsor Admin", "Monitor"])
    normalized = get_normalized_roles(request)
    assert normalized == ["sponsor admin", "monitor"]
    assert request.state.roles == ["sponsor admin", "monitor"]


def test_verify_not_auditor_denies_auditors() -> None:
    """Test verify_not_auditor raises 403 for auditor personas."""

    class MockRequest:
        def __init__(self, roles_str: str):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_str
            self.headers = {}

    for auditor_role in ["auditor", "inspector", "regulatory_inspector"]:
        request = MockRequest(f"user,{auditor_role}")
        with pytest.raises(Exception) as exc_info:
            verify_not_auditor(request)
        assert exc_info.value.status_code == 403


def test_verify_not_auditor_allows_others() -> None:
    """Test verify_not_auditor allows non-auditor roles."""

    class MockRequest:
        def __init__(self, roles_str: str):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_str
            self.headers = {}

    request = MockRequest("admin,sponsor_dm,cra")
    assert verify_not_auditor(request) == ["admin", "sponsor_dm", "cra"]


def test_verify_is_auditor_denies_non_auditors() -> None:
    """Test verify_is_auditor raises 403 for non-auditors."""

    class MockRequest:
        def __init__(self, roles_str: str):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_str
            self.headers = {}

    request = MockRequest("admin,sponsor_dm,cra")
    with pytest.raises(Exception) as exc_info:
        verify_is_auditor(request)
    assert exc_info.value.status_code == 403


def test_verify_is_auditor_allows_auditors() -> None:
    """Test verify_is_auditor allows auditor personas."""

    class MockRequest:
        def __init__(self, roles_str: str):
            class State:
                pass

            self.state = State()
            self.state.roles = roles_str
            self.headers = {}

    for auditor_role in ["auditor", "inspector", "regulatory_inspector"]:
        request = MockRequest(auditor_role)
        assert verify_is_auditor(request) == [auditor_role]


# ==========================================
# Integration Tests for eTMF API Endpoints
# ==========================================


@pytest.mark.asyncio
async def test_etmf_ingest_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from ingesting eTMF documents."""
    client = TestClient(etmf_app)
    payload = {
        "study_id": "study_001",
        "artifact_type": "Clinical Trial Protocol",
        "filename": "protocol_v1.pdf",
        "content": "Protocol text",
        "mime_type": "application/pdf",
    }

    # 1. Reject "auditor" role
    resp = client.post(
        "/api/v1/etmf/ingest", json=payload, headers=get_auth_headers("auditor")
    )
    assert resp.status_code == 403

    # 2. Reject "inspector" role
    resp = client.post(
        "/api/v1/etmf/ingest", json=payload, headers=get_auth_headers("inspector")
    )
    assert resp.status_code == 403

    # 3. Reject "regulatory_inspector" role
    resp = client.post(
        "/api/v1/etmf/ingest",
        json=payload,
        headers=get_auth_headers("regulatory_inspector"),
    )
    assert resp.status_code == 403

    # 4. Allow non-auditor write role "admin"
    resp = client.post(
        "/api/v1/etmf/ingest", json=payload, headers=get_auth_headers("admin")
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_etmf_edl_creation_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from creating EDL expectations."""
    client = TestClient(etmf_app)
    payload = {
        "study_id": "study_xyz",
        "milestone": "INITIATION",
        "artifact_type": "Clinical Trial Protocol",
        "reason_for_change": "Adding signature requirement",
    }

    resp = client.post(
        "/api/v1/etmf/edl", json=payload, headers=get_auth_headers("auditor")
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/etmf/edl", json=payload, headers=get_auth_headers("admin")
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_etmf_edl_update_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from updating EDL expectations."""
    client = TestClient(etmf_app)

    # Ingest one first as admin
    payload = {
        "study_id": "study_xyz",
        "milestone": "INITIATION",
        "artifact_type": "Clinical Trial Protocol",
        "reason_for_change": "Adding signature requirement",
    }
    setup_resp = client.post(
        "/api/v1/etmf/edl", json=payload, headers=get_auth_headers("admin")
    )
    assert setup_resp.status_code == 201
    edl_id = setup_resp.json()["id"]

    # Try updating as auditor -> should be blocked
    resp = client.put(
        f"/api/v1/etmf/edl/{edl_id}", json=payload, headers=get_auth_headers("auditor")
    )
    assert resp.status_code == 403

    # Try updating as admin -> should succeed
    resp = client.put(
        f"/api/v1/etmf/edl/{edl_id}", json=payload, headers=get_auth_headers("admin")
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_etmf_document_transition_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from transitioning document statuses."""
    client = TestClient(etmf_app)

    # Ingest document as admin
    ingest_payload = {
        "study_id": "study_001",
        "artifact_type": "Clinical Trial Protocol",
        "filename": "protocol.pdf",
        "content": "Protocol text",
        "mime_type": "application/pdf",
    }
    ingest_resp = client.post(
        "/api/v1/etmf/ingest", json=ingest_payload, headers=get_auth_headers("admin")
    )
    assert ingest_resp.status_code == 201
    doc_id = ingest_resp.json()["document_id"]

    # Try transitioning status as auditor -> should fail with 403
    transition_payload = {
        "to_status": "TECHNICAL_QC",
        "reason_for_change": "Proceeding with QC process",
    }
    resp = client.post(
        f"/api/v1/etmf/documents/{doc_id}/transition",
        json=transition_payload,
        headers=get_auth_headers("auditor"),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_etmf_audit_logs_gated_to_auditors() -> None:
    """Verify GET /api/v1/etmf/audit-logs is gated to only authorized auditors and maintains self-auditing."""
    client = TestClient(etmf_app)

    # 1. Deny access to non-auditor "admin" role
    resp = client.get("/api/v1/etmf/audit-logs", headers=get_auth_headers("admin"))
    assert resp.status_code == 403

    # 2. Allow access to "auditor"
    resp = client.get("/api/v1/etmf/audit-logs", headers=get_auth_headers("auditor"))
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    # Check that AUDIT_VIEW self-audit event is recorded
    assert logs[0]["action"] == "AUDIT_VIEW"

    # 3. Allow access to "regulatory_inspector"
    resp = client.get(
        "/api/v1/etmf/audit-logs", headers=get_auth_headers("regulatory_inspector")
    )
    assert resp.status_code == 200


# ==========================================
# Integration Tests for Clinical Execution API
# ==========================================


@pytest.mark.asyncio
async def test_execution_subject_creation_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from creating clinical subjects."""
    client = TestClient(exec_app)
    payload = {
        "subject_id": "SUBJ_101",
        "study_id": "study_001",
        "demographics": {"name": "John Doe", "gender": "male"},
    }

    resp = client.post(
        "/api/v1/execution/subjects", json=payload, headers=get_auth_headers("auditor")
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/execution/subjects", json=payload, headers=get_auth_headers("admin")
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_execution_visit_creation_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from creating clinical visits."""
    client = TestClient(exec_app)
    payload = {
        "subject_id": "SUBJ_101",
        "visit_name": "Screening",
        "study_id": "study_001",
    }

    resp = client.post(
        "/api/v1/execution/visits",
        json=payload,
        headers=get_auth_headers("regulatory_inspector"),
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/execution/visits", json=payload, headers=get_auth_headers("admin")
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_execution_observation_creation_auditor_forbidden() -> None:
    """Verify auditor personas are forbidden from creating clinical observations."""
    client = TestClient(exec_app)
    payload = {
        "subject_id": "SUBJ_101",
        "study_id": "study_001",
        "domain": "VS",
        "test_code": "SYSBP",
        "test_name": "Systolic Blood Pressure",
        "value": 120.0,
        "unit": "mmHg",
    }

    resp = client.post(
        "/api/v1/execution/observations",
        json=payload,
        headers=get_auth_headers("inspector"),
    )
    assert resp.status_code == 403

    # Must register subject first for admin creation to pass if visit_id is missing or to infer study_id
    subj_payload = {
        "subject_id": "SUBJ_101",
        "study_id": "study_001",
    }
    client.post(
        "/api/v1/execution/subjects",
        json=subj_payload,
        headers=get_auth_headers("admin"),
    )

    resp = client.post(
        "/api/v1/execution/observations",
        json=payload,
        headers=get_auth_headers("admin"),
    )
    assert resp.status_code == 200
