from datetime import datetime

import pytest
from sqlalchemy import select, text

from apps.execution.database.core import db_manager
from apps.execution.database.migrate import deploy_database_triggers
from apps.execution.database.models import (
    AuditLog,
    Base,
    ClinicalCodingAssignment,
    ClinicalCodingLedgerEntry,
    CodingState,
    DictionaryImportJob,
    DictionaryType,
    ImportState,
    MedDRAHierarchy,
    MedDRATerm,
    RecodingState,
    WHODrugATC,
    WHODrugDrugIngredientMap,
    WHODrugIngredient,
    WHODrugRecord,
)
from apps.execution.trial_lock import TrialLockManager


@pytest.fixture(autouse=True)
async def setup_test_db():
    TrialLockManager.reset()
    db_manager.init_db(
        "sqlite+aiosqlite:///:memory:",
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
async def test_meddra_terminology_persistence_and_lookup():
    # @req:PRD-SYS-004
    """
    Verify that MedDRATerm and MedDRAHierarchy correctly persist the 5 MedDRA levels
    and their hierarchical relationships, and enforce uniqueness constraints and lookup indexes.
    """
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            # Disable database writing mode so that SQLAlchemy listeners trigger if needed
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )

            # Insert terms for different levels
            llt = MedDRATerm(
                dictionary_version="26.0",
                level="LLT",
                code="10019211",
                term="Headache",
                term_normalized="headache",
            )
            pt = MedDRATerm(
                dictionary_version="26.0",
                level="PT",
                code="10019211",
                term="Headache",
                term_normalized="headache",
            )
            hlt = MedDRATerm(
                dictionary_version="26.0",
                level="HLT",
                code="10019231",
                term="Headaches NEC",
                term_normalized="headaches nec",
            )
            hlgt = MedDRATerm(
                dictionary_version="26.0",
                level="HLGT",
                code="10029214",
                term="Headache and facial pain",
                term_normalized="headache and facial pain",
            )
            soc = MedDRATerm(
                dictionary_version="26.0",
                level="SOC",
                code="10029205",
                term="Nervous system disorders",
                term_normalized="nervous system disorders",
            )
            session.add_all([llt, pt, hlt, hlgt, soc])

            # Insert mdhier relationship
            hier = MedDRAHierarchy(
                dictionary_version="26.0",
                llt_code="10019211",
                pt_code="10019211",
                hlt_code="10019231",
                hlgt_code="10029214",
                soc_code="10029205",
                primary_soc_flag="Y",
            )
            session.add(hier)

    # 1. Verify retrieval and lookup indexes (by version and normalized term / code)
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(
            select(MedDRATerm).where(
                MedDRATerm.dictionary_version == "26.0",
                MedDRATerm.term_normalized == "headache",
            )
        )
        terms = result.scalars().all()
        assert len(terms) == 2
        assert {t.level for t in terms} == {"LLT", "PT"}

        # Verify Hierarchy relation record
        result_hier = await session.execute(
            select(MedDRAHierarchy).where(
                MedDRAHierarchy.dictionary_version == "26.0",
                MedDRAHierarchy.llt_code == "10019211",
            )
        )
        saved_hier = result_hier.scalar_one()
        assert saved_hier.pt_code == "10019211"
        assert saved_hier.soc_code == "10029205"
        assert saved_hier.primary_soc_flag == "Y"

    # 2. Verify uniqueness constraint: prevent duplicate level-code for same version
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            duplicate_term = MedDRATerm(
                dictionary_version="26.0",
                level="LLT",
                code="10019211",
                term="Duplicate Headache",
                term_normalized="duplicate headache",
            )
            session.add(duplicate_term)
            with pytest.raises(Exception):
                await session.flush()


