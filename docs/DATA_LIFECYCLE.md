# eTMF Document Lifecycle Specification

This document defines the Quality Control (QC) review and approval lifecycle for documents stored in the Electronic Trial Master File (eTMF) of the Cadence Clinical platform.

Clinical trials require absolute integrity, non-repudiation, and auditability for all documentation to meet FDA (21 CFR Part 11) and EMA (EU Annex 11) regulations. The eTMF document lifecycle guarantees that all clinical artifacts undergo strict multi-tier review before final archiving.

---

## 1. Document Lifecycle Stages

Every document uploaded/ingested into the eTMF repository is associated with a distinct lifecycle status. The following statuses are supported:

| Status | Description |
|---|---|
| `DRAFT` | The initial stage when a document is newly ingested. The document is open for changes and editing. |
| `TECHNICAL_QC` | Gated review stage where technical reviewers check metadata, signature validity, and correct taxonomy mapping. |
| `CLINICAL_QC` | Gated review stage where clinical experts assess correctness of clinical content and clinical trial alignment. |
| `APPROVED` | The final validated state. The document is marked approved and is ready for use / reference. |
| `ARCHIVED` | The terminal immutable state. The document is locked and archived for long-term historical GxP storage. |
| `REJECTED` | Rejection phase when a document fails technical or clinical QC, allowing the author to revise and resubmit it back to `DRAFT`. |

---

## 2. Valid Transitions State Machine

Document status can only transition through validated state machine paths. Illegal transitions are strictly blocked at the database transaction layer.

```
+---------+         +--------------+         +-------------+         +----------+         +----------+
|  DRAFT  | ------> | TECHNICAL_QC | ------> | CLINICAL_QC | ------> | APPROVED | ------> | ARCHIVED |
+---------+         +--------------+         +-------------+         +----------+         +----------+
     ^                      |                       |
     |                      v                       v
     |              +--------------+         +-------------+
     +------------- |   REJECTED   | <-------+             |
                    +--------------+                       |
                           ^                               |
                           +-------------------------------+
```

The valid forward and rejection paths are explicitly defined as:
* `DRAFT` → `TECHNICAL_QC`
* `TECHNICAL_QC` → `CLINICAL_QC` or `REJECTED`
* `CLINICAL_QC` → `APPROVED` or `REJECTED`
* `APPROVED` → `ARCHIVED`
* `REJECTED` → `DRAFT`
* `ARCHIVED` → *Terminal (no further transitions allowed)*

---

## 3. Role-Based Access Control (RBAC) Gates

To satisfy authority checks, each target stage transition is gated behind strict OIDC gateway user roles. The lowercase list of required roles follows standard platform conventions:

| Target Stage | Required Roles | Description |
|---|---|---|
| `DRAFT` | `author`, `data_manager`, `sponsor_dm`, `admin` | Resubmitting a rejected document to draft or initial draft creation. |
| `TECHNICAL_QC` | `technical_qc_reviewer`, `technical_qc`, `admin` | Promoting a draft document to technical review. |
| `CLINICAL_QC` | `clinical_qc_reviewer`, `clinical_qc`, `admin` | Promoting a document that has passed technical checks to clinical review. |
| `APPROVED` | `approver`, `admin` | Approving a document after clinical QC. |
| `ARCHIVED` | `approver`, `admin` | Locking down an approved document in the long-term archive. |
| `REJECTED` | `technical_qc_reviewer`, `clinical_qc_reviewer`, `technical_qc`, `clinical_qc`, `admin` | Rejecting a document during technical or clinical QC review. |

Any request made by a user lacking the required role will be rejected with an `HTTP 403 Forbidden` error.

---

## 4. 21 CFR Part 11 Audit Trail & Traceability

Every document transition is atomically recorded inside a single SQL transaction using two separate historical ledgers to guarantee absolute compliance:

1. **`DocumentQCTransition` history table:** An append-only relational ledger recording the `document_id`, `from_status`, `to_status`, `user_id`, `user_role`, `reason_for_change`, and `timestamp` of every change.
2. **`TMFAuditLog` ledger:** A global immutable audit trail capturing the broad action `QC_TRANSITION` alongside detailed context regarding the transitioned document.

### Mandatory Change Reason

To prevent administrative bypass, **every status transition requires a non-empty `X-Change-Reason` header** (capturing `reason_for_change`). Requests with empty or missing change-reason headers are rejected with an `HTTP 400 Bad Request` or `HTTP 403 Forbidden` error.
