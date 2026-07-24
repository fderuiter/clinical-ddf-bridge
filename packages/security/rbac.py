import copy
from typing import Any, List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

# Canonical role definitions
SYSADMIN = "sysadmin"
SPONSOR_DESIGNER = "sponsor_designer"
SPONSOR_DM = "sponsor_dm"
SPONSOR_MM = "sponsor_mm"
SPONSOR_STATISTICIAN = "sponsor_statistician"
INVESTIGATOR = "investigator"
CRC = "crc"
CRA = "cra"
SUBJECT = "subject"
AUDITOR = "auditor"

# Role normalization aliases (all keys should be defined with space separators only)
ROLE_ALIASES = {
    # SysAdmin
    "admin": SYSADMIN,
    "system": SYSADMIN,
    "sysadmin": SYSADMIN,
    "system administrator": SYSADMIN,
    "sponsor admin": SYSADMIN,

    # Sponsor Designer
    "sponsor designer": SPONSOR_DESIGNER,
    "sponsor study designer": SPONSOR_DESIGNER,
    "sponsor designer role": SPONSOR_DESIGNER,

    # Sponsor DM
    "sponsor data manager": SPONSOR_DM,
    "sponsor dm": SPONSOR_DM,
    "sponsor dm role": SPONSOR_DM,
    "grants manager": SPONSOR_DM,

    # Sponsor Clinical
    "sponsor clinical": "sponsor_clinical",

    # Sponsor MM
    "sponsor medical monitor": SPONSOR_MM,
    "sponsor mm": SPONSOR_MM,
    "sponsor mm role": SPONSOR_MM,

    # Sponsor Statistician
    "sponsor statistician": SPONSOR_STATISTICIAN,
    "sponsor statistician role": SPONSOR_STATISTICIAN,

    # Investigator
    "principal investigator": INVESTIGATOR,
    "site investigator": INVESTIGATOR,
    "investigator": INVESTIGATOR,
    "pi": INVESTIGATOR,
    "investigator role": INVESTIGATOR,

    # CRC
    "clinical research coordinator": CRC,
    "site coordinator": CRC,
    "coordinator": CRC,
    "crc": CRC,
    "coordinator role": CRC,

    # CRA
    "clinical research associate": CRA,
    "site monitor": CRA,
    "monitor": CRA,
    "cra": CRA,
    "monitor role": CRA,

    # Subject
    "subject": SUBJECT,
    "patient": SUBJECT,
    "epro": SUBJECT,

    # Auditor / Inspector
    "auditor": AUDITOR,
    "inspector": AUDITOR,
    "regulatory inspector": AUDITOR,
}

# Role to permission matrix matching §2.2
ROLE_PERMISSIONS = {
    SYSADMIN: {
        "study_design": "R",
        "subject_enrollment": "N",
        "ecrf_data_entry": "N",
        "query_lifecycle": "N",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "R",
    },
    SPONSOR_DESIGNER: {
        "study_design": "C/R/U/D",
        "subject_enrollment": "N",
        "ecrf_data_entry": "N",
        "query_lifecycle": "N",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "N",
    },
    SPONSOR_DM: {
        "study_design": "R",
        "subject_enrollment": "R",
        "ecrf_data_entry": "R",
        "query_lifecycle": "C/R/U/D",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "C/R/U",
    },
    SPONSOR_MM: {
        "study_design": "R",
        "subject_enrollment": "R",
        "ecrf_data_entry": "R",
        "query_lifecycle": "C/R/U",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "R",
    },
    SPONSOR_STATISTICIAN: {
        "study_design": "R",
        "subject_enrollment": "N",
        "ecrf_data_entry": "N",
        "query_lifecycle": "N",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "C/R/U",
    },
    INVESTIGATOR: {
        "study_design": "R",
        "subject_enrollment": "C/R/U",
        "ecrf_data_entry": "C/R/U",
        "query_lifecycle": "R/U",
        "sdv": "R",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "N",
    },
    CRC: {
        "study_design": "R",
        "subject_enrollment": "C/R/U",
        "ecrf_data_entry": "C/R/U",
        "query_lifecycle": "R/U",
        "sdv": "N",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "N",
    },
    CRA: {
        "study_design": "R",
        "subject_enrollment": "R",
        "ecrf_data_entry": "R",
        "query_lifecycle": "C/R/U/D",
        "sdv": "C/R/U/D",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "R",
    },
    SUBJECT: {
        "study_design": "N",
        "subject_enrollment": "N",
        "ecrf_data_entry": "C/U",
        "query_lifecycle": "N",
        "sdv": "N",
        "system_audit_logs": "N",
        "export_unmasked": "N",
        "export_masked": "N",
    },
    AUDITOR: {
        "study_design": "R",
        "subject_enrollment": "R",
        "ecrf_data_entry": "R",
        "query_lifecycle": "R",
        "sdv": "R",
        "system_audit_logs": "R",
        "export_unmasked": "N",
        "export_masked": "R",
    }
}

