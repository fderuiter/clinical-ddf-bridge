# ADR-20260722: CDISC USDM Schema and API Boundary Fast-Fail

* **Status:** Accepted
* **Date:** 2026-07-22
* **Authors:** @jules
* **Deciders:** @cadence-team

---

## 1. Context & Problem Statement
Prior to this enhancement, the trial execution engine microservice processed payloads from external registries without performing validation at the entry boundary. This resulted in delayed background job failures when encountering malformed data, increasing troubleshooting time and monitoring overhead.

## 2. Decision Drivers & Constraints
* **Driver 1:** Immediate detection of malformed configurations (fast-fail) before resource allocation.
* **Driver 2:** High alignment with the CDISC USDM standard types.
* **Driver 3:** Low latency impact on valid requests (< 100 milliseconds overhead).
* **Driver 4:** Clear, human-readable structural failure reasons returned directly in the response payload.

## 3. Options Considered
### Option 1: In-Worker Validation
* **Overview:** Validate the payload dictionary at the start of the background worker task.
* **Pros:**
  * ✅ Easy to implement within the existing worker.
* **Cons:**
  * ❌ Clients receive `200 Accepted` even if the payload is malformed, requiring manual inspection of background logs or databases to troubleshoot.

### Option 2: API Gateway Pydantic Schema Validation (Selected)
* **Overview:** Define strict Pydantic v2 schemas in a centralized reusable package (`packages/core-models`), and type the incoming endpoint payload with this schema.
* **Pros:**
  * ✅ Immediate rejection of malformed configurations with standard `422 Unprocessable Entity` status and detailed error messages.
  * ✅ Leverages and extends the official `usdm_model` Pydantic classes to guarantee compliance with international specifications.
  * ✅ Resides in a reusable shared package, allowing other services (e.g., designer, registry adapters) to import the same models.
* **Cons:**
  * ❌ Slight upfront initialization cost, but well within our 100ms latency budget.

## 4. Decision Outcome
* **Chosen Option:** Option 2
* **Justification:** Implementing validation at the API controller boundary using Pydantic schemas under `packages/core-models` ensures immediate error feedback to external registry orchestrators. This eliminates delayed background failures and aligns our platform with CDISC USDM standards.

## 5. Consequences & Trade-offs
* **Positive Impact:**
  * Reduced troubleshooting overhead for external integration partners.
  * Zero background translation failures due to malformed structural schemas or type mismatches.
* **Negative Impact / Technical Debt:**
  * Subclassing `usdm_model.Study` requires handling `instanceType` Literal values carefully since `ApiBaseModel` dynamically sets `instanceType` to the subclass name.

## 6. Implementation & Verification
* **Affected Repositories / Services:**
  * `packages/core-models` (new package)
  * `apps/execution/main.py` (updated event boundary model)
* **Verification Plan:**
  * Add unit tests in `tests/test_core_models.py` verifying model validation.
  * Run `pytest` to verify the `/events/study-published` endpoint rejects invalid payloads with 422 and proceeds successfully for valid payloads.
