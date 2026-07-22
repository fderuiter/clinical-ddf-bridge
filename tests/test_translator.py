import pytest
from fastapi.testclient import TestClient
from apps.execution.main import app, AsyncSessionLocal
from apps.execution.database.models import TranslationJob, AuditLog
import xml.etree.ElementTree as ET

@pytest.mark.asyncio
async def test_study_published_event_triggers_translation():
    study_payload = {
        "study_id": "test_study_123",
        "payload": {
            "name": "Acme Clinical Trial",
            "protocol": {
                "items": [
                    {"id": "sys_bp", "name": "Systolic Blood Pressure", "type": "int"},
                    {"name": "Heart Rate", "type": "int"}
                ]
            }
        }
    }
    
    # Using context manager to trigger FastAPI's startup event which creates the DB tables
    with TestClient(app) as client:
        response = client.post("/events/study-published", json=study_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        
        # TestClient blocks until background tasks are done when running synchronously.
        # But since we use background_tasks.add_task in an async endpoint, the task finishes quickly.
        
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            TranslationJob.__table__.select().where(TranslationJob.study_id == "test_study_123")
        )
        job = result.mappings().first()
        
        assert job is not None
        if job["status"] != "COMPLETED":
            print("ERROR MESSAGE:", job["error_message"])
        assert job["status"] == "COMPLETED"
        assert job["odm_payload"] is not None
        assert job["openrosa_payload"] is not None
        
        odm_xml = job["odm_payload"]
        odm_root = ET.fromstring(odm_xml)
        assert "ODM" in odm_root.tag
        
        openrosa_xml = job["openrosa_payload"]
        openrosa_root = ET.fromstring(openrosa_xml)
        assert "html" in openrosa_root.tag
        
        # Determine the namespace for ODM dynamically if present
        odm_ns = ""
        if "}" in odm_root.tag:
            odm_ns = odm_root.tag.split("}")[0] + "}"
        
        study = odm_root.find(f"{odm_ns}Study")
        mdv = study.find(f"{odm_ns}MetaDataVersion")
        item_defs = mdv.findall(f"{odm_ns}ItemDef")
        odm_ids = [item.get("OID") for item in item_defs]
        
        ns = {'xf': 'http://www.w3.org/2002/xforms'}
        head = openrosa_root.find("{http://www.w3.org/1999/xhtml}head")
        model = head.find("xf:model", ns)
        binds = model.findall("xf:bind", ns)
        
        openrosa_ids = [bind.get("nodeset").replace("/", "") for bind in binds]
        
        assert set(odm_ids) == set(openrosa_ids)
        assert "sys_bp" in odm_ids
        assert len(odm_ids) == 2
        
        audit_res = await session.execute(
            AuditLog.__table__.select().where(AuditLog.table_name == "translation_jobs")
        )
        logs = list(audit_res.mappings().all())
        assert len(logs) >= 1

@pytest.mark.asyncio
async def test_translation_validation_failure():
    study_payload = {
        "study_id": "test_study_invalid",
        "payload": {
            "name": "Invalid Trial"
        }
    }
    
    with TestClient(app) as client:
        response = client.post("/events/study-published", json=study_payload)
        assert response.status_code == 200
        
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            TranslationJob.__table__.select().where(TranslationJob.study_id == "test_study_invalid")
        )
        job = result.mappings().first()
        assert job is not None
        assert job["status"] == "FAILED"
        assert "protocol" in job["error_message"]

