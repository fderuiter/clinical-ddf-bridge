from fastapi import HTTPException, Request

# Minimal, allow-list-based role constants
ROLE_CRA = "CRA"
ROLE_DATA_MANAGER = "Data Manager"
ROLE_SITE_INVESTIGATOR = "Site Investigator"
ROLE_AUDITOR = "Auditor"
ROLE_SPONSOR_ADMIN = "Sponsor Admin"

AUDITOR_ROLES = {"auditor", "inspector", "regulatory_inspector"}


def get_normalized_roles(request: Request) -> list[str]:
    """
    Retrieves and normalizes request.state.roles or raw X-User-Roles headers.
    Updates request.state.roles to be a list of lowercase, stripped strings.
    """
    roles_val = getattr(request.state, "roles", None)
    if roles_val is None:
        roles_val = request.headers.get("X-User-Roles", "")

    if isinstance(roles_val, str):
        normalized = [r.strip().lower() for r in roles_val.split(",") if r.strip()]
    elif isinstance(roles_val, list):
        normalized = [str(r).strip().lower() for r in roles_val if str(r).strip()]
    else:
        normalized = []

    request.state.roles = normalized
    return normalized


def verify_not_auditor(request: Request) -> list[str]:
    """
    FastAPI dependency to verify that the request does not originate from an auditor persona.
    Raises HTTP 403 Forbidden if any auditor roles are detected.
    """
    roles = get_normalized_roles(request)
    if any(role in AUDITOR_ROLES for role in roles):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Auditor personas are restricted to read-only access.",
        )
    return roles


def verify_is_auditor(request: Request) -> list[str]:
    """
    FastAPI dependency to verify that the request is made by an authorized auditor persona.
    Raises HTTP 403 Forbidden if no authorized auditor/inspection roles are detected.
    """
    roles = get_normalized_roles(request)
    if not any(role in AUDITOR_ROLES for role in roles):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Access is restricted to authorized auditor/inspection roles.",
        )
    return roles


ROLE_EXPANSIONS = {
    "site investigator": {"site investigator", "investigator", "site-investigator", "site_investigator", "investigator_user"},
    "data manager": {"data manager", "data_manager", "data-manager", "sponsor_dm", "dm", "admin"},
    "cra": {"cra"},
    "auditor": {"auditor", "inspector", "regulatory_inspector"},
    "sponsor admin": {"sponsor admin", "sponsor_admin", "admin"},
}


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory to enforce that the caller has at least one of the allowed roles.
    Allows case-insensitive, whitespace-insensitive matches and role synonym expansion.
    """
    def dependency(request: Request) -> list[str]:
        roles = get_normalized_roles(request)
        expanded_allowed = set()
        for role in allowed_roles:
            norm_role = role.strip().lower()
            expanded_allowed.add(norm_role)
            if norm_role in ROLE_EXPANSIONS:
                expanded_allowed.update(ROLE_EXPANSIONS[norm_role])

        if not any(role in expanded_allowed for role in roles):
            raise HTTPException(
                status_code=403,
                detail="User role is not authorized for this action.",
            )
        return roles
    return dependency

