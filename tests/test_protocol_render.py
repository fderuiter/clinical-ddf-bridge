import uuid
from datetime import datetime

import pytest
from protocol_render import (
    ExportMetadata,
    NarrativeItemView,
    NarrativeSectionView,
    RenderedProtocolDocument,
    SoACellView,
    SoAHeaderEncounter,
    SoAHeaderEpoch,
    SoAMatrixView,
    SoARowView,
    SynopsisView,
)
from pydantic import ValidationError
from usdm_model import Study


def test_export_metadata_valid_initial():
    """
    Test that a valid ExportMetadata with version_index = 1 parses successfully
    with or without change_reason.
    """
    meta = ExportMetadata(creator="user123")
    assert meta.creator == "user123"
    assert meta.version_index == 1
    assert meta.change_reason is None
    assert isinstance(meta.timestamp, datetime)

    meta_with_reason = ExportMetadata(
        creator="user123",
        change_reason="Initial export",
        version_index=1,
    )
    assert meta_with_reason.change_reason == "Initial export"


def test_export_metadata_invalid_version():
    """
    Test that version_index < 1 raises a ValidationError.
    """
    with pytest.raises(ValidationError) as exc:
        ExportMetadata(creator="user123", version_index=0)
    assert "version_index must be greater than or equal to 1" in str(exc.value)


def test_export_metadata_missing_change_reason_on_version_bump():
    """
    Test that for version_index > 1, a non-empty change_reason is required.
    """
    # Missing completely
    with pytest.raises(ValidationError) as exc:
        ExportMetadata(creator="user123", version_index=2)
    assert "change_reason is required and must be non-empty" in str(exc.value)

    # Empty string
    with pytest.raises(ValidationError) as exc:
        ExportMetadata(creator="user123", version_index=2, change_reason="  ")
    assert "change_reason is required and must be non-empty" in str(exc.value)


def test_export_metadata_valid_version_bump():
    """
    Test that a valid ExportMetadata with version_index > 1 and non-empty change_reason
    parses successfully.
    """
    meta = ExportMetadata(
        creator="user123",
        version_index=2,
        change_reason="Updated section 3.2",
    )
    assert meta.version_index == 2
    assert meta.change_reason == "Updated section 3.2"


def test_narrative_item_and_section_views():
    """
    Test creation and ordering of NarrativeItemView and NarrativeSectionView.
    """
    item1 = NarrativeItemView(
        id="item-1",
        name="intro_p1",
        text="This is the first paragraph of the introduction.",
        order=1,
    )
    item2 = NarrativeItemView(
        id="item-2",
        name="intro_p2",
        text="This is the second paragraph.",
        order=2,
    )

    subsection = NarrativeSectionView(
        section_id="sec-1.1",
        section_number="1.1",
        title="Background Information",
        items=[item1, item2],
        order=1,
    )

    parent_section = NarrativeSectionView(
        section_id="sec-1",
        section_number="1",
        title="Introduction",
        items=[],
        subsections=[subsection],
        order=1,
    )

    assert parent_section.title == "Introduction"
    assert len(parent_section.subsections) == 1
    assert parent_section.subsections[0].section_number == "1.1"
    assert len(parent_section.subsections[0].items) == 2
    assert parent_section.subsections[0].items[0].text == "This is the first paragraph of the introduction."


def test_synopsis_view_parsing():
    """
    Test that a SynopsisView parses key clinical summary fields.
    """
    synopsis = SynopsisView(
        study_id="study-abc",
        protocol_title="A Phase II Trial of Compound X in Patients with Disease Y",
        protocol_number="PROT-X-202",
        sponsor_name="Pharma Corp",
        phase="Phase II",
        objectives=["To evaluate the efficacy of Compound X.", "To assess safety and tolerability."],
        study_design_type="Randomized, Double-Blind, Placebo-Controlled",
        population="Adults with diagnosed Disease Y.",
        sample_size=150,
        duration="12 weeks",
        interventions=["Compound X 50mg daily", "Placebo daily"],
    )

    assert synopsis.study_id == "study-abc"
    assert synopsis.phase == "Phase II"
    assert len(synopsis.objectives) == 2
    assert synopsis.sample_size == 150
    assert synopsis.interventions[0] == "Compound X 50mg daily"


def test_soa_matrix_view():
    """
    Test Epochs, Encounters, Rows, Cells, and complete SoAMatrixView construction.
    """
    epoch_tx = SoAHeaderEpoch(epoch_id="ep-tx", epoch_name="Treatment", sequence=1)
    epoch_fu = SoAHeaderEpoch(epoch_id="ep-fu", epoch_name="Follow-up", sequence=2)

    visit1 = SoAHeaderEncounter(
        encounter_id="v1", encounter_name="Week 1", epoch_id="ep-tx", sequence=1
    )
    visit2 = SoAHeaderEncounter(
        encounter_id="v2", encounter_name="Week 2", epoch_id="ep-tx", sequence=2
    )
    visit_fu = SoAHeaderEncounter(
        encounter_id="v3", encounter_name="End of Study", epoch_id="ep-fu", sequence=3
    )

    cell1 = SoACellView(
        activity_id="act-vitals", encounter_id="v1", epoch_id="ep-tx", is_applicable=True
    )
    cell2 = SoACellView(
        activity_id="act-vitals", encounter_id="v2", epoch_id="ep-tx", is_applicable=True
    )
    cell3 = SoACellView(
        activity_id="act-vitals",
        encounter_id="v3",
        epoch_id="ep-fu",
        is_applicable=False,
        details="Not required unless clinically indicated.",
    )

    row = SoARowView(
        activity_id="act-vitals",
        activity_name="Vital Signs",
        cells=[cell1, cell2, cell3],
    )

    matrix = SoAMatrixView(
        epochs=[epoch_tx, epoch_fu],
        encounters=[visit1, visit2, visit_fu],
        rows=[row],
    )

    assert len(matrix.epochs) == 2
    assert len(matrix.encounters) == 3
    assert len(matrix.rows) == 1
    assert matrix.rows[0].activity_name == "Vital Signs"
    assert matrix.rows[0].cells[2].is_applicable is False
    assert matrix.rows[0].cells[2].details == "Not required unless clinically indicated."


def test_rendered_protocol_document_with_usdm_study():
    """
    Test the integrated RenderedProtocolDocument model wrapping metadata,
    synopsis, narrative, and SoA, including the official usdm_model.Study type.
    """
    study_id_uuid = str(uuid.uuid4())
    # Instantiate official USDM Study model
    usdm_study = Study(
        id=study_id_uuid,
        name="Study 2026-X",
        instanceType="Study",
    )

    meta = ExportMetadata(creator="auditor1", change_reason="Routine FDA submission", version_index=3)
    synopsis = SynopsisView(
        study_id="study-abc",
        protocol_title="Integrated Study Protocol",
        phase="Phase III",
    )
    matrix = SoAMatrixView()

    doc = RenderedProtocolDocument(
        metadata=meta,
        synopsis=synopsis,
        narrative_sections=[],
        soa_matrix=matrix,
        source_study=usdm_study,
    )

    assert doc.metadata.creator == "auditor1"
    assert doc.metadata.version_index == 3
    assert doc.synopsis.protocol_title == "Integrated Study Protocol"
    assert doc.source_study is not None
    assert str(doc.source_study.id) == study_id_uuid
    assert doc.source_study.name == "Study 2026-X"
