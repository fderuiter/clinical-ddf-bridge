# ADR-13: 2026-07-22 Cryptographic Audit Ledger and GxP-Lock Safety Freeze

## Status
Accepted

## 1. Context & Problem Statement
In clinical trials, compliance with FDA 21 CFR Part 11 guidelines dictates strict audit trail non-repudiation. Administrative users or direct database access can potentially bypass application-level audit logging, leading to silent data tampering. We need a robust mechanism to guarantee audit integrity and enforce a system-wide read-only freeze if tampering is detected.

## 2. Decision Drivers & Constraints
- FDA 21 CFR Part 11 compliance requires non-repudiation.
- Must prevent administrative users or database administrators from bypassing logging.
- System must automatically halt data modification upon detecting tampering.

## 3. Options Considered
- *Option 1: Third-party Blockchain/Immutable Ledger Service.* High integration overhead, potential data privacy concerns, and latency.
- *Option 2: Asynchronous messaging to external SIEM tools.* Does not provide immediate, transactional, native lock mechanisms to prevent ongoing data corruption.
- *Option 3: Cryptographic Ledger & GxP-Lock.* Creating a chronological ledger inside the existing relational database using Merkle roots, protected by database-level triggers, and continuously validated by a native asynchronous application loop.

## 4. Decision Outcome
Selected Option 3. It leverages SQLModel/SQLAlchemy to establish a `AuditLedgerBlock` and groups logs in 60-second batches. Database triggers natively block unauthorized `UPDATE` and `DELETE` commands. An application lifecycle background task verifies Merkle roots sequentially; if tampering occurs, a global `is_safety_freeze_active` boolean halts write operations across all application instances, turning the system read-only.

## 5. Consequences & Trade-offs
- *Positive:* Ensures regulatory compliance with no external system dependencies. Database triggers provide robust defense-in-depth against direct database administration override. The background verification prevents tampering from going unnoticed.
- *Negative:* Slight storage overhead for block hashes and roots. Global variable for safety freeze will necessitate distributed caching (like Redis) when scaling to multi-node setups to synchronize the freeze state instantly across instances, adding a bit of future technical debt.

## 6. Implementation & Verification
- Implementation involves `AuditLedgerBlock` and background hashing tasks.
- Triggers added for SQLite and PostgreSQL via migrations.
- Verified by automated tests checking tampering detection and lock enforcement.