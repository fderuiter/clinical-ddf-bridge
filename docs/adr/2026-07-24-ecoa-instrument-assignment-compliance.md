# ADR-055: eCOA Instrument Assignment and GxP Compliance

* **Status:** Accepted
* **Date:** 2026-07-24
* **Authors:** @jules
* **Deciders:** @fderuiter, @jules

---

## 1. Context & Problem Statement

To support clinical trial electronic Clinical Outcome Assessments (eCOAs) like questionnaires and patient diaries, the Cadence Clinical platform requires a flexible, highly auditable data model. This introduces the schema, APIs, and security configurations to support creating assessment templates (`Instrument`) and scheduling them for trial participants (`SubjectAssignment`). Furthermore, to preserve proper database-level decoupling between the clinical execution and interop services, the global execution database before-flush listener must exclude these interop-specific tables.

## 2. Decision Drivers & Constraints

* **Driver 1 (Flexibility & Performance):** Preventing over-engineered relational structures for highly dynamic questionnaires by leveraging structured JSON fields for items, response types, and scoring metadata.
* **Driver 2 (Compliance & 21 CFR Part 11):** Ensuring regulatory tracking across both models with standard audit fields (`created_at`, `created_by`, `reason_for_change`, `version_index`).
* **Driver 3 (Decoupling and Separation of Concerns):** Ensuring that the global execution before-flush database listener does not intercept interop-specific tables, preventing database errors.

## 3. Options Considered

### Option 1: Global audit listeners for all schemas with shared database transactions
* **Overview:** Rely on a single global audit mechanism for all platform database schemas.
* **Pros:**
  * ✅ Single centralized auditing logic for every table.
* **Cons:**
  * ❌ Violates system boundary separation of concerns by coupling execution and interop models.
  * ❌ Causes database-level errors during interop-specific flushes due to execution schema requirements.

### Option 2: Table-level exclusions in the execution global listener combined with localized audit fields (Selected)
* **Overview:** Define localized audit fields for `Instrument` and `SubjectAssignment` models, and explicitly exclude these tables (`"instruments"` and `"subject_assignments"`) from the global `before_flush` execution listener.
* **Pros:**
  * ✅ Guarantees 100% database-level decoupling between execution and interop models.
  * ✅ Meets all GxP and 21 CFR Part 11 audit guidelines independently.
  * ✅ High modularity and cleaner separation of domain boundaries.
* **Cons:**
  * ❌ Requires manual specification of excluded tables in the execution global listener.

## 4. Decision Outcome

* **Chosen Option:** Option 2
* **Justification:** Option 2 preserves the modular boundary rules of the Cadence Clinical platform while ensuring 100% compliant audits for clinical outcomes.

## 5. Consequences & Trade-offs

* **Positive Impact:** Decoupled execution and interop data writes. Proper 21 CFR Part 11 compliance tracking for questionnaires and subject scheduling.
* **Negative Impact / Technical Debt:** Future interop-related tables may also need to be registered/excluded in global execution listeners if they utilize the same session context.
* **Mitigation Strategy:** Periodically audit model associations and keep schemas strictly separated via isolated transaction listeners.

## 6. Implementation & Verification

* **Affected Repositories / Services:** `apps/interop/models.py`, `apps/interop/main.py`, `apps/execution/database/audit.py`
* **Verification Plan:** Verified via automated backend test suite (`tests/test_interop.py`) including cascading-delete validations and authorization boundary checks.
