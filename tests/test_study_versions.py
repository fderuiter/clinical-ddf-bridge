import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from apps.designer.db import (
    MOCK_RULES,
    MOCK_STUDY_VERSIONS,
    assert_mock_study_mutable,
    create_mock_study_version,
)
from apps.designer.delta import (
    ConcurrentLockingError,
    ImmutabilityViolationError,
    assert_graph_mutable,
    create_library_object_version,
    create_study_version,
    update_study_properties,
)
from apps.designer.main import app

GATEWAY_SECRET = "internal-gateway-secret-12345"


def get_auth_headers(
    user_id="test_designer",
    roles="STUDY_DESIGNER",
    change_reason="Study versioning operations",
):
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


# =====================================================================
# FAKE STRUCTURES TO TEST assert_graph_mutable WITHOUT TRIGGERING BYPASS
# =====================================================================


class FakeRecord:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data[key]


class FakeResult:
    def __init__(self, record_data):
        self.record_data = record_data

    async def single(self):
        return FakeRecord(self.record_data) if self.record_data else None


class FakeTransaction:
    def __init__(self, record_data=None):
        self.record_data = record_data
        self.queries = []

    async def run(self, query, **kwargs):
        self.queries.append((query, kwargs))
        return FakeResult(self.record_data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeSession:
    def __init__(self, tx):
        self.tx = tx

    async def begin_transaction(self):
        return self.tx

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeDriver:
    def __init__(self, tx):
        self.tx = tx

    def session(self):
        return FakeSession(self.tx)


# =====================================================================
# 1. UNIT TESTS FOR CUSTOM EXCEPTIONS AND DELTA FUNCTIONS (MOCKED NEO4J)
# =====================================================================


@pytest.mark.asyncio
async def test_neo4j_create_study_version_success():
    driver_mock = MagicMock()
    session_mock = AsyncMock()
    session_ctx = AsyncMock()
    session_ctx.__aenter__.return_value = session_mock
    driver_mock.session.return_value = session_ctx

    tx_mock = AsyncMock()
    tx_mock.__aenter__.return_value = tx_mock
    session_mock.begin_transaction.return_value = tx_mock

    # Side effects for tx.run:
    # 1. Lock study query
    lock_res = AsyncMock()
    # 2. Check existing versions (none found)
    check_res = AsyncMock()
    check_res.single.return_value = None
    # 3. Create version query
    create_res = AsyncMock()
    create_res.single.return_value = {"id": "version_123"}

    tx_mock.run.side_effect = [lock_res, check_res, create_res]

    version_id = await create_study_version(
        driver_mock,
        study_id="study_1",
        version_id="version_123",
        version_tag="1.0",
        status="DRAFT",
        version_index=1,
        created_by="user_designer",
    )

    assert version_id == "version_123"
    assert tx_mock.run.call_count == 3


@pytest.mark.asyncio
async def test_neo4j_create_study_version_duplicate_raises_conflict():
    driver_mock = MagicMock()
    session_mock = AsyncMock()
    session_ctx = AsyncMock()
    session_ctx.__aenter__.return_value = session_mock
    driver_mock.session.return_value = session_ctx

    tx_mock = AsyncMock()
    tx_mock.__aenter__.return_value = tx_mock
    session_mock.begin_transaction.return_value = tx_mock

    # Side effects for tx.run:
    # 1. Lock study query
    lock_res = AsyncMock()
    # 2. Check existing versions (finds an existing version)
    check_res = AsyncMock()
    check_res.single.return_value = {"id": "version_123"}

    tx_mock.run.side_effect = [lock_res, check_res]

    with pytest.raises(ConcurrentLockingError) as exc_info:
        await create_study_version(
            driver_mock,
            study_id="study_1",
            version_id="version_124",
            version_tag="1.0",
            status="DRAFT",
            version_index=1,
            created_by="user_designer",
        )

    assert "Version index or tag already exists" in str(exc_info.value)
    assert tx_mock.run.call_count == 2


@pytest.mark.asyncio
async def test_assert_graph_mutable_permits_draft_active():
    tx = FakeTransaction({"status": "DRAFT"})
    # Should succeed without raising exception
    await assert_graph_mutable(tx, study_id="study_1")

    tx = FakeTransaction({"status": "ACTIVE"})
    await assert_graph_mutable(tx, study_id="study_1")


@pytest.mark.asyncio
async def test_assert_graph_mutable_rejects_frozen_states():
    for frozen_state in ("LOCKED", "PUBLISHED", "ARCHIVED"):
        tx = FakeTransaction({"status": frozen_state})
        with pytest.raises(ImmutabilityViolationError):
            await assert_graph_mutable(tx, study_id="study_1")


@pytest.mark.asyncio
async def test_assert_graph_mutable_library_object_permits_active():
    tx = FakeTransaction({"status": "DRAFT"})
    # Should succeed without raising exception
    await assert_graph_mutable(tx, object_id="lib_1")


@pytest.mark.asyncio
async def test_assert_graph_mutable_library_object_rejects_frozen():
    tx = FakeTransaction({"status": "LOCKED"})
    with pytest.raises(ImmutabilityViolationError):
        await assert_graph_mutable(tx, object_id="lib_1")


@pytest.mark.asyncio
async def test_update_study_properties_guards():
    tx = FakeTransaction({"status": "LOCKED"})
    driver = FakeDriver(tx)

    with pytest.raises(ImmutabilityViolationError):
        await update_study_properties(
            driver, "study_1", "user_1", "change", {"title": "New Title"}
        )


@pytest.mark.asyncio
async def test_create_library_object_version_guards():
    tx = FakeTransaction({"status": "ARCHIVED"})
    driver = FakeDriver(tx)

    with pytest.raises(ImmutabilityViolationError):
        await create_library_object_version(
            driver, "lib_obj_1", {"name": "New Version"}
        )


# =====================================================================
# 2. IN-MEMORY FALLBACK MUTABLE TESTS (MOCK SYSTEM)
# =====================================================================


def test_mock_study_version_creation_and_immutability():
    study_id = "test_mock_study"
    MOCK_STUDY_VERSIONS[study_id] = []

    # 1. Initially mutable (no versions exist)
    assert_mock_study_mutable(study_id)

    # 2. Draft is mutable
    create_mock_study_version(
        study_id, {"version_tag": "1.0", "version_index": 1, "status": "DRAFT"}
    )
    assert_mock_study_mutable(study_id)

    # 3. Cannot create duplicate index/tag -> raises ConcurrentLockingError
    with pytest.raises(ConcurrentLockingError):
        create_mock_study_version(
            study_id, {"version_tag": "1.0", "version_index": 2, "status": "DRAFT"}
        )

    with pytest.raises(ConcurrentLockingError):
        create_mock_study_version(
            study_id, {"version_tag": "1.1", "version_index": 1, "status": "DRAFT"}
        )

    # 4. Create frozen version
    create_mock_study_version(
        study_id, {"version_tag": "2.0", "version_index": 2, "status": "LOCKED"}
    )

    # 5. Now immutable -> assert_mock_study_mutable raises ImmutabilityViolationError
    with pytest.raises(ImmutabilityViolationError):
        assert_mock_study_mutable(study_id)


# =====================================================================
# 3. REST API ENDPOINT INTEGRATION TESTS
# =====================================================================


@pytest.mark.asyncio
async def test_api_study_version_creation_and_guards():
    # Use a completely unique study ID to avoid contaminating other tests (like study_1)
    study_id = "study_versions_isolated_test"
    MOCK_STUDY_VERSIONS[study_id] = []
    MOCK_RULES.clear()

    # Seed mock study projection so that the endpoints can find it
    import copy

    from apps.designer.db import MOCK_STUDIES

    MOCK_STUDIES[study_id] = copy.deepcopy(MOCK_STUDIES["study_1"])
    MOCK_STUDIES[study_id]["study_id"] = study_id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Put study in a DRAFT version
        res_v1 = await client.post(
            f"/api/v1/studies/{study_id}/versions",
            json={
                "id": "v_1",
                "version_tag": "1.0",
                "status": "DRAFT",
                "version_index": 1,
            },
            headers=get_auth_headers(),
        )
        assert res_v1.status_code == 201

        # 2. Rule creation works on DRAFT
        rule_payload = {
            "type": "skip_logic",
            "condition": {
                "type": "comparison",
                "operator": "==",
                "operands": [
                    {"type": "field_ref", "field_ref": {"field_id": "act_1"}},
                    {"type": "constant", "value": "N"},
                ],
            },
            "action": "hide",
            "target_field": "act_2",
        }
        res_create_rule = await client.post(
            f"/api/v1/studies/{study_id}/rules",
            json=rule_payload,
            headers=get_auth_headers(),
        )
        assert res_create_rule.status_code == 201
        rule_id = res_create_rule.json()["id"]

        # 3. Create a duplicate study version -> 409 CONCURRENT_LOCKING_CONFLICT
        res_dup = await client.post(
            f"/api/v1/studies/{study_id}/versions",
            json={
                "id": "v_1_dup",
                "version_tag": "1.0",
                "status": "DRAFT",
                "version_index": 1,
            },
            headers=get_auth_headers(),
        )
        assert res_dup.status_code == 409
        assert "CONCURRENT_LOCKING_CONFLICT" in res_dup.json()["detail"]

        # 4. Advance study to LOCKED state
        res_v2 = await client.post(
            f"/api/v1/studies/{study_id}/versions",
            json={
                "id": "v_2",
                "version_tag": "2.0",
                "status": "LOCKED",
                "version_index": 2,
            },
            headers=get_auth_headers(),
        )
        assert res_v2.status_code == 201

        # 5. Rule mutations fail with 403 IMMUTABILITY_VIOLATION
        res_fail_create = await client.post(
            f"/api/v1/studies/{study_id}/rules",
            json=rule_payload,
            headers=get_auth_headers(),
        )
        assert res_fail_create.status_code == 403
        assert "IMMUTABILITY_VIOLATION" in res_fail_create.json()["detail"]

        # 6. Rule update fails with 403
        res_fail_update_put = await client.put(
            f"/api/v1/studies/{study_id}/rules/{rule_id}",
            json=rule_payload,
            headers=get_auth_headers(),
        )
        assert res_fail_update_put.status_code == 403
        assert "IMMUTABILITY_VIOLATION" in res_fail_update_put.json()["detail"]

        res_fail_delete = await client.delete(
            f"/api/v1/studies/{study_id}/rules/{rule_id}",
            headers=get_auth_headers(),
        )
        assert res_fail_delete.status_code == 403
        assert "IMMUTABILITY_VIOLATION" in res_fail_delete.json()["detail"]
