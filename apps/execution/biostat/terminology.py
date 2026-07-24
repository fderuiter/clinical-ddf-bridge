import re
from typing import List, Optional, Union

# CDISC Controlled Terminology sets
VALID_SEX_VALUES = {"M", "F", "U"}

VALID_RACE_VALUES = {
    "AMERICAN INDIAN OR ALASKA NATIVE",
    "ASIAN",
    "BLACK OR AFRICAN AMERICAN",
    "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
    "WHITE",
    "MULTIPLE",
    "OTHER",
}

VALID_AESEV_VALUES = {"MILD", "MODERATE", "SEVERE"}


def normalize_sex(val: Optional[str]) -> str:
    """Normalizes and validates SEX value to CDISC Controlled Terminology: 'M', 'F', 'U'.

    Args:
        val (str): Raw string representing sex.

    Returns:
        str: Normalized sex code ('M', 'F', 'U').

    Raises:
        ValueError: If the value cannot be normalized to a valid CDISC SEX term.
    """
    if val is None:
        raise ValueError("SEX value cannot be None")

    cleaned = str(val).strip().upper()
    if cleaned in {"M", "MALE", "M_GEN"}:
        return "M"
    if cleaned in {"F", "FEMALE", "F_GEN"}:
        return "F"
    if cleaned in {"U", "UNKNOWN", "UNDIFFERENTIATED", "NOT REPORTED", "NOT_REPORTED"}:
        return "U"

    raise ValueError(f"Value '{val}' is not a valid or normalizable CDISC SEX value.")


def normalize_race(val: Union[str, List[str]]) -> str:
    """Normalizes and validates RACE value to CDISC Controlled Terminology.

    If multiple races are provided (as a list or a delimited string), returns 'MULTIPLE'.

    Args:
        val (Union[str, List[str]]): Raw race value or list of race values.

    Returns:
        str: Normalized race string.

    Raises:
        ValueError: If the value cannot be normalized to a valid CDISC RACE term.
    """
    if val is None:
        raise ValueError("RACE value cannot be None")

    # If list is passed
    if isinstance(val, list):
        if len(val) == 0:
            raise ValueError("RACE list cannot be empty")
        if len(val) > 1:
            return "MULTIPLE"
        val = val[0]

    # Handle string with multiple checked items separated by common delimiters
    # e.g., "WHITE, ASIAN" or "White; Black" or "White and Black"
    raw_str = str(val).strip()
    if not raw_str:
        raise ValueError("RACE string cannot be blank")

    # Split on comma, semicolon, or " and "
    parts = re.split(r',|;| and | AND ', raw_str, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) > 1:
        return "MULTIPLE"

    # Single race term normalization
    cleaned = parts[0].upper()
    # Remove duplicate internal spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Exact matches first
    if cleaned in VALID_RACE_VALUES:
        return cleaned

    # Common aliases and fuzzy matches
    if cleaned in {"WHITE", "CAUCASIAN", "EUROPEAN"}:
        return "WHITE"
    if cleaned in {"BLACK", "AFRICAN", "AFRICAN AMERICAN", "BLACK OR AFRICAN AMERICAN"}:
        return "BLACK OR AFRICAN AMERICAN"
    if cleaned in {"ASIAN", "EAST ASIAN", "SOUTH ASIAN"}:
        return "ASIAN"
    if cleaned in {"AMERICAN INDIAN", "ALASKA NATIVE", "AMERICAN INDIAN OR ALASKA NATIVE"}:
        return "AMERICAN INDIAN OR ALASKA NATIVE"
    if cleaned in {"HAWAIIAN", "PACIFIC ISLANDER", "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER"}:
        return "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER"
    if cleaned in {"MULTIPLE", "MIXED", "MORE THAN ONE RACE"}:
        return "MULTIPLE"
    if cleaned in {"OTHER", "NOT REPORTED", "UNKNOWN", "DECLINED"}:
        return "OTHER"

    raise ValueError(f"Value '{val}' is not a valid or normalizable CDISC RACE value.")


def normalize_severity(val: Optional[str]) -> str:
    """Normalizes and validates AE severity (AESEV) to CDISC Controlled Terminology: 'MILD', 'MODERATE', 'SEVERE'.

    Args:
        val (str): Raw severity string.

    Returns:
        str: Normalized severity string.

    Raises:
        ValueError: If the value cannot be normalized to a valid AESEV term.
    """
    if val is None:
        raise ValueError("AE Severity value cannot be None")

    cleaned = str(val).strip().upper()
    if cleaned in VALID_AESEV_VALUES:
        return cleaned

    # Map numeric severity or common synonyms
    if cleaned in {"1", "MILD", "GRADE 1", "LOW"}:
        return "MILD"
    if cleaned in {"2", "MODERATE", "GRADE 2", "MEDIUM"}:
        return "MODERATE"
    if cleaned in {"3", "4", "5", "SEVERE", "GRADE 3", "GRADE 4", "GRADE 5", "HIGH"}:
        return "SEVERE"

    raise ValueError(f"Value '{val}' is not a valid or normalizable AE Severity value.")
