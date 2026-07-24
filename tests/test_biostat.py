import pytest
from pydantic import ValidationError

from apps.execution.biostat.models import (
    VariableMetadata,
    SUPPRecord,
    DatasetJSONItemGroup,
    ClinicalData,
    DatasetJSON,
)
from apps.execution.biostat.mappings import (
    SDTM_MAPPINGS,
    get_mappings_for_domain,
    get_mappings_by_domain,
)
from apps.execution.biostat.terminology import (
    normalize_sex,
    normalize_race,
    normalize_severity,
)


# --- Tests for Pydantic v2 Models ---

def test_variable_metadata_validation():
    """Verify that VariableMetadata correctly validates types and fields."""
    # Valid model
    vm = VariableMetadata(
        name="USUBJID",
        label="Unique Subject Identifier",
        type="string",
        length=200,
    )
    assert vm.name == "USUBJID"
    assert vm.type == "string"

    # Lowercases the type automatically
    vm2 = VariableMetadata(
        name="AGE",
        label="Age",
        type="INTEGER",
    )
    assert vm2.type == "integer"

    # Invalid type should raise ValidationError
    with pytest.raises(ValidationError):
        VariableMetadata(
            name="INVALID",
            label="Invalid",
            type="complex_type",
        )


def test_supp_record_row_conversion():
    """Verify that SUPPRecord initializes correctly and serializes to ordered rows."""
    supp = SUPPRecord(
        STUDYID="STUDY-123",
        RDOMAIN="DM",
        USUBJID="STUDY-123-001",
        IDVAR="",
        IDVARVAL="",
        QNAM="MULTIRAC",
        QLABEL="Multiple Race Flag",
        QVAL="Y",
    )
    assert supp.QEVAL == ""

    # Convert to row based on ordered list of variable names
    vars_list = ["STUDYID", "RDOMAIN", "USUBJID", "QNAM", "QVAL"]
    row = supp.to_row(vars_list)
    assert row == ["STUDY-123", "DM", "STUDY-123-001", "MULTIRAC", "Y"]


def test_dataset_json_integration_structure():
    """Verify that the full DatasetJSON container model constructs a compliant schema."""
    # Create variable metadata
    variables = [
        VariableMetadata(name="STUDYID", label="Study OID", type="string"),
        VariableMetadata(name="USUBJID", label="Subject ID", type="string"),
        VariableMetadata(name="AGE", label="Age", type="integer"),
    ]

    item_group = DatasetJSONItemGroup(
        records=2,
        name="DM",
        label="Demographics",
        items=variables,
        itemData=[
            ["STUDY-01", "STUDY-01-001", 35],
            ["STUDY-01", "STUDY-01-002", 42],
        ]
    )

    clinical_data = ClinicalData(
        studyOID="STUDY.01",
        metaDataVersionOID="MDV.01",
        itemGroupData={"IG.DM": item_group}
    )

    dj = DatasetJSON(
        creationDateTime="2026-07-29T12:00:00Z",
        datasetJSONVersion="1.0.0",
        clinicalData=clinical_data,
    )

    assert dj.datasetJSONVersion == "1.0.0"
    assert dj.clinicalData is not None
    assert "IG.DM" in dj.clinicalData.itemGroupData
    assert dj.clinicalData.itemGroupData["IG.DM"].records == 2

    # Check validation on incorrect timestamp format
    with pytest.raises(ValidationError):
        DatasetJSON(
            creationDateTime="not-a-timestamp",
            clinicalData=clinical_data,
        )


# --- Tests for Declarative Mapping Table ---

