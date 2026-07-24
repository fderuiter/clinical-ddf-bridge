import hashlib
import hmac
import os
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text

from apps.execution.database.core import db_manager
from apps.execution.database.models import (
    AuditLog,
    Base,
    ClinicalObservation,
    ClinicalSubject,
    ClinicalVisit,
    SDVSignOff,
)
from apps.execution.main import app
from apps.execution.trial_lock import TrialLockManager

GATEWAY_SECRET = os.getenv("GATEWAY_SECRET", "internal-gateway-secret-12345")


def get_auth_headers(
    user_id="test_user", roles="admin", change_reason="system_operation"
):
    """Generate Gateway signature-compliant authentication headers."""
    import json

    timestamp = str(time.time())
    payload = {
        "change_reason": change_reason,
        "roles": roles,
        "timestamp": timestamp,
        "user_id": user_id,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        GATEWAY_SECRET.encode(), serialized.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "X-User-Id": user_id,
        "X-User-Roles": roles,
        "X-Gateway-Timestamp": timestamp,
        "X-Gateway-Signature": signature,
        "X-Signature-Version": "2",
        "X-Change-Reason": change_reason,
    }


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Setup in-memory SQLite database before each test and clear down after."""
    TrialLockManager.reset()
    db_manager.init_db("sqlite+aiosqlite:///:memory:")
    async with db_manager.engine.begin() as conn:
        if db_manager.engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit_schema;"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()
    TrialLockManager.reset()


@pytest.mark.asyncio
async def test_sdv_signoff_authorization_roles() -> None:
    # @req:PRD-QRY-005
    """Verify that only CRA and monitor roles are authorized to sign off."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "scope": "PAGE",
            "target_id": "PAGE-001",
            "subject_id": "SUBJ-001",
            "study_id": "STUDY-001",
        }

        # 1. Non-CRA / Non-monitor role should get HTTP 403
        res = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=payload,
            headers=get_auth_headers(roles="subject"),
        )
        assert res.status_code == 403

        res_inv = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=payload,
            headers=get_auth_headers(roles="investigator"),
        )
        assert res_inv.status_code == 403

        # 2. CRA or monitor role should bypass roles guard (but fail on subject not found as 400 validation check)
        res_cra = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=payload,
            headers=get_auth_headers(roles="CRA"),
        )
        assert res_cra.status_code == 400
        assert "Subject not found" in res_cra.json()["detail"]

        res_monitor = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=payload,
            headers=get_auth_headers(roles="monitor"),
        )
        assert res_monitor.status_code == 400
        assert "Subject not found" in res_monitor.json()["detail"]


@pytest.mark.asyncio
async def test_sdv_signoff_scopes_happy_paths() -> None:
    # @req:PRD-QRY-005
    """Verify happy-path sign-offs for FIELD, VISIT, and PAGE scopes with idempotency."""
    async with db_manager.get_session_maker()() as session:
        # Seed subject
        subj = ClinicalSubject(
            subject_id="SUBJ-GOOD",
            study_id="STUDY-GOOD",
        )
        # Seed observation
        obs = ClinicalObservation(
            id="OBS-101",
            subject_id="SUBJ-GOOD",
            study_id="STUDY-GOOD",
            domain="VS",
            test_code="SYSBP",
            test_name="Systolic",
            value=120.0,
        )
        # Seed visit
        visit = ClinicalVisit(
            id="VISIT-101",
            subject_id="SUBJ-GOOD",
            study_id="STUDY-GOOD",
            visit_name="Week 1",
        )
        session.add_all([subj, obs, visit])
        await session.commit()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. FIELD Scope Sign-Off
        field_payload = {
            "scope": "FIELD",
            "target_id": "OBS-101",
            "subject_id": "SUBJ-GOOD",
            "study_id": "STUDY-GOOD",
        }
        res_field = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=field_payload,
            headers=get_auth_headers(user_id="cra_jane", roles="CRA"),
        )
        assert res_field.status_code == 201
        data_field = res_field.json()
        assert data_field["scope"] == "FIELD"
        assert data_field["target_id"] == "OBS-101"
        assert data_field["is_verified"] is True
        assert data_field["verified_by"] == "cra_jane"

        # Verify observation itself was updated
        async with db_manager.get_session_maker()() as session:
            stmt = select(ClinicalObservation).where(
                ClinicalObservation.id == "OBS-101"
            )
            res_obs_db = await session.execute(stmt)
            obs_db = res_obs_db.scalar_one()
            assert obs_db.is_sdv_verified is True
            assert obs_db.sdv_verified_by == "cra_jane"

        # 2. Repeated sign-off (idempotency check)
        res_field_again = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=field_payload,
            headers=get_auth_headers(user_id="cra_jane_2", roles="CRA"),
        )
        assert res_field_again.status_code == 201
        data_field_again = res_field_again.json()
        assert data_field_again["id"] == data_field["id"]  # Same SDVSignOff ID
        assert data_field_again["verified_by"] == "cra_jane_2"  # Updated verifier

        # 3. VISIT Scope Sign-Off
        visit_payload = {
            "scope": "VISIT",
            "target_id": "VISIT-101",
            "subject_id": "SUBJ-GOOD",
            "study_id": "STUDY-GOOD",
        }
        res_visit = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=visit_payload,
            headers=get_auth_headers(user_id="cra_jane", roles="CRA"),
        )
        assert res_visit.status_code == 201
        data_visit = res_visit.json()
        assert data_visit["scope"] == "VISIT"
        assert data_visit["target_id"] == "VISIT-101"
        assert data_visit["is_verified"] is True

        # 4. PAGE Scope Sign-Off
        page_payload = {
            "scope": "PAGE",
            "target_id": "PAGE-101",
            "subject_id": "SUBJ-GOOD",
            "study_id": "STUDY-GOOD",
        }
        res_page = await client.post(
            "/api/v1/execution/sdv/signoff",
            json=page_payload,
            headers=get_auth_headers(user_id="cra_jane", roles="CRA"),
        )
        assert res_page.status_code == 201
        data_page = res_page.json()
        assert data_page["scope"] == "PAGE"
        assert data_page["target_id"] == "PAGE-101"
        assert data_page["is_verified"] is True


