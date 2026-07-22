# Agent Guidelines: Cadence Clinical Platform

## Product Mission
Cadence Clinical is a unified, standalone eClinical platform synthesizing upstream Clinical Metadata Management (MDR) with downstream Electronic Data Capture (EDC) into an automated Digital Data Flow (DDF) platform.

---

## Multi-Repository Context & System Boundaries

When operating within the Jules Multi-Repo Workspace, you have access to three connected repositories:

1. **`openstudybuilder-ref`** *(READ-ONLY REFERENCE)*
   - Use strictly as a reference blueprint for CDISC USDM graph algorithms, protocol versioning logic, and Schedule of Activities (SoA) definitions.
   - **DO NOT** edit or submit commits to this repository.

2. **`openclinica-ref`** *(READ-ONLY REFERENCE)*
   - Use strictly as a reference blueprint for eCRF form evaluation, OpenRosa/Enketo XForm rendering rules, subject state machines, query management, and audit log schemas.
   - **DO NOT** edit or submit commits to this repository.

3. **`cadence-clinical`** *(PRIMARY OWNED REPOSITORY)*
   - **ALL** new code generation, refactoring, API endpoints, Pydantic v2 domain models, Keycloak OIDC configs, and Docker setups MUST be authored strictly within this repository.

---

## Technical Stack & Standards

- **Language & Runtime:** Python 3.11+
- **Frameworks:** FastAPI, Pydantic v2 (strict typing required), HTTPX (async REST)
- **Code Style:** Black formatting, Ruff linting
- **Database Access:** - `apps/designer`: Async Neo4j Python Driver
  - `apps/execution`: Async SQLAlchemy / SQLModel for PostgreSQL
- **Standards:** CDISC USDM (v3.0/v4.0), CDISC ODM XML/JSON, 21 CFR Part 11 compliant audit fields (`created_at`, `created_by`, `reason_for_change`, `version_index`).

---

## Directory Target Rules for Generated Code

- Data models & CDISC schemas ──► `packages/core-models/`
- Study authoring / MDR logic ──► `apps/designer/`
- Data capture / eCRF logic ──► `apps/execution/`
- OIDC Auth & Routers ──► `apps/gateway/`
- Stack orchestration ──► `docker/`
