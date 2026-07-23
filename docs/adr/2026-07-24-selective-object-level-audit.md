# ADR 2026-07-24: Selective Object-Level Audit Logging

## Status
Accepted

## Context
The prior database flush listener checked the entire session globally for the presence of external domain models (such as eTMF documents or interop audit logs). If any external domain model was present in the session, clinical audit logging was completely bypassed for all clinical objects modified in that same session. This caused critical clinical updates to go un-audited, violating regulatory standards and GxP requirements.

## Decision
We decided to replace the whole-session check with a granular, object-by-object audit evaluation. Each modified object is individually evaluated for audit eligibility. Objects inheriting from `AuditedModel` (i.e. clinical entities) are fully audited and tracked, whereas specified external models and non-audited models bypass audit log generation safely and performantly, without affecting clinical records in mixed-domain sessions. Furthermore, hard-deletion checks are also performed on an object-by-object basis to raise validation errors only for attempts to hard-delete clinical models, while allowing external systems to safely operate.

## Alternatives Considered
- **Whole-Session Session Isolation:** Separating clinical and external domain queries into completely isolated, independent database sessions. This was rejected due to significant transaction boundary complexity and potential database write performance degradation.
- **Explicit Manual Audit Tracking:** Requiring developers to manually trigger audit logging in the application services. This was rejected as it is error-prone and risks missing audits on some database pathways, violating regulatory requirements.

## Trade-offs
- **Positive:** Ensures continuous GxP and regulatory compliance by capturing all clinical mutations even in mixed-domain sessions, without duplicating database trigger logs or degrading external system write performance.
- **Negative:** Evaluating audit requirements per object adds a minor CPU overhead during flush operations, but this is negligible.
