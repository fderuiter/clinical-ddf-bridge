import pytest
import pytest_asyncio
from sqlalchemy import text

from apps.execution.database import provision_tenant, rollback
from apps.execution.database.context import current_session, get_session
from apps.execution.database.core import db_manager
from apps.execution.database.models import Base, ClinicalObservation
from apps.execution.outliers import (
    calculate_cohort_stats,
    identify_outliers,
    recalculate_cohort_outliers,
)


def test_placeholders_and_scripts():
    # Test provision_tenant placeholder main
    provision_tenant.main()
    assert True

    # Test rollback placeholder main
    rollback.main()
    assert True


def test_get_session_error_handling():
    # Reset session just to be sure
    token = current_session.set(None)
    try:
        with pytest.raises(RuntimeError, match="No database session found"):
            get_session()
    finally:
        current_session.reset(token)


@pytest.mark.asyncio
async def test_sqlite_custom_settings_missing_ok():
    # Ensure database is initialized with sqlite
    db_manager.init_db("sqlite+aiosqlite:///:memory:")
    try:
        async with db_manager.engine.connect() as conn:
            # Let's call the functions directly from raw SQL to test all logic
            # set_config
            await conn.execute(
                text("SELECT set_config('cadence.custom_test_var', 'hello_world', 1)")
            )

            # current_setting missing_ok=True (or 1)
            res = await conn.execute(
                text("SELECT current_setting('cadence.custom_test_var', 1)")
            )
            val = res.scalar()
            assert val == "hello_world"

            # current_setting missing_ok=False (or 0) for non-existent setting
            with pytest.raises(Exception):
                await conn.execute(
                    text("SELECT current_setting('cadence.non_existent', 0)")
                )

            # current_setting with existing but missing_ok=False
            res2 = await conn.execute(
                text("SELECT current_setting('cadence.custom_test_var', 0)")
            )
            assert res2.scalar() == "hello_world"
    finally:
        await db_manager.close()


def test_outliers_calculate_cohort_stats_edge_cases():
    # Empty list
    mean, std_dev = calculate_cohort_stats([])
    assert mean == 0.0
    assert std_dev == 0.0

    # Single element
    mean, std_dev = calculate_cohort_stats([10.0])
    assert mean == 10.0
    assert std_dev == 0.0

    # Identical elements
    mean, std_dev = calculate_cohort_stats([5.0, 5.0, 5.0])
    assert mean == 5.0
    assert std_dev == 0.0


def test_identify_outliers_edge_cases():
    # std_dev is 0.0
    res = identify_outliers([5.0, 5.0], 5.0, 0.0)
    assert res == [False, False]

    # Less than 2 elements
    res = identify_outliers([10.0], 10.0, 1.0)
    assert res == [False]


@pytest_asyncio.fixture
async def temp_db():
    db_manager.init_db("sqlite+aiosqlite:///:memory:")
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


@pytest.mark.asyncio
async def test_recalculate_cohort_outliers_scenarios(temp_db):
    session_maker = db_manager.get_session_maker()

    # Scenario 1: Empty observations
    async with session_maker() as session:
        count = await recalculate_cohort_outliers(session, "study_123", "TEST")
        assert count == 0

    # Scenario 2: Fewer than 2 observations (say, 1)
    async with session_maker() as session:
        obs1 = ClinicalObservation(
            subject_id="SUBJ-01",
            study_id="study_123",
            domain="VS",
            test_code="TEST",
            test_name="Test Name",
            normalized_value=10.0,
            is_outlier=True,
            version=1,
        )
        session.add(obs1)
        await session.commit()

    async with session_maker() as session:
        count = await recalculate_cohort_outliers(session, "study_123", "TEST")
        assert count == 0
        # Check that is_outlier was set to False
        res = await session.execute(
            text(
                "SELECT is_outlier, version FROM clinical_observations WHERE study_id='study_123'"
            )
        )
        row = res.fetchone()
        assert row[0] == 0  # False in SQLite
        assert row[1] == 2  # Version incremented

    # Scenario 3: Observations exist but valid_obs (normalized_value not None) < 2
    async with session_maker() as session:
        await session.execute(text("DELETE FROM clinical_observations"))
        obs1 = ClinicalObservation(
            subject_id="SUBJ-01",
            study_id="study_123",
            domain="VS",
            test_code="TEST",
            test_name="Test Name",
            normalized_value=None,
            is_outlier=True,
            version=1,
        )
        obs2 = ClinicalObservation(
            subject_id="SUBJ-02",
            study_id="study_123",
            domain="VS",
            test_code="TEST",
            test_name="Test Name",
            normalized_value=12.0,
            is_outlier=True,
            version=1,
        )
        session.add_all([obs1, obs2])
        await session.commit()

    async with session_maker() as session:
        count = await recalculate_cohort_outliers(session, "study_123", "TEST")
        assert count == 0
        res = await session.execute(
            text(
                "SELECT is_outlier FROM clinical_observations WHERE study_id='study_123'"
            )
        )
        rows = res.fetchall()
        assert all(row[0] == 0 for row in rows)

    # Scenario 4: Multiple elements with one actual statistical outlier (> 3 std dev)
    # 10 values of 10.0 and one value of 10000.0
    async with session_maker() as session:
        await session.execute(text("DELETE FROM clinical_observations"))
        obs_list = []
        for i in range(10):
            obs_list.append(
                ClinicalObservation(
                    subject_id=f"SUBJ-{i:02d}",
                    study_id="study_123",
                    domain="VS",
                    test_code="TEST",
                    test_name="Test Name",
                    normalized_value=10.0,
                    is_outlier=False,
                    version=1,
                )
            )
        obs_list.append(
            ClinicalObservation(
                subject_id="SUBJ-10",
                study_id="study_123",
                domain="VS",
                test_code="TEST",
                test_name="Test Name",
                normalized_value=10000.0,
                is_outlier=False,
                version=1,
                # Wait, this version starts at 1, will be incremented when updated to is_outlier=True
            )
        )
        session.add_all(obs_list)
        await session.commit()

    async with session_maker() as session:
        count = await recalculate_cohort_outliers(session, "study_123", "TEST")
        # Outlier count should be exactly 1 (the 10000.0 observation)
        assert count == 1
        res = await session.execute(
            text(
                "SELECT is_outlier, normalized_value FROM clinical_observations WHERE study_id='study_123'"
            )
        )
        rows = res.fetchall()
        for row in rows:
            is_outlier, val = row[0], row[1]
            if val == 10000.0:
                assert is_outlier == 1
            else:
                assert is_outlier == 0
