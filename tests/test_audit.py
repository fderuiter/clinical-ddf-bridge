import datetime

import pytest
import pytest_asyncio
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

import apps.execution.database.audit  # noqa: F401 (Imported for side-effects: registers event listener)
from apps.execution.database.context import (
    current_change_reason,
    current_session,
    current_user_id,
)
from apps.execution.database.core import db_manager
from apps.execution.database.decorators import transactional
from apps.execution.database.models import AuditedModel, AuditLog, Base
from packages.security.context import (
    audit_context,
)


# Create a test model that extends AuditedModel
class ClinicalRecord(AuditedModel):
    __tablename__ = "clinical_records"
    data_value: Mapped[str] = mapped_column(String(255), nullable=True)


# Create a test model that extends Base but NOT AuditedModel (representing external models)
class MockTMFDocument(Base):
    __tablename__ = "tmf_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=True)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    import os

    from apps.execution.database.migrate import deploy_database_triggers

    db_manager.init_db(
        os.getenv(
            "TEST_DATABASE_URL",
            "sqlite+aiosqlite:///:memory:",
        ),
        echo=False,
    )
    async with db_manager.engine.begin() as conn:
        from sqlalchemy import text

        if db_manager.engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit_schema;"))
        await conn.run_sync(Base.metadata.create_all)
        await deploy_database_triggers(conn, db_manager.engine.dialect.name)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


@pytest.mark.asyncio
async def test_insert_generates_audit_log():
    # @req:PRD-SYS-001
    current_user_id.set("user_123")
    current_change_reason.set("initial setup")

    # Pass the getter method from db_manager so transactional gets the factory
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_record():
        session = current_session.get()
        record = ClinicalRecord(data_value="patient_a")
        session.add(record)
        await session.flush()
        await session.flush()
        return record

    record = await create_record()

    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].action == "INSERT"
        assert logs[0].user_id == "user_123"
        assert logs[0].change_reason == "initial setup"
        assert logs[0].new_values["data_value"] == "patient_a"
        assert logs[0].record_id == record.id
        assert logs[0].table_name == "clinical_records"
        assert logs[0].old_values is None
        assert logs[0].version_index == 1


@pytest.mark.asyncio
async def test_update_generates_audit_log():
    # @req:PRD-SYS-001
    # Insert initially
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_record():
        session = current_session.get()
        record = ClinicalRecord(data_value="patient_a")
        session.add(record)
        await session.flush()
        await session.flush()
        return record.id

    record_id = await create_record()

    current_user_id.set("user_456")
    current_change_reason.set("correction")

    @transactional(lambda: db_manager.get_session_maker()())
    async def update_record():
        session = current_session.get()
        result = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
        )
        record = result.scalars().first()
        record.data_value = "patient_a_updated"
        await session.flush()
        return record.version

    new_version = await update_record()

    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.timestamp))
        logs = result.scalars().all()

        assert len(logs) == 2
        assert logs[1].action == "UPDATE"
        assert logs[1].user_id == "user_456"
        assert logs[1].change_reason == "correction"
        assert logs[1].old_values["data_value"] == "patient_a"
        assert logs[1].new_values["data_value"] == "patient_a_updated"
        assert logs[1].version_index == 2
        assert new_version == 2


@pytest.mark.asyncio
async def test_soft_delete_generates_audit_log():
    # @req:PRD-SYS-002
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_record():
        session = current_session.get()
        record = ClinicalRecord(data_value="patient_to_delete")
        session.add(record)
        await session.flush()
        return record.id

    record_id = await create_record()

    @transactional(lambda: db_manager.get_session_maker()())
    async def delete_record():
        session = current_session.get()
        result = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
        )
        record = result.scalars().first()
        record.is_deleted = True

    await delete_record()

    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.timestamp))
        logs = result.scalars().all()

        assert len(logs) == 2
        assert logs[1].action == "DELETE"
        assert logs[1].old_values["is_deleted"] is False
        assert logs[1].new_values["is_deleted"] is True


@pytest.mark.asyncio
async def test_hard_delete_is_prevented():
    # @req:Trace-1
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_record():
        session = current_session.get()
        record = ClinicalRecord(data_value="patient_to_delete")
        session.add(record)
        await session.flush()
        return record.id

    record_id = await create_record()

    @transactional(lambda: db_manager.get_session_maker()())
    async def hard_delete_record():
        session = current_session.get()
        result = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
        )
        record = result.scalars().first()
        await session.delete(record)

    with pytest.raises(ValueError, match="Hard deletion .* is forbidden"):
        await hard_delete_record()


@pytest.mark.asyncio
async def test_rollback_prevents_orphan_audit_logs():
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        initial_count = len(result.scalars().all())

    @transactional(lambda: db_manager.get_session_maker()())
    async def failing_transaction():
        session = current_session.get()
        record = ClinicalRecord(data_value="will_fail")
        session.add(record)
        await session.flush()
        session.add(
            AuditLog(table_name="dummy", record_id="dummy", action="INSERT")
        )  # This is to make sure nothing flushes successfully
        # Trigger an exception intentionally
        raise RuntimeError("Intentional Failure")

    with pytest.raises(RuntimeError):
        await failing_transaction()

    # Verify no audit logs were persisted
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        final_count = len(result.scalars().all())
        assert final_count == initial_count


