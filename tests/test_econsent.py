import time
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from audit import AuditFields
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from apps.econsent.database import EConsentDatabaseManager, db_manager
from apps.econsent.main import ConsentDocumentCreate, app
from apps.econsent.models import Base, ConsentAuditLog, ConsentDocument
from apps.gateway.main import generate_signature


@pytest_asyncio.fixture(autouse=True)
async def setup_econsent_db():
    """
    Setup in-memory eConsent database for unit and integration testing.
    """
    db_manager.init_db("sqlite+aiosqlite:///:memory:", echo=False)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


def get_auth_headers(
    user_id: str = "consent_test_user",
    roles: str = "investigator",
    change_reason: str = "eConsent initial creation",
) -> dict:
    """
    Helper to generate valid gateway V2 signed headers for eConsent testing.
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


def test_econsent_health_check():
    """
    Verify health check of independent eConsent service is publicly accessible
    and bypasses GatewayAuthMiddleware checks.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "econsent"


@pytest.mark.asyncio
async def test_econsent_database_schema_creation():
    """
    Verify that eConsent tables are properly created and can be queried.
    """
    async with db_manager.get_session_maker()() as session:
        docs_res = await session.execute(select(ConsentDocument))
        audit_res = await session.execute(select(ConsentAuditLog))

        assert docs_res.scalars().all() == []
        assert audit_res.scalars().all() == []


