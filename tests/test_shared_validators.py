"""Unit tests for the centralized shared validators module."""

import pytest
from pydantic import ValidationError
from shared_validators import (
    CDASHMapping,
    is_valid_xml_name,
    sanitize_identifier,
    validate_cdisc_xml_structure,
    validate_mapping_csv,
)


def test_cdash_mapping_model():
    """Verify that the CDASHMapping pydantic model validates fields correctly."""
    mapping = CDASHMapping(domain="VS", variable_name="VSSBP", data_type="NUMERIC")
    assert mapping.domain == "VS"
    assert mapping.variable_name == "VSSBP"
    assert mapping.data_type == "NUMERIC"

    with pytest.raises(ValidationError):
        # Missing data_type should fail validation
        CDASHMapping(domain="VS", variable_name="VSSBP")  # type: ignore


def test_is_valid_xml_name():
    """Verify is_valid_xml_name with valid and invalid names, including colon rules."""
    assert is_valid_xml_name("validName") is True
    assert is_valid_xml_name("_valid_name_123") is True
    assert is_valid_xml_name("prefix:localName") is True

    assert is_valid_xml_name("") is False
    assert is_valid_xml_name("1invalid") is False
    assert is_valid_xml_name("spaced name") is False
    assert is_valid_xml_name("prefix:local:name") is False  # Multiple colons


def test_validate_mapping_csv():
    """Verify validate_mapping_csv handles valid and invalid CSV content correctly."""
    valid_csv = "to_name,to_alias\nvalid_one,alias_one\nprefix:local,namespace:alias"
    rows = validate_mapping_csv(valid_csv)
    assert len(rows) == 2
    assert rows[0]["to_name"] == "valid_one"

    # Missing headers
    with pytest.raises(ValueError, match="Missing mandatory headers"):
        validate_mapping_csv("invalid,header\nval,val")

    # Empty CSV content
    with pytest.raises(ValueError, match="Missing headers"):
        validate_mapping_csv("")

    # Invalid XML name in to_name
    invalid_to_name = "to_name,to_alias\n1invalid,aliasName"
    with pytest.raises(ValueError, match="Invalid XML name in 'to_name'"):
        validate_mapping_csv(invalid_to_name)

    # Invalid XML name in to_alias
    invalid_to_alias = "to_name,to_alias\nvalidName,spaced aliasName"
    with pytest.raises(ValueError, match="Invalid XML name in 'to_alias'"):
        validate_mapping_csv(invalid_to_alias)


def test_sanitize_identifier():
    """Verify sanitize_identifier sanitizes invalid strings and returns valid ones."""
    assert sanitize_identifier("sys_bp") == "sys_bp"
    assert sanitize_identifier("heart rate") == "heart_rate"
    assert sanitize_identifier("1_systolic") == "item_1_systolic"
    assert sanitize_identifier("item-A") == "item_2dA"
    assert sanitize_identifier("item_A") == "item_A"

    # Leading digit and special characters
    assert sanitize_identifier("2b_c") == "item_2b_c"

    # Edge cases (empty, None, blank spaces)
    assert sanitize_identifier("") != ""
    assert sanitize_identifier(None) != ""
    assert sanitize_identifier("   ") != ""


def test_validate_cdisc_xml_structure():
    """Verify validate_cdisc_xml_structure handles valid and structurally invalid CDISC XMLs."""
    # Well-formed valid CDISC ODM XML
    valid_xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="file_123">'
        '  <ClinicalData StudyOID="study_123">'
        '    <SubjectData SubjectKey="subj_01"/>'
        "  </ClinicalData>"
        "</ODM>"
    )
    is_valid, msg = validate_cdisc_xml_structure(valid_xml)
    assert is_valid is True
    assert "Structure matches" in msg

    # Bad XML syntax
    invalid_syntax = "<ODM><ClinicalData></ODM>"
    is_valid, msg = validate_cdisc_xml_structure(invalid_syntax)
    assert is_valid is False
    assert "XML parsing error" in msg

    # Incorrect root tag
    wrong_root = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<NotODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="file_123"/>'
    )
    is_valid, msg = validate_cdisc_xml_structure(wrong_root)
    assert is_valid is False
    assert "Invalid root element" in msg

    # Missing FileOID
    missing_file_oid = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3">'
        '  <ClinicalData StudyOID="study_123"/>'
        "</ODM>"
    )
    is_valid, msg = validate_cdisc_xml_structure(missing_file_oid)
    assert is_valid is False
    assert "Missing mandatory attribute 'FileOID'" in msg

    # Missing ClinicalData
    missing_clinical = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="file_123"/>'
    )
    is_valid, msg = validate_cdisc_xml_structure(missing_clinical)
    assert is_valid is False
    assert "Missing mandatory element" in msg

    # Missing StudyOID
    missing_study_oid = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="file_123">'
        "  <ClinicalData/>"
        "</ODM>"
    )
    is_valid, msg = validate_cdisc_xml_structure(missing_study_oid)
    assert is_valid is False
    assert "Missing mandatory attribute 'StudyOID'" in msg

    # Missing SubjectKey
    missing_subj_key = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="file_123">'
        '  <ClinicalData StudyOID="study_123">'
        "    <SubjectData/>"
        "  </ClinicalData>"
        "</ODM>"
    )
    is_valid, msg = validate_cdisc_xml_structure(missing_subj_key)
    assert is_valid is False
    assert "Missing mandatory attribute 'SubjectKey'" in msg
