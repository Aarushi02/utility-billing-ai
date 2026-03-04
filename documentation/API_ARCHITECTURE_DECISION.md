# API Architecture Decision (ADR-001)

**Date:** 2026-03-04  
**Project:** Utility Billing AI  
**Status:** Approved  
**Decision Owner:** Engineering Team

## 1. Context

The current implementation is a Streamlit application where UI, business logic, data access, and workflow orchestration are tightly coupled.  
This causes:
- difficult testing
- slow feature changes
- limited reuse for integrations/mobile/automation
- deployment coupling (UI and backend must release together)

## 2. Decision

We will adopt a **hybrid decoupled architecture**:

- Keep **Streamlit** as the current UI framework.
- Introduce **FastAPI** as the backend API boundary.
- Move business logic out of Streamlit into service/repository layers.
- Migrate incrementally feature-by-feature (Strangler pattern).

## 3. Target Architecture

```text
Streamlit UI --> FastAPI (/api/v1) --> Services --> Repositories --> DB/S3
                                      |
                                      +--> Worker/Orchestrator (async jobs)
```

## 4. Scope

### In Scope (Now)
1. Create FastAPI app and `/api/v1` routes for existing Streamlit features.
2. Extract business logic from UI into `src/services`.
3. Extract DB access into `src/repositories`.
4. Add job endpoints for long-running workflows.
5. Add API contracts (Pydantic models), logging, health checks, tests.

### Out of Scope (Now)
- Rewriting UI in React/Vue
- Full microservices split
- Public external API program

## 5. Why this decision

- Preserves team productivity with Python/Streamlit.
- Decouples backend safely without a full rewrite.
- Enables separate hosting/scaling for UI, API, and workers.
- Improves maintainability and testability immediately.

## 6. Migration Plan

### Phase 1 (Week 1-2): Foundation
- Add `src/api/main.py` and API router structure.
- Add shared settings/config module.
- Add API health endpoints and error model.

### Phase 2 (Week 3-4): First feature migration
- Pick one feature (e.g., tariff details viewer).
- Move logic to service/repository.
- Streamlit calls API endpoint instead of direct backend calls.

### Phase 3 (Week 5-6): Jobs/workflows
- Add async job endpoints (`POST /jobs`, `GET /jobs/{id}`).
- Route document processing through worker/orchestrator.

### Phase 4 (Week 7+): Expand + harden
- Migrate remaining pages.
- Add contract/integration tests.
- deprecate direct UI-to-DB calls.

## 7. Hosting Model

- **UI (Streamlit):** Streamlit Cloud or container host
- **API (FastAPI):** Render/Railway/Fly.io/AWS App Runner/ECS
- **Workers:** Airflow/Celery/Background worker container
- **Data:** existing RDS + S3
- **Secrets:** environment-based config per service

## 8. Success Criteria

- 0 direct DB/agent calls from Streamlit UI for migrated features.
- API p95 latency under defined SLO.
- Independent deploy pipeline for UI and API.
- At least one end-to-end feature fully served via API.
- Test coverage added for service and API contracts.

## 9. Re-evaluation Triggers

Revisit architecture if:
- >100 concurrent users
- mandatory mobile app/external integrations
- Streamlit UI constraints block product goals
- operational SLOs are not met
