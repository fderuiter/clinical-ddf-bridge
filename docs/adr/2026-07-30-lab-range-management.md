# ADR-050: Lab Range Management

* **Status:** Proposed
* **Date:** 2026-07-30
* **Authors:** @jules
* **Deciders:** @fderuiter, @jules

---

## 1. Context & Problem Statement

Clinical trials require the monitoring and validation of laboratory results from both central and local laboratories. In order to ensure data quality, patient safety, and regulatory compliance (FDA 21 CFR Part 11 / EU Annex 11), the platform needs a robust Lab Range Management system. Specifically, we require:
- Central and local laboratory normal range tables.
- Age/sex-adjusted normal reference ranges.
- Automated out-of-range flag triggers that automatically mark clinical observations as out of range and raise clinical queries.

## 2. Decision Drivers & Constraints

* **Driver 1 (Compliance):** GxP compliance (FDA 21 CFR Part 11) requires complete traceability of all modifications. Clinical observations and any generated queries must adhere to the immutable write-once read-many audit trail pattern.
* **Driver 2 (Flexibility):** Lab ranges can be configured globally (central lab defaults) or specifically per local laboratory site. Furthermore, normal range boundaries often depend on demographic factors such as age and sex.
* **Driver 3 (Automated Verification):** Incoming laboratory observations must be validated in real-time, matching against the best-fit reference range, converting units dynamically if needed, and automatically triggering flags and queries.

## 3. Options Considered

### Option 1: Live Relational Database-Backed Ranges and Inline Validation (Selected)

Model laboratories (`laboratories` table) and normal reference ranges (`lab_reference_ranges` table) as fully audited database relations. During clinical observation ingestion, perform inline lookups against the subject's demographics (age, sex) and the laboratory ID to apply the matching range, and trigger an automated `ClinicalQuery` if the value is out of range.
* **Pros:**
  * ✅ Highly dynamic; clinical study designers can define new central and local labs and adjust age/sex-adjusted normal ranges on-the-fly without rebuilding the application.
  * ✅ Fits perfectly into the GxP audited database infrastructure (`AuditedModel` automatically captures insertion and changes).
  * ✅ Allows automatic unit standard conversion before comparing values against limits.
* **Cons:**
  * ❌ Relies on database queries during observation ingestion, which adds minimal latency.

### Option 2: Hardcoded Range Rules in Layout Translation Engine

Define lab normal ranges as declarative spreadsheet/edit-checks in the study designer layout engine.
* **Pros:**
  * ✅ Moves validation to the client side or layout level.
* **Cons:**
  * ❌ Cannot support multi-laboratory variations (central vs. multiple local sites with different reference ranges).
  * ❌ Cannot adjust dynamically as laboratory reference bounds evolve during a longitudinal study.

---

## 4. Decision Outcome

* **Chosen Option:** Option 1
* **Justification:** Option 1 provides the required flexibility for central and local lab range configurations, handles demographics-adjusted matching cleanly, and leverages the database audit infrastructure for full traceability.

### Schema Design

1. **`Laboratory` model**:
   - `id`: unique identifier (UUID)
   - `name`: descriptive name of the lab (e.g. "Quest Diagnostics Central Lab")
   - `code`: unique identifier code (e.g. "QUEST_CENTRAL")
   - `lab_type`: CENTRAL or LOCAL
   - `location`: location address/details

2. **`LabReferenceRange` model**:
   - `id`: unique identifier (UUID)
   - `laboratory_id`: nullable foreign key to `Laboratory` (if null, acts as a global fallback/central default)
   - `test_code`: e.g. "ALT", "AST", "GLUC"
   - `test_name`: full description
   - `sex`: "M", "F", or "ALL"
   - `age_min`: nullable float (minimum age in years)
   - `age_max`: nullable float (maximum age in years)
   - `low_value`: float (lower normal bound)
   - `high_value`: float (upper normal bound)
   - `unit`: string (associated unit)

3. **`ClinicalObservation` model update**:
   - `laboratory_id`: nullable string referencing `Laboratory`
   - `is_out_of_range`: boolean indicating if the value was flagged as out-of-range

### Lookup & Verification Workflow

- Upon creating a `ClinicalObservation` with domain "LB" (or any matching test code) and optional `laboratory_id`:
  1. Retrieve subject demographics (`encrypted_demographics` is decrypted dynamically to obtain `birthdate` or `age` and `gender`/`sex`).
  2. Query the `LabReferenceRange` table for matching `test_code` and `laboratory_id`. If `laboratory_id` is supplied but has no specific ranges, fall back to global/central defaults (`laboratory_id` is null).
  3. Filter matching ranges by subject `sex` (matching "M", "F", or "ALL") and `age` (where `age_min <= age <= age_max` or they are null).
  4. Perform dynamic unit conversion if the observation's unit is different from the matched range's unit (using `convert_unit` from `apps/execution/ucum.py`).
  5. Check if the value is `< low_value` or `> high_value`. If so, set `is_out_of_range = True`.
  6. Automatically generate a system-raised `ClinicalQuery` with status `OPEN`, explanation describing the out-of-range details, origin as `automated`, and rule ID `LAB_RANGE_OUT_OF_BOUNDS`.

---

## 5. Consequences & Trade-offs

* **Positive Impact:** Provides clear traceability, clinical alerts on out-of-range labs, automated query workflows to reduce monitoring lag, and support for multi-lab studies.
* **Negative Impact:** Demographics decryption adds slight compute overhead, but this is negligible given the safety and data-integrity benefits.

## 6. Implementation & Verification

* **Affected Repositories / Services:** `apps/execution/database/models.py`, `apps/execution/main.py`, `apps/execution/database/migrate.py`
* **Verification Plan:** Unit and integration tests in `tests/test_lab_range_management.py` will verify correct matching of laboratory scopes, demographic lookup adjustments, unit standardizations, and automated query raising.