def test_uninitialized_database_manager_econsent():
    """
    Ensure the eConsent database manager raises an exception when accessed before initialization.
    """
    mgr = EConsentDatabaseManager()
    with pytest.raises(Exception) as exc_info:
        mgr.get_session_maker()
    assert "eConsent database session manager is not initialized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_database_url_override_and_init(monkeypatch):
    """
    Verify that database lifecycle supports ECONSENT_DATABASE_URL override.
    """
    monkeypatch.setenv("ECONSENT_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    mgr = EConsentDatabaseManager()
    mgr.init_db()  # Should pick up ECONSENT_DATABASE_URL from env
    assert mgr.engine is not None
    assert mgr.session_maker is not None
    await mgr.close()


def test_shared_audit_fields_validation():
    """
    Verify that AuditFields can be successfully instantiated with valid fields,
    and validates reason_for_change appropriately.
    """
    # Happy Path
    audit = AuditFields(
        created_by="user_456",
        reason_for_change="Initial creation",
    )
    assert audit.created_by == "user_456"
    assert audit.reason_for_change == "Initial creation"
    assert audit.version_index == 1
    assert isinstance(audit.created_at, datetime)

    # Check timezone is UTC
    assert abs((datetime.now(timezone.utc) - audit.created_at).total_seconds()) < 5

    # Validation: empty/blank reason
    with pytest.raises(ValidationError) as excinfo:
        AuditFields(
            created_by="user_456",
            reason_for_change="   ",
        )
    assert "Reason for change cannot be empty or consist only of whitespace." in str(
        excinfo.value
    )


def test_econsent_pydantic_schemas():
    """
    Verify that eConsent API schemas inherit from and enforce the shared AuditFields base.
    """
    # 1. Test ConsentDocumentCreate validation
    with pytest.raises(ValidationError) as excinfo:
        ConsentDocumentCreate(
            created_by="user_test",
            reason_for_change=" ",  # invalid
            study_id="study-01",
            site_id="site-01",
            document_name="Consent Form V1",
            content="Consent terms and details.",
        )
    assert "Reason for change cannot be empty" in str(excinfo.value)

    # Valid schema creation
    create_schema = ConsentDocumentCreate(
        created_by="user_test",
        reason_for_change="Legitimate creation of consent template",
        study_id="study-01",
        site_id="site-01",
        document_name="Consent Form V1",
        content="Consent terms and details.",
    )
    assert create_schema.study_id == "study-01"
    assert create_schema.reason_for_change == "Legitimate creation of consent template"


def test_gateway_auth_middleware_denials():
    """
    Verify that GatewayAuthMiddleware blocks requests with missing or invalid headers.
    """
    client = TestClient(app)

    # No headers on mutation -> 403 Forbidden
    response = client.post("/api/v1/econsent/documents", json={})
    assert response.status_code == 403
    assert "Missing gateway authentication headers" in response.json()["detail"]

    # No headers on GET -> 401 Unauthorized
    response = client.get("/api/v1/econsent/documents/some-uuid")
    assert response.status_code == 401
    assert "Missing gateway authentication headers" in response.json()["detail"]

    # Invalid signature -> 403 Forbidden on mutation
    headers = {
        "X-User-Id": "test_user",
        "X-User-Roles": "investigator",
        "X-Gateway-Timestamp": str(time.time()),
        "X-Gateway-Signature": "bad-sig",
        "X-Signature-Version": "2",
        "X-Change-Reason": "Some change",
    }
    response = client.post("/api/v1/econsent/documents", json={}, headers=headers)
    assert response.status_code == 403
    assert "Invalid gateway signature" in response.json()["detail"]


def test_econsent_document_lifecycle_and_audit_context():
    """
    Verify that calling eConsent document endpoints with valid gateway signatures
    successfully populates the request audit context, saves documents with exact audit fields,
    and appends correct Part 11 entries to the immutable ConsentAuditLog.
    """
    client = TestClient(app)

    # 1. Create a document
    doc_payload = {
        "created_by": "test_author",
        "reason_for_change": "Initial creation reason",
        "version_index": 1,
        "study_id": "study-xyz",
        "site_id": "site-999",
        "document_name": "Informed Consent Form V2.0",
        "content": "I hereby consent to participate in this clinical investigation.",
    }

    headers = get_auth_headers(
        user_id="consent_creator",
        roles="Grants Manager",
        change_reason="Deploying new consent form version",
    )

    response = client.post(
        "/api/v1/econsent/documents", json=doc_payload, headers=headers
    )
    assert response.status_code == 201
    created_data = response.json()

    assert created_data["id"] is not None
    assert created_data["study_id"] == "study-xyz"
    assert created_data["site_id"] == "site-999"
    assert created_data["document_name"] == "Informed Consent Form V2.0"
    assert created_data["content"].startswith("I hereby consent")

    # Created_by and reason_for_change are extracted from the gateway headers
    assert created_data["created_by"] == "consent_creator"
    assert created_data["reason_for_change"] == "Deploying new consent form version"
    assert created_data["version_index"] == 1

    doc_id = created_data["id"]

    # 2. Retrieve/View the document
    view_headers = get_auth_headers(
        user_id="consent_viewer",
        roles="Monitor",
        change_reason="Audit verification read",
    )
    response = client.get(f"/api/v1/econsent/documents/{doc_id}", headers=view_headers)
    assert response.status_code == 200
    retrieved_data = response.json()
    assert retrieved_data["id"] == doc_id
    assert retrieved_data["document_name"] == "Informed Consent Form V2.0"

    # 3. Verify Database and Part 11 Audit Trail Entries
    async def verify_db():
        async with db_manager.get_session_maker()() as session:
            # Check document state in DB
            stmt = select(ConsentDocument).where(ConsentDocument.id == doc_id)
            doc_res = await session.execute(stmt)
            db_doc = doc_res.scalar_one()
            assert db_doc.created_by == "consent_creator"
            assert db_doc.reason_for_change == "Deploying new consent form version"

            # Check audit logs in chronological order
            audit_stmt = select(ConsentAuditLog).order_by(
                ConsentAuditLog.timestamp.asc()
            )
            audit_res = await session.execute(audit_stmt)
            logs = audit_res.scalars().all()

            assert len(logs) == 2

            # Log 1: CREATE_DOCUMENT
            create_log = logs[0]
            assert create_log.actor_id == "consent_creator"
            assert create_log.actor_role == "Grants Manager"
            assert create_log.action == "CREATE_DOCUMENT"
            assert create_log.document_id == doc_id
            assert "Created consent document" in create_log.details
            assert create_log.reason_for_change == "Deploying new consent form version"

            # Log 2: VIEW_DOCUMENT
            view_log = logs[1]
            assert view_log.actor_id == "consent_viewer"
            assert view_log.actor_role == "Monitor"
            assert view_log.action == "VIEW_DOCUMENT"
            assert view_log.document_id == doc_id
            assert "Viewed consent document" in view_log.details
            assert view_log.reason_for_change == "Audit verification read"

    # Run the verification block
    import asyncio

    asyncio.run(verify_db())


def test_econsent_get_not_found():
    """
    Verify 404 behavior for non-existent eConsent documents.
    """
    client = TestClient(app)
    headers = get_auth_headers()
    response = client.get(
        "/api/v1/econsent/documents/non-existent-uuid", headers=headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
