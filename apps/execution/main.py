import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from pydantic import BaseModel

from apps.execution.database.core import db_manager
from apps.execution.database.middleware import ContextResetMiddleware
from apps.execution.translator import process_translation
from packages.security.middleware import GatewayAuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle the lifespan events for the FastAPI application.

    Initializes the database session manager on startup and securely
    cleans up connections on shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    # Initialize shared database library
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    db_manager.init_db(db_url)
    yield
    # Cleanup database connection
    await db_manager.close()


app = FastAPI(
    title="Cadence Clinical - EDC Execution Engine", version="0.1.0", lifespan=lifespan
)

app.add_middleware(ContextResetMiddleware)

app.add_middleware(GatewayAuthMiddleware)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Service health check endpoint.

    Returns a basic JSON payload indicating the service is operational.

    Returns:
        dict[str, str]: The health status payload.
    """
    return {"status": "ok", "service": "execution"}


class StudyEvent(BaseModel):
    """Pydantic model representing an incoming study publication event.

    Attributes:
        study_id (str): The unique identifier of the study.
        payload (dict[str, Any]): The raw USDM protocol payload.
    """

    study_id: str
    payload: dict[str, Any]


@app.post("/events/study-published")
async def study_published(
    event: StudyEvent, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Ingest study publication events and trigger layout generation asynchronously.

    Args:
        event (StudyEvent): The incoming study event payload.
        background_tasks (BackgroundTasks): FastAPI background task manager.

    Returns:
        dict[str, str]: A status message confirming job acceptance.
    """
    # Requirement 1: Listen for study publication events and trigger translation processes in the background.
    background_tasks.add_task(
        process_translation,
        event.study_id,
        event.payload,
        db_manager.get_session_maker(),
    )
    return {"status": "accepted", "message": "Translation job queued in background."}


# --- NEW CLINICAL ENGINE ENDPOINTS ---


class UnitDetail(BaseModel):
    """Details for a single value/unit pair."""

    value: float
    unit: str


class UCUMConvertRequest(BaseModel):
    """Request schema for UCUM unit conversion.

    Attributes:
        value (float): The numeric value to convert.
        source_unit (str): The source UCUM unit code.
        target_unit (str): The target standard UCUM unit code.
        domain (str, optional): The clinical domain / substance context.
    """

    value: float
    source_unit: str
    target_unit: str
    domain: Optional[str] = None


class UCUMConvertResponse(BaseModel):
    """Response schema for UCUM unit conversion.

    Attributes:
        source (UnitDetail): Original value and unit.
        target (UnitDetail, optional): Normalized target value and unit.
        is_compatible (bool): Compatibility flag.
        scale_factor (float, optional): Scaling multiplier.
        offset (float, optional): Offset parameter.
    """

    source: UnitDetail
    target: Optional[UnitDetail] = None
    is_compatible: bool
    scale_factor: Optional[float] = None
    offset: Optional[float] = None


@app.post("/api/v1/dictionaries/ucum/convert", response_model=UCUMConvertResponse)
async def ucum_convert(req: UCUMConvertRequest) -> dict[str, Any]:
    """Standardize numeric values and verify scale compatibility between source and target UCUM units.

    Args:
        req (UCUMConvertRequest): Request payload containing the value and units.

    Returns:
        dict[str, Any]: Formatted conversion response.
    """
    from apps.execution.ucum import convert_ucum

    target_val, mult, offset, is_compatible = convert_ucum(
        req.value, req.source_unit, req.target_unit, req.domain
    )
    if is_compatible:
        return {
            "source": {"value": req.value, "unit": req.source_unit},
            "target": {"value": target_val, "unit": req.target_unit},
            "is_compatible": True,
            "scale_factor": mult,
            "offset": offset,
        }
    else:
        return {
            "source": {"value": req.value, "unit": req.source_unit},
            "target": None,
            "is_compatible": False,
            "scale_factor": None,
            "offset": None,
        }


class OutlierDetectRequest(BaseModel):
    """Request schema for testing outlier detection algorithms.

    Attributes:
        values (List[float]): A batch of numeric observations to analyze.
        method (str, optional): Method to use ("zscore", "modified_zscore", or "tukey").
        threshold (float, optional): Custom standard deviation or fence threshold.
    """

    values: List[float]
    method: Optional[str] = "zscore"
    threshold: Optional[float] = None


