# Agent Guidelines: Cadence Clinical Platform

## Product Vision
Cadence Clinical is a standalone, next-generation eClinical platform that unifies Clinical Metadata Management (MDR) and Electronic Data Capture (EDC) into a single, cohesive product suite.

## Workspace Architecture & Reference Codebases
- `openstudybuilder-ref`: Read-only reference for CDISC USDM graph schemas, protocol versioning, and Schedule of Activities.
- `openclinica-ref`: Read-only reference for eCRF form evaluation, Enketo/XForm rendering, subject lifecycle state machines, and audit trail enforcement.

## System Guardrails
- Upstream reference repositories (`openstudybuilder-ref`, `openclinica-ref`) MUST remain untouched.
- All newly extracted modules, Pydantic v2 schemas, FastAPI routes, and database migrations MUST be generated exclusively inside `cadence-clinical`.
- Stack: Python 3.11+ (FastAPI, Pydantic v2, HTTPX), Keycloak OIDC, Docker Compose setup.
