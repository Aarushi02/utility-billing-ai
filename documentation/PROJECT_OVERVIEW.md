# Utility Billing AI - Project Overview

## What This Project Does

Utility Billing AI automates utility bill auditing.

It:

1. Extracts bill data from PDFs.
2. Parses tariff/rate logic.
3. Recalculates expected charges.
4. Compares expected vs actual billed amount.
5. Flags potential overcharges and produces reports.

## Why It Exists

Manual bill auditing is slow and error-prone. This project makes auditing faster, repeatable, and scalable.

## Current Scope

Current deployment scope is two services:

1. FastAPI backend (internal API)
2. Streamlit frontend (user-facing app)

Airflow is kept aside for now and can be reintroduced later.

## Core Capabilities

1. Upload and ingest bill/tariff documents.
2. Bill review and audit insights.
3. Tariff rule management.
4. Report generation.
5. Historical upload/result tracking.

## Primary Tech Stack

1. Python
2. Streamlit
3. FastAPI
4. PostgreSQL
5. AWS S3
6. Docker and Docker Compose

## Where to Read Next

1. `documentation/ARCHITECTURE.md` for system structure.
2. `documentation/DEPLOYMENT.md` for local + AWS deployment steps.