@app.post("/api/v1/execution/outliers/detect")
async def detect_outliers_endpoint(req: OutlierDetectRequest) -> dict[str, Any]:
    """Utility endpoint to test pure-Python statistical outlier detection algorithms on dry-run lists.

    Args:
        req (OutlierDetectRequest): Request containing raw values and selected method.

    Returns:
        dict[str, Any]: Identified outlier records.
    """
    from apps.execution.outliers import (
        detect_modified_zscore_outliers,
        detect_tukey_outliers,
        detect_zscore_outliers,
    )

    method = req.method.lower() if req.method else "zscore"
    if method == "zscore":
        thresh = req.threshold if req.threshold is not None else 3.0
        outliers = detect_zscore_outliers(req.values, threshold=thresh)
    elif method == "modified_zscore":
        thresh = req.threshold if req.threshold is not None else 3.5
        outliers = detect_modified_zscore_outliers(req.values, threshold=thresh)
    elif method == "tukey":
        k = req.threshold if req.threshold is not None else 1.5
        outliers = detect_tukey_outliers(req.values, k=k)
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported outlier method: {req.method}"
        )

    return {
        "method": method,
        "input_count": len(req.values),
        "outlier_count": len(outliers),
        "outliers": outliers,
    }


class SubjectCreate(BaseModel):
    """Request schema for creating clinical subjects.

    Attributes:
        study_id (str): Associated clinical study identifier.
        subject_key (str): Pseudonymized subject key (e.g. SUB-101).
        status (str, optional): Initial subject state. Defaults to "Screening".
    """

    study_id: str
    subject_key: str
    status: Optional[str] = "Screening"


@app.post("/api/v1/execution/subjects")
async def create_subject(req: SubjectCreate) -> Any:
    """Creates or retrieves a clinical trial subject record.

    Ensures that unencrypted PII is never stored in observation/subject schemas.

    Args:
        req (SubjectCreate): Request details.

    Returns:
        Any: Created Subject instance.
    """
    from sqlalchemy import select

    from apps.execution.database.models import Subject

    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            stmt = select(Subject).where(
                Subject.study_id == req.study_id,
                Subject.subject_key == req.subject_key,
                Subject.is_deleted == False,
            )
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return {
                    "id": existing.id,
                    "study_id": existing.study_id,
                    "subject_key": existing.subject_key,
                    "status": existing.status,
                    "is_deleted": existing.is_deleted,
                }

            sub = Subject(
                study_id=req.study_id,
                subject_key=req.subject_key,
                status=req.status,
            )
            session.add(sub)
            await session.flush()
            return {
                "id": sub.id,
                "study_id": sub.study_id,
                "subject_key": sub.subject_key,
                "status": sub.status,
                "is_deleted": sub.is_deleted,
            }


class VisitCreate(BaseModel):
    """Request schema for establishing scheduled study visits.

    Attributes:
        study_id (str): Unique study identifier.
        subject_key (str): Subject unique key.
        visit_oid (str): Clinical/protocol Visit OID.
        visit_name (str): display/logical name of the visit.
        visit_number (int, optional): Order number of the visit.
    """

    study_id: str
    subject_key: str
    visit_oid: str
    visit_name: str
    visit_number: Optional[int] = None


@app.post("/api/v1/execution/visits")
async def create_visit(req: VisitCreate) -> Any:
    """Record a scheduled clinical visit/event occurrence.

    Args:
        req (VisitCreate): Request details.

    Returns:
        Any: Created Visit record.
    """
    from sqlalchemy import select

    from apps.execution.database.models import Visit

    async with db_manager.get_session_maker()() as session:
        async with session.begin():
            stmt = select(Visit).where(
                Visit.study_id == req.study_id,
                Visit.subject_key == req.subject_key,
                Visit.visit_oid == req.visit_oid,
                Visit.is_deleted == False,
            )
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return {
                    "id": existing.id,
                    "study_id": existing.study_id,
                    "subject_key": existing.subject_key,
                    "visit_oid": existing.visit_oid,
                    "visit_name": existing.visit_name,
                    "visit_number": existing.visit_number,
                    "is_deleted": existing.is_deleted,
                }

            vis = Visit(
                study_id=req.study_id,
                subject_key=req.subject_key,
                visit_oid=req.visit_oid,
                visit_name=req.visit_name,
                visit_number=req.visit_number,
            )
            session.add(vis)
            await session.flush()
            return {
                "id": vis.id,
                "study_id": vis.study_id,
                "subject_key": vis.subject_key,
                "visit_oid": vis.visit_oid,
                "visit_name": vis.visit_name,
                "visit_number": vis.visit_number,
                "is_deleted": vis.is_deleted,
            }


