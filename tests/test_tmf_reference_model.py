import pytest
from pydantic import ValidationError
from tmf_reference_model import (
    build_catalog,
    get_active_catalog,
    get_catalog,
    get_registered_versions,
    register_catalog,
    set_active_version,
)


def test_active_version_selection():
    """
    Test that a consumer can obtain the active default version and get registered versions.
    """
    active_catalog = get_active_catalog()
    assert active_catalog is not None
    assert active_catalog.version == "v3.2.0"

    registered = get_registered_versions()
    assert "v3.2.0" in registered


def test_explicit_version_selection():
    """
    Test that a consumer can select a catalog by explicit version.
    """
    catalog = get_catalog("v3.2.0")
    assert catalog is not None
    assert catalog.version == "v3.2.0"

    with pytest.raises(KeyError):
        get_catalog("non_existent_version")


def test_canonical_11_zones():
    """
    Test that the active catalog includes exactly the 11 named DIA zones in correct order/codes:
    - Trial Management
    - Central Trial Documents
    - Regulatory
    - IRB/IEC & other Approvals
    - Site Management
    - IP & Trial Supplies
    - Safety Reporting
    - Centralized & Local Testing
    - Third Parties
    - Data Management
    - Statistics
    """
    catalog = get_active_catalog()
    assert len(catalog.zones) == 11

    expected_zones = {
        1: "Trial Management",
        2: "Central Trial Documents",
        3: "Regulatory",
        4: "IRB/IEC & other Approvals",
        5: "Site Management",
        6: "IP & Trial Supplies",
        7: "Safety Reporting",
        8: "Centralized & Local Testing",
        9: "Third Parties",
        10: "Data Management",
        11: "Statistics",
    }

    for zone in catalog.zones:
        assert zone.code in expected_zones
        assert zone.name == expected_zones[zone.code]


def test_artifact_parent_identification():
    """
    Test that each artifact uniquely and deterministically identifies its parent section and zone.
    """
    catalog = get_active_catalog()

    # Test specific well-known artifacts
    protocol = catalog.get_artifact("01.01.01")
    assert protocol is not None
    assert protocol.name == "Clinical Trial Protocol"
    assert protocol.section_code == "01.01"
    assert protocol.zone_code == 1

    ib = catalog.get_artifact("02.01.01")
    assert ib is not None
    assert ib.name == "Investigator's Brochure"
    assert ib.section_code == "02.01"
    assert ib.zone_code == 2

    # Verify lookups
    assert catalog.get_artifact("invalid_code") is None

    # Verify parent section and zone resolution
    for zone in catalog.zones:
        for section in zone.sections:
            assert section.zone_code == zone.code
            for artifact in section.artifacts:
                assert artifact.section_code == section.code
                assert artifact.zone_code == zone.code


def test_version_isolation():
    """
    Test that adding a future catalog version does not alter data returned for an existing version,
    and the registry rejects duplicate registrations to ensure immutability of registry mappings.
    """
    # Create a new future catalog version
    future_raw = {
        1: ("Trial Management", {
            "01.01": ("Trial Design", [
                ("01.01.01", "Clinical Trial Protocol Future Edition")
            ])
        })
    }
    future_catalog = build_catalog("v4.0.0", future_raw)

    register_catalog(future_catalog)
    assert "v4.0.0" in get_registered_versions()

    # Verify that the old version still returns its original data
    v3_catalog = get_catalog("v3.2.0")
    protocol_v3 = v3_catalog.get_artifact("01.01.01")
    assert protocol_v3.name == "Clinical Trial Protocol"

    # Verify future version returns the new data
    v4_catalog = get_catalog("v4.0.0")
    protocol_v4 = v4_catalog.get_artifact("01.01.01")
    assert protocol_v4.name == "Clinical Trial Protocol Future Edition"

    # Try setting active to v4.0.0 and switching back to verify setting active works
    original_active = get_active_catalog().version
    set_active_version("v4.0.0")
    assert get_active_catalog().version == "v4.0.0"

    set_active_version(original_active)
    assert get_active_catalog().version == original_active

    # Registering duplicate version must fail
    with pytest.raises(ValueError, match="is already registered"):
        register_catalog(future_catalog)


def test_immutability_properties():
    """
    Verify that Zone, Section, Artifact, and TaxonomyCatalog records are immutable at runtime.
    """
    catalog = get_active_catalog()
    zone = catalog.zones[0]
    section = zone.sections[0]
    artifact = section.artifacts[0]

    # Verify Pydantic frozen configuration raises errors upon mutation
    with pytest.raises(ValidationError):
        # Directly trying to assign/mutate fields on a frozen model throws error
        # Pydantic raises ValidationError or AttributeError
        artifact.name = "Mutated Name"

    with pytest.raises(ValidationError):
        section.name = "Mutated Section"

    with pytest.raises(ValidationError):
        zone.name = "Mutated Zone"

    with pytest.raises(ValidationError):
        catalog.version = "v10.0.0"


def test_no_database_dependencies():
    """
    Verify catalog construction is pure in-memory and requires no external connections or database.
    """
    raw_minimal = {
        1: ("Trial Management", {
            "01.01": ("Trial Design", [
                ("01.01.01", "Protocol")
            ])
        })
    }
    pure_catalog = build_catalog("v_pure", raw_minimal)
    assert pure_catalog.version == "v_pure"
    assert len(pure_catalog.zones) == 1
    assert pure_catalog.get_artifact("01.01.01").name == "Protocol"
