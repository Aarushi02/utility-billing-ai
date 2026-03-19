# Utility Billing AI — Architecture Guide

<!-- Purpose: Deep-dive technical architecture reference for developers and reviewers.
     Covers system layers, component interactions, data flow, deployment topology,
     design decisions, and cross-cutting concerns (auth, logging, security).
     Dependencies: README.md (overview), DEPLOYMENT.md (run instructions), AWS_REUSE_SETUP_RUNBOOK.md (infra).
     Usage: Read this before making changes to routing, agent logic, or infrastructure layout. -->

## 1. Purpose

This document is the definitive technical reference for the system's internal structure. It explains how each layer works, how components communicate, why key design decisions were made, and what constraints must be respected when extending the system.

---

## 2. System Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                                 │
│  Streamlit UI (app/)  ←→  User browser                             │
│  Port 8501 — publicly reachable                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP REST (API_BASE_URL)
┌──────────────────────────────▼──────────────────────────────────────┐
│  API GATEWAY LAYER                                                  │
│  FastAPI backend (src/api/)                                         │
│  Port 8000 — internal only (127.0.0.1 on production)               │
│  Handles authentication, request validation, routing                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Python function calls
┌──────────────────────────────▼──────────────────────────────────────┐
│  SERVICE LAYER                                                      │
│  src/services/  — business/use-case logic                           │
│  Decouples the API boundary from the data layer and pipeline        │
└──────────┬───────────────────────────────────┬──────────────────────┘
           │ direct calls                      │ module calls