class ObservationCreate(BaseModel):
    """Request schema for posting a clinical trial observation record.

    Attributes:
        study_id (str): Study identifier.
        subject_key (str): Pseudonymized subject key.
        visit_oid (str): Associated visit OID.
        form_oid (str): Form OID.
        form_version (str, optional): Version index of form. Defaults to "1.0".
        item_group_oid (str): Item group OID.
        item_oid (str): Concept/item OID.
        value (str): Textual or numeric value.
        unit (str, optional): UCUM unit associated with measurement.
    """

    study_id: str
    subject_key: str
    visit_oid: str
    form_oid: str
    form_version: Optional[str] = "1.0"
    item_group_oid: str
    item_oid: str
    value: str
    unit: Optional[str] = None


@app.post("/api/v1/execution/observations")
async def create_observation(req: ObservationCreate) -> Any:
    """Record and persist clinical subject observations, visits, and measurement histories.

    Performs on-the-fly standard unit normalization via UCUM rules, saves history logs,
    and runs pure-Python standard Z-score outlier flagging (outside of 3 standard deviations).

    Args:
        req (ObservationCreate): Observation data to save.

    Returns:
        Any: Created Observation record.
    """
    from sqlalchemy import select

    from apps.execution.database.models import (
        MeasurementHistory,
        Observation,
        Subject,
        Visit,
    )
    from apps.execution.outliers import calculate_mean, calculate_sample_std_dev
    from apps.execution.ucum import convert_ucum

    normalized_value = None
    normalized_unit = None

    # Try parsing value as float for UCUM conversion and outlier checks
    try:
        val_float = float(req.value)
        is_numeric = True
    except ValueError:
        is_numeric = False

    if is_numeric and req.unit:
        # Resolve target unit dynamically
        from apps.execution.ucum import UCUM_CONVERSION_RULES

        target_unit = None
        for src, tgt in UCUM_CONVERSION_RULES.keys():
            if src == req.unit:
                target_unit = tgt
                break

        if req.unit == "[degF]":
            target_unit = "Cel"

        if target_unit:
            t_val, mult, offset, is_compatible = convert_ucum(
                val_float, req.unit, target_unit, req.item_oid
            )
            if is_compatible:
                normalized_value = t_val
                normalized_unit = target_unit

    is_outlier = False
    check_val = normalized_value if normalized_value is not None else val_float

    async with db_manager.get_session_maker()() as session:
        # Pre-populate subject/visit if missing to provide a smooth DX
        async with session.begin():
            # Check subject
            sub_stmt = select(Subject).where(
                Subject.study_id == req.study_id,
                Subject.subject_key == req.subject_key,
                Subject.is_deleted == False,
            )
            sub_res = await session.execute(sub_stmt)
            if not sub_res.scalars().first():
                session.add(
                    Subject(study_id=req.study_id, subject_key=req.subject_key)
                )

            # Check visit
            vis_stmt = select(Visit).where(
                Visit.study_id == req.study_id,
                Visit.subject_key == req.subject_key,
                Visit.visit_oid == req.visit_oid,
                Visit.is_deleted == False,
            )
            vis_res = await session.execute(vis_stmt)
            if not vis_res.scalars().first():
                session.add(
                    Visit(
                        study_id=req.study_id,
                        subject_key=req.subject_key,
                        visit_oid=req.visit_oid,
                        visit_name=f"Visit {req.visit_oid}",
                    )
                )

            # Retrieve existing numeric observation values for study populations to run Z-score check
            if is_numeric:
                stmt = select(Observation).where(
                    Observation.study_id == req.study_id,
                    Observation.item_oid == req.item_oid,
                    Observation.is_deleted == False,
                )
                res = await session.execute(stmt)
                existing_obs = res.scalars().all()

                values = []
                for obs in existing_obs:
                    try:
                        o_val = (
                            obs.normalized_value
                            if obs.normalized_value is not None
                            else float(obs.value)
                        )
                        values.append(o_val)
                    except ValueError:
                        continue

                # Standard Z-Score Outlier Flag: $|Z_i| > 3.0$
                if len(values) >= 3:
                    mean = calculate_mean(values)
                    std_dev = calculate_sample_std_dev(values, mean)
                    if std_dev > 0.0:
                        z_score = (check_val - mean) / std_dev
                        if abs(z_score) > 3.0:
                            is_outlier = True

            # Commit final Observation and MeasurementHistory records
            obs = Observation(
                study_id=req.study_id,
                subject_key=req.subject_key,
                visit_oid=req.visit_oid,
                form_oid=req.form_oid,
                form_version=req.form_version,
                item_group_oid=req.item_group_oid,
                item_oid=req.item_oid,
                value=req.value,
                unit=req.unit,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                is_outlier=is_outlier,
            )
            session.add(obs)
            await session.flush()

            if is_numeric:
                hist = MeasurementHistory(
                    study_id=req.study_id,
                    subject_key=req.subject_key,
                    item_oid=req.item_oid,
                    value=check_val,
                    unit=normalized_unit or req.unit,
                )
                session.add(hist)
                await session.flush()

            return {
                "id": obs.id,
                "study_id": obs.study_id,
                "subject_key": obs.subject_key,
                "visit_oid": obs.visit_oid,
                "form_oid": obs.form_oid,
                "form_version": obs.form_version,
                "item_group_oid": obs.item_group_oid,
                "item_oid": obs.item_oid,
                "value": obs.value,
                "unit": obs.unit,
                "normalized_value": obs.normalized_value,
                "normalized_unit": obs.normalized_unit,
                "is_outlier": obs.is_outlier,
                "is_deleted": obs.is_deleted,
            }