AUDITOR_ROLES = {AUDITOR, "auditor", "inspector", "regulatory_inspector", "regulatory inspector"}

class Principal(BaseModel):
    """
    Unified Principal abstraction containing user identity and context bounds.
    """
    user_id: str
    roles: List[str]  # Normalized canonical roles
    assigned_sites: List[str] = []
    unblinded_status: bool = False
    change_reason: Optional[str] = None

def normalize_role(role: str) -> str:
    """
    Normalizes a role string to its canonical form from ROLE_ALIASES.
    """
    cleaned = role.strip().lower().replace("_", " ").replace("-", " ")
    return ROLE_ALIASES.get(cleaned, cleaned)

def get_normalized_roles(request: Request) -> List[str]:
    """
    Retrieves and normalizes request.state.roles or raw X-User-Roles headers.
    Updates request.state.roles to be a list of lowercase, canonicalized strings.
    """
    roles_val = getattr(request.state, "roles", None)
    if roles_val is None:
        roles_val = request.headers.get("X-User-Roles", "")

    if isinstance(roles_val, str):
        raw_roles = [r.strip() for r in roles_val.split(",") if r.strip()]
    elif isinstance(roles_val, list):
        raw_roles = [str(r).strip() for r in roles_val if str(r).strip()]
    else:
        raw_roles = []

    normalized = [normalize_role(r) for r in raw_roles]
    request.state.roles = normalized
    return normalized

def verify_not_auditor(request: Request) -> List[str]:
    """
    FastAPI dependency to verify that the request does not originate from an auditor persona.
    Raises HTTP 403 Forbidden if any auditor roles are detected.
    """
    roles = get_normalized_roles(request)
    if any(role == AUDITOR or role in AUDITOR_ROLES for role in roles):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Auditor personas are restricted to read-only access.",
        )
    return roles

def verify_is_auditor(request: Request) -> List[str]:
    """
    FastAPI dependency to verify that the request is made by an authorized auditor persona.
    Raises HTTP 403 Forbidden if no authorized auditor/inspection roles are detected.
    """
    roles = get_normalized_roles(request)
    if not any(role == AUDITOR or role in AUDITOR_ROLES for role in roles):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Access is restricted to authorized auditor/inspection roles.",
        )
    return roles

def has_permission(principal: Principal, action: str) -> bool:
    """
    Checks if a Principal has the requested action permission based on §2.2.
    Action format: "resource:operation" (e.g. "query_lifecycle:create")
    """
    if ":" not in action:
        return False
    resource, operation = action.split(":", 1)
    resource = resource.lower().strip()
    operation = operation.lower().strip()

    op_map = {
        "create": "C",
        "read": "R",
        "update": "U",
        "delete": "D"
    }
    target_letter = op_map.get(operation, operation.upper())

    for role in principal.roles:
        role_perms = ROLE_PERMISSIONS.get(role, {})
        perm = role_perms.get(resource, "N")
        if target_letter in perm:
            return True

    return False

def can_access_site(principal: Principal, site_id: str) -> bool:
    """
    Checks if a Principal is authorized to access data/resources for a given site_id.
    Safely denies access if the user has site-level restrictions and site_id is outside their scope.
    """
    if not principal.assigned_sites:
        return True

    normalized_assigned = {s.lower() for s in principal.assigned_sites}
    return site_id.lower() in normalized_assigned