@pytest.mark.asyncio
async def test_read_only_queries_do_not_generate_audit_logs():
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_record():
        session = current_session.get()
        record = ClinicalRecord(data_value="read_only_test")
        session.add(record)
        await session.flush()
        await session.flush()
        return record.id

    record_id = await create_record()

    # Check current audit count
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        initial_count = len(result.scalars().all())

    @transactional(lambda: db_manager.get_session_maker()())
    async def read_record():
        session = current_session.get()
        result = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
        )
        record = result.scalars().first()
        return record.data_value

    val = await read_record()
    assert val == "read_only_test"

    # Verify count did not increase
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        final_count = len(result.scalars().all())
        assert final_count == initial_count


@pytest.mark.asyncio
async def test_audit_records_ip_and_custom_timestamp():
    """
    Verify that custom IP address and custom timestamp are correctly recorded in the audit logs.
    """
    custom_time = datetime.datetime(2026, 7, 24, 14, 32, 1, 0)

    with audit_context(
        user_id="dr_john_doe",
        change_reason="GCP protocol validation",
        ip_address="192.168.42.105",
        timestamp=custom_time,
    ):

        @transactional(lambda: db_manager.get_session_maker()())
        async def create_record():
            session = current_session.get()
            record = ClinicalRecord(data_value="patient_b")
            session.add(record)
            await session.flush()
            return record.id

        record_id = await create_record()

    async with db_manager.get_session_maker()() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.record_id == record_id)
        )
        log = result.scalars().first()

        assert log is not None
        assert log.user_id == "dr_john_doe"
        assert log.change_reason == "GCP protocol validation"
        assert log.ip_address == "192.168.42.105"
        assert log.timestamp == custom_time


@pytest.mark.asyncio
async def test_mixed_domain_session_clinical_logged_external_skipped():
    """
    Verify that in a shared database session containing both a clinical modification
    and an external domain model modification, only the clinical change is logged,
    while the external change is skipped.
    """
    current_user_id.set("user_mixed")
    current_change_reason.set("mixed transaction test")

    @transactional(lambda: db_manager.get_session_maker()())
    async def run_mixed_transaction():
        session = current_session.get()
        # Add clinical record
        clinical_rec = ClinicalRecord(data_value="clinical_data_1")
        session.add(clinical_rec)
        # Add external model record
        import uuid

        external_doc = MockTMFDocument(id=str(uuid.uuid4()), filename="doc_1.pdf")
        session.add(external_doc)
        await session.flush()
        return clinical_rec.id, external_doc.id

    clinical_id, external_id = await run_mixed_transaction()

    # Query the generated audit logs
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(select(AuditLog))
        logs = result.scalars().all()

        # We should only have 1 audit log entry corresponding to the clinical record
        assert len(logs) == 1
        assert logs[0].action == "INSERT"
        assert logs[0].table_name == "clinical_records"
        assert logs[0].record_id == clinical_id
        assert logs[0].new_values["data_value"] == "clinical_data_1"


@pytest.mark.asyncio
async def test_mixed_domain_session_hard_delete_clinical_fails_external_succeeds():
    """
    Verify that attempts to hard-delete clinical models in mixed-domain sessions
    raise a validation error and abort the transaction, while deleting external models
    succeeds without raising a validation error and without generating audit logs.
    """
    import uuid

    # 1. Insert initial records
    @transactional(lambda: db_manager.get_session_maker()())
    async def create_records():
        session = current_session.get()
        clinical_rec = ClinicalRecord(data_value="to_be_deleted")
        external_doc = MockTMFDocument(
            id=str(uuid.uuid4()), filename="to_be_deleted.pdf"
        )
        session.add_all([clinical_rec, external_doc])
        await session.flush()
        return clinical_rec.id, external_doc.id

    clinical_id, external_id = await create_records()

    # 2. Verify that deleting the clinical record fails
    @transactional(lambda: db_manager.get_session_maker()())
    async def delete_clinical():
        session = current_session.get()
        res = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == clinical_id)
        )
        clinical_rec = res.scalars().first()
        await session.delete(clinical_rec)
        await session.flush()

    with pytest.raises(
        ValueError, match="Hard deletion of ClinicalRecord is forbidden"
    ):
        await delete_clinical()

    # 3. Verify that deleting the external record succeeds and does not generate audit logs
    @transactional(lambda: db_manager.get_session_maker()())
    async def delete_external():
        session = current_session.get()
        res = await session.execute(
            select(MockTMFDocument).where(MockTMFDocument.id == external_id)
        )
        external_doc = res.scalars().first()
        await session.delete(external_doc)
        await session.flush()

    await delete_external()

    # Verify no new audit logs are generated for the delete action
    async with db_manager.get_session_maker()() as session:
        # We initially had 1 audit log for inserting the ClinicalRecord
        result = await session.execute(select(AuditLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].action == "INSERT"
        assert logs[0].table_name == "clinical_records"
        assert logs[0].record_id == clinical_id
