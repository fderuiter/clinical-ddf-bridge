import os

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from apps.execution.database.core import db_manager
from apps.execution.database.models import (
    AuditLog,
    Base,
    ClinicalCodingAssignment,
    DictionaryImportJob,
    MedDRAHierarchy,
    MedDRATerm,
    WHODrugRecord,
)
from apps.execution.trial_lock import TrialLockManager


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    from apps.execution.database.migrate import deploy_database_triggers

    TrialLockManager.reset()

    db_manager.init_db(
        os.getenv(
            "TEST_DATABASE_URL",
            "sqlite+aiosqlite:///:memory:",
        ),
        echo=False,
    )
    async with db_manager.engine.begin() as conn:
        if db_manager.engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit_schema;"))
        await conn.run_sync(Base.metadata.create_all)
        await deploy_database_triggers(conn, db_manager.engine.dialect.name)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()
    TrialLockManager.reset()


@pytest.mark.asyncio
async def test_meddra_term_unique_constraint():
    """Verify that unique constraints prevent duplicate terminology records for identical version, code, and level."""
    # First insert
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            term1 = MedDRATerm(
                dictionary_version="26.0",
                code="10019211",
                term_name="Headache",
                level="LLT",
            )
            session.add(term1)

    # Second insert with identical version, code, and level should fail
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            term2 = MedDRATerm(
                dictionary_version="26.0",
                code="10019211",
                term_name="Cephalea",
                level="LLT",
            )
            session.add(term2)
            with pytest.raises(IntegrityError):
                await session.commit()


@pytest.mark.asyncio
async def test_whodrug_record_unique_constraint():
    """Verify that unique constraints prevent duplicate WHODrug record inserts for identical version and drug_code."""
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            drug1 = WHODrugRecord(
                dictionary_version="2024-03",
                drug_code="00010101001",
                preferred_name="ASPIRIN",
                drug_name="ASPIRIN TABLET",
            )
            session.add(drug1)

    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            drug2 = WHODrugRecord(
                dictionary_version="2024-03",
                drug_code="00010101001",
                preferred_name="ASPIRIN PAIN RELIEF",
                drug_name="ASPIRIN FORTE",
            )
            session.add(drug2)
            with pytest.raises(IntegrityError):
                await session.commit()


@pytest.mark.asyncio
async def test_lookup_and_indexes():
    """Assert that lookup-oriented index queries function correctly on terminology tables."""
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            term1 = MedDRATerm(
                dictionary_version="26.0",
                code="10019205",
                term_name="Nervous system disorders",
                level="SOC",
            )
            session.add(term1)

            hierarchy1 = MedDRAHierarchy(
                dictionary_version="26.0",
                llt_code="10019211",
                pt_code="10019211",
                hlt_code="10019231",
                hlgt_code="10029214",
                soc_code="10029205",
                primary_soc_flag="Y",
            )
            session.add(hierarchy1)

    async with db_manager.get_session_maker()() as session:
        # Test term query
        term_stmt = select(MedDRATerm).where(
            MedDRATerm.dictionary_version == "26.0",
            MedDRATerm.code == "10019205",
            MedDRATerm.level == "SOC"
        )
        term_res = await session.execute(term_stmt)
        queried_term = term_res.scalar_one_or_none()
        assert queried_term is not None
        assert queried_term.term_name == "Nervous system disorders"

        # Test hierarchy query
        hier_stmt = select(MedDRAHierarchy).where(
            MedDRAHierarchy.dictionary_version == "26.0",
            MedDRAHierarchy.pt_code == "10019211"
        )
        hier_res = await session.execute(hier_stmt)
        queried_hier = hier_res.scalar_one_or_none()
        assert queried_hier is not None
        assert queried_hier.soc_code == "10029205"