┌──────────▼──────────┐            ┌───────────▼──────────────────────┐
│  DATA LAYER          │            │  AI PROCESSING PIPELINE         │
│  src/database/       │            │  src/agents/  — 6 modules       │
│  PostgreSQL via      │            │  Each = one fixed pipeline step  │
│  SQLAlchemy ORM      │            │  2 modules use LLM API calls    │
│  AWS S3 via          │            │  4 modules are rule-based Python │
│  aws_app.py          │            └─────────────────────────────────┘
└─────────────────────┘
```

---

## 3. Component Deep-Dives

### 3.1 Presentation Layer — Streamlit UI (`app/`)

**Entry point**: `app/streamlit_app.py` — handles routing, session state, and page rendering.

**Pages (components)**:

| Component File | Page | What It Does |
|---------------|------|-------------|
| `login.py` | Login | JWT-based authentication form |
| `dashboard.py` | Home | 6 navigation cards — entry point after login |
| `file_uploader.py` | Upload & Ingest | PDF upload → calls `POST /api/v1/upload` |
| `user_bills_viewer.py` | Audit Bills | Fetches bills + validation results from API |
| `tariff_details_viewer.py` | Manage Tariffs | View/upload tariff structures |
| `pipeline_monitor.py` | Pipeline Status | Airflow DAG status via API |
| `reports_viewer.py` | Reports | Trigger report generation + download |
| `upload_history.py` | History | Past uploads with status |

**Key constraint**: Streamlit components must call API routes — they must not import from `src/` directly. All database and agent logic must go through the FastAPI boundary.

### 3.2 API Gateway Layer — FastAPI (`src/api/`)

**Entry point**: `src/api/main.py` — creates the FastAPI app, mounts routers, sets CORS, initialises DB.

**Routers** (`src/api/routers/`):

| Router | Prefix | Responsibility |
|--------|--------|---------------|
| `auth.py` | `/api/v1/auth` | Login, token issue, token refresh |
| `upload.py` | `/api/v1/upload` | Bill/tariff PDF upload → S3 + DB |
| `bills.py` | `/api/v1/bills` | CRUD for user bills and audit results |
| `tariffs.py` | `/api/v1/tariffs` | Tariff document management |
| `pipeline.py` | `/api/v1/pipeline` | Trigger/monitor Airflow DAGs |
| `reports.py` | `/api/v1/reports` | Report generation + download |
| `health.py` | `/api/v1/health` | Liveness + readiness probes |

**Authentication**: JWT tokens (`python-jose`). Login returns a Bearer token. All protected routes require `Authorization: Bearer <token>` header. Token validation is a FastAPI dependency injected per route.

### 3.3 Service Layer (`src/services/`)

One service file per domain feature. Services hold all business logic — they are called by API routers and call database utilities or agents.

| Service | Key Responsibilities |
|---------|---------------------|
| `upload_service.py` | Validates file type, stores to S3, creates DB record |
| `billing_service.py` | Orchestrates the bill validation agent and stores results |
| `tariff_service.py` | Loads tariff JSONs, triggers tariff pipeline |
| `processing_service.py` | Runs document extraction, tariff grouping |
| `report_service.py` | Builds report data, exports PDF/CSV |
| `workflow_service.py` | Integrates with Airflow REST API |
| `airflow_service.py` | Airflow API client (trigger, poll status) |

### 3.4 AI Processing Pipeline Modules (`src/agents/`)

Six specialised processing modules, each owning one fixed step in the pipeline. They are stateless Python classes/functions — no module retains state between calls.

> **Not agentic**: These are not autonomous agents. Each module does one deterministic task. Only 2 of 6 make an LLM API call — both are single, one-shot calls with no reasoning loop, no tool use, and no inter-module LLM coordination. The LLM is used purely as a **structured text parser** at two fixed pipeline steps.

| Module | Directory | Core Task | LLM API Call? |
|--------|-----------|----------|---------------|
| Document Processor | `document_processor_agent/` | PDF text + table extraction via `pdfplumber` + `camelot` | No — rule-based |
| Tariff Analyzer | `tariff_analysis_agent/` | Parse SC documents → group rates by service class | No — rule-based |
| Logic Extractor | `tariff_analysis_agent/extract_logic_llm_call.py` | Grouped tariff text → structured billing rules JSON | ✅ Single API call |
| Audit Calculator | `audit_calculation_agent/` | Apply extracted rules to bill data → calculate expected charge | No — arithmetic |
| Anomaly Detector | `billing_anomaly_detector_agent/` | Compare expected vs actual → explain discrepancy in plain English | ✅ Single API call |
| Report Generator | `reporting_generating_agent/` | Build audit report from validation results (PDF/CSV) | No — rule-based |

**LLM API call path**:
```
Module → src/utils/llm_client.py (LLMClient) → OpenAI REST API → gpt-4o-mini
```

### 3.5 Data Layer (`src/database/`)

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy ORM table definitions |
| `db_utils.py` | Session management, query helpers |
| `init_db.py` | Creates all tables on first run: `python -m src.database.init_db` |
| `utils/` | Domain-specific DB helpers (e.g. bill helpers, tariff helpers) |

**Tables**:

| Table | Holds |
|-------|-------|
| `users` | Login credentials (hashed passwords) |
| `raw_documents` | Uploaded PDF metadata + S3 key |
| `pipeline_runs` | Airflow DAG execution records |
| `user_bills` | Extracted bill fields (account, period, charges) |
| `bill_validation_results` | Expected charge, actual charge, delta, overcharge flag |
| `tariff_documents` | Uploaded tariff metadata |
| `tariff_logic_versions` | Versioned extracted billing rule JSON |
| `logs` | Pipeline execution events |

### 3.6 Orchestration — Apache Airflow (`airflow/dags/`)

Airflow manages multi-step pipeline execution with dependency tracking, retries, and logging.

**DAGs**:

| DAG ID | File | Tasks | Trigger |
|--------|------|-------|---------|
| `utility_billing_pipeline` | `pipeline_runner_dag.py` | 1. Extract PDF → 2. Group Tariffs → 3. Extract Logic (LLM) | API or manual |
| `tariff_pipeline_dag` | `tariff_pipeline_dag.py` | Tariff document ingestion + rule extraction | Manual |

**Integration**: The FastAPI `workflow_service.py` calls the Airflow REST API (`/api/v2/dags/<dag_id>/dagRuns`) to trigger runs and poll status. Airflow is not called directly from Streamlit.

---

## 4. Complete Data Flow

### Bill Upload → Audit → Report

```
1. User uploads PDF via Streamlit (file_uploader.py)
        ↓
2. POST /api/v1/upload  →  upload_service.py
        ↓
3. File saved to S3 + raw_documents record created in DB
        ↓
4. Airflow DAG triggered: utility_billing_pipeline
        ├─ Task 1: Document Processor Agent
        │    ├─ pdfplumber / camelot extract text + tables
        │    └─ Structured bill fields saved to user_bills table
        │
        ├─ Task 2: Tariff Analyzer Agent
        │    ├─ Load tariff PDFs for the bill's service class
        │    ├─ Group rates by tier + service class
        │    └─ Save grouped_tariffs.json to S3 + DB
        │
        └─ Task 3: Logic Extractor Agent (LLM)
             ├─ GPT-4o-mini reads grouped tariff text
             ├─ Returns structured billing rule JSON
             └─ Save final_logic_output.json + tariff_logic_versions record
        ↓