def require_permission_imperative(principal: Principal, action: str) -> None:
    """
    Imperative guard to verify that the Principal has the specified permission.
    Raises HTTP 403 Forbidden if not authorized.
    """
    if not has_permission(principal, action):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Insufficient permissions for action '{action}'",
        )

def get_principal(request: Request) -> Principal:
    """
    FastAPI dependency to construct and return the Principal from the request.
    """
    user_id = request.headers.get("X-User-Id", getattr(request.state, "user_id", "anonymous"))
    roles = get_normalized_roles(request)

    sites_val = request.headers.get("X-Assigned-Sites", request.headers.get("X-User-Sites", request.headers.get("X-Site-Id", "")))
    assigned_sites = [s.strip() for s in sites_val.split(",") if s.strip()] if sites_val else []

    unblinded_val = request.headers.get("X-Unblinded-Access", request.headers.get("X-Unblinded", "false")).strip().lower()
    unblinded_status = unblinded_val in ("true", "1")

    change_reason = request.headers.get("X-Change-Reason", getattr(request.state, "change_reason", None))

    return Principal(
        user_id=user_id,
        roles=roles,
        assigned_sites=assigned_sites,
        unblinded_status=unblinded_status,
        change_reason=change_reason
    )

def require_permission(action: str):
    """
    FastAPI dependency generator to enforce permission checks before route execution.
    """
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        require_permission_imperative(principal, action)
        return principal
    return dependency

def mask_payload(payload: Any, principal: Principal) -> Any:
    """
    Schema-agnostic helper to recursively mask sensitive fields in dictionaries,
    lists, or Pydantic models based on the Principal's unblinded_status.
    """
    if principal.unblinded_status:
        return payload

    if isinstance(payload, list):
        return [mask_payload(item, principal) for item in payload]
    elif isinstance(payload, dict):
        masked_dict = {}
        for k, v in payload.items():
            k_lower = k.lower()
            if k_lower in ("ssn", "dob", "initials"):
                masked_dict[k] = "REDACTED"
            elif k_lower in ("treatment_arm_id", "treatment_arm", "active_vs_placebo"):
                masked_dict[k] = "BLINDED"
            elif k_lower in ("administered_drug_code", "drug_code"):
                masked_dict[k] = "Kit Number XYZ"
            elif k_lower in ("changed_reason", "reason_for_change") and "blind" in str(v).lower():
                masked_dict[k] = "OBFUSCATED"
            else:
                masked_dict[k] = mask_payload(v, principal)
        return masked_dict
    elif hasattr(payload, "__dict__"):
        is_pydantic_v2 = hasattr(payload, "model_dump")
        is_pydantic_v1 = hasattr(payload, "dict") and hasattr(payload, "parse_obj")
        if is_pydantic_v2:
            data = payload.model_dump()
            masked_data = mask_payload(data, principal)
            return payload.__class__.model_validate(masked_data)
        elif is_pydantic_v1:
            data = payload.dict()
            masked_data = mask_payload(data, principal)
            return payload.__class__.parse_obj(masked_data)
        else:
            try:
                obj_copy = copy.copy(payload)
                for k in list(obj_copy.__dict__.keys()):
                    k_lower = k.lower()
                    v = getattr(obj_copy, k)
                    if k_lower in ("ssn", "dob", "initials"):
                        setattr(obj_copy, k, "REDACTED")
                    elif k_lower in ("treatment_arm_id", "treatment_arm", "active_vs_placebo"):
                        setattr(obj_copy, k, "BLINDED")
                    elif k_lower in ("administered_drug_code", "drug_code"):
                        setattr(obj_copy, k, "Kit Number XYZ")
                    elif k_lower in ("changed_reason", "reason_for_change") and "blind" in str(v).lower():
                        setattr(obj_copy, k, "OBFUSCATED")
                    else:
                        setattr(obj_copy, k, mask_payload(v, principal))
                return obj_copy
            except Exception:
                return payload
    else:
        return payload
