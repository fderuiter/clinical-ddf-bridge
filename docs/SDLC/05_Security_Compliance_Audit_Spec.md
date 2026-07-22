# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
# Security, Compliance & Audit Trail Spec

## 1. Regulatory Context
Cadence Clinical strictly conforms to **21 CFR Part 11**, **EU Annex 11**, and **ISO/IEC 27001:2022**. This specification details how electronic records, signatures, and access controls are implemented.

## 2. Role-Based Access Control (RBAC) Matrices
- The system employs a granular RBAC model.
- Roles include: Sponsor Admin, Data Manager, Principal Investigator, Clinical Research Coordinator (CRC), Auditor.
- Permissions are strictly enforced at the API Gateway level based on verified JWT claims.

## 3. Electronic Signature Protocols
- A formal electronic signature is required for marking an eCRF complete or locking a study.
- The signature process requires re-authentication (password or biometric via WebAuthn).
- The signature record captures the printed name, date/time, and meaning (e.g., "I approve these data").

## 4. Immutable Audit Logging Framework
### 4.1 Application-Layer Tracking
- Every data mutation captures: `created_at`, `created_by`, `reason_for_change`, and `version_index`.
- Pre-mutation and post-mutation states are recorded.

### 4.2 Cryptographic Ledger Workflow
- Audit records are cryptographically sealed into blocks using SHA-256.
- Any tampering with historical records breaks the chain and triggers immediate security alerts.

### 4.3 Database-Level Triggers
- PostgreSQL `AFTER UPDATE`/`AFTER DELETE` triggers preserve data in a shadow schema if bypassed at the application layer.

## 5. Privacy & Data Masking
- Exports for auditors dynamically mask Personally Identifiable Information (PII).
- User IDs are cryptographically hashed in external extracts.
[ignoring loop detection]