@pytest.mark.asyncio
async def test_audit_trigger_logging_on_coding_workflow():
    """Verify that mutations on clinical coding models write audit trail records correctly."""
    # 1. INSERT audit log test
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            assignment = ClinicalCodingAssignment(
                verbatim_text="headache symptom",
                source_field="AE.AETERM",
                observation_id="obs_123",
                dictionary_type="MEDDRA",
                dictionary_version="26.0",
                coded_code="10019211",
                coded_term="Headache",
                status="CODED",
            )
            session.add(assignment)

    # Verify INSERT audit log exists
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            res = await session.execute(
                select(AuditLog).where(
                    AuditLog.table_name == "clinical_coding_assignments"
                )
            )
            logs = res.scalars().all()
            insert_logs = [log for log in logs if log.action == "INSERT"]
            assert len(insert_logs) >= 1
            assert any(lg.new_values["verbatim_text"] == "headache symptom" for lg in insert_logs)
            assert any(lg.new_values["coded_code"] == "10019211" for lg in insert_logs)

    # 2. UPDATE audit log test
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            # Query and update status
            stmt = select(ClinicalCodingAssignment).where(
                ClinicalCodingAssignment.observation_id == "obs_123"
            )
            res = await session.execute(stmt)
            obj = res.scalar_one()
            obj.status = "RECODING_REQUIRED"

    # Verify UPDATE audit log is recorded
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            res = await session.execute(
                select(AuditLog).where(
                    AuditLog.table_name == "clinical_coding_assignments"
                )
            )
            logs = res.scalars().all()
            update_logs = [log for log in logs if log.action == "UPDATE"]
            assert len(update_logs) >= 1
            assert any(lg.old_values["status"] == "CODED" for lg in update_logs)
            assert any(lg.new_values["status"] == "RECODING_REQUIRED" for lg in update_logs)

    # 3. Prevent hard delete, but allow soft delete
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            # Hard delete should raise exception from trigger/session handler
            with pytest.raises(Exception, match="Hard deletions are strictly forbidden"):
                await session.execute(
                    text("DELETE FROM clinical_coding_assignments WHERE observation_id = 'obs_123';")
                )

    # Soft delete instead
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            stmt = select(ClinicalCodingAssignment).where(
                ClinicalCodingAssignment.observation_id == "obs_123"
            )
            res = await session.execute(stmt)
            obj = res.scalar_one()
            obj.is_deleted = True

    # Verify soft delete maps to 'DELETE' action in AuditLog
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            res = await session.execute(
                select(AuditLog).where(
                    AuditLog.table_name == "clinical_coding_assignments"
                )
            )
            logs = res.scalars().all()
            delete_logs = [log for log in logs if log.action == "DELETE"]
            assert len(delete_logs) >= 1
            assert any(lg.old_values["is_deleted"] is False for lg in delete_logs)
            assert any(lg.new_values["is_deleted"] is True for lg in delete_logs)


@pytest.mark.asyncio
async def test_dictionary_import_job_lifecycle():
    """Verify that import job lifecycle can be persisted, tracked, and audited."""
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            job = DictionaryImportJob(
                dictionary_type="WHODRUG",
                dictionary_version="2024-03",
                status="PENDING",
            )
            session.add(job)

    # Update job state
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            stmt = select(DictionaryImportJob).where(
                DictionaryImportJob.dictionary_version == "2024-03"
            )
            res = await session.execute(stmt)
            job_obj = res.scalar_one()
            job_obj.status = "COMPLETED"
            job_obj.progress_percentage = 100
            job_obj.records_imported = 45000

    # Assert persistence and audit capture
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            stmt = select(DictionaryImportJob).where(
                DictionaryImportJob.dictionary_version == "2024-03"
            )
            res = await session.execute(stmt)
            job_obj = res.scalar_one()
            assert job_obj.status == "COMPLETED"
            assert job_obj.records_imported == 45000

            res_logs = await session.execute(
                select(AuditLog).where(
                    AuditLog.table_name == "dictionary_import_jobs"
                )
            )
            logs = res_logs.scalars().all()
            assert len(logs) > 0
            # Ensure audit is tracking changes on dictionary_import_jobs
            assert any(lg.action == "INSERT" for lg in logs)
            assert any(lg.action == "UPDATE" for lg in logs)
