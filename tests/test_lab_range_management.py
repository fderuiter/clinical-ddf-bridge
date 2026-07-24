import pytest
import httpx
from datetime import datetime, date
from typing import AsyncGenerator

from apps.execution.database.core import db_manager
from apps.execution.database.models import Base, ClinicalSubject, Laboratory, LabReferenceRange, ClinicalQuery, ClinicalObservation
from apps.execution.main import app, encrypt_demographics
from tests.test_clinical_queries import get_v2_auth_headers


@pytest.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Setup in-memory SQLite database before each test and clear down after."""
    db_manager.init_db("sqlite+aiosqlite:///:memory:")
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_manager.close()


@pytest.mark.asyncio
async def test_laboratory_crud() -> None:
    # @req:PRD-QRY-003
    """Verify that laboratories can be created and listed correctly, and duplicates are rejected."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Add testing labs")
    payload = {
        "name": "Quest Diagnostics Central Lab",
        "code": "QUEST_CENTRAL",
        "lab_type": "CENTRAL",
        "location": "New York, NY"
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create Laboratory
        response = await client.post("/api/v1/execution/laboratories", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "QUEST_CENTRAL"
        assert data["lab_type"] == "CENTRAL"
        assert data["version"] == 1

        # Attempt to create duplicate code
        response_dup = await client.post("/api/v1/execution/laboratories", json=payload, headers=headers)
        assert response_dup.status_code == 400
        assert "already exists" in response_dup.json()["detail"]

        # List Laboratories
        response_list = await client.get("/api/v1/execution/laboratories", headers=headers)
        assert response_list.status_code == 200
        labs = response_list.json()
        assert len(labs) == 1
        assert labs[0]["code"] == "QUEST_CENTRAL"


@pytest.mark.asyncio
async def test_lab_reference_range_crud() -> None:
    # @req:PRD-QRY-003
    """Verify that lab reference ranges can be created and queried correctly."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Add testing ranges")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create Laboratory first
        lab_payload = {
            "name": "LabCorp Local",
            "code": "LC_LOCAL",
            "lab_type": "LOCAL"
        }
        resp_lab = await client.post("/api/v1/execution/laboratories", json=lab_payload, headers=headers)
        assert resp_lab.status_code == 201
        lab_id = resp_lab.json()["id"]

        # Create Reference Range linking to LabCorp Local
        range_payload = {
            "laboratory_id": lab_id,
            "test_code": "ALT",
            "test_name": "Alanine Aminotransferase",
            "sex": "ALL",
            "age_min": 18.0,
            "age_max": 65.0,
            "low_value": 7.0,
            "high_value": 56.0,
            "unit": "U/L"
        }
        resp_range = await client.post("/api/v1/execution/lab-ranges", json=range_payload, headers=headers)
        assert resp_range.status_code == 201
        range_data = resp_range.json()
        assert range_data["test_code"] == "ALT"
        assert range_data["laboratory_id"] == lab_id

        # Query ranges
        resp_query = await client.get(f"/api/v1/execution/lab-ranges?test_code=ALT&laboratory_id={lab_id}", headers=headers)
        assert resp_query.status_code == 200
        ranges = resp_query.json()
        assert len(ranges) == 1
        assert ranges[0]["test_code"] == "ALT"


@pytest.mark.asyncio
async def test_observation_in_range() -> None:
    # @req:PRD-QRY-003
    """Verify that a normal in-range observation does not trigger out-of-range flags or clinical queries."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Normal observation ingestion")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create subject
        sub_payload = {
            "subject_id": "SUBJ-001",
            "study_id": "STUDY-01",
            "demographics": {
                "gender": "Male",
                "birthdate": "1990-01-01"
            }
        }
        await client.post("/api/v1/execution/subjects", json=sub_payload, headers=headers)

        # Create a central default reference range (laboratory_id=None) for Glucose
        range_payload = {
            "laboratory_id": None,
            "test_code": "GLUC",
            "test_name": "Glucose",
            "sex": "ALL",
            "low_value": 70.0,
            "high_value": 100.0,
            "unit": "mg/dL"
        }
        await client.post("/api/v1/execution/lab-ranges", json=range_payload, headers=headers)

        # Create Clinical Observation with Glucose = 85.0 mg/dL (In range!)
        obs_payload = {
            "subject_id": "SUBJ-001",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "GLUC",
            "test_name": "Glucose",
            "value": 85.0,
            "unit": "mg/dL"
        }
        resp_obs = await client.post("/api/v1/execution/observations", json=obs_payload, headers=headers)
        assert resp_obs.status_code == 200
        obs_data = resp_obs.json()
        assert obs_data["is_out_of_range"] is False

        # Verify no queries created
        resp_queries = await client.get("/api/v1/execution/queries", headers=headers)
        assert len(resp_queries.json()) == 0


@pytest.mark.asyncio
async def test_observation_out_of_range_central_lab() -> None:
    # @req:PRD-QRY-003
    """Verify that an out-of-range observation triggers out-of-range flags and open ClinicalQueries."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Ingest out of range value")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create subject
        sub_payload = {
            "subject_id": "SUBJ-002",
            "study_id": "STUDY-01",
            "demographics": {
                "gender": "Female",
                "birthdate": "1985-05-05"
            }
        }
        await client.post("/api/v1/execution/subjects", json=sub_payload, headers=headers)

        # Create central reference range for AST
        range_payload = {
            "laboratory_id": None,
            "test_code": "AST",
            "test_name": "Aspartate Aminotransferase",
            "sex": "ALL",
            "low_value": 8.0,
            "high_value": 48.0,
            "unit": "U/L"
        }
        await client.post("/api/v1/execution/lab-ranges", json=range_payload, headers=headers)

        # Create Observation AST = 120.0 U/L (Out of range!)
        obs_payload = {
            "subject_id": "SUBJ-002",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "AST",
            "test_name": "Aspartate Aminotransferase",
            "value": 120.0,
            "unit": "U/L"
        }
        resp_obs = await client.post("/api/v1/execution/observations", json=obs_payload, headers=headers)
        assert resp_obs.status_code == 200
        obs_data = resp_obs.json()
        assert obs_data["is_out_of_range"] is True

        # Verify query was automatically created and is open
        resp_queries = await client.get("/api/v1/execution/queries", headers=headers)
        queries = resp_queries.json()
        assert len(queries) == 1
        query = queries[0]
        assert query["status"] == "OPEN"
        assert query["test_code"] == "AST"
        assert query["origin"] == "automated"
        assert query["rule_id"] == "LAB_RANGE_OUT_OF_BOUNDS"
        assert "120.0" in query["explanation"]


@pytest.mark.asyncio
async def test_observation_age_sex_adjusted_range() -> None:
    # @req:PRD-QRY-003
    """Verify that age/sex-adjusted lookup properly separates ranges for different demographics."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Verify age/sex adjustments")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create adult female subject
        sub_payload_f = {
            "subject_id": "SUBJ-FEMALE",
            "study_id": "STUDY-01",
            "demographics": {
                "gender": "Female",
                "birthdate": "1990-01-01"
            }
        }
        await client.post("/api/v1/execution/subjects", json=sub_payload_f, headers=headers)

        # Create child subject
        sub_payload_c = {
            "subject_id": "SUBJ-CHILD",
            "study_id": "STUDY-01",
            "demographics": {
                "gender": "Male",
                "birthdate": "2020-01-01"
            }
        }
        await client.post("/api/v1/execution/subjects", json=sub_payload_c, headers=headers)

        # Create reference range for adult female Hemoglobin (12.0 - 15.5 g/dL)
        range_female = {
            "laboratory_id": None,
            "test_code": "HEMOG",
            "test_name": "Hemoglobin",
            "sex": "F",
            "age_min": 18.0,
            "age_max": 99.0,
            "low_value": 12.0,
            "high_value": 15.5,
            "unit": "g/dL"
        }
        await client.post("/api/v1/execution/lab-ranges", json=range_female, headers=headers)

        # Create reference range for children Hemoglobin (11.0 - 14.0 g/dL)
        range_child = {
            "laboratory_id": None,
            "test_code": "HEMOG",
            "test_name": "Hemoglobin",
            "sex": "ALL",
            "age_min": 0.0,
            "age_max": 12.0,
            "low_value": 11.0,
            "high_value": 14.0,
            "unit": "g/dL"
        }
        await client.post("/api/v1/execution/lab-ranges", json=range_child, headers=headers)

        # Test child value 11.5 (Normal for child, would be low for adult female)
        obs_child = {
            "subject_id": "SUBJ-CHILD",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "HEMOG",
            "test_name": "Hemoglobin",
            "value": 11.5,
            "unit": "g/dL",
            "observation_date": datetime(2026, 7, 30).isoformat()
        }
        resp_c = await client.post("/api/v1/execution/observations", json=obs_child, headers=headers)
        assert resp_c.status_code == 200
        assert resp_c.json()["is_out_of_range"] is False

        # Test female value 11.5 (Low for adult female, normal for child)
        obs_female = {
            "subject_id": "SUBJ-FEMALE",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "HEMOG",
            "test_name": "Hemoglobin",
            "value": 11.5,
            "unit": "g/dL",
            "observation_date": datetime(2026, 7, 30).isoformat()
        }
        resp_f = await client.post("/api/v1/execution/observations", json=obs_female, headers=headers)
        assert resp_f.status_code == 200
        assert resp_f.json()["is_out_of_range"] is True