5. Audit Calculator Agent
        ├─ Load bill data from user_bills
        ├─ Load billing rules from tariff_logic_versions
        ├─ Calculate expected charge (tier-by-tier arithmetic)
        └─ Compare expected vs actual → save bill_validation_results
        ↓
6. Billing Anomaly Detector Agent (if discrepancy > threshold)
        ├─ GPT-4o-mini explains likely cause of overcharge
        └─ Appended to bill_validation_results
        ↓
7. User views results: GET /api/v1/bills → Streamlit audit page
        ↓
8. User requests report: POST /api/v1/reports
        ├─ Report Generator Agent builds PDF/CSV
        └─ Uploaded to S3, download link returned
```

---

## 5. Deployment Topology

### Local Development

```
localhost:8501  →  streamlit container
localhost:8000  →  api container          (no external auth required locally)
localhost:8080  →  airflow container      (optional)
localhost:5432  →  postgres container
```

### Production (AWS EC2)

```
Internet:80     →  nginx container         (public — only entry point)
                       └─ proxy_pass http://streamlit:8501
(internal)      →  streamlit container     (Docker network only — not public)
127.0.0.1:8000  →  api container           (EC2-internal only)
127.0.0.1:8080  →  airflow container       (EC2-internal only, profile-gated)
(internal)      →  postgres container      (Docker network only)

EC2 IAM Role  →  AWS S3 (no stored credentials — instance metadata)
GitHub Actions  →  SSH into EC2  →  git pull + docker compose rebuild (api+streamlit+nginx)

EC2 Start/Stop:
  Manual:    aws ec2 start-instances / stop-instances (current active mode)
  Scheduled: EventBridge Scheduler → Lambda (DISABLED — enable when needed)
             Timezone: America/New_York — DST auto-handled — 9AM start / 6PM stop
```

---

## 6. Cross-Cutting Concerns

### Authentication & Authorisation

- **Login**: `POST /api/v1/auth/login` returns a JWT Bearer token
- **Token validation**: FastAPI dependency `get_current_user` decodes + verifies on every protected endpoint
- **Token storage**: Streamlit stores the token in `st.session_state` — never in cookies or localStorage
- **Passwords**: Hashed with `bcrypt` via `passlib` — plain-text passwords never stored

### Logging

- `src/utils/logger.py` provides a shared logger instance used across all modules
- Log level configurable via `LOG_LEVEL` env var (`INFO` default)
- Airflow task logs: stored in `airflow/logs/` and viewable in Airflow UI
- API access logs: FastAPI middleware writes to stdout → captured by Docker

### Security Considerations

| Risk | Mitigation |
|------|-----------|
| API exposed publicly | Bound to `127.0.0.1` on production — not reachable outside EC2 |
| DB exposed publicly | Port 5432 not in Security Group — internal Docker network only |
| Secrets in git | `.env` gitignored; `terraform.tfvars` gitignored; `.pem` files gitignored |
| LLM prompt injection | LLM input is structured tariff text — not user-controlled free text |
| S3 bucket policy | Bucket is private; EC2 accesses via IAM role with least-privilege permissions |

### Configuration Management

`src/utils/config.py` loads all settings from environment variables via `pydantic-settings`. All components import settings from this single module — no direct `os.environ` calls scattered through the codebase.

---

## 7. Key Design Rules

1. **Streamlit calls API routes only** — never imports `src/` modules directly.
2. **Business logic lives in `src/services/`** — not in API routers and not in Streamlit components.
3. **Agents are stateless** — no agent stores state between calls; state lives in the DB.
4. **All LLM calls go through `llm_client.py`** — centralises model selection, retries, and cost control.
5. **Docker Compose is the runtime contract** — local and production must use the same compose files.
6. **Infrastructure is code** — all AWS resources managed by Terraform; no manual console clicks.
7. **Sensitive values are environment variables** — no secrets in source code or docker images.

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Project overview, feature list, quick start |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Step-by-step run instructions (local + production) |
| [AWS_REUSE_SETUP_RUNBOOK.md](AWS_REUSE_SETUP_RUNBOOK.md) | Full AWS + Terraform setup guide |
| [TERRAFORM_INFRA_GUIDE.md](TERRAFORM_INFRA_GUIDE.md) | Terraform resource reference |
| [DEPLOYMENT_PROGRESS_CHECKLIST.md](DEPLOYMENT_PROGRESS_CHECKLIST.md) | Current deployment status tracker |