@app.get("/api/v1/execution/studies/{study_id}/export")
async def export_study_data(
    study_id: str,
    format: str,
    version: Optional[str] = "1.3.2",
) -> Response:
    """Exports patient capturing datasets in bulk.

    Handles CDISC ODM-XML, CDISC ODM-JSON, and CSV-ZIP formats.

    Args:
        study_id (str): Unique identifier of the study.
        format (str): Targeted export format (ODM-XML, ODM-JSON, or CSV-ZIP).
        version (str, optional): Target CDISC ODM version standard. Defaults to "1.3.2".

    Returns:
        Response: Formatted Response containing raw content or attachments.
    """
    from sqlalchemy import select

    from apps.execution.database.models import Observation, Subject, Visit
    from apps.execution.export import export_csv_zip, export_odm_json, export_odm_xml

    fmt = format.upper()
    if fmt not in ["ODM-XML", "ODM-JSON", "CSV-ZIP"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Must be ODM-XML, ODM-JSON, or CSV-ZIP.",
        )

    async with db_manager.get_session_maker()() as session:
        # Fetch all observations
        stmt = select(Observation).where(
            Observation.study_id == study_id, Observation.is_deleted == False
        )
        res = await session.execute(stmt)
        observations = res.scalars().all()

        if fmt == "ODM-XML":
            xml_content = export_odm_xml(study_id, list(observations), version=version)
            return Response(content=xml_content, media_type="application/xml")

        elif fmt == "ODM-JSON":
            json_content = export_odm_json(
                study_id, list(observations), version=version
            )
            from fastapi.encoders import jsonable_encoder
            from fastapi.responses import JSONResponse

            return JSONResponse(content=jsonable_encoder(json_content))

        elif fmt == "CSV-ZIP":
            sub_stmt = select(Subject).where(
                Subject.study_id == study_id, Subject.is_deleted == False
            )
            sub_res = await session.execute(sub_stmt)
            subjects = sub_res.scalars().all()

            vis_stmt = select(Visit).where(
                Visit.study_id == study_id, Visit.is_deleted == False
            )
            vis_res = await session.execute(vis_stmt)
            visits = vis_res.scalars().all()

            zip_bytes = export_csv_zip(
                list(subjects), list(visits), list(observations)
            )

            headers = {
                "Content-Disposition": f'attachment; filename="clinical_export_{study_id}.zip"'
            }
            return Response(
                content=zip_bytes, media_type="application/zip", headers=headers
            )

    raise HTTPException(status_code=500, detail="Failed to process export.")

