"""CDISC Clinical Data Export Engine.

Provides utilities to export stored clinical subject observation records into
validated CDISC formats (ODM-XML, ODM-JSON) or standard row-structured CSV-ZIP archives.
"""

import csv
import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import zipfile

from jinja2 import Environment, FileSystemLoader

from apps.execution.database.models import Observation, Subject, Visit

# Setup Jinja environment for XML templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def group_observations(observations: List[Observation]) -> List[Dict[str, Any]]:
    """Groups flat database observations into a nested hierarchical structure.

    Groups observations by SubjectKey -> VisitOID -> (FormOID, FormVersion) -> ItemGroupOID.

    Args:
        observations (List[Observation]): A list of flat database Observation models.

    Returns:
        List[Dict[str, Any]]: A nested representation suitable for Jinja rendering and JSON output.
    """
    grouped: Dict[str, Dict[str, Dict[tuple, Dict[str, List[Dict[str, Any]]]]]] = {}

    for obs in observations:
        sub_key = obs.subject_key
        v_oid = obs.visit_oid
        f_oid = obs.form_oid
        f_ver = obs.form_version or "1.0"
        ig_oid = obs.item_group_oid
        item_oid = obs.item_oid
        val = obs.value

        if sub_key not in grouped:
            grouped[sub_key] = {}
        if v_oid not in grouped[sub_key]:
            grouped[sub_key][v_oid] = {}

        form_key = (f_oid, f_ver)
        if form_key not in grouped[sub_key][v_oid]:
            grouped[sub_key][v_oid][form_key] = {}
        if ig_oid not in grouped[sub_key][v_oid][form_key]:
            grouped[sub_key][v_oid][form_key][ig_oid] = []

        grouped[sub_key][v_oid][form_key][ig_oid].append(
            {"item_oid": item_oid, "value": val}
        )

    # Transform into hierarchical list of dictionaries
    subjects_list = []
    for sub_key, visits in grouped.items():
        visits_list = []
        for v_oid, forms in visits.items():
            forms_list = []
            for (f_oid, f_ver), igs in forms.items():
                igs_list = []
                for ig_oid, items in igs.items():
                    igs_list.append({"item_group_oid": ig_oid, "items_list": items})
                forms_list.append(
                    {
                        "form_oid": f_oid,
                        "form_version": f_ver,
                        "item_groups": igs_list,
                    }
                )
            visits_list.append({"visit_oid": v_oid, "forms": forms_list})
        subjects_list.append({"subject_key": sub_key, "visits": visits_list})

    return subjects_list


def export_odm_xml(
    study_id: str,
    observations: List[Observation],
    version: str = "1.3.2",
) -> str:
    """Generates standard CDISC ODM-XML formatted string using pre-configured Jinja template.

    Args:
        study_id (str): The unique ID of the clinical trial study.
        observations (List[Observation]): List of observation records to export.
        version (str, optional): Target CDISC ODM standard version. Defaults to '1.3.2'.

    Returns:
        str: Validated CDISC ODM-XML string.
    """
    subjects_tree = group_observations(observations)
    template = jinja_env.get_template("clinical_data_export.xml.j2")

    creation_time = datetime.utcnow().isoformat() + "Z"
    file_oid = f"CADENCE.{study_id}.{int(datetime.utcnow().timestamp())}"

    return template.render(
        file_oid=file_oid,
        creation_datetime=creation_time,
        odm_version=version,
        study_id=study_id,
        metadata_version_oid="MV.001",
        subjects=subjects_tree,
    )