@pytest.mark.asyncio
async def test_observation_unit_conversion_range() -> None:
    # @req:PRD-QRY-003
    """Verify that unit conversion is automatically performed if observation unit differs from range unit."""
    headers = get_v2_auth_headers(roles="Data Manager", change_reason="Verify unit conversion")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create subject
        sub_payload = {
            "subject_id": "SUBJ-003",
            "study_id": "STUDY-01",
            "demographics": {
                "gender": "Male",
                "birthdate": "1990-01-01"
            }
        }
        await client.post("/api/v1/execution/subjects", json=sub_payload, headers=headers)

        # Create reference range in grams (low: 0.5 g, high: 1.5 g)
        range_payload = {
            "laboratory_id": None,
            "test_code": "MASS_TEST",
            "test_name": "Mass test",
            "sex": "ALL",
            "low_value": 0.5,
            "high_value": 1.5,
            "unit": "g"
        }
        await client.post("/api/v1/execution/lab-ranges", json=range_payload, headers=headers)

        # Ingest 1000 mg (which is 1.0 g -> Normal/in-range!)
        obs_normal = {
            "subject_id": "SUBJ-003",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "MASS_TEST",
            "test_name": "Mass test",
            "value": 1000.0,
            "unit": "mg"
        }
        resp_normal = await client.post("/api/v1/execution/observations", json=obs_normal, headers=headers)
        assert resp_normal.status_code == 200
        assert resp_normal.json()["is_out_of_range"] is False

        # Ingest 2000 mg (which is 2.0 g -> High/out-of-range!)
        obs_high = {
            "subject_id": "SUBJ-003",
            "study_id": "STUDY-01",
            "domain": "LB",
            "test_code": "MASS_TEST",
            "test_name": "Mass test",
            "value": 2000.0,
            "unit": "mg"
        }
        resp_high = await client.post("/api/v1/execution/observations", json=obs_high, headers=headers)
        assert resp_high.status_code == 200
        assert resp_high.json()["is_out_of_range"] is True
