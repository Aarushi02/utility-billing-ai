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

## 10. Current Coupling Findings (Codebase Analysis)

The following UI modules currently call backend logic directly and must be decoupled first:

- `app/streamlit_app.py`
    - Initializes DB directly via `src.database.init_db.init_db`.
- `app/components/workflow_trigger.py`
    - Calls orchestrator functions directly (`src.orchestrator.workflow_manager.*`).
- `app/components/reports_viewer.py`
    - Uses DB engine directly (`src.database.db_utils.get_engine`).
    - Reads bills directly (`src.database.utils.user_bills_utils.fetch_user_bills`).
    - Calls agent logic directly (`AuditEngine`, `store_override_values`).
- `app/components/user_bills_viewer.py`
    - Reads bills/issues directly from DB utils.
- `app/components/tariff_details_viewer.py`
    - Reads tariff/version logic directly from DB utils.
- `app/components/pipeline_monitor.py`
    - Reads processed run data directly from DB utils.
- `app/components/airflow_trigger.py`
    - Calls Airflow endpoints directly from UI.

## 11. Required Changes to Decouple (What to change/add)

### 11.1 Add API Boundary

Create:
- `src/api/main.py`
- `src/api/routers/health.py`
- `src/api/routers/tariffs.py`
- `src/api/routers/bills.py`
- `src/api/routers/reports.py`
- `src/api/routers/jobs.py`
- `src/api/schemas/*` (Pydantic contracts)

Rules:
- All endpoints under `/api/v1`.
- Streamlit UI must call API only (HTTP), not `src.database`, `src.agents`, or `src.orchestrator` directly.

### 11.2 Add Service Layer

Create:
- `src/services/tariff_service.py`
- `src/services/billing_service.py`
- `src/services/report_service.py`
- `src/services/workflow_service.py`

Rules:
- All business logic lives here.
- API routers orchestrate services only.

### 11.3 Add Repository Layer

Create:
- `src/repositories/tariff_repository.py`
- `src/repositories/billing_repository.py`
- `src/repositories/run_repository.py`

Rules:
- All SQL/DB calls move here.
- Services never execute raw SQL directly.

### 11.4 Add Async Job Pattern for Long-Running Work

Create API contracts/endpoints:
- `POST /api/v1/jobs` (submit run)
- `GET /api/v1/jobs/{job_id}` (status/result)

Rules:
- UI never executes long-running agent pipelines inline.
- UI polls job status.

### 11.5 Add Platform Cross-Cutting Components

Create/add:
- shared settings module (single source for env config)
- structured logging with `trace_id`/`job_id`
- standardized error response model (`code`, `message`, `details`, `trace_id`)
- health endpoints (`/health/live`, `/health/ready`)

## 12. Feature-by-Feature Migration Backlog

Execute in this order:

1. **Tariff Details Viewer**
     - UI file: `app/components/tariff_details_viewer.py`
     - Add API: `GET /api/v1/tariffs/sc-codes`, `GET /api/v1/tariffs/{sc}/versions`, `GET /api/v1/tariffs/{sc}/versions/{effective_date}`
2. **User Bills Viewer**
     - UI file: `app/components/user_bills_viewer.py`
     - Add API: `GET /api/v1/bills/accounts`, `GET /api/v1/bills?account_id=...`, `GET /api/v1/bills/issues?account_id=...`
3. **Pipeline Monitor**
     - UI file: `app/components/pipeline_monitor.py`
     - Add API: `GET /api/v1/runs?limit=20`
4. **Workflow Trigger**
     - UI file: `app/components/workflow_trigger.py`
     - Replace direct orchestrator calls with jobs API (`POST/GET /jobs`).
5. **Reports Viewer**
     - UI file: `app/components/reports_viewer.py`
     - Move expected bill computation and override persistence behind API.
6. **Airflow Trigger**
     - UI file: `app/components/airflow_trigger.py`
     - Move Airflow authentication/trigger calls to backend service.

## 13. Definition of Done (Per Migrated Feature)

A feature is considered decoupled only if all are true:
- Streamlit page has zero imports from `src.database`, `src.agents`, `src.orchestrator`.
- Streamlit page calls `/api/v1/*` only.
- API endpoint has request/response schema.
- Service and repository tests exist.
- Endpoint has success and error-path tests.

## 14. Hosting and Deployment Model (UI + API + Workers)

### 14.1 Services
- **UI (Streamlit):** Streamlit Cloud or container host.
- **API (FastAPI):** Render / Railway / Fly.io / AWS App Runner / ECS.
- **Workers:** Airflow/Celery/background worker container.
- **Data:** Existing RDS + S3.

### 14.2 Deployment Separation
- Build and deploy UI and API independently.
- UI receives `API_BASE_URL` via env config.
- API/Worker use separate secrets from UI (principle of least privilege).

### 14.3 Minimum Production Readiness for API
- HTTPS endpoint
- health/readiness probes
- autoscaling or fixed min replicas
- structured logs and error monitoring
- timeout/retry policy for upstream dependencies

## 15. Governance Guardrails

To prevent re-coupling:
- Block PRs where `app/**` imports from `src.database`, `src.agents`, `src.orchestrator`.
- Require new backend functionality to be exposed via service + API route.
- Keep `src/api`, `src/services`, `src/repositories` ownership explicit in code reviews.


## 16. Layer Responsibilities

- **Routers:** HTTP endpoint layer (URL mapping). Example: `src/api/routers/tariffs.py`.
- **Services:** business logic/use-cases (rules/workflow logic, no HTTP details). Example: `src/services/tariff_service.py`.
- **Repositories:** data access only (DB queries, persistence). Example: `src/repositories/tariff_repository.py`.
- **Schemas:** request/response contracts (Pydantic models for API shape). Example: `src/api/schemas/tariffs.py`.

## 17. Decoupling Flow

- **Before:** Streamlit page directly imports DB utilities.
- **Now:** Streamlit → API router → service → repository → DB.
- **First migrated example:** Tariff page (`app/components/tariff_details_viewer.py`).

## 18. Current Implementation Status (March 2026)

Completed migrations to API-backed UI flows:

- `app/components/tariff_details_viewer.py`
- `app/components/user_bills_viewer.py`
- `app/components/pipeline_monitor.py`
- `app/components/workflow_trigger.py`
- `app/components/reports_viewer.py`
- `app/components/airflow_trigger.py`

Backend structure currently in place:

- `src/api/*` (entrypoint, routers, schemas)
- `src/services/*` (workflow/report/tariff/billing/airflow services)
- `src/repositories/*` (billing/tariff/run repositories)

## 19. Frontend Resilience Pattern (Added)

To reduce transient timeout failures and improve perceived speed in Streamlit pages:

- API client helpers use retry with backoff for transient request errors.
- GET calls on high-traffic views use short TTL cache (`st.cache_data`).
- Local orchestration script (`run_local_stack.sh`) provides deterministic startup/stop/status/logs.

Operational impact:

- fewer intermittent `Read timed out` UI errors,
- faster rerenders when data is unchanged,
- easier local troubleshooting.

## 20. Next Documentation

For adding new logic, endpoints, and pages, see:

- `documentation/DEVELOPER_EXTENSION_GUIDE.md`