def test_declarative_mappings_coverage():
    """Verify that the declarative mapping covers DM, AE, VS, LB, and MH domains with expected variables."""
    # Group mappings
    grouped = get_mappings_by_domain()
    assert "DM" in grouped
    assert "AE" in grouped
    assert "VS" in grouped
    assert "LB" in grouped
    assert "MH" in grouped

    # Check some critical variables
    dm_vars = {m.variable_name for m in grouped["DM"]}
    ae_vars = {m.variable_name for m in grouped["AE"]}
    vs_vars = {m.variable_name for m in grouped["VS"]}
    lb_vars = {m.variable_name for m in grouped["LB"]}
    mh_vars = {m.variable_name for m in grouped["MH"]}

    # Demographics
    assert "STUDYID" in dm_vars
    assert "USUBJID" in dm_vars
    assert "SEX" in dm_vars
    assert "RACE" in dm_vars
    assert "ARM" in dm_vars

    # Adverse Events
    assert "AESEQ" in ae_vars
    assert "AETERM" in ae_vars
    assert "AESEV" in ae_vars
    assert "AEREL" in ae_vars

    # Vital Signs
    assert "VSSEQ" in vs_vars
    assert "VSTESTCD" in vs_vars
    assert "VSSTRESN" in vs_vars

    # Labs
    assert "LBSEQ" in lb_vars
    assert "LBTESTCD" in lb_vars
    assert "LBSTRESN" in lb_vars

    # Medical History
    assert "MHSEQ" in mh_vars
    assert "MHTERM" in mh_vars
    assert "MHDECOD" in mh_vars


def test_mapping_helpers():
    """Verify helper functions retrieve mapped records accurately."""
    ae_mappings = get_mappings_for_domain("AE")
    assert len(ae_mappings) > 0
    for mapping in ae_mappings:
        assert mapping.domain == "AE"
        assert mapping.transformation_kind in {"DIRECT", "CONCATENATION", "COMPUTED", "FIXED", "CONTROLLED_TERMINOLOGY"}


# --- Tests for Controlled Terminology Helpers ---

def test_normalize_sex():
    """Verify SEX field normalization and validation."""
    assert normalize_sex("male") == "M"
    assert normalize_sex("M") == "M"
    assert normalize_sex("Female") == "F"
    assert normalize_sex("f_gen") == "F"
    assert normalize_sex("UNKNOWN") == "U"
    assert normalize_sex("not reported") == "U"

    with pytest.raises(ValueError):
        normalize_sex("alien")

    with pytest.raises(ValueError):
        normalize_sex(None)


def test_normalize_race():
    """Verify RACE field normalization, handling of multiple entries, and validation."""
    # Single race terms
    assert normalize_race("white") == "WHITE"
    assert normalize_race("caucasian") == "WHITE"
    assert normalize_race("black") == "BLACK OR AFRICAN AMERICAN"
    assert normalize_race("African American") == "BLACK OR AFRICAN AMERICAN"
    assert normalize_race("asian") == "ASIAN"
    assert normalize_race("AMERICAN INDIAN OR ALASKA NATIVE") == "AMERICAN INDIAN OR ALASKA NATIVE"
    assert normalize_race("pacific islander") == "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER"
    assert normalize_race("declined") == "OTHER"

    # Multi-race options (lists or strings with separators)
    assert normalize_race(["White", "Asian"]) == "MULTIPLE"
    assert normalize_race("White, Black") == "MULTIPLE"
    assert normalize_race("White; Asian") == "MULTIPLE"
    assert normalize_race("White and Asian") == "MULTIPLE"

    with pytest.raises(ValueError):
        normalize_race("invalid-race-name")

    with pytest.raises(ValueError):
        normalize_race([])

    with pytest.raises(ValueError):
        normalize_race("")


def test_normalize_severity():
    """Verify AESEV (Severity) field normalization and validation."""
    assert normalize_severity("mild") == "MILD"
    assert normalize_severity("1") == "MILD"
    assert normalize_severity("grade 1") == "MILD"

    assert normalize_severity("Moderate") == "MODERATE"
    assert normalize_severity("2") == "MODERATE"

    assert normalize_severity("severe") == "SEVERE"
    assert normalize_severity("GRADE 3") == "SEVERE"
    assert normalize_severity("HIGH") == "SEVERE"

    with pytest.raises(ValueError):
        normalize_severity("critical")

    with pytest.raises(ValueError):
        normalize_severity(None)