@pytest.mark.asyncio
async def test_sdv_signoff_coordinate_validation_failures() -> None:
    # @req:PRD-QRY-005
    """Verify that inconsistent or nonexistent target coordinates generate clear errors."""
    async with db_manager.get_session_maker()() as session:
        subj = ClinicalSubject(subject_id="SUBJ-A", study_id="STUDY-A")
        obs_other = ClinicalObservation(
            id="OBS-OTHER",
            subject_id="SUBJ-B",
            study_id="STUDY-B",
            domain="VS",
            test_code="SYSBP",
            test_name="Systolic",
        )
        session.add_all([subj, obs_other])
        await session.commit()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Subject exists, but observation doesn't
        res_nonexistent_obs = await client.post(
            "/api/v1/execution/sdv/signoff",
            json={
                "scope": "FIELD",
                "target_id": "NONEXISTENT",
                "subject_id": "SUBJ-A",
                "study_id": "STUDY-A",
            },
            headers=get_auth_headers(roles="CRA"),
        )
        assert res_nonexistent_obs.status_code == 404
        assert "Observation target not found" in res_nonexistent_obs.json()["detail"]

        # 2. Observation exists, but subject/study parameters mismatch the observation's own coordinates
        res_mismatch = await client.post(
            "/api/v1/execution/sdv/signoff",
            json={
                "scope": "FIELD",
                "target_id": "OBS-OTHER",
                "subject_id": "SUBJ-A",
                "study_id": "STUDY-A",
            },
            headers=get_auth_headers(roles="CRA"),
        )
        assert res_mismatch.status_code == 400
        assert "Inconsistent target coordinates" in res_mismatch.json()["detail"]


