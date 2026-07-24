# ADR-050: Schedule of Activities (SoA) Domain Contracts and Graph Schema Extensions

* **Status:** Proposed
* **Date:** 2026-07-30
* **Authors:** @jules
* **Deciders:** @fderuiter, @jules

---

## 1. Context & Problem Statement

In the Cadence Clinical platform, upstream Study Design (MDR/SDR) is managed inside the `apps/designer` service using Neo4j as its core graph store. While initial designs stored basic visit-level schedules using simplified properties (such as `visit_window_days`), professional clinical protocols require a highly robust, arm-aware, and conditional Schedule of Activities (SoA) model.

Specifically, we need to represent:
1. **Arm Applicability:** A procedure or activity might only occur in certain study arms, or visits may belong to different arms.
2. **Conditional Timing:** Certain activities/procedures are only performed at specific visits under specific conditional rules (e.g., "if clinically indicated" or "if systolic blood pressure > 140 mmHg").
3. **Advanced Timing Windows:** We need to capture precise target days, tolerance ranges (forward/backward window offsets), and time units, which goes far beyond legacy flat properties like `visit_window_days`.
4. **Graph-Model Extensions:** We need to explicitly document how these arm-aware schedules, conditional cells, and advanced Timing Windows are represented as graph relationships in Neo4j.
5. **USDM Alignment and Graph Diffability:** All models must align with CDISC USDM (Unified Study Definitions Model) guidelines, maintaining high performant graph-diffing capabilities.

## 2. Decision Drivers & Constraints

* **Driver 1 (Compliance & Traceability):** ISO 14155:2020 and 21 CFR Part 11 require full GxP-compliant audit metadata tracking (who, when, what, why) for all metadata schema mutations, including the Schedule of Activities.
* **Driver 2 (Complex Logic & Validation):** Cells must support conditional flags. Pydantic contracts must guarantee that if a procedure cell is marked as "conditional," a valid justification or reason string is supplied.
* **Driver 3 (Performant Projections):** The Designer API and Web UI require a unified matrix projection (arm × epoch × visit × procedure) response payload representing the entire study schedule.
* **Driver 4 (USDM Alignment & Diffability):** The graph model must scale gracefully, align with USDM structures, and support the platform's API-first, in-memory tree-diffing algorithms.

## 3. Options Considered

### Option 1: Relational Schema or Embedded Document Models in Neo4j

Embed timing and applicability arrays as properties inside traditional Visit or Procedure nodes.
* **Pros:**
  * ✅ Avoids adding new node and relationship types in Neo4j.
* **Cons:**
  * ❌ Fails to scale for multiple arms with conflicting schedules or conditional timings.
  * ❌ Makes graph-diffing extremely complex, as changes are buried within embedded properties of other nodes.
  * ❌ Violates standard graph database best practices.

### Option 2: Extended Graph Schema with Dedicated TimingWindow and Cell Nodes (Selected)

We extend the Neo4j graph model to introduce:
1. **`TimingWindow` Node:** Encapsulates target day, backward tolerance, forward tolerance, and unit of time.
2. **`SoACell` / `ScheduledInstance` Node or Directed Graph Relationships:** Connect `Visit` and `Procedure` with specific `TimingWindow` overrides, and represent arm-specific applicability via relationship qualifiers or dedicated nodes.
* **Pros:**
  * ✅ **Visit Window Extension:** Moves beyond flat `visit_window_days` to highly descriptive timing windows.
  * ✅ **USDM Alignment:** Map structure perfectly to CDISC USDM's `ScheduleOfActivities`, `ScheduledActivityInstance`, and `DefinedActivity`.
  * ✅ **Graph Diffability:** Granular nodes and relationship types (`HAS_WINDOW`, `APPLICABLE_TO_ARM`, `UNDER_CONDITION`) participate directly in our standard Cypher-based tree-diffing algorithms.
  * ✅ **Clear Separation of Concerns:** Relational and conditional constraints are clear first-class citizens in the graph.
* **Cons:**
  * ❌ Slightly increases graph traversal depth, but this is highly optimized in Neo4j.

---

## 4. Decision Outcome

* **Chosen Option:** Option 2
* **Justification:** An extended, explicit graph schema best represents the complex, multi-dimensional nature of clinical protocols while preserving CDISC USDM alignment. This ensures optimal performant traversals and native graph diffing.

### 4.1 Graph Relationships & TimingWindow Model
The Neo4j graph structure for the Schedule of Activities is defined as follows:

```
  (StudyVersion) -[:HAS_ARM]-> (StudyArm)
  (StudyVersion) -[:HAS_EPOCH]-> (Epoch) -[:HAS_VISIT]-> (Visit)
  (Visit) -[:HAS_DEFAULT_WINDOW]-> (TimingWindow)

  (Visit) -[:SCHEDULES_ACTIVITY]-> (SoACell)
  (SoACell) -[:MEASURES_PROCEDURE]-> (ProcedureActivity)
  (SoACell) -[:APPLIES_TO_ARM]-> (StudyArm)
  (SoACell) -[:OVERRIDE_WINDOW]-> (TimingWindow)
```

Where:
* **`TimingWindow` Properties:** `id` (UUID), `name`, `target_day` (Int), `window_back` (Int), `window_forward` (Int), `time_unit` (String/Enum).
* **`SoACell` Properties:** `id` (UUID), `is_applicable` (Boolean), `is_conditional` (Boolean), `conditional_reason` (String/Nullable).
* **`StudyArm` Properties:** `id` (UUID), `name`, `arm_type` (Enum).
* **`Epoch` Properties:** `id` (UUID), `name`, `sequence_order` (Int).
* **`Visit` Properties:** `id` (UUID), `name`, `visit_window_days` (Int/Legacy).
* **`ProcedureActivity` Properties:** `id` (UUID), `name`, `code` (String/Nullable).

### 4.2 GxP Audit Metadata & Change Reason Alignment
Every entity node holds standard Designer metadata properties matching regulatory compliance guidelines (21 CFR Part 11 / ISO 14155:2020):
* `created_at`: DateTime of creation.
* `created_by`: Identity UUID of the creator.
* `updated_at`: DateTime of last edit.
* `updated_by`: Identity UUID of the updater.
* `reason_for_change`: Mandatory change log string justifying modifications.
* `version`: Schema/Record semantic version.

### 4.3 Validation Rules
* **Conditional Logic:** If `is_conditional` is `True`, the `conditional_reason` MUST be populated and non-empty. This is enforced via custom Pydantic v2 validators.

---

## 5. Consequences & Trade-offs

* **Positive Impact:** Enables perfect representation of complex protocols (e.g., adaptive trials, multi-arm trials, pediatric cohorts with conditional procedures). Highly readable and performant matrix projection endpoint for UI visualization.
* **Negative Impact:** Requires updating downstream EDC translation templates to map from these advanced `TimingWindow` nodes instead of legacy `visit_window_days`.

## 6. Implementation & Verification

* **Affected Repositories / Services:** `apps/designer/`
* **Verification Plan:**
  * Introduce Pydantic v2 models in `apps/designer/soa_models.py`.
  * Expose validation and projection endpoints in `apps/designer/main.py`.
  * Validate structural checks via unit and integration tests under `tests/test_soa_contracts.py`.