def export_odm_json(
    study_id: str,
    observations: List[Observation],
    version: str = "1.3.2",
) -> Dict[str, Any]:
    """Generates standard CDISC ODM-JSON format representation of the observations.

    Args:
        study_id (str): The unique ID of the clinical trial study.
        observations (List[Observation]): List of observation records to export.
        version (str, optional): Target CDISC ODM standard version. Defaults to '1.3.2'.

    Returns:
        Dict[str, Any]: Nested dictionary representation matching CDISC ODM-JSON specification.
    """
    subjects_tree = group_observations(observations)
    creation_time = datetime.utcnow().isoformat() + "Z"
    file_oid = f"CADENCE.{study_id}.{int(datetime.utcnow().timestamp())}"

    # Construct standard ODM JSON payload
    odm_json = {
        "odmVersion": version,
        "fileOID": f"ODM.{file_oid}",
        "fileType": "Transactional",
        "creationDateTime": creation_time,
        "clinicalData": [
            {
                "studyOID": study_id,
                "metaDataVersionOID": "MV.001",
                "subjectData": [
                    {
                        "subjectKey": sub["subject_key"],
                        "studyEventData": [
                            {
                                "studyEventOID": vis["visit_oid"],
                                "formData": [
                                    {
                                        "formOID": frm["form_oid"],
                                        "formVersion": frm["form_version"],
                                        "itemGroupData": [
                                            {
                                                "itemGroupOID": ig["item_group_oid"],
                                                "itemData": [
                                                    {
                                                        "itemOID": item["item_oid"],
                                                        "value": item["value"],
                                                    }
                                                    for item in ig["items_list"]
                                                ],
                                            }
                                            for ig in frm["item_groups"]
                                        ],
                                    }
                                    for frm in vis["forms"]
                                ],
                            }
                            for vis in sub["visits"]
                        ],
                    }
                    for sub in subjects_tree
                ],
            }
        ],
    }
    return odm_json


def export_csv_zip(
    subjects: List[Subject],
    visits: List[Visit],
    observations: List[Observation],
) -> bytes:
    """Packs clinical datasets into a standard ZIP archive containing clean, row-structured CSVs.

    Args:
        subjects (List[Subject]): List of clinical Subject records.
        visits (List[Visit]): List of Visit records.
        observations (List[Observation]): List of clinical Observation records.

    Returns:
        bytes: Raw zip file byte stream.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. subjects.csv
        subjects_io = io.StringIO()
        sub_writer = csv.writer(subjects_io)
        sub_writer.writerow(["id", "study_id", "subject_key", "status"])
        for sub in subjects:
            sub_writer.writerow(
                [sub.id, sub.study_id, sub.subject_key, sub.status]
            )
        zip_file.writestr("subjects.csv", subjects_io.getvalue())

        # 2. visits.csv
        visits_io = io.StringIO()
        vis_writer = csv.writer(visits_io)
        vis_writer.writerow(
            ["id", "study_id", "subject_key", "visit_oid", "visit_name", "visit_date"]
        )
        for vis in visits:
            v_date = vis.visit_date.isoformat() if vis.visit_date else ""
            vis_writer.writerow(
                [
                    vis.id,
                    vis.study_id,
                    vis.subject_key,
                    vis.visit_oid,
                    vis.visit_name,
                    v_date,
                ]
            )
        zip_file.writestr("visits.csv", visits_io.getvalue())

        # 3. observations.csv
        obs_io = io.StringIO()
        obs_writer = csv.writer(obs_io)
        obs_writer.writerow(
            [
                "id",
                "study_id",
                "subject_key",
                "visit_oid",
                "form_oid",
                "form_version",
                "item_group_oid",
                "item_oid",
                "value",
                "unit",
                "normalized_value",
                "normalized_unit",
                "is_outlier",
            ]
        )
        for obs in observations:
            obs_writer.writerow(
                [
                    obs.id,
                    obs.study_id,
                    obs.subject_key,
                    obs.visit_oid,
                    obs.form_oid,
                    obs.form_version,
                    obs.item_group_oid,
                    obs.item_oid,
                    obs.value,
                    obs.unit,
                    obs.normalized_value,
                    obs.normalized_unit,
                    obs.is_outlier,
                ]
            )
        zip_file.writestr("observations.csv", obs_io.getvalue())

    return zip_buffer.getvalue()