@pytest.mark.asyncio
@patch("apps.execution.trial_lock.NotificationRouter.send_dashboard_notification")
async def test_centralized_auto_drop_workflow(mock_notify: MagicMock) -> None:
    # @req:PRD-QRY-006
    """Verify that editing clinical values on a verified observation triggers auto-drop,

    rejects missing change reasons, clears verification state, sets signoff unverified,
    and dispatches a mockable dashboard notification.
    """
    async with db_manager.get_session_maker()() as session:
        subj = ClinicalSubject(subject_id="SUBJ-X", study_id="STUDY-Y")
        obs = ClinicalObservation(
            id="OBS-VERIFIED",
            subject_id="SUBJ-X",
            study_id="STUDY-Y",
            domain="VS",
            test_code="SYSBP",
            test_name="Systolic",
            value=120.0,
            is_sdv_verified=True,
            sdv_verified_by="cra_john",
            sdv_verified_at=datetime.utcnow(),
            visit_id="VISIT-ABC",
        )
        so = SDVSignOff(
            scope="FIELD",
            target_id="OBS-VERIFIED",
            subject_id="SUBJ-X",
            study_id="STUDY-Y",
            is_verified=True,
            verified_by="cra_john",
            verified_at=datetime.utcnow(),
        )
        session.add_all([subj, obs, so])
        await session.commit()

    # 1. Update clinical value without meaningful change reason (should raise ValueError)
    async with db_manager.get_session_maker()() as session:
        # Load observation
        res = await session.execute(
            select(ClinicalObservation).where(ClinicalObservation.id == "OBS-VERIFIED")
        )
        db_obs = res.scalar_one()
        db_obs.value = 135.0  # edit clinical value

        # Try to save with default change reason
        with pytest.raises(
            ValueError, match="Meaningful GxP change reason is required"
        ):
            await session.commit()

    # 2. Update with a meaningful change reason
    from packages.security.context import audit_context

    with audit_context(
        user_id="editor_user", change_reason="Correction of transcription error."
    ):
        async with db_manager.get_session_maker()() as session:
            res = await session.execute(
                select(ClinicalObservation).where(
                    ClinicalObservation.id == "OBS-VERIFIED"
                )
            )
            db_obs = res.scalar_one()
            db_obs.value = 135.0
            await session.commit()

    # 3. Verify that the observation verification state was cleared
    async with db_manager.get_session_maker()() as session:
        res = await session.execute(
            select(ClinicalObservation).where(ClinicalObservation.id == "OBS-VERIFIED")
        )
        db_obs = res.scalar_one()
        assert db_obs.is_sdv_verified is False
        assert db_obs.sdv_verified_by is None
        assert db_obs.sdv_verified_at is None

        # Verify that the SDVSignOff was marked unverified and has dropped details
        res_so = await session.execute(
            select(SDVSignOff).where(
                SDVSignOff.scope == "FIELD", SDVSignOff.target_id == "OBS-VERIFIED"
            )
        )
        db_so = res_so.scalar_one()
        assert db_so.is_verified is False
        assert db_so.dropped_reason == "Clinical value modified"
        assert db_so.dropped_at is not None

        # Verify Audit logs captured the transitions
        res_audit = await session.execute(
            select(AuditLog)
            .where(AuditLog.table_name == "clinical_observations")
            .order_by(AuditLog.timestamp.desc())
        )
        logs = res_audit.scalars().all()
        assert len(logs) > 0
        latest_audit = logs[0]
        assert latest_audit.old_values["value"] == 120.0
        assert latest_audit.new_values["value"] == 135.0
        assert latest_audit.old_values["is_sdv_verified"] is True
        assert latest_audit.new_values["is_sdv_verified"] is False
        assert latest_audit.change_reason == "Correction of transcription error."

    # 4. Verify that the notification was dispatched correctly
    mock_notify.assert_called_once()
    recipients, payload = mock_notify.call_args[0]
    assert recipients == ["cra_john"]
    assert (
        payload["message"]
        == "Previously verified field modified on Subject SUBJ-X - Visit VISIT-ABC."
    )
    assert payload["study_id"] == "STUDY-Y"
    assert payload["subject_id"] == "SUBJ-X"
    assert payload["visit_id"] == "VISIT-ABC"
    assert payload["editor"] == "editor_user"
    assert payload["change_reason"] == "Correction of transcription error."


@pytest.mark.asyncio
async def test_metadata_only_edits_do_not_drop_verification() -> None:
    # @req:PRD-QRY-006
    """Verify that metadata-only updates (which do not alter clinical value) do not drop verification."""
    async with db_manager.get_session_maker()() as session:
        subj = ClinicalSubject(subject_id="SUBJ-Z", study_id="STUDY-W")
        obs = ClinicalObservation(
            id="OBS-METADATA",
            subject_id="SUBJ-Z",
            study_id="STUDY-W",
            domain="VS",
            test_code="SYSBP",
            test_name="Systolic",
            value=120.0,
            is_sdv_verified=True,
            sdv_verified_by="cra_bill",
            sdv_verified_at=datetime.utcnow(),
            page_id="FORM-OLD",
        )
        session.add_all([subj, obs])
        await session.commit()

    # Update metadata field only (page_id)
    async with db_manager.get_session_maker()() as session:
        res = await session.execute(
            select(ClinicalObservation).where(ClinicalObservation.id == "OBS-METADATA")
        )
        db_obs = res.scalar_one()
        db_obs.page_id = "FORM-NEW"  # non-clinical-value edit
        await session.commit()

    # Verify verification state remained unchanged
    async with db_manager.get_session_maker()() as session:
        res = await session.execute(
            select(ClinicalObservation).where(ClinicalObservation.id == "OBS-METADATA")
        )
        db_obs = res.scalar_one()
        assert db_obs.is_sdv_verified is True
        assert db_obs.sdv_verified_by == "cra_bill"
        assert db_obs.page_id == "FORM-NEW"
