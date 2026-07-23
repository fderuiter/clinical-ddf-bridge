# ADR 2026-07-23: Decoupled Database and Preboot Migration Consolidation

## Status
Accepted

## Context
With the expansion of the Cadence Clinical Platform to include several microservices such as execution, eTMF, and interop, we had multiple decoupled database session manager implementations. This duplication led to inconsistent session configurations, different SQLite compatibility logic, and redundant migration pipelines across individual repositories/services. To achieve perfect architectural alignment, we need to consolidate all database configurations and session management into a shared package (`packages/database`) and unify the pre-boot migration scripts across all clinical microservices.

## Decision
We consolidated all database session management and pre-boot migration logic under `packages/database`.
Specifically:
1. Created `packages/database` as a shared utility library across the execution, eTMF, and interop services.
2. Standardized `DatabaseSessionManager` inside the shared package to manage engine creation, SQLite foreign keys enforcement, and PostgreSQL compatibility functions (like custom `set_config` and `gen_random_uuid`).
3. Decoupled and centralized startup logic for all microservices, ensuring that they only use pre-boot schema migrations and completely removed runtime table generation.
4. Updated execution, eTMF, and interop to import connection helpers and run identical automated pre-boot migration scripts.

## Alternatives Considered
- **Maintaining microservice-specific DB utilities:** This approach is prone to drift, as PostgreSQL compatibility functions or foreign key PRAGMAs would need to be maintained in three separate places.
- **Using a shared ORM model library instead of shared connection library:** This was rejected because the microservices use highly specialized database tables/models (e.g., eTMF logs versus clinical trial execution models) but share the exact same connection pool, transactional, and auditing mechanics.

## Trade-offs
- **Positive:** Standardized connection handling, 100% test coverage of database consolidation mechanics, zero schema drift across services, and simplified microservice boot times.
- **Negative:** Shared package dependencies make the service build pipeline slightly more interdependent.
