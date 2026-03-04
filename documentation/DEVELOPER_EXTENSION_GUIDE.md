# Developer Extension Guide

This guide explains how to add new business logic, new API endpoints, and new Streamlit pages in the current decoupled architecture.

## 1) Mental Model

Use this chain for all new features:

`Streamlit page` -> `API router` -> `service` -> `DB utils/agent/orchestrator` -> `DB/external system`

Rules:
- Streamlit components should not import `src.database`, `src.agents`, or `src.orchestrator` directly for migrated patterns.
- Routers contain HTTP mapping + validation only.
- Services contain business rules.
- Data access stays in backend (`src/services` + `src/database/*`) only.

---

## 2) Add New Business Logic (Backend)

### Step A: Add/extend service

Location: `src/services/`

Purpose:
- orchestrate DB utility calls and business rules.
- no HTTP-specific code.

Example filename:
- `src/services/customer_service.py`

### Step B: Add schema contracts (inside router)

Location: top of `src/api/routers/<domain>.py`

Purpose:
- define request/response shape with Pydantic models close to endpoint logic.

Example:
- `class CustomersResponse(BaseModel): ...` in `src/api/routers/customers.py`

### Step C: Add router

Location: `src/api/routers/`

Purpose:
- map HTTP methods/paths to service methods.

Example filename:
- `src/api/routers/customers.py`

### Step D: Register router

File:
- `src/api/main.py`

Add include line:
- `app.include_router(customers.router, prefix="/api/v1", tags=["customers"])`

---

## 3) Add New API Endpoint

Checklist:
1. Define request/response models at the top of `src/api/routers/<domain>.py`.
2. Add service method in `src/services/<domain>_service.py`.
3. Add/extend DB utility function in `src/database/db_utils.py` or `src/database/utils/*` if needed.
4. Expose endpoint in `src/api/routers/<domain>.py`.
5. Register router in `src/api/main.py`.
6. Verify endpoint in Swagger: `/docs`.

Naming convention:
- route group: plural noun (example `/customers`)
- endpoint: REST style (`GET /customers`, `POST /customers`)

---

## 4) Add New Streamlit Page

### Step A: Create component

Location: `app/components/`

Example:
- `app/components/customers_viewer.py`

Pattern:
- read `API_BASE_URL` from config.
- call API via helper function (`_get_api_json`, `_post_api_json`).
- handle `requests.RequestException` with `st.error`.

### Step B: Register in navigation

File:
- `app/streamlit_app.py`

Update:
- `page_icons` dictionary
- `page_options` routing block
- import/render function in route section

### Step C: Keep UI decoupled

Do not import:
- `src.database.*`
- `src.agents.*`
- `src.orchestrator.*`

---

## 5) Performance & Reliability Pattern

For API calls in Streamlit:
- use retry with small backoff for transient failures,
- use `st.cache_data` for GET calls with short TTL,
- keep POST calls uncached.

For local run:
- use `./run_local_stack.sh start` to ensure API is available before UI.

---

## 6) Where to Put What (Quick Map)

- API entrypoint: `src/api/main.py`
- Routers: `src/api/routers/`
- Router-local schema models: top of `src/api/routers/<domain>.py`
- Services: `src/services/`
- DB utilities: `src/database/` and `src/database/utils/`
- Streamlit pages: `app/components/`
- App navigation: `app/streamlit_app.py`
- Deployment runbook: `RUNBOOK_DEPLOYMENT.md`
- Architecture ADR: `documentation/API_ARCHITECTURE_DECISION.md`

---

## 7) Example End-to-End Template

Use this order:

1. `src/services/example_service.py`
2. `src/database/utils/example_utils.py` (if new shared data access needed)
3. add request/response models in `src/api/routers/example.py`
4. update `src/api/main.py`
5. create `app/components/example_viewer.py`
6. update `app/streamlit_app.py`
7. run and verify in `/docs` and Streamlit page

---

## 8) Verification Checklist Before Merge

- API endpoint visible in Swagger and responds correctly.
- Streamlit page works without direct backend-module coupling.
- Errors are user-friendly in UI (`st.error`).
- Local stack still starts with `run_local_stack.sh`.
- Documentation updated if new env vars or pages are added.

---

## 9) Common Pitfalls

- Using `localhost` inside Docker service-to-service communication.
- Adding business logic directly in router or Streamlit component.
- Forgetting to register router in `src/api/main.py`.
- Forgetting to set `API_BASE_URL` correctly per environment.
- Forgetting to restart Streamlit after page-level code changes.
