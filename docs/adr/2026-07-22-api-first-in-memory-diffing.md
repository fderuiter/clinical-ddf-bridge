# ADR 2026-07-22: Decoupled API-First In-Memory Diffing

## Status
Accepted

## Context
Currently, the `/api/v1/studies/{study_id}/differences` endpoint requires a direct connection to the underlying graph database (Neo4j/Cypher) to compute differences between two versions of a clinical study. As we migrate to an API-first microservices architecture, direct database connections from downstream domain services are deprecated. This resulted in the endpoint throwing a persistent `503 Service Unavailable` error, blocking clinical study designers from comparing different study design versions.

## Decision
We decided to implement a decoupled, API-first in-memory diffing architecture for study version comparisons. 
Instead of computing differences within the database, the service will asynchronously fetch complete study payloads (in a compliant USDM structure) from an external registry (`STUDY_REGISTRY_URL`). Once the payloads are retrieved, the application flattens the nested JSON-like dictionaries into a 1D dot-notated structure, enabling dynamic, high-performance in-memory comparison of fields (additions, modifications, deletions). 

## Alternatives Considered
- **Direct Database Diffing (Status Quo):** Retaining the direct Neo4j connection for this single endpoint. Rejected because it violates the API-first separation of concerns and creates tight coupling to the database schema.
- **Dedicated Diffing Microservice:** Spinning up an entirely new microservice solely for diffing JSON payloads. Rejected due to the overhead of deploying and maintaining a new service when the logic is lightweight and easily contained within the existing designer service.

## Trade-offs
- **Positive:** Decouples the designer service from the database layer completely.
- **Positive:** Ensures high availability and eliminates the `503 Service Unavailable` errors.
- **Positive:** Extremely fast for standard payload sizes (meets the <2 second requirement easily).
- **Negative:** Increased memory footprint on the service when comparing very large payloads (>10MB).
- **Negative:** Introduces a dependency on the external registry's uptime and network latency. (Mitigated by graceful timeout and 502/504 error handling).