@pytest.mark.asyncio
async def test_whodrug_terminology_persistence_and_lookup():
    # @req:PRD-SYS-004
    """
    Verify that WHODrugRecord, WHODrugIngredient, WHODrugATC, and mapping tables
    correctly persist WHODrug records, enforce uniqueness, and indexes are searchable.
    """
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )

            # Insert Drug Record
            drug = WHODrugRecord(
                dictionary_version="2023-09",
                drug_code="00012301001",
                drug_name="ASPIRIN",
                drug_name_normalized="aspirin",
                atc_code="N02BA01",
            )
            # Insert Ingredient
            ing = WHODrugIngredient(
                dictionary_version="2023-09",
                substance_code="001020",
                substance_name="ACETYLSALICYLIC ACID",
                substance_name_normalized="acetylsalicylic acid",
            )
            # Insert ATC classification
            atc = WHODrugATC(
                dictionary_version="2023-09",
                atc_code="N02BA01",
                atc_text="SALICYLIC ACID AND DERIVATIVES",
                atc_text_normalized="salicylic acid and derivatives",
            )
            # Insert Map
            drug_ing_map = WHODrugDrugIngredientMap(
                dictionary_version="2023-09",
                drug_code="00012301001",
                substance_code="001020",
            )
            session.add_all([drug, ing, atc, drug_ing_map])

    # 1. Verify retrieval and lookup
    async with db_manager.get_session_maker()() as session:
        result_drug = await session.execute(
            select(WHODrugRecord).where(
                WHODrugRecord.dictionary_version == "2023-09",
                WHODrugRecord.drug_name_normalized == "aspirin",
            )
        )
        saved_drug = result_drug.scalar_one()
        assert saved_drug.drug_code == "00012301001"
        assert saved_drug.atc_code == "N02BA01"

        result_map = await session.execute(
            select(WHODrugDrugIngredientMap).where(
                WHODrugDrugIngredientMap.dictionary_version == "2023-09",
                WHODrugDrugIngredientMap.drug_code == "00012301001",
            )
        )
        saved_map = result_map.scalar_one()
        assert saved_map.substance_code == "001020"

    # 2. Verify unique constraints
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            dup_drug = WHODrugRecord(
                dictionary_version="2023-09",
                drug_code="00012301001",
                drug_name="ASPIRIN DUPLICATE",
                drug_name_normalized="aspirin duplicate",
            )
            session.add(dup_drug)
            with pytest.raises(Exception):
                await session.flush()


@pytest.mark.asyncio
async def test_import_job_lifecycle():
    # @req:PRD-SYS-004
    """
    Verify DictionaryImportJob captures metadata, timestamps, progress percentage,
    imported records count, and error details accurately.
    """
    now = datetime.now()
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )
            job = DictionaryImportJob(
                dictionary_type=DictionaryType.MEDDRA,
                dictionary_version="26.0",
                status=ImportState.PENDING,
                started_at=now,
                progress_percentage=0,
                records_imported=0,
                errors_encountered=0,
            )
            session.add(job)

    # Update job state to FAILED with error details
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )
            result = await session.execute(
                select(DictionaryImportJob).where(
                    DictionaryImportJob.dictionary_type == "MEDDRA"
                )
            )
            saved_job = result.scalar_one()
            saved_job.status = ImportState.FAILED
            saved_job.progress_percentage = 40
            saved_job.records_imported = 2000
            saved_job.errors_encountered = 1
            saved_job.error_details = (
                "NullPointerException: SOC parent missing for LLT code 100"
            )
            saved_job.completed_at = datetime.now()

    # Verify updated values
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(
            select(DictionaryImportJob).where(
                DictionaryImportJob.dictionary_type == "MEDDRA"
            )
        )
        final_job = result.scalar_one()
        assert final_job.status == ImportState.FAILED
        assert final_job.progress_percentage == 40
        assert final_job.records_imported == 2000
        assert final_job.errors_encountered == 1
        assert "NullPointerException" in final_job.error_details
        assert final_job.completed_at is not None


