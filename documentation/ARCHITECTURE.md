# Utility Billing AI - Architecture

## Purpose

The system audits utility bills by extracting bill data, applying tariff logic, and flagging overcharges.

## High-Level Design

```text
Browser
  -> Streamlit UI
     -> FastAPI backend (/api/v1)
        -> Services layer
           -> Database utilities + agent logic
              -> PostgreSQL + S3
```

## Main Components

1. Streamlit UI (`app/`)
- Uploads bills/tariffs
- Shows audit data and reports
- Calls backend via `API_BASE_URL`

2. FastAPI backend (`src/api/`)
- API boundary for UI
- Health endpoints and feature routes
- Orchestrates services

3. Services (`src/services/`)
- Business/use-case logic
- Keeps UI and DB decoupled

4. Agents (`src/agents/`)
- Document extraction
- Tariff analysis
- Validation and reporting

5. Data layer (`src/database/`)
- SQLAlchemy models
- DB utilities and helper modules

6. Storage
- PostgreSQL for structured records
- S3 for files and JSON artifacts

## Runtime Topology

Local Docker (current focus):

1. `api` container
2. `streamlit` container

Airflow can be enabled later, but it is out of scope for this deployment phase.

## Key Design Rules

1. Streamlit should call API routes, not DB utilities directly.
2. Business logic should live in `src/services`.
3. Long-running workflows should be triggered from backend pathways, not inline in UI.
