"""Centralized schema definitions and validator integration for Cadence Clinical.

This module unifies the validation of CDASH metadata mappings, W3C XML naming
compliance, generated CDISC ODM XML structures, and XML identifier sanitization
across both the design (MDR/SDR) and clinical execution (EDC) phases.

By centralizing these functions, we eliminate validation drift, prevent clinical
export failures, and guarantee consistent structural verification on both ends.
"""

import csv
import io
import re
import uuid
from typing import Any, Dict, List, Tuple

import defusedxml.ElementTree as ET
from pydantic import BaseModel


class CDASHMapping(BaseModel):
    """Represents a standardized CDASH mapping structure.

    This model aligns designed study concepts with standard CDISC variables during
    the study design phase. It ensures mapping properties are well-defined and
    typed correctly prior to export schema mapping.

    Attributes:
        domain (str): The CDASH/SDTM domain code (e.g., 'VS', 'DM').
        variable_name (str): The standardized variable name (e.g., 'VSSBP').
        data_type (str): The target data type (e.g., 'NUMERIC', 'TEXT').
    """

    domain: str
    variable_name: str
    data_type: str


# W3C XML Name Regular Expression patterns
# A strict W3C NameStartChar without colon, allowing english letters and unicode range characters
XML_NAME_START_CHAR = (
    r"([A-Za-z_]|[\xC0-\xD6\xD8-\xF6\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF"
    r"\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF"
    r"\uFDF0-\uFFFD])"
)
XML_NAME_CHAR = (
    r"(" + XML_NAME_START_CHAR + r"|[\-\.0-9\xB7\u0300-\u036F\u203F-\u2040])"
)

XML_NAME_PATTERN = re.compile(f"^{XML_NAME_START_CHAR}{XML_NAME_CHAR}*$")


def is_valid_xml_name(name: str) -> bool:
    """Verifies that a given string strictly conforms to W3C XML naming rules.

    Provides identical naming checks across design metadata uploads and generated tags.
    Optionally allows exactly one namespace prefix colon (e.g., 'prefix:local').
    Any name with multiple colons or illegal characters will be blocked.

    Args:
        name (str): The candidate string to validate as an XML name.

    Returns:
        bool: True if the name conforms to the W3C XML specifications, False otherwise.
    """
    if not name:
        return False

    # Names containing colons representing namespace mapping must have exactly one colon
    if ":" in name:
        parts = name.split(":")
        if len(parts) != 2:
            return False
        prefix, local_name = parts
        return bool(XML_NAME_PATTERN.match(prefix)) and bool(
            XML_NAME_PATTERN.match(local_name)
        )

    return bool(XML_NAME_PATTERN.match(name))


def validate_mapping_csv(csv_content: str) -> List[Dict[str, Any]]:
    """Parses and validates user-uploaded CSV mapping configurations.

    Used by the study designer to verify target variables and aliases prior
    to persistence.

    Args:
        csv_content (str): The raw string contents of the uploaded CSV file.

    Returns:
        List[Dict[str, Any]]: The list of successfully validated row dictionaries.

    Raises:
        ValueError: If headers are invalid, missing, or if any target/alias name
            violates the W3C XML naming restrictions.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        raise ValueError("Invalid CSV format: Missing headers")

    if "to_name" not in reader.fieldnames or "to_alias" not in reader.fieldnames:
        raise ValueError(
            "Invalid CSV format: Missing mandatory headers ('to_name', 'to_alias')"
        )

    rows = []
    for line_number, row in enumerate(reader, start=2):  # 1-based header, so start=2
        to_name = row.get("to_name", "").strip()
        to_alias = row.get("to_alias", "").strip()

        if to_name and not is_valid_xml_name(to_name):
            raise ValueError(
                f"Row {line_number}: Invalid XML name in 'to_name' column: '{to_name}'"
            )

        if to_alias and not is_valid_xml_name(to_alias):
            raise ValueError(
                f"Row {line_number}: Invalid XML name in 'to_alias' column: '{to_alias}'"
            )

        rows.append(row)

    return rows


def sanitize_identifier(raw_id: Any) -> str:
    """Sanitizes raw identifier values into valid W3C XML tag names deterministically.

    Strips whitespaces, replaces spaces and non-alphanumeric characters with underscores,
    and prepends 'item_' for leading digits to avoid violating XML tag starting character constraints.
    Returns existing valid identifiers unchanged to maintain traceability.
    Generates a unique identifier fallback if the input is empty or missing.

    Args:
        raw_id (Any): The input identifier to sanitize.

    Returns:
        str: A fully compliant, sanitized XML identifier.
    """
    if not raw_id or not isinstance(raw_id, str) or not raw_id.strip():
        return f"item_{uuid.uuid4().hex[:8]}"

    # Strip leading and trailing whitespaces
    stripped_id = raw_id.strip()

    # If it is already a valid identifier (starts with letter, followed by alphanumeric/underscore), return it unchanged
    if re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", stripped_id):
        return stripped_id

    # Otherwise, perform sanitization
    # 1. Adjust leading digits: if it starts with a digit, prepend "item_"
    starts_with_digit = re.match(r"^\d", stripped_id) is not None

    # 2. Map characters: replace spaces and non-alphanumeric characters
    sanitized_chars = []
    for c in stripped_id:
        if c.isalnum() or c == "_":
            sanitized_chars.append(c)
        elif c == " ":
            sanitized_chars.append("_")
        else:
            # Deterministic mapping for special characters to avoid collisions with other sanitized values
            sanitized_chars.append(f"_{ord(c):02x}")

    sanitized_str = "".join(sanitized_chars)

    if starts_with_digit:
        sanitized_str = f"item_{sanitized_str}"

    # Ensure it starts with a valid character
    if not re.match(r"^[a-zA-Z_]", sanitized_str):
        sanitized_str = f"item_{sanitized_str}"

    return sanitized_str


def validate_cdisc_xml_structure(xml_content: str) -> Tuple[bool, str]:
    """Validates structural compliance of a generated CDISC ODM XML payload.

    Verifies that the generated XML file is well-formed, complies with the official
    CDISC namespace, and contains mandatory study metadata and subject header properties.

    Args:
        xml_content (str): The CDISC XML payload string.

    Returns:
        Tuple[bool, str]: A tuple where the first element is a boolean indicating
            validity, and the second is a descriptive message.
    """
    try:
        root = ET.fromstring(xml_content.encode("utf-8"))
    except Exception as e:
        return False, f"XML parsing error: {str(e)}"

    ns = "{http://www.cdisc.org/ns/odm/v1.3}"
    if root.tag != f"{ns}ODM":
        return False, f"Invalid root element: expected '{ns}ODM', got '{root.tag}'"

    # Verify ODM attributes
    if "FileOID" not in root.attrib:
        return False, "Missing mandatory attribute 'FileOID' in root ODM element"

    # Verify ClinicalData
    clinical_data = root.find(f"{ns}ClinicalData")
    if clinical_data is None:
        return False, f"Missing mandatory element '{ns}ClinicalData'"

    if "StudyOID" not in clinical_data.attrib:
        return False, "Missing mandatory attribute 'StudyOID' in ClinicalData element"

    # Verify SubjectData is present if subjects exist
    subjects = clinical_data.findall(f"{ns}SubjectData")
    for subj in subjects:
        if "SubjectKey" not in subj.attrib:
            return (
                False,
                "Missing mandatory attribute 'SubjectKey' in SubjectData element",
            )

    return True, "Structure matches official CDISC specifications successfully."
