import hashlib
import hmac
import time
import zipfile
import io
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient

from apps.execution.main import app as execution_app
from apps.gateway.main import app as gateway_app
from apps.execution.ucum import convert_ucum
from apps.execution.outliers import (
    calculate_mean,
    calculate_sample_std_dev,
    calculate_median,
    calculate_mad,
    calculate_percentile,
    detect_zscore_outliers,
    detect_modified_zscore_outliers,
    detect_tukey_outliers,
)
from apps.execution.export import (
    group_observations,
    export_odm_xml,
    export_odm_json,
    export_csv_zip,
)
from apps.execution.database.models import Subject, Visit, Observation, Base
from apps.execution.database.core import db_manager
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    import os

    db_url = "sqlite+aiosqlite:///file:test_db?mode=memory&cache=shared"
    monkeypatch.setenv("DATABASE_URL", db_url)

    db_manager.init_db(db_url)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await db_manager.close()


def get_auth_headers():
    """Generates standard gateway authorization headers for direct testing."""
    user_id = "test-user"
    roles = "admin,system"
    timestamp = str(time.time())
    message = f"{user_id}:{roles}:{timestamp}"
    signature = hmac.new(
        b"internal-gateway-secret-12345", message.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "X-User-Id": user_id,
        "X-User-Roles": roles,
        "X-Gateway-Timestamp": timestamp,
        "X-Gateway-Signature": signature,
    }


def test_ucum_engine():
    """Verify UCUM unit conversion rules and compatibilities."""
    # Test identical unit conversion
    val, mult, offset, is_compat = convert_ucum(10.0, "kg", "kg")
    assert is_compat is True
    assert val == 10.0
    assert mult == 1.0
    assert offset == 0.0

    # Test [degF] -> Cel
    val, mult, offset, is_compat = convert_ucum(98.6, "[degF]", "Cel")
    assert is_compat is True
    assert abs(val - 37.0) < 1e-5

    # Test Cel -> Cel
    val, mult, offset, is_compat = convert_ucum(37.0, "Cel", "Cel")
    assert is_compat is True
    assert val == 37.0

    # Test pounds -> kg
    val, mult, offset, is_compat = convert_ucum(10.0, "[lb_av]", "kg")
    assert is_compat is True
    assert abs(val - 4.536) < 1e-3

    # Test grams -> kg
    val, mult, offset, is_compat = convert_ucum(1500.0, "g", "kg")
    assert is_compat is True
    assert val == 1.5

    # Test inches -> cm
    val, mult, offset, is_compat = convert_ucum(10.0, "[in_i]", "cm")
    assert is_compat is True
    assert val == 25.4

    # Test Glucose mg/dL -> mmol/L
    val, mult, offset, is_compat = convert_ucum(100.0, "mg/dL", "mmol/L")
    assert is_compat is True
    assert val == 5.55

    # Test Creatinine mg/dL -> umol/L
    val, mult, offset, is_compat = convert_ucum(1.0, "mg/dL", "umol/L", domain="Creatinine")
    assert is_compat is True
    assert val == 88.4

    # Test Bilirubin mg/dL -> umol/L
    val, mult, offset, is_compat = convert_ucum(1.0, "mg/dL", "umol/L", domain="Bilirubin")
    assert is_compat is True
    assert val == 17.1

    # Test incompatible units
    val, mult, offset, is_compat = convert_ucum(100.0, "mg/dL", "Cel")
    assert is_compat is False
    assert val is None


