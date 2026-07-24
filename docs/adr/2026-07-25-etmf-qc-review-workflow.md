# ADR-045: eTMF Multi-Stage Quality Control Review Workflow

* **Status:** Accepted
* **Date:** 2026-07-25
* **Authors:** @google-labs-jules
* **Deciders:** @fderuiter

---

## 1. Context & Problem Statement
The electronic Trial Master File (eTMF) is a critical compliance component in clinical trials that houses essential study documentation. Previously, the eTMF module only supported document ingestion and basic metadata storage, lacking a validated Quality Control (QC) review lifecycle. For 21 CFR Part 11 and GxP compliance, clinical documents must progress through structured, multi-tier QC review cycles (e.g., Draft → Technical QC → Clinical QC → Final Approval → Archive) with strict role-based access control (RBAC), state machine validation, and transactional audit logging.

## 2. Decision Drivers & Constraints
* **Driver 1:** Compliance with 21 CFR Part 11 and EU Annex 11, specifically requiring immutable, chronological transition records, role-based authority checks, and mandatory reasons for change.
* **Driver 2:** Integrity and correctness of the document lifecycle state machine to prevent illegal transitions (e.g., directly from Draft to Archived or Approved back to Draft).
* **Driver 3:** High performance and transactional safety (guaranteeing that status changes, QC records, and standard audit log entries are persisted within a single transaction).

## 3. Options Considered
### Option 1: In-Memory / Client-Driven State Management
* **Overview:** Rely on client-side status tracking and manual updates directly to the document status.
* **Pros:**
  * ✅ Very simple implementation.
  * ✅ Minimal database changes.
* **Cons:**
  * ❌ Violates 21 CFR Part 11 as there is no server-validated state machine or immutable transition history.
  * ❌ Prone to split-brain states and unauthorized status modifications.

### Option 2: Fully Orchestrated Multi-Stage QC Workflow - Selected
* **Overview:** Implement a server-side state machine in `apps/etmf` with strict backend RBAC gates, a persistent status column on `TMFDocument`, an append-only transition history model `DocumentQCTransition`, and a transaction-scoped API endpoint.
* **Pros:**
  * ✅ Full 21 CFR Part 11 compliance: every change is authenticated, validated, and logged chronologically.
  * ✅ Implements a robust state machine preventing invalid status transitions.
  * ✅ Provides a complete, immutable audit ledger for QC transitions.
* **Cons:**
  * ❌ Increased complexity in backend validation logic and model definition.
  * ❌ Requires additional storage for the transition ledger.

## 4. Decision Outcome
* **Chosen Option:** Option 2
* **Justification:** Option 2 is the only option that satisfies the strict regulatory compliance requirements of GxP and 21 CFR Part 11. It guarantees non-repudiation, strict role gates, and validation of the state machine.

### State Machine Specification
The document lifecycle is defined by the following ordered statuses:
* **DRAFT**
* **TECHNICAL_QC**
* **CLINICAL_QC**
* **APPROVED**
* **ARCHIVED**
* **REJECTED**

### Valid Transitions
* `DRAFT` → `TECHNICAL_QC` (submitted for review)
* `TECHNICAL_QC` → `CLINICAL_QC` (technical review passed) or `REJECTED` (technical review failed)
* `CLINICAL_QC` → `APPROVED` (clinical review passed) or `REJECTED` (clinical review failed)
* `APPROVED` → `ARCHIVED` (document archived)
* `REJECTED` → `DRAFT` (back to draft for revision)

### Role-Based Gates
* Transitioning to `TECHNICAL_QC` or `REJECTED` from Draft/Tech QC requires `technical_qc_reviewer`, `technical_qc`, or `admin`.
* Transitioning to `CLINICAL_QC` or `REJECTED` from Clinical QC requires `clinical_qc_reviewer`, `clinical_qc`, or `admin`.
* Transitioning to `APPROVED` or `ARCHIVED` requires `approver` or `admin`.
* Resubmission to `DRAFT` from Rejected requires `author`, `data_manager`, `sponsor_dm`, or `admin`.

## 5. Consequences & Trade-offs
* **Positive Impact:** Robust multi-tier QC cycles are fully enforced, with secure role gates and full GxP auditable traceability.
* **Negative Impact / Technical Debt:** Additional overhead of managing and querying an append-only history table.
* **Mitigation Strategy:** Automated database indices are created on `document_id` and `timestamp` fields of the transition model to ensure efficient history lookups.

### Deferred Follow-ups
* **Notifications:** Real-time notifications and task-assignment alerts to reviewers when documents transition states are deferred to a future Phase 3 implementation.
* **Database Migrations:** We utilize the automatic lifespan SQLite schema creation (`Base.metadata.create_all`) for development and testing. Production-grade pre-boot database migrations (e.g., via Alembic or equivalent scripts) are deferred.

## 6. Implementation & Verification
* **Affected Services:** `apps/etmf` (`models.py`, `main.py`)
* **Verification Plan:** Full end-to-end integration tests have been implemented in `tests/test_etmf.py` covering successful forward progression, role-based rejection, state machine validation, missing change reason rejections, and correct writing of both the `DocumentQCTransition` history table and the general `TMFAuditLog`.
