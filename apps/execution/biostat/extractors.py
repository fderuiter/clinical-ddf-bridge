import base64
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet

from apps.execution.biostat.models import SUPPRecord
from apps.execution.biostat.terminology import normalize_race, normalize_sex

# Symmetric encryption helper for patient demographics (matching main.py key)
_DEMO_KEY = base64.urlsafe_b64encode(b"cadence_clinical_demographics_32")
_fernet = Fernet(_DEMO_KEY)


def decrypt_demographics(encrypted_str: str) -> dict:
    """Decrypt demographic details to retrieve raw PII payload."""
    try:
        decrypted = _fernet.decrypt(encrypted_str.encode("utf-8"))
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


def calculate_age(rfstdtc: Optional[str], brthdtc: Optional[str]) -> Optional[int]:
    """Derive AGE from RFSTDTC and BRTHDTC where source precision supports the calculation.

    Requires full YYYY-MM-DD precision for both dates.
    """
    if not rfstdtc or not brthdtc:
        return None

    # Match YYYY-MM-DD at the start of strings
    match_rf = re.match(r"^(\d{4})-(\d{2})-(\d{2})", rfstdtc.strip())
    match_br = re.match(r"^(\d{4})-(\d{2})-(\d{2})", brthdtc.strip())

    if not match_rf or not match_br:
        return None

    try:
        from datetime import date

        rf_y, rf_m, rf_d = map(int, match_rf.groups())
        br_y, br_m, br_d = map(int, match_br.groups())

        rf_date = date(rf_y, rf_m, rf_d)
        br_date = date(br_y, br_m, br_d)

        delta_days = (rf_date - br_date).days
        if delta_days < 0:
            return None
        return int(delta_days // 365.25)
    except Exception:
        return None


def get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to retrieve value from dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_demographics(subject: Any) -> dict:
    """Extracts demographics dict from subject (handling encryption and structures)."""
    demographics = get_value(subject, "demographics")
    if not demographics:
        enc = get_value(subject, "encrypted_demographics")
        if enc:
            demographics = decrypt_demographics(enc)
    if isinstance(demographics, dict):
        return demographics
    elif hasattr(demographics, "model_dump"):
        return demographics.model_dump()
    elif hasattr(demographics, "dict"):
        return demographics.dict()
    return {}


def extract_dm(
    subjects: List[Any],
    observations: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """Pure extractor for SDTM Demographics (DM) dataset from in-memory source models.

    Args:
        subjects: List of clinical subject records (objects or dicts).
        observations: Optional list of clinical observation records (objects or dicts).

    Returns:
        List[Dict[str, Any]]: List of mapped DM domain dictionaries.
    """
    obs_list = observations or []

    # Pre-group observations by subject_id for fast lookup
    obs_by_subject: Dict[str, List[Any]] = {}
    for obs in obs_list:
        sub_id = get_value(obs, "subject_id")
        if sub_id:
            obs_by_subject.setdefault(sub_id, []).append(obs)

    dm_records = []

    for subj in subjects:
        sub_id = get_value(subj, "subject_id")
        if not sub_id:
            continue

        study_id = get_value(subj, "study_id") or ""
        demographics = get_demographics(subj)

        # 1. STUDYID
        # 2. SUBJID
        # 3. USUBJID
        site_id = (
            get_value(subj, "site_id")
            or demographics.get("site_id")
            or demographics.get("siteID")
            or "001"
        )
        usubjid = (
            get_value(subj, "usubjid")
            or get_value(subj, "USUBJID")
            or demographics.get("usubjid")
            or demographics.get("USUBJID")
        )
        if not usubjid:
            usubjid = f"{study_id}-{site_id}-{sub_id}"

        sub_obs = obs_by_subject.get(sub_id, [])

        # 4. RFSTDTC (First treatment exposure)
        rfstdtc = None
        ex_obs = [
            o
            for o in sub_obs
            if str(get_value(o, "domain")).upper() == "EX"
            or str(get_value(o, "test_code")).upper() in {"EXSTDTC", "RFSTDTC"}
        ]
        if ex_obs:
            dates = []
            for o in ex_obs:
                val_str = get_value(o, "value_string")
                obs_dt = get_value(o, "observation_date")
                if val_str:
                    dates.append(str(val_str).strip())
                elif obs_dt:
                    if hasattr(obs_dt, "isoformat"):
                        dates.append(obs_dt.isoformat())
                    else:
                        dates.append(str(obs_dt))
            if dates:
                rfstdtc = min(dates)

        if not rfstdtc:
            rfstdtc = (
                get_value(subj, "rfstdtc")
                or get_value(subj, "RFSTDTC")
                or demographics.get("rfstdtc")
                or demographics.get("RFSTDTC")
            )

        # 5. RFENDTC (Last study exposure or completion)
        rfendtc = None
        ds_obs = [
            o
            for o in sub_obs
            if str(get_value(o, "domain")).upper() == "DS"
            or str(get_value(o, "test_code")).upper() in {"DSSTDTC", "RFENDTC"}
        ]
        if ds_obs:
            dates = []
            for o in ds_obs:
                val_str = get_value(o, "value_string")
                obs_dt = get_value(o, "observation_date")
                if val_str:
                    dates.append(str(val_str).strip())
                elif obs_dt:
                    if hasattr(obs_dt, "isoformat"):
                        dates.append(obs_dt.isoformat())
                    else:
                        dates.append(str(obs_dt))
            if dates:
                rfendtc = max(dates)

        if not rfendtc:
            rfendtc = (
                get_value(subj, "rfendtc")
                or get_value(subj, "RFENDTC")
                or demographics.get("rfendtc")
                or demographics.get("RFENDTC")
            )

        # 6. BRTHDTC
        brthdtc = (
            demographics.get("birthdate")
            or demographics.get("birth_date")
            or demographics.get("BRTHDTC")
        )
        if not brthdtc:
            brth_obs = [
                o
                for o in sub_obs
                if str(get_value(o, "test_code")).upper() == "BRTHDTC"
            ]
            if brth_obs:
                brthdtc = get_value(brth_obs[0], "value_string")

        # 7. AGE & AGEU
        age = calculate_age(rfstdtc, brthdtc)
        ageu = "YEARS"

        # 8. SEX
        raw_sex = (
            demographics.get("gender")
            or demographics.get("sex")
            or demographics.get("SEX")
        )
        if not raw_sex:
            sex_obs = [
                o for o in sub_obs if str(get_value(o, "test_code")).upper() == "SEX"
            ]
            if sex_obs:
                raw_sex = get_value(sex_obs[0], "value_string")
        if not raw_sex:
            raw_sex = "U"
        sex = normalize_sex(raw_sex)

        # 9. RACE
        raw_race = demographics.get("race") or demographics.get("RACE")
        if not raw_race:
            race_obs = [
                o for o in sub_obs if str(get_value(o, "test_code")).upper() == "RACE"
            ]
            if race_obs:
                raw_race = get_value(race_obs[0], "value_string")
        if not raw_race:
            raw_race = "OTHER"
        race = normalize_race(raw_race)

        # 10. ARM
        arm = demographics.get("arm") or demographics.get("ARM")
        if not arm:
            arm_obs = [
                o
                for o in sub_obs
                if str(get_value(o, "test_code")).upper() in {"ARM", "ACTARM"}
            ]
            if arm_obs:
                arm = get_value(arm_obs[0], "value_string")
        if not arm:
            arm = "SCREEN FAILURE"

        record = {
            "STUDYID": study_id,
            "USUBJID": usubjid,
            "SUBJID": sub_id,
            "RFSTDTC": rfstdtc or "",
            "RFENDTC": rfendtc or "",
            "BRTHDTC": brthdtc or "",
            "AGE": age,
            "AGEU": ageu,
            "SEX": sex,
            "RACE": race,
            "ARM": arm,
        }
        dm_records.append(record)

    return dm_records


def extract_mh(
    subjects: List[Any],
    observations: List[Any],
) -> Tuple[List[Dict[str, Any]], List[SUPPRecord]]:
    """Pure extractor for SDTM Medical History (MH) dataset and SUPPMH records.

    Args:
        subjects: List of clinical subject records (objects or dicts).
        observations: List of clinical observations of the MH domain (objects or dicts).

    Returns:
        Tuple[List[Dict[str, Any]], List[SUPPRecord]]:
            - List of MH SDTM dictionaries.
            - List of SUPPRecord models for unmapped qualifier fields.
    """
    # 1. Index subjects by subject_id for fast lookup
    subjects_by_id = {}
    for s in subjects:
        sub_id = get_value(s, "subject_id")
        if sub_id:
            subjects_by_id[sub_id] = s

    # 2. Filter observations for MH domain
    mh_obs = [o for o in observations if str(get_value(o, "domain")).upper() == "MH"]

    # 3. Group MH observations by subject_id
    obs_by_subject: Dict[str, List[Any]] = {}
    for o in mh_obs:
        sub_id = get_value(o, "subject_id")
        if sub_id:
            obs_by_subject.setdefault(sub_id, []).append(o)

    mh_records: List[Dict[str, Any]] = []
    supp_records: List[SUPPRecord] = []

    # 4. For each subject, process and sequence their MH events
    for sub_id, sub_obs in obs_by_subject.items():
        subj = subjects_by_id.get(sub_id)
        study_id = get_value(subj, "study_id") if subj else ""
        demographics = get_demographics(subj) if subj else {}

        site_id = (
            get_value(subj, "site_id")
            or demographics.get("site_id")
            or demographics.get("siteID")
            or "001"
        )
        usubjid = (
            get_value(subj, "usubjid")
            or get_value(subj, "USUBJID")
            or demographics.get("usubjid")
            or demographics.get("USUBJID")
        )
        if not usubjid:
            usubjid = f"{study_id}-{site_id}-{sub_id}"

        # Group observations by page_id (or observation_date if page_id is missing/None)
        # to identify a single medical history record/form submission
        groups: Dict[str, List[Any]] = {}
        for o in sub_obs:
            page_id = get_value(o, "page_id")
            if page_id:
                group_key = f"page_{page_id}"
            else:
                obs_dt = get_value(o, "observation_date")
                if obs_dt:
                    if hasattr(obs_dt, "isoformat"):
                        group_key = f"date_{obs_dt.isoformat()}"
                    else:
                        group_key = f"date_{str(obs_dt)}"
                else:
                    group_key = f"uniq_{id(o)}"
            groups.setdefault(group_key, []).append(o)

        subject_mh_records = []

        for group_key, group_obs in groups.items():
            record_data = {
                "STUDYID": study_id,
                "USUBJID": usubjid,
                "SUBJID": sub_id,
            }

            # Map the standard fields
            unmapped_observations = []
            for o in group_obs:
                tcode = str(get_value(o, "test_code")).upper()
                val_str = get_value(o, "value_string")
                val_num = get_value(o, "value")
                val = (
                    val_str
                    if val_str is not None
                    else (str(val_num) if val_num is not None else "")
                )

                if tcode == "MHTERM":
                    record_data["MHTERM"] = val
                elif tcode == "MHDECOD":
                    record_data["MHDECOD"] = val
                elif tcode == "MHBODSYS":
                    record_data["MHBODSYS"] = val
                elif tcode in {"MHSTDTC", "MHDTC"}:
                    record_data["MHSTDTC"] = val
                elif tcode == "MHENDTC":
                    record_data["MHENDTC"] = val
                elif tcode == "MHENRTP":
                    record_data["MHENRTP"] = val
                else:
                    # Non-standard/unmapped qualifier field
                    unmapped_observations.append(o)

            # Ensure minimal requirements: MHTERM should be present
            if "MHTERM" not in record_data:
                # Fallback to test_name of first observation if MHTERM is missing
                fallback_term = ""
                for o in group_obs:
                    fallback_term = (
                        get_value(o, "test_name") or get_value(o, "test_code") or ""
                    )
                    if fallback_term:
                        break
                record_data["MHTERM"] = fallback_term

            # Save the unmapped observations list with the record data temporarily
            # so we can generate SUPPMH records after sorting and sequencing
            record_data["_unmapped_obs"] = unmapped_observations
            subject_mh_records.append(record_data)

        # 5. Stable per-subject sequencing based on MHSTDTC (onset date field), then MHTERM
        subject_mh_records.sort(
            key=lambda r: (
                r.get("MHSTDTC") or "",
                r.get("MHTERM") or "",
            )
        )

        # 6. Assign MHSEQ and generate SUPPMH records
        for seq, rec in enumerate(subject_mh_records, start=1):
            rec["MHSEQ"] = seq
            unmapped_obs = rec.pop("_unmapped_obs", [])

            # Generate SUPPMH records for unmapped content
            for o in unmapped_obs:
                qname = str(get_value(o, "test_code"))
                qlabel = str(get_value(o, "test_name") or qname)
                val_str = get_value(o, "value_string")
                val_num = get_value(o, "value")
                qval = (
                    val_str
                    if val_str is not None
                    else (str(val_num) if val_num is not None else "")
                )

                supp = SUPPRecord(
                    STUDYID=study_id,
                    RDOMAIN="MH",
                    USUBJID=usubjid,
                    IDVAR="MHSEQ",
                    IDVARVAL=str(seq),
                    QNAM=qname,
                    QLABEL=qlabel,
                    QVAL=qval,
                )
                supp_records.append(supp)

            # Clean and finalize standard MH fields in record
            final_record = {
                "STUDYID": rec["STUDYID"],
                "USUBJID": rec["USUBJID"],
                "SUBJID": rec["SUBJID"],
                "MHSEQ": rec["MHSEQ"],
                "MHTERM": rec.get("MHTERM") or "",
                "MHDECOD": rec.get("MHDECOD") or "",
                "MHBODSYS": rec.get("MHBODSYS") or "",
                "MHSTDTC": rec.get("MHSTDTC") or "",
                "MHENDTC": rec.get("MHENDTC") or "",
                "MHENRTP": rec.get("MHENRTP") or "",
            }
            mh_records.append(final_record)

    return mh_records, supp_records