def test_outlier_calculations():
    """Verify raw mathematical functions for statistical computations."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    mean = calculate_mean(data)
    assert mean == 3.0

    std_dev = calculate_sample_std_dev(data, mean)
    # std dev of [1,2,3,4,5] is sqrt(2.5) ~ 1.5811388
    assert abs(std_dev - 1.5811) < 1e-3

    # Mean of empty list
    assert calculate_mean([]) == 0.0
    # Std dev of small lists
    assert calculate_sample_std_dev([1.0], 1.0) == 0.0

    # Medians
    assert calculate_median([1.0, 3.0, 2.0]) == 2.0
    assert calculate_median([1.0, 4.0, 2.0, 3.0]) == 2.5
    assert calculate_median([]) == 0.0

    # MAD
    assert calculate_mad([1.0, 2.0, 3.0, 4.0, 10.0], 3.0) == 1.0
    assert calculate_mad([], 0.0) == 0.0

    # Percentiles
    assert calculate_percentile([1.0, 2.0, 3.0, 4.0], 25.0) == 1.75
    assert calculate_percentile([1.0, 2.0, 3.0, 4.0], 75.0) == 3.25
    assert calculate_percentile([], 50.0) == 0.0
    assert calculate_percentile([42.0], 50.0) == 42.0


def test_outlier_algorithms():
    """Verify high-level outlier detection algorithms."""
    values = [10.0, 11.0, 12.0, 10.5, 9.5, 100.0]

    # Z-Score Outliers
    z_outliers = detect_zscore_outliers(values, threshold=2.0)
    assert len(z_outliers) == 1
    assert z_outliers[0]["index"] == 5
    assert z_outliers[0]["value"] == 100.0

    # Z-score on small list
    assert detect_zscore_outliers([1.0]) == []
    # Z-score with 0 std dev
    assert detect_zscore_outliers([5.0, 5.0, 5.0]) == []

    # Modified Z-Score Outliers
    mod_outliers = detect_modified_zscore_outliers(values, threshold=3.5)
    assert len(mod_outliers) == 1
    assert mod_outliers[0]["index"] == 5

    # Modified Z-score with 0 MAD
    assert detect_modified_zscore_outliers([5.0, 5.0, 5.0]) == []

    # Tukey Fences Outliers
    tukey_outliers = detect_tukey_outliers(values, k=1.5)
    assert len(tukey_outliers) == 1
    assert tukey_outliers[0]["index"] == 5

    # Tukey on small list
    assert detect_tukey_outliers([1.0, 2.0, 3.0]) == []


def test_outlier_detection_performance_benchmark():
    """Verify outlier routine meets success metrics (1,000 observations processed in under 100 milliseconds)."""
    large_dataset = [float(i) for i in range(1000)] + [10000.0]

    start_time = time.perf_counter()
    outliers = detect_zscore_outliers(large_dataset, threshold=3.0)
    duration_ms = (time.perf_counter() - start_time) * 1000

    assert duration_ms < 100.0
    assert len(outliers) == 1
    assert outliers[0]["value"] == 10000.0


def test_export_payload_structures():
    """Test standard and custom exporter formatting outputs."""
    obs_list = [
        Observation(
            subject_key="SUB-101",
            visit_oid="SE.SCREENING",
            form_oid="F.DEMO",
            form_version="1.0",
            item_group_oid="IG.DEMO_VALS",
            item_oid="I.AGE",
            value="42",
        ),
        Observation(
            subject_key="SUB-101",
            visit_oid="SE.SCREENING",
            form_oid="F.DEMO",
            form_version="1.0",
            item_group_oid="IG.DEMO_VALS",
            item_oid="I.SEX",
            value="F",
        ),
    ]

    # Test grouping function
    grouped = group_observations(obs_list)
    assert len(grouped) == 1
    assert grouped[0]["subject_key"] == "SUB-101"
    assert len(grouped[0]["visits"]) == 1
    assert grouped[0]["visits"][0]["visit_oid"] == "SE.SCREENING"

    # Test ODM XML export structure
    xml_str = export_odm_xml("study_abc", obs_list)
    assert xml_str is not None
    assert "study_abc" in xml_str
    # Verify XML parser validity
    root = ET.fromstring(xml_str)
    assert root.tag.endswith("ODM")
    assert len(root.findall(".//{http://www.cdisc.org/ns/odm/v1.3}SubjectData")) == 1

    # Test ODM JSON export structure
    json_data = export_odm_json("study_abc", obs_list)
    assert json_data["odmVersion"] == "1.3.2"
    assert json_data["clinicalData"][0]["studyOID"] == "study_abc"

    # Test CSV ZIP export structures
    subjects = [Subject(id="1", study_id="study_abc", subject_key="SUB-101", status="Screening")]
    visits = [Visit(id="2", study_id="study_abc", subject_key="SUB-101", visit_oid="SE.SCREENING", visit_name="Screening")]
    zip_bytes = export_csv_zip(subjects, visits, obs_list)

    # Validate zip file integrity
    zip_io = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_io) as zip_file:
        files = zip_file.namelist()
        assert "subjects.csv" in files
        assert "visits.csv" in files
        assert "observations.csv" in files

        # Check subjects csv
        subs_csv = zip_file.read("subjects.csv").decode("utf-8")
        assert "SUB-101" in subs_csv


def test_api_endpoints_ucum_and_outliers():
    """Test execution service API handlers for unit conversion and outlier queries."""
    with TestClient(execution_app) as client:
        # 1. UCUM conversion endpoint (valid)
        response = client.post(
            "/api/v1/dictionaries/ucum/convert",
            json={"value": 98.6, "source_unit": "[degF]", "target_unit": "Cel"},
            headers=get_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_compatible"] is True
        assert data["target"]["value"] == 37.0

        # UCUM conversion (incompatible)
        response = client.post(
            "/api/v1/dictionaries/ucum/convert",
            json={"value": 12.0, "source_unit": "[lb_av]", "target_unit": "Cel"},
            headers=get_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["is_compatible"] is False

        # 2. Outliers utility detect
        response = client.post(
            "/api/v1/execution/outliers/detect",
            json={"values": [1.0, 1.1, 1.2, 0.9, 1.0, 100.0], "method": "zscore", "threshold": 2.0},
            headers=get_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["outlier_count"] == 1
        assert data["outliers"][0]["value"] == 100.0

        # Outliers utility detect (modified zscore)
        response = client.post(
            "/api/v1/execution/outliers/detect",
            json={"values": [1.0, 1.1, 1.2, 0.9, 1.0, 100.0], "method": "modified_zscore"},
            headers=get_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["outlier_count"] == 1

        # Outliers utility detect (tukey)
        response = client.post(
            "/api/v1/execution/outliers/detect",
            json={"values": [1.0, 1.1, 1.2, 0.9, 1.0, 100.0], "method": "tukey"},
            headers=get_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["outlier_count"] == 1

        # Outliers invalid method
        response = client.post(
            "/api/v1/execution/outliers/detect",
            json={"values": [1.0, 2.0], "method": "invalid_method"},
            headers=get_auth_headers(),
        )
        assert response.status_code == 400


def test_subject_visit_observation_persistence():
    """Verify transactional relational insertions, unit normalization, and outlier flagging."""
    with TestClient(execution_app) as client:
        # Create subject
        sub_resp = client.post(
            "/api/v1/execution/subjects",
            json={"study_id": "std_1", "subject_key": "SUB-101", "status": "Screening"},
            headers=get_auth_headers(),
        )
        assert sub_resp.status_code == 200
        assert sub_resp.json()["subject_key"] == "SUB-101"

        # Create visit
        vis_resp = client.post(
            "/api/v1/execution/visits",
            json={
                "study_id": "std_1",
                "subject_key": "SUB-101",
                "visit_oid": "SE.V1",
                "visit_name": "Visit 1",
                "visit_number": 1,
            },
            headers=get_auth_headers(),
        )
        assert vis_resp.status_code == 200
        assert vis_resp.json()["visit_oid"] == "SE.V1"

        # Create observations in batch to trigger outlier detection
        # We need at least 3 values for Z-score outlier flagging.
        # Let's insert standard observations first.
        for i, val in enumerate(["70.0", "72.0", "68.0", "71.0"]):
            obs_resp = client.post(
                "/api/v1/execution/observations",
                json={
                    "study_id": "std_1",
                    "subject_key": f"SUB-{100+i}",
                    "visit_oid": "SE.V1",
                    "form_oid": "F.VS",
                    "item_group_oid": "IG.VS",
                    "item_oid": "I.WEIGHT",
                    "value": val,
                    "unit": "kg",
                },
                headers=get_auth_headers(),
            )
            assert obs_resp.status_code == 200
            assert obs_resp.json()["is_outlier"] is False

        # Now insert an extreme outlier! 700 kg weight instead of ~70 kg.
        obs_resp = client.post(
            "/api/v1/execution/observations",
            json={
                "study_id": "std_1",
                "subject_key": "SUB-999",
                "visit_oid": "SE.V1",
                "form_oid": "F.VS",
                "item_group_oid": "IG.VS",
                "item_oid": "I.WEIGHT",
                "value": "700.0",
                "unit": "kg",
            },
            headers=get_auth_headers(),
        )
        assert obs_resp.status_code == 200
        # Should be flagged as standard Z-score outlier (> 3 std dev)!
        assert obs_resp.json()["is_outlier"] is True

        # Test UCUM unit normalization in observation creation
        # Insert a temperature of 98.6 [degF], should normalize to 37.0 Cel!
        obs_resp = client.post(
            "/api/v1/execution/observations",
            json={
                "study_id": "std_1",
                "subject_key": "SUB-101",
                "visit_oid": "SE.V1",
                "form_oid": "F.VS",
                "item_group_oid": "IG.VS",
                "item_oid": "I.TEMP",
                "value": "98.6",
                "unit": "[degF]",
            },
            headers=get_auth_headers(),
        )
        assert obs_resp.status_code == 200
        data = obs_resp.json()
        assert data["normalized_value"] == 37.0
        assert data["normalized_unit"] == "Cel"


def test_bulk_study_export():
    """Verify CDISC bulk study exporter formats on database records."""
    with TestClient(execution_app) as client:
        # Populate some trial records
        study_id = "std_export_test"
        client.post(
            "/api/v1/execution/observations",
            json={
                "study_id": study_id,
                "subject_key": "SUB-701",
                "visit_oid": "SE.V1",
                "form_oid": "F.DEMO",
                "item_group_oid": "IG.DEMO",
                "item_oid": "I.AGE",
                "value": "25",
            },
            headers=get_auth_headers(),
        )

        # 1. Export as ODM-XML
        xml_resp = client.get(
            f"/api/v1/execution/studies/{study_id}/export?format=ODM-XML",
            headers=get_auth_headers(),
        )
        assert xml_resp.status_code == 200
        assert xml_resp.headers["content-type"] == "application/xml"
        assert "std_export_test" in xml_resp.text
        assert "SUB-701" in xml_resp.text

        # 2. Export as ODM-JSON
        json_resp = client.get(
            f"/api/v1/execution/studies/{study_id}/export?format=ODM-JSON",
            headers=get_auth_headers(),
        )
        assert json_resp.status_code == 200
        data = json_resp.json()
        assert data["clinicalData"][0]["studyOID"] == study_id

        # 3. Export as CSV-ZIP
        zip_resp = client.get(
            f"/api/v1/execution/studies/{study_id}/export?format=CSV-ZIP",
            headers=get_auth_headers(),
        )
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"] == "application/zip"
        zip_io = io.BytesIO(zip_resp.content)
        with zipfile.ZipFile(zip_io) as zip_file:
            files = zip_file.namelist()
            assert "subjects.csv" in files
            assert "visits.csv" in files
            assert "observations.csv" in files


def test_api_gateway_routing_to_dictionary(monkeypatch):
    """Test that the API Gateway correctly proxies api/v1/dictionaries and api/v1/execution requests."""
    monkeypatch.setenv("JWT_TEST_SECRET", "test_secret")
    from jose import jwt
    token = jwt.encode(
        {"sub": "user1", "roles": ["admin"]}, "test_secret", algorithm="HS256"
    )

    from unittest.mock import AsyncMock, MagicMock
    import httpx
    mock_send = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status": "ok"}'
    mock_resp.headers = {"content-type": "application/json"}
    mock_send.return_value = mock_resp
    monkeypatch.setattr(httpx.AsyncClient, "send", mock_send)

    with TestClient(gateway_app) as client:
        # Route to api/v1/dictionaries -> should route to execution service
        res = client.post(
            "/api/v1/dictionaries/ucum/convert",
            json={"value": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert str(mock_send.call_args.args[0].url) == "http://localhost:8002/api/v1/dictionaries/ucum/convert"

        # Route to api/v1/execution -> should route to execution service
        res = client.get(
            "/api/v1/execution/studies/study_abc/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert str(mock_send.call_args.args[0].url) == "http://localhost:8002/api/v1/execution/studies/study_abc/export"