@pytest.mark.asyncio
async def test_clinical_coding_assignments_and_ledger():
    # @req:PRD-SYS-004
    """
    Verify ClinicalCodingAssignment and ClinicalCodingLedgerEntry correctly capture
    verbatims, assigned terms, and historical recoding decisions with status enums.
    """
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )
            assignment = ClinicalCodingAssignment(
                observation_id="OBS-992",
                verbatim_term="HEADAHE",
                dictionary_type=DictionaryType.MEDDRA,
                dictionary_version="25.0",
                assigned_code="10019211",
                assigned_term="Headache",
                coding_state=CodingState.CODED,
                assigned_by="CoderA",
                assigned_at=datetime.now(),
            )
            session.add(assignment)

    # Log a recoding ledger change (e.g., due to up-versioning to MedDRA 26.0)
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('cadence.app_writing', 'true', 1);")
            )
            result = await session.execute(
                select(ClinicalCodingAssignment).where(
                    ClinicalCodingAssignment.observation_id == "OBS-992"
                )
            )
            saved_assignment = result.scalar_one()

            # Up-version assignment
            saved_assignment.dictionary_version = "26.0"
            saved_assignment.assigned_at = datetime.now()

            # Record ledger history entry
            ledger = ClinicalCodingLedgerEntry(
                assignment_id=saved_assignment.id,
                observation_id=saved_assignment.observation_id,
                verbatim_term=saved_assignment.verbatim_term,
                dictionary_type=saved_assignment.dictionary_type,
                dictionary_version_old="25.0",
                dictionary_version_new="26.0",
                assigned_code_old="10019211",
                assigned_code_new="10019211",
                assigned_term_old="Headache",
                assigned_term_new="Headache",
                recoding_state=RecodingState.RECODED,
                change_reason="Standardized database up-versioning audit logic for v26.0",
                performed_by="SystemUpgrade",
                performed_at=datetime.now(),
            )
            session.add(ledger)

    # Verify coding assignment and ledger entries
    async with db_manager.get_session_maker()() as session:
        result_assignment = await session.execute(
            select(ClinicalCodingAssignment).where(
                ClinicalCodingAssignment.observation_id == "OBS-992"
            )
        )
        saved_ass = result_assignment.scalar_one()
        assert saved_ass.dictionary_version == "26.0"

        result_ledger = await session.execute(
            select(ClinicalCodingLedgerEntry).where(
                ClinicalCodingLedgerEntry.assignment_id == saved_ass.id
            )
        )
        saved_ledg = result_ledger.scalar_one()
        assert saved_ledg.dictionary_version_old == "25.0"
        assert saved_ledg.dictionary_version_new == "26.0"
        assert saved_ledg.recoding_state == RecodingState.RECODED
        assert "up-versioning" in saved_ledg.change_reason


@pytest.mark.asyncio
async def test_audit_trail_and_hard_delete_prevention():
    # @req:PRD-SYS-001
    # @req:PRD-SYS-004
    """
    Verify that Part 11 compliant audit triggers and SQLAlchemy event listeners
    log insert/update operations, and prevent hard deletes for new terminology/coding models.
    """
    # Insert a MedDRATerm and verify a row in audit_logs is created
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            # Run without setting app_writing to ensure db triggers / listeners capture mutations
            term = MedDRATerm(
                dictionary_version="26.0",
                level="PT",
                code="10019211",
                term="Headache",
                term_normalized="headache",
            )
            session.add(term)

    # Retrieve and verify audit_logs table
    async with db_manager.get_session_maker()() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.table_name == "meddra_terms")
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        assert logs[0].action == "INSERT"
        assert logs[0].new_values["code"] == "10019211"
        assert logs[0].new_values["level"] == "PT"

    # Prevent hard deletions
    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            with pytest.raises(
                Exception, match="Hard deletions are strictly forbidden"
            ):
                await session.execute(
                    text("DELETE FROM meddra_terms WHERE code = '10019211';")
                )
