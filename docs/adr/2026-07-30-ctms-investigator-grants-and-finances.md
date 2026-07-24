# ADR-050: CTMS Investigator Grants, Budgets, Milestones, and Payables Tracking

* **Status:** Accepted
* **Date:** 2026-07-30
* **Authors:** @fderuiter, @jules
* **Deciders:** @fderuiter, @jules

---

## 1. Context & Problem Statement
Site financial management requires auditable grants, planned-versus-actual budgets, and deterministic milestone transitions that create payable records. The platform needs investigator grant, budget, payment-milestone, and payable tracking for CTMS.

## 2. Decision Drivers & Constraints
- Site operations must have robust financial controls.
- Transition from milestones to payables must be deterministic, automated, and idempotent.
- Any modifications to financial entities must satisfy GxP/21 CFR Part 11 requirements (versioning, change-reason, audit logs).
- Approved investigator grants are locked to prevent unauthorized/accidental budget modifications.

## 3. Options Considered
### Option 1: Generic Rules Engine
Use a dynamic, user-configurable rules engine to monitor database state and trigger payables.
- ❌ Higher risk of infinite loops or non-deterministic executions.
- ❌ Harder to audit and validate for GxP/clinical trials.

### Option 2: Deterministic Inline Domain Logic with Approved Grants Locking (Selected)
Define precise, database-backed ORM entities for InvestigatorGrant, BudgetLineItem, PaymentMilestone, and InvestigatorPayable. Provide a focused domain service that evaluates known, rigid milestone conditions (e.g. `VISIT_COMPLETED` checking CTMS monitoring visits) idempotently and registers payables. Once a grant is approved, enforce version locking.
- ✅ High predictability and auditability.
- ✅ Enforces strict GxP and Part 11 compliance with standard audit fields and `CTMSAuditLog` entries.
- ✅ Robust, idempotent evaluation logic that prevents duplicate payables.

## 4. Decision Outcome
- **Chosen Option:** Option 2
- **Locking Decision:** Once an investigator grant's status is changed to `APPROVED`, its total budget, currency, associated budget line items, and payment milestones are locked and cannot be modified.

## 5. Consequences & Trade-offs
- **Positive:** Clear, predictable financial tracking. Standardized audit logging. Defends against budget manipulation.
- **Negative:** Hardcoded milestone conditions require code updates for new types of milestone conditions.

## 6. Implementation & Verification
- **Affected Services:** `apps/ctms/models.py`, `apps/ctms/main.py`, `apps/execution/database/audit.py`.
- **Verification Plan:** Unit and integration testing using TestClient, verifying RBAC boundaries, approved grant locking, milestone evaluation, idempotency, and audit log persistence.
