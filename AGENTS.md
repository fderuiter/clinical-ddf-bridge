# Agent Guidelines: Clinical DDF Integration Bridge

## Role & Purpose
This repository serves as the orchestration and transformation middleware connecting:
- Upstream: OpenStudyBuilder (Clinical Metadata Repository / USDM DDF API)
- Downstream: OpenClinica (Electronic Data Capture engine / eCRFs and Study Build API)

## Workspace Architecture
- Do NOT modify upstream core logic in OpenStudyBuilder or OpenClinica directly.
- All ETL pipelines, data transformers (USDM -> XForms/ODM), and SSO/Keycloak orchestration code belong in this repository.

## Target Stack & Conventions
- **Language:** Python 3.11+ (FastAPI, Pydantic v2, HTTPX)
- **Code Style:** Black / Ruff linting, typed python with strict type hints.
- **Testing:** Pytest for schema transformation unit tests.
