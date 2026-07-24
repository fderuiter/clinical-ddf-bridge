import time
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.ctms.database import db_manager
from apps.ctms.main import app
from apps.ctms.models import (
    Base,
    CTMSAuditLog,
    GeneratedLetter,
    MonitoringVisit,
    MonitoringVisitFinding,
)
from apps.gateway.main import generate_signature


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """
    Setup in-memory CTMS database for unit and integration testing.
    """
    db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


def get_auth_headers(roles: str = "admin", change_reason: str = "Authorized change") -> dict:
    """
    Helper to generate valid gateway V2 signed headers for testing.
    """
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
    }
    if change_reason:
        headers["X-Change-Reason"] = change_reason
    return headers


def test_ctms_health_check():
    """
    Verify health check of independent CTMS service.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ctms"


@pytest.mark.asyncio
async def test_create_and_list_studies_rbac():
    """
    Verify creation of studies with appropriate RBAC roles, Part 11 audit fields,
    and automatic writing to the append-only CTMSAuditLog.
    """
    client = TestClient(app)

    # 1. Non-permitted role (e.g. Site Investigator) trying to POST study -> 403 Forbidden
    unauthorized_headers = get_auth_headers(
        roles="Site Investigator", change_reason="Unauthorized attempt"
    )
    payload = {
        "study_id": "study_ctms_101",
        "name": "CTMS Trial site operations",
        "status": "ACTIVE",
    }
    response = client.post(
        "/api/v1/ctms/studies", json=payload, headers=unauthorized_headers
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

    # 2. Permitted role (e.g. Monitor) trying to POST study -> 201 Created
    authorized_headers = get_auth_headers(
        roles="Monitor", change_reason="Initiate study tracking in CTMS"
    )
    response_created = client.post(
        "/api/v1/ctms/studies", json=payload, headers=authorized_headers
    )
    assert response_created.status_code == 201
    created_data = response_created.json()
    assert created_data["study_id"] == "study_ctms_101"
    assert created_data["name"] == "CTMS Trial site operations"
    assert created_data["status"] == "ACTIVE"
    assert created_data["created_by"] == "test_user"
    assert created_data["reason_for_change"] == "Initiate study tracking in CTMS"
    assert created_data["version_index"] == 1

    # 3. Permitted role (e.g. Grants Manager) listing studies -> 200 OK
    grants_headers = get_auth_headers(roles="Grants Manager")
    response_list = client.get("/api/v1/ctms/studies", headers=grants_headers)
    assert response_list.status_code == 200
    studies = response_list.json()
    assert len(studies) == 1
    assert studies[0]["study_id"] == "study_ctms_101"

    # 4. Check CTMSAuditLog database records
    async with db_manager.get_session_maker()() as session:
        stmt = select(CTMSAuditLog).order_by(CTMSAuditLog.timestamp.desc())
        result = await session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) >= 2
        actions = [log.action for log in logs]
        assert "LIST_STUDIES" in actions
        assert "CREATE_STUDY" in actions

        create_log = next(log for log in logs if log.action == "CREATE_STUDY")
        assert create_log.user_id == "test_user"
        assert create_log.user_role == "Monitor"
        assert "Initiate study tracking" in create_log.details


@pytest.mark.asyncio
async def test_get_audit_trail_rbac():
    """
    Verify auditing trail endpoint RBAC restriction and logging behavior.
    """
    client = TestClient(app)

    # 1. Auditor retrieves the audit log list
    auditor_headers = get_auth_headers(roles="Auditor")
    response_logs = client.get("/api/v1/ctms/audit-logs", headers=auditor_headers)
    assert response_logs.status_code == 200
    logs = response_logs.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "VIEW_AUDIT_LOGS"

    # 2. Non-auditor (e.g. Site Investigator) denied access to audit logs
    investigator_headers = get_auth_headers(roles="Site Investigator")
    response_denied = client.get(
        "/api/v1/ctms/audit-logs", headers=investigator_headers
    )
    assert response_denied.status_code == 403


@pytest.mark.asyncio
async def test_database_manager_uninitialized():
    """
    Test exception when getting session maker from an uninitialized CTMS database manager.
    """
    from apps.ctms.database import CTMSDatabaseManager

    mgr = CTMSDatabaseManager()
    with pytest.raises(Exception) as exc_info:
        mgr.get_session_maker()
    assert "not initialized" in str(exc_info.value)


# --- New Monitoring Visits & Correspondence Tests ---

@pytest.mark.asyncio
async def test_monitoring_visit_workflow_happy_path():
    """
    Verify scheduling, completing, retrieving, and signing off on monitoring visits.
    Ensure letters are generated, stored, and retrieved without re-rendering.
    Ensure CTMSAuditLog is updated on every mutation.
    """
    client = TestClient(app)
    cra_headers = get_auth_headers(roles="CRA", change_reason="CRA operations")
    monitor_headers = get_auth_headers(roles="Monitor", change_reason="Monitor operations")

    # 1. Schedule a Visit (CRA role)
    scheduled_date = datetime.utcnow() + timedelta(days=5)
    payload = {
        "study_id": "study_001",
        "site_id": "site_99",
        "cra_id": "cra_fderuiter",
        "visit_type": "IMV",
        "scheduled_date": scheduled_date.isoformat(),
    }
    response = client.post(
        "/api/v1/ctms/monitoring-visits", json=payload, headers=cra_headers
    )
    assert response.status_code == 201
    visit_data = response.json()
    visit_id = visit_data["id"]
    assert visit_data["status"] == "SCHEDULED"
    assert visit_data["study_id"] == "study_001"
    assert visit_data["version_index"] == 1
    assert visit_data["created_by"] == "test_user"

    # Verify confirmation letter exists and is stored
    response_letters = client.get(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/letters", headers=cra_headers
    )
    assert response_letters.status_code == 200
    letters = response_letters.json()
    assert len(letters) == 1
    assert letters[0]["letter_type"] == "CONFIRMATION"
    assert "CONFIRMATION OF CLINICAL MONITORING VISIT" in letters[0]["rendered_content"]
    assert "study_001" in letters[0]["rendered_content"]
    assert "site_99" in letters[0]["rendered_content"]

    # Retrieve specific letter by type
    response_letter_type = client.get(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/letters/CONFIRMATION",
        headers=cra_headers,
    )
    assert response_letter_type.status_code == 200
    assert response_letter_type.json()["id"] == letters[0]["id"]

    # 2. Complete the Visit (CRA role) with findings
    actual_date = datetime.utcnow()
    completion_payload = {
        "actual_date": actual_date.isoformat(),
        "findings": [
            {
                "text": "Informed consent form missing date for Subject 01.",
                "severity": "CRITICAL",
                "resolution_status": "OPEN",
            },
            {
                "text": "Temperature log gap of 2 hours.",
                "severity": "MINOR",
                "resolution_status": "OPEN",
            },
        ],
    }
    response_complete = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=completion_payload,
        headers=cra_headers,
    )
    assert response_complete.status_code == 200
    completed_data = response_complete.json()
    assert completed_data["status"] == "COMPLETED"
    assert completed_data["version_index"] == 2
    assert completed_data["actual_date"] is not None

    # Verify follow-up letter exists and is stored
    response_letters_2 = client.get(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/letters", headers=cra_headers
    )
    assert response_letters_2.status_code == 200
    letters_2 = response_letters_2.json()
    assert len(letters_2) == 2
    types = [l["letter_type"] for l in letters_2]
    assert "CONFIRMATION" in types
    assert "FOLLOW_UP" in types

    follow_up = next(l for l in letters_2 if l["letter_type"] == "FOLLOW_UP")
    assert "CLINICAL MONITORING VISIT FOLLOW-UP LETTER" in follow_up["rendered_content"]
    assert "Informed consent form missing date" in follow_up["rendered_content"]
    assert "CRITICAL" in follow_up["rendered_content"]
    assert "Temperature log gap" in follow_up["rendered_content"]

    # Verify direct retrieval from database without dynamic re-rendering
    # We modify the stored letter in the DB directly and check if the API returns our modified content.
    async with db_manager.get_session_maker()() as session:
        stmt = select(GeneratedLetter).where(
            GeneratedLetter.visit_id == visit_id,
            GeneratedLetter.letter_type == "FOLLOW_UP",
        )
        res = await session.execute(stmt)
        stored_letter = res.scalars().first()
        assert stored_letter is not None
        stored_letter.rendered_content = "MODIFIED_TAMPERED_LETTER_CONTENT"
        session.add(stored_letter)
        await session.commit()

    # Query via API again
    response_tampered = client.get(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/letters/FOLLOW_UP",
        headers=cra_headers,
    )
    assert response_tampered.status_code == 200
    assert response_tampered.json()["rendered_content"] == "MODIFIED_TAMPERED_LETTER_CONTENT"

    # 3. Monitor supervisory sign-off (Monitor role)
    response_signoff = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/sign-off", headers=monitor_headers
    )
    assert response_signoff.status_code == 200
    signed_data = response_signoff.json()
    assert signed_data["status"] == "SIGNED_OFF"
    assert signed_data["version_index"] == 3

    # 4. Check CTMSAuditLog entries for all changes
    async with db_manager.get_session_maker()() as session:
        stmt = select(CTMSAuditLog).order_by(CTMSAuditLog.timestamp.desc())
        result = await session.execute(stmt)
        logs = result.scalars().all()

        actions = [l.action for l in logs]
        assert "CREATE_VISIT" in actions
        assert "GENERATE_LETTER" in actions
        assert "COMPLETE_VISIT" in actions
        assert "CREATE_FINDING" in actions
        assert "SIGN_OFF_VISIT" in actions

        signoff_log = next(l for l in logs if l.action == "SIGN_OFF_VISIT")
        assert signoff_log.user_role == "Monitor"
        assert "Monitor supervisory sign-off" in signoff_log.details


@pytest.mark.asyncio
async def test_monitoring_visit_workflow_rbac_denials():
    """
    Ensure strict RBAC enforcement:
    - Site Investigator cannot create, complete, list, retrieve, or sign off.
    - CRA cannot sign off.
    - Monitor cannot create or complete visits.
    """
    client = TestClient(app)

    # Pre-populate a scheduled visit using System/CRA role
    cra_headers = get_auth_headers(roles="CRA")
    scheduled_date = datetime.utcnow() + timedelta(days=2)
    payload = {
        "study_id": "study_001",
        "site_id": "site_99",
        "cra_id": "cra_fderuiter",
        "visit_type": "IMV",
        "scheduled_date": scheduled_date.isoformat(),
    }
    response_create = client.post(
        "/api/v1/ctms/monitoring-visits", json=payload, headers=cra_headers
    )
    assert response_create.status_code == 201
    visit_id = response_create.json()["id"]

    # 1. Site Investigator attempting to schedule visit -> 403
    si_headers = get_auth_headers(roles="Site Investigator")
    response_si_create = client.post(
        "/api/v1/ctms/monitoring-visits", json=payload, headers=si_headers
    )
    assert response_si_create.status_code == 403

    # 2. Monitor attempting to schedule visit -> 403 (Only CRA / Admin)
    monitor_headers = get_auth_headers(roles="Monitor")
    response_m_create = client.post(
        "/api/v1/ctms/monitoring-visits", json=payload, headers=monitor_headers
    )
    assert response_m_create.status_code == 403

    # 3. Monitor attempting to complete visit -> 403 (Only CRA / Admin)
    completion_payload = {
        "actual_date": datetime.utcnow().isoformat(),
        "findings": [],
    }
    response_m_complete = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=completion_payload,
        headers=monitor_headers,
    )
    assert response_m_complete.status_code == 403

    # Complete it via CRA role so we can test sign-off
    response_comp = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=completion_payload,
        headers=cra_headers,
    )
    assert response_comp.status_code == 200

    # 4. CRA attempting to sign off -> 403 (Only Monitor / Admin)
    response_cra_signoff = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/sign-off", headers=cra_headers
    )
    assert response_cra_signoff.status_code == 403

    # 5. Site Investigator attempting to retrieve letters -> 403
    response_si_letters = client.get(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/letters", headers=si_headers
    )
    assert response_si_letters.status_code == 403


@pytest.mark.asyncio
async def test_monitoring_visit_invalid_state_and_findings():
    """
    Test various edge-case failures:
    - Completing a non-existent visit
    - Signing off a non-completed (scheduled) visit
    - Completing a visit that is already completed
    - Finding with invalid severity
    - Retrieving non-existent letter
    """
    client = TestClient(app)
    cra_headers = get_auth_headers(roles="CRA")
    monitor_headers = get_auth_headers(roles="Monitor")

    # Schedule a visit
    scheduled_date = datetime.utcnow() + timedelta(days=2)
    payload = {
        "study_id": "study_001",
        "site_id": "site_99",
        "cra_id": "cra_fderuiter",
        "visit_type": "IMV",
        "scheduled_date": scheduled_date.isoformat(),
    }
    response_create = client.post(
        "/api/v1/ctms/monitoring-visits", json=payload, headers=cra_headers
    )
    assert response_create.status_code == 201
    visit_id = response_create.json()["id"]

    # Try signing off a scheduled visit -> 400
    response_invalid_signoff = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/sign-off", headers=monitor_headers
    )
    assert response_invalid_signoff.status_code == 400
    assert "Only completed" in response_invalid_signoff.json()["detail"]

    # Try completing with invalid severity -> 400
    bad_completion_payload = {
        "actual_date": datetime.utcnow().isoformat(),
        "findings": [
            {
                "text": "Bad severity finding",
                "severity": "SUPER_CRITICAL",
            }
        ],
    }
    response_bad_severity = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=bad_completion_payload,
        headers=cra_headers,
    )
    assert response_bad_severity.status_code == 400
    assert "Invalid finding severity" in response_bad_severity.json()["detail"]

    # Complete it properly
    good_completion_payload = {
        "actual_date": datetime.utcnow().isoformat(),
        "findings": [],
    }
    response_ok_completion = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=good_completion_payload,
        headers=cra_headers,
    )
    assert response_ok_completion.status_code == 200

    # Try completing a completed visit -> 400
    response_already_completed = client.post(
        f"/api/v1/ctms/monitoring-visits/{visit_id}/complete",
        json=good_completion_payload,
        headers=cra_headers,
    )
    assert response_already_completed.status_code == 400

    # Try retrieving non-existent letter type -> 404
    response_no_letter = client.get(
        f"/api/v1/ctms/monitoring-visits/non-existent-id/letters/CONFIRMATION",
        headers=cra_headers,
    )
    assert response_no_letter.status_code == 404
