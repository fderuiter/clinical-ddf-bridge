import time

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.gateway.main import generate_signature
from apps.notifications.database import db_manager
from apps.notifications.main import app
from apps.notifications.models import (
    Base,
    Notification,
    NotificationAuditLog,
    NotificationCategory,
    NotificationPriority,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_notifications_db():
    """
    Setup in-memory Notifications database for unit and integration testing.
    """
    db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


def get_auth_headers(
    user_id: str = "notifications_test_user",
    roles: str = "admin",
    change_reason: str = "",
) -> dict:
    """
    Helper to generate valid gateway V2 signed headers for testing.
    """
    timestamp = str(time.time())
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


def test_notifications_health_check():
    """
    Verify health check of independent Notifications service.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "notifications"


@pytest.mark.asyncio
async def test_notifications_database_schema_creation():
    """
    Verify that notification tables can be created and queried successfully.
    """
    async with db_manager.get_session_maker()() as session:
        notifications = await session.execute(select(Notification))
        logs = await session.execute(select(NotificationAuditLog))

        assert notifications.scalars().all() == []
        assert logs.scalars().all() == []


@pytest.mark.asyncio
async def test_notification_creation_and_auditing():
    """
    Verify that creating a notification persists all fields and writes an audit log.
    """
    client = TestClient(app)
    headers = get_auth_headers(
        user_id="user_creator",
        roles="Grants Manager",
        change_reason="Notify principal investigator",
    )

    payload = {
        "recipient_user_id": "pi_john",
        "recipient_role": "investigator",
        "category": "ACTION_ITEMS",
        "priority": "HIGH",
        "channels": "IN_APP,EMAIL",
        "message_content": "Please sign off on the pending visit log.",
        "related_entity_id": "visit_abc_123",
        "related_entity_type": "VISIT",
    }

    response = client.post("/api/v1/notifications", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["recipient_user_id"] == "pi_john"
    assert data["recipient_role"] == "investigator"
    assert data["category"] == "ACTION_ITEMS"
    assert data["priority"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["delivery_state"] == "DELIVERED"
    assert data["version_index"] == 1

    # Verify audit log was written
    async with db_manager.get_session_maker()() as session:
        stmt = select(NotificationAuditLog).where(
            NotificationAuditLog.action == "NOTIFICATION_CREATE"
        )
        res = await session.execute(stmt)
        audit = res.scalars().first()
        assert audit is not None
        assert audit.user_id == "user_creator"
        assert "grants manager" in audit.user_role
        assert "pi_john" in audit.details


@pytest.mark.asyncio
async def test_notification_list_visibility_and_filtering():
    """
    Verify target-based visibility: users can only fetch notifications for their user ID or roles, or global.
    """
    # Pre-seed notifications
    async with db_manager.get_session_maker()() as session:
        notif_user = Notification(
            recipient_user_id="alice",
            recipient_role="admin",
            category=NotificationCategory.ALERTS,
            priority=NotificationPriority.CRITICAL,
            message_content="For Alice specifically",
            created_by="system",
            reason_for_change="Initial seed",
        )
        notif_role = Notification(
            recipient_user_id="bob",
            recipient_role="investigator",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.MEDIUM,
            message_content="For Investigators",
            created_by="system",
            reason_for_change="Initial seed",
        )
        notif_other = Notification(
            recipient_user_id="charlie",
            recipient_role="monitor",
            category=NotificationCategory.ACTION_ITEMS,
            priority=NotificationPriority.LOW,
            message_content="For Charlie/Monitor",
            created_by="system",
            reason_for_change="Initial seed",
        )
        notif_global = Notification(
            recipient_user_id=None,
            recipient_role=None,
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.LOW,
            message_content="Global broadcast",
            created_by="system",
            reason_for_change="Initial seed",
        )
        session.add_all([notif_user, notif_role, notif_other, notif_global])
        await session.commit()

    client = TestClient(app)

    # 1. Fetch as Alice (roles: admin). Should see "For Alice specifically" and "Global broadcast".
    # Note that although alice's role is admin, but recipient_user_id matches, or recipient_role matches (both match for Alice).
    headers_alice = get_auth_headers(user_id="alice", roles="admin")
    response = client.get("/api/v1/notifications", headers=headers_alice)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    contents = [n["message_content"] for n in data]
    assert "For Alice specifically" in contents
    assert "Global broadcast" in contents

    # 2. Fetch as Dave (roles: investigator). Dave does not have a user ID match, but role is 'investigator'.
    # Should see "For Investigators" (matching recipient_role="investigator") and "Global broadcast".
    headers_dave = get_auth_headers(user_id="dave", roles="investigator")
    response = client.get("/api/v1/notifications", headers=headers_dave)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    contents = [n["message_content"] for n in data]
    assert "For Investigators" in contents
    assert "Global broadcast" in contents

    # 3. List with priority filter
    response = client.get(
        "/api/v1/notifications?priority=CRITICAL", headers=headers_alice
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["message_content"] == "For Alice specifically"


@pytest.mark.asyncio
async def test_notification_detail_visibility():
    """
    Verify detail endpoint visibility restrictions.
    """
    async with db_manager.get_session_maker()() as session:
        notif = Notification(
            recipient_user_id="alice",
            recipient_role="admin",
            category=NotificationCategory.ALERTS,
            priority=NotificationPriority.CRITICAL,
            message_content="Super secret alert for Alice",
            created_by="system",
            reason_for_change="Initial seed",
        )
        session.add(notif)
        await session.commit()
        notif_id = notif.id

    client = TestClient(app)

    # Alice can view her notification
    headers_alice = get_auth_headers(user_id="alice", roles="admin")
    res1 = client.get(f"/api/v1/notifications/{notif_id}", headers=headers_alice)
    assert res1.status_code == 200
    assert res1.json()["message_content"] == "Super secret alert for Alice"

    # Bob (roles: investigator) cannot view Alice's notification -> 403 Forbidden
    headers_bob = get_auth_headers(user_id="bob", roles="investigator")
    res2 = client.get(f"/api/v1/notifications/{notif_id}", headers=headers_bob)
    assert res2.status_code == 403
    assert "Recipient target boundary violation" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_lifecycle_transitions_and_justifications():
    """
    Verify state transitions OPEN -> ACKNOWLEDGED -> RESOLVED, requiring change reasons.
    """
    async with db_manager.get_session_maker()() as session:
        notif = Notification(
            recipient_user_id="alice",
            recipient_role="admin",
            category=NotificationCategory.ALERTS,
            priority=NotificationPriority.CRITICAL,
            message_content="Action required",
            created_by="system",
            reason_for_change="Initial seed",
        )
        session.add(notif)
        await session.commit()
        notif_id = notif.id

    client = TestClient(app)

    # 1. Transition: Acknowledge. Must supply change reason.
    headers_no_reason = get_auth_headers(user_id="alice", roles="admin")
    res = client.post(
        f"/api/v1/notifications/{notif_id}/acknowledge", headers=headers_no_reason
    )
    # The gateway auth middleware blocks non-GET mutations missing X-Change-Reason
    assert res.status_code == 403

    headers_ack = get_auth_headers(
        user_id="alice", roles="admin", change_reason="I have read this notification"
    )
    res_ack = client.post(
        f"/api/v1/notifications/{notif_id}/acknowledge", headers=headers_ack
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "ACKNOWLEDGED"
    assert res_ack.json()["version_index"] == 2
    assert res_ack.json()["reason_for_change"] == "I have read this notification"

    # 2. Cannot acknowledge again
    res_ack_double = client.post(
        f"/api/v1/notifications/{notif_id}/acknowledge", headers=headers_ack
    )
    assert res_ack_double.status_code == 422
    assert "Invalid transition" in res_ack_double.json()["detail"]

    # 3. Transition: Resolve. Must supply change reason.
    headers_res = get_auth_headers(
        user_id="alice", roles="admin", change_reason="Issue resolved in clinical DB"
    )
    res_resolve = client.post(
        f"/api/v1/notifications/{notif_id}/resolve", headers=headers_res
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"
    assert res_resolve.json()["version_index"] == 3

    # 4. Cannot resolve once already resolved
    res_resolve_double = client.post(
        f"/api/v1/notifications/{notif_id}/resolve", headers=headers_res
    )
    assert res_resolve_double.status_code == 422


@pytest.mark.asyncio
async def test_direct_transition_open_to_resolved():
    """
    Verify that an OPEN notification can directly transition to RESOLVED.
    """
    async with db_manager.get_session_maker()() as session:
        notif = Notification(
            recipient_user_id="alice",
            recipient_role="admin",
            category=NotificationCategory.ALERTS,
            priority=NotificationPriority.CRITICAL,
            message_content="Direct resolve test",
            created_by="system",
            reason_for_change="Initial seed",
        )
        session.add(notif)
        await session.commit()
        notif_id = notif.id

    client = TestClient(app)

    headers_res = get_auth_headers(
        user_id="alice",
        roles="admin",
        change_reason="Direct resolution from open status",
    )
    res_resolve = client.post(
        f"/api/v1/notifications/{notif_id}/resolve", headers=headers_res
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"
    assert res_resolve.json()["version_index"] == 2
