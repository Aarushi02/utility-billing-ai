# 🏢 The Agentic Auditor - Utility Billing AI ⚡📄💰

**An intelligent, LLM-integrated AI pipeline for automating utility bill auditing, tariff analysis, and overcharge detection.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red) ![Airflow](https://img.shields.io/badge/Orchestration-Airflow-green) ![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791) ![AWS](https://img.shields.io/badge/Cloud-AWS-FF9900) ![Docker](https://img.shields.io/badge/Container-Docker-2496ED)

---

## 📖 Project Overview

Commercial utility bills are complex documents with multiple rate tiers, surcharges, and taxes. Manual auditing is time-consuming and error-prone, leading to undetected overcharges costing businesses thousands of dollars annually.

**The Agentic Auditor** is an automated, AI-powered solution that:
- ✅ Extracts data from utility bill PDFs automatically
- ✅ Parses tariff documents to understand billing rules
- ✅ Calculates what customers *should* be charged based on official tariffs
- ✅ Detects discrepancies and overcharges with precision
- ✅ Generates comprehensive audit reports

This system leverages a **Modular AI Pipeline** with **LLM-integrated processing modules** orchestrated by **Apache Airflow**, making it enterprise-ready and scalable.

---

## 🎯 Problem & Solution

### **The Problem**
- 📊 Utility bills contain complex rate structures (tier 1, tier 2, surcharges, taxes)
- 🧑‍💼 Manual auditing takes hours per bill and is prone to human error
- 💸 Overcharges often go unnoticed, costing businesses money
- 📈 At scale, businesses cannot manually audit thousands of bills

### **The Solution**
- 🤖 **Automated Extraction**: AI-powered PDF parsing extracts all billing data
- 🧠 **LLM Analysis**: OpenAI GPT models understand complex tariff rules
- 🔢 **Automated Calculation**: Recalculates charges based on official tariffs
- 🚨 **Anomaly Detection**: Flags overcharges and discrepancies automatically
- 📋 **Reporting**: Generates detailed audit reports with visualizations

---

## 🏗️ System Architecture

### **Layered Architecture**

```
┌──────────────────────────────────────────────────────────┐
│           FRONTEND (Streamlit UI - "The Agentic Auditor") │
│  ✓ Login/Authentication                                  │
│  ✓ Dashboard with 6 navigation cards                     │
│  ✓ File upload interface                                 │
│  ✓ Bill viewer and audit results                         │
│  ✓ Report generation                                     │
└─────────────────────┬──────────────────────────────────┘
                      │
┌─────────────────────v──────────────────────────────────┐
│      ORCHESTRATOR (Apache Airflow 3.1)                  │
│  ✓ utility_billing_pipeline DAG (3 sequential tasks)   │
│  ✓ tariff_pipeline_dag for tariff processing           │
│  ✓ Dependency management                                │
│  ✓ REST API for task triggering                         │
│  ✓ Execution logging and monitoring                     │
└─────────────────────┬──────────────────────────────────┘
                      │
┌─────────────────────v──────────────────────────────────┐
│    AI PROCESSING PIPELINE (Specialized Modules)         │
│                                                         │
│  1️⃣  Document Processor Module                          │
│      └─ PDF text extraction (pdfplumber)                │
│      └─ Table extraction (camelot)                      │
│      └─ Data cleaning & normalisation                   │
│                                                         │
│  2️⃣  Tariff Analyzer Module                             │
│      └─ Parse Service Classification (SC) documents     │
│      └─ Extract rate structures                         │
│      └─ Group tariffs by service class                  │
│                                                         │
│  3️⃣  Logic Extractor Module  🤖 LLM API Call            │
│      └─ OpenAI GPT-4o-mini API call                     │
│      └─ Interprets tariff text → structured rules       │
│      └─ Returns JSON with tier thresholds & rates       │
│                                                         │
│  4️⃣  Audit Calculation Module                           │
│      └─ Rule-based arithmetic engine                    │
│      └─ Computes expected charge from tariff rules      │
│      └─ Compares calculated vs actual charges           │
│                                                         │
│  5️⃣  Anomaly Detector Module  🤖 LLM API Call           │
│      └─ OpenAI GPT-4o-mini API call                     │
│      └─ Explains discrepancies in plain English         │
│      └─ Flags overcharges with threshold detection      │
│                                                         │
│  6️⃣  Report Generator Module                            │
│      └─ Builds audit reports from validation results    │
│      └─ Export to PDF/CSV                               │
│      └─ Summary statistics                              │
└─────────────────────┬──────────────────────────────────┘
                      │
┌─────────────────────v──────────────────────────────────┐
│           DATA LAYER                                    │
│                                                         │
│  Database (PostgreSQL RDS)                              │
│  ├─ raw_documents                                       │
│  ├─ pipeline_runs                                       │
│  ├─ user_bills                                          │
│  ├─ bill_validation_results                             │
│  ├─ tariff_documents                                    │
│  ├─ tariff_logic_versions                               │
│  └─ logs                                                │
│                                                         │
│  File Storage (AWS S3)                                  │
│  ├─ raw_extracted_tariff.json                           │
│  ├─ grouped_tariffs.json                                │
│  ├─ final_logic_output.json                             │
│  └─ audit_reports (PDF/CSV)                             │
└──────────────────────────────────────────────────────────┘
```

---

## 🎮 User Interface Pages

The Streamlit frontend provides an intuitive dashboard with **6 main pages**:

### **🏠 Home Dashboard**
- Welcome screen with animated cards
- Navigation to all features
- Quick access to recent audits

### **📁 Upload & Ingest**
- Upload utility bill PDFs
- Automatic data extraction
- Preview extracted information
- Store in database and S3

### **📄 Audit Bills**
- View all uploaded bills
- See extracted bill information
- Check validation results
- View calculated vs. actual amounts
- Identify overcharges with visual indicators

### **📑 Manage Tariffs**
- Upload tariff documents
- View extracted tariff rules
- Manage rate structures
- Test tariff logic

### **📊 Pipeline Status** (Coming Soon)
- Real-time monitoring of DAG execution
- Task progress tracking
- Execution logs and error messages
- Performance metrics

### **📋 Generate Reports**
- Create detailed audit reports
- Export as PDF/CSV
- Summary statistics
- Overcharge breakdown
- Historical trends

### **📜 Upload History**
- View all uploaded files
- Track processing status
- Reprocess files if needed
- Download results

---

## 📂 Repository Structure

```
utility-billing-ai/
│
├── 📄 README.md                           # This file
├── 📄 RUNBOOK_DEPLOYMENT.md               # Local/deployment runbook
├── 📦 requirements.txt                    # Python dependencies
├── 🐋 docker-compose.yml                  # Container orchestration
├── 🐋 docker-compose.prod.yml             # Production port-binding override
├── 🔧 .env                                # Runtime environment values (local/server)
├── 🔧 .env.example                        # Sanitized environment template
├── 🔒 LICENSE                             # Project license
│
├── 🌐 app/                                # Streamlit Frontend
│   ├── 📄 streamlit_app.py                # Main entry point & routing
│   ├── 🎨 assets/                         # Images, logos, static files
│   ├── utils/                             # Frontend utilities
│   └── components/                        # UI Components
│       ├── login.py                       # Authentication & login page
│       ├── dashboard.py                   # Home dashboard with 6 cards
│       ├── home.py                        # Home page utilities
│       ├── file_uploader.py               # Bill & tariff upload interface
│       ├── user_bills_viewer.py           # Bills list & audit results
│       ├── tariff_details_viewer.py       # Tariff management & viewing
│       ├── pipeline_monitor.py            # Pipeline status (coming soon)
│       ├── reports_viewer.py              # Report generation & viewing
│       ├── upload_history.py              # File history & reprocessing
│       ├── airflow_trigger.py             # Airflow API integration
│       └── workflow_*                     # Additional workflow components
│
├── 🤖 src/                                # Core Application Logic
│   ├── agents/                            # AI Processing Pipeline (6 Modules)
│   │   ├── document_processor_agent/      # PDF Extraction & Parsing
│   │   │   └── utility_bill_doc_processor.py
│   │   ├── tariff_analysis_agent/         # Tariff Rule Extraction
│   │   │   ├── pagewise_text_extractor.py
│   │   │   ├── group_extracted_raw_text.py
│   │   │   ├── extract_logic_llm_call.py
│   │   │   ├── prompts_to_extract_logic.py
│   │   │   └── rule_db_loader.py
│   │   ├── audit_calculation_agent/       # Bill Validation & Calculation
│   │   │   ├── calculation_engine.py
│   │   │   └── calc_engine_updated.py
│   │   ├── billing_anomaly_detector_agent/# Overcharge Detection
│   │   │   └── anomaly_detector_llm_call.py
│   │   ├── reporting_generating_agent/    # Report Generation
│   │   │   └── report_generator.py
│   │   └── validation_agent/              # Data Validation
│   │       └── tafiff_defination_validation.py
│   ├── api/                               # FastAPI backend boundary
│   │   ├── main.py                        # API app entrypoint
│   │   └── routers/                       # API route handlers (+ local models)
│   ├── database/                          # Data Layer
│   │   ├── db_utils.py                    # Database utilities
│   │   ├── init_db.py                     # Database initialization
│   │   ├── models.py                      # SQLAlchemy ORM models
│   │   └── utils/                         # Domain-specific DB helpers
│   ├── orchestrator/                      # Airflow Integration
│   │   ├── pipeline_runner.py
│   │   └── workflow_manager.py
│   ├── services/                          # Backend business/use-case logic
│   └── utils/                             # Core Utilities
│       ├── config.py                      # Configuration management
│       ├── data_paths.py                  # Data path constants
│       ├── helpers.py                     # Helper functions
│       ├── logger.py                      # Logging configuration
│       ├── llm_client.py                  # OpenAI LLM client
│       └── aws_app.py                     # AWS S3 integration
│
├── 🌬️ airflow/                            # Apache Airflow Orchestration
│   ├── airflow.cfg                        # Airflow configuration
│   ├── simple_auth_manager_passwords.json # Airflow auth (generated)
│   ├── dags/                              # DAG definitions
│   │   ├── pipeline_runner_dag.py         # Main billing pipeline
│   │   └── tariff_pipeline_dag.py         # Tariff processing pipeline
│   ├── logs/                              # Airflow execution logs
│   │   ├── dag_processor/                 # DAG parsing logs
│   │   └── scheduler/                     # Scheduler logs
│   └── plugins/                           # Custom Airflow plugins
│
├── 📊 data/                               # Data Storage (Local)
│   ├── incoming/                          # Uploaded PDFs (temporary)
│   ├── raw/                               # Raw extracted data
│   ├── processed/                         # Processed results
│   ├── samples/                           # Test/sample files
│   └── output/                            # Generated outputs
│
├── 📚 documentation/                      # Project architecture and guides
│   ├── ARCHITECTURE.md                    # System architecture design
│   ├── DEPLOYMENT.md                      # Local deployment guide
│   ├── PROJECT_OVERVIEW.md                # Project scope and goals
│   ├── AWS_REUSE_SETUP_RUNBOOK.md         # Primary cloud setup runbook
│   ├── TERRAFORM_INFRA_GUIDE.md           # Terraform infrastructure reference
│   └── DEPLOYMENT_PROGRESS_CHECKLIST.md   # Active deployment tracker
│
└── ▶️ run_local_stack.sh                  # Local API + Streamlit launcher
```

---

## 🔄 Complete Data Flow

**USER UPLOADS BILL** → **EXTRACTION** → **TARIFF ANALYSIS** → **VALIDATION** → **REPORTING**

```
USER UPLOADS BILL (customer_oct_2024.pdf)
    ↓
STREAMLIT UI: Upload & Ingest Page
    ↓
AIRFLOW DAG: utility_billing_pipeline (3 Tasks)
    ├─ TASK 1: Extract PDF Data
    ├─ TASK 2: Group Tariffs by Service Class
    └─ TASK 3: Extract Billing Logic (LLM)
    ↓
BILL VALIDATION AGENT
    • Calculates expected charge
    • Compares with actual bill
    • Detects overcharge
    ↓
DATABASE STORAGE (PostgreSQL)
    ↓
USER VIEWS RESULTS (Audit Bills Page)
    ↓
GENERATE REPORT (PDF/CSV export)
```

See [documentation/PROJECT_OVERVIEW.md](documentation/PROJECT_OVERVIEW.md) for detailed workflow examples.

---

## 🚀 Key Features

| Feature | Description | Benefits |
|---------|-------------|----------|
| **📄 Automated PDF Extraction** | PDF parsing with `pdfplumber` + `camelot` | Eliminates manual data entry |
| **⚖️ Tariff Rule Engine** | Rule-based parsing of rate structures | Understands complex billing logic |
| **🔍 Overcharge Detection** | Arithmetic engine: calculated vs actual charges | Identifies billing errors automatically |
| **🧠 LLM API Integration** | OpenAI GPT-4o-mini for tariff parsing & anomaly explanation | Handles complex, unstructured tariff text |
| **📊 Interactive Dashboard** | Streamlit UI with responsive design | Easy-to-use interface |
| **⚡ Airflow Orchestration** | Robust DAG-based pipeline | Scalable, reliable workflow management |
| **💾 PostgreSQL Database** | Persistent data storage | Reliable, queryable data |
| **☁️ AWS S3 Integration** | Cloud file storage | Scalable, secure document management |
| **📋 Report Generation** | Comprehensive audit reports | PDF/CSV export with visualizations |
| **🔐 Authentication** | User login & session management | Secure access control |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit |
| **Backend API** | FastAPI |
| **Orchestration** | Apache Airflow 3.1 |
| **LLM** | OpenAI API (GPT-4o-mini) |
| **Database** | PostgreSQL |
| **File Storage** | AWS S3 |
| **PDF Processing** | pdfplumber, camelot |
| **Containerization** | Docker & Docker Compose |
| **Cloud Infra** | AWS EC2 + Terraform |
| **CI/CD** | GitHub Actions |
| **Authentication** | JWT Tokens |

---

## 📋 Quick Start

### **With Docker (Local)**
```bash
git clone https://github.com/harshalsp0011/utility-billing-ai.git
cd utility-billing-ai
cp .env.example .env
# Edit .env with your AWS & OpenAI credentials
docker compose up -d --build api streamlit
# Access: http://localhost:8501
```

### **Production (AWS EC2 — already deployed)**
- Public URL: `http://3.12.193.9` *(via Nginx on port 80)*
- Infra provisioned via Terraform (`terraform/`)
- See [documentation/AWS_REUSE_SETUP_RUNBOOK.md](documentation/AWS_REUSE_SETUP_RUNBOOK.md) for full setup guide

### **Local Development**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app/streamlit_app.py
```

---

## 📚 Documentation

| File | Purpose |
|------|--------|
| [documentation/PROJECT_OVERVIEW.md](documentation/PROJECT_OVERVIEW.md) | Project purpose, scope, and goals |
| [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md) | System architecture and component design |
| [documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md) | Local development deployment guide |
| [documentation/AWS_REUSE_SETUP_RUNBOOK.md](documentation/AWS_REUSE_SETUP_RUNBOOK.md) | **Primary cloud setup guide** — Terraform + EC2 + Docker deploy |
| [documentation/TERRAFORM_INFRA_GUIDE.md](documentation/TERRAFORM_INFRA_GUIDE.md) | Terraform infrastructure reference |
| [documentation/DEPLOYMENT_PROGRESS_CHECKLIST.md](documentation/DEPLOYMENT_PROGRESS_CHECKLIST.md) | Current deployment progress and pending steps |
| [terraform/README.md](terraform/README.md) | Terraform folder file-by-file breakdown |

---

## 🎓 Project Status

✅ **Production Ready — Deployed on AWS**
- Core extraction pipeline working
- Tariff rule parsing with LLM
- Airflow orchestration (3-task DAG) — optional, disabled in default deploy
- PostgreSQL database setup
- Streamlit UI (6 pages)
- AWS S3 integration
- Authentication system
- Modular AI processing pipeline (6 specialised modules)
- FastAPI backend (REST API layer)
- AWS EC2 provisioned via Terraform (`t3.micro`, `us-east-1`)
- GitHub Actions CI/CD — auto-deploys on merge to `main`

---

## ⚙️ CI/CD — Auto Deploy on Merge to `main`

The workflow file at [.github/workflows/deploy.yml](.github/workflows/deploy.yml) automatically deploys to EC2 every time you merge `dev` → `main`.

### How it works

```
dev branch  ──► pull request ──► merge to main
                                      │
                                      ▼
                            GitHub Actions triggers
                                      │
                                      ▼
                            SSH into EC2 (3.12.193.9)
                                      │
                                      ▼
                      git fetch + git reset --hard origin/main
                                      │
                                      ▼
                  docker compose up -d --build api streamlit
```

### One-time GitHub setup (required before first auto-deploy)

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret** and add these three secrets:

| Secret Name | Value |
|-------------|-------|
| `EC2_HOST` | `3.12.193.9` *(update if IP changes after terraform destroy+apply)* |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Full contents of `~/Desktop/utility-billing-key.pem` |

### What about `.env`?

`.env` is **gitignored** — `git pull` never touches it. It stays on the EC2 server permanently after you copied it there once via `scp`. You only need to update it on the server if you rotate API keys.

### Workflow

| Branch | Purpose | Auto-deploy? |
|--------|---------|-------------|
| `dev` | Development, testing | ❌ No |
| `main` | Production code | ✅ Yes, on every push/merge |

---

## � Docker & Container Architecture

The entire application stack is containerised with **Docker** and orchestrated using **Docker Compose**. This means every service runs inside an isolated, reproducible container — no dependency conflicts, identical behaviour on any machine.

### **Container Services**

| Service | Build Source | Exposed Port | Purpose |
|---------|-------------|-------------|---------|
| `api` | `Dockerfile.api` | `127.0.0.1:8000` (internal only) | FastAPI backend — all AI logic & DB calls |
| `streamlit` | `app/Dockerfile` | Internal only (via Nginx) | Streamlit frontend — user-facing dashboard |
| `nginx` | `nginx:alpine` | `0.0.0.0:80` (public) | Reverse proxy — only public entry point |
| `airflow` | `apache/airflow` | `127.0.0.1:8080` (disabled by default) | Apache Airflow — DAG scheduler (profile-gated) |
| `db` | `postgres:15` | `5432` (internal network only) | PostgreSQL — persistent structured data |

### **Docker Compose Files**

| File | When to Use |
|------|------------|
| `docker-compose.yml` | Base config — services, networks, volumes, health-checks |
| `docker-compose.prod.yml` | Production override — binds API/Airflow to `127.0.0.1` so they are not internet-reachable |

Run locally (both services):
```bash
docker compose up -d --build api streamlit
```

Run with production port binding:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### **Container Networking**

All containers share an internal Docker bridge network. The Streamlit container calls the FastAPI container via `http://api:8000` — the Docker service name `api` resolves automatically inside the network. Neither `api` nor `airflow` are reachable from outside EC2.

```
Internet ──► EC2:80 ──► nginx container
                              │  proxy_pass http://streamlit:8501
                              ▼
                          streamlit container
                              │  http://api:8000
                              ▼
                          api container
                              │  postgres://db:5432
                              ▼
                          db container (PostgreSQL)
```

### **Volumes & Persistent State**

| Volume | Mounted Path | Holds |
|--------|-------------|-------|
| `postgres_data` | `/var/lib/postgresql/data` | All DB records survive container restarts |
| `./data` | `/app/data` | Uploaded PDFs, raw extracts, processed JSON |
| `./airflow/logs` | `/opt/airflow/logs` | Airflow task execution logs |

### **Environment Variables (`.env`)**

`.env` is **never committed to git**. Copy the template and fill in real secrets:

```bash
cp .env.example .env
# Edit .env with real values
```

Key variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI GPT-4o-mini access |
| `DATABASE_URL` | PostgreSQL connection string |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 access (local only — EC2 uses IAM role) |
| `AWS_S3_BUCKET_NAME` | Target S3 bucket name |
| `SECRET_KEY` | JWT token signing secret |
| `AIRFLOW_ADMIN_PASSWORD` | Airflow UI login password |

---

## ☁️ AWS Infrastructure

The production stack runs on **AWS** using a cost-effective single-VM design. No load balancers, no ECS, no NAT gateways — just the minimum required to run a reliable production service.

### **AWS Services Used**

| Service | Role in This Project |
|---------|---------------------|
| **EC2** (`t3.micro`, `us-east-1`) | Single VM that runs all Docker containers (with 2GB swap auto-configured) |
| **Elastic IP** | Static public IP — survives EC2 stop/start (changes only on destroy+recreate) |
| **IAM Role + Instance Profile** | Grants EC2 permission to read/write S3 — no hard-coded AWS keys on server |
| **S3 Bucket** | Stores uploaded bill PDFs, tariff JSONs, and generated audit reports |
| **Security Group** | Firewall — only ports `22` (SSH, your IP only) and `80` (Nginx, public) are open |
| **Lambda** (x2) | Tiny Python functions: one starts EC2, one stops EC2 — triggered by EventBridge |
| **EventBridge** (x2) | Cron scheduler — fires at 9 AM and 6 PM EST Mon–Fri to start/stop EC2 |

### **Security Group Rules**

| Port | Protocol | Source | Reason |
|------|----------|--------|--------|
| `22` | TCP | Your IP only | SSH admin access |
| `80` | TCP | `0.0.0.0/0` | Nginx public access (proxies to Streamlit) |
| `8501` | — | ❌ Blocked | Streamlit internal only (Nginx handles it) |
| `8000` | — | ❌ Blocked | FastAPI internal only |
| `8080` | — | ❌ Blocked | Airflow internal only |

### **IAM Role — How EC2 Accesses S3 Without Keys**

The EC2 instance has an attached **IAM Instance Profile**. The attached role grants `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, and `s3:ListBucket` on the project S3 bucket. Benefits:
- No AWS credentials stored in `.env` on the server
- The application gains S3 access automatically via AWS instance metadata service (IMDS)
- Rotating access: update the IAM policy — no server changes required

### **S3 Bucket Structure**

```
s3://<bucket-name>/
├── uploads/           # Raw bill PDFs uploaded by users
├── tariffs/           # Uploaded tariff PDF documents
├── processed/         # Extracted JSON artifacts
│   ├── raw_extracted_tariff.json
│   ├── grouped_tariffs.json
│   └── final_logic_output.json
└── reports/           # Generated audit reports (PDF / CSV)
```

### **Full AWS Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP port 80 (public)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│           EC2 Instance  ──  Elastic IP: 3.12.193.9               │
│           AMI: Ubuntu 24.04 LTS  |  t3.micro  |  us-east-1      │
│           Disk: 20GB gp3  |  RAM: 1GB  |  Swap: 2GB             │
│           Security Group: port 22 (your IP) + port 80 (public)  │
│           IAM Role ──► S3 read/write (no stored credentials)     │
│                                                                  │
│  ┌─────────────────── Docker Compose Stack ──────────────────┐  │
│  │                                                            │  │
│  │  [nginx :80]  ◄── Only public entry point                 │  │
│  │       │  proxy_pass http://streamlit:8501                  │  │
│  │       ▼                                                    │  │
│  │  [streamlit :8501]  ◄── Internal Docker network only       │  │
│  │       │  http://api:8000                                   │  │
│  │       ▼                                                    │  │
│  │  [api :8000]  ◄── Internal only (127.0.0.1 bound)         │  │
│  │                                                            │  │
│  │  [airflow :8080]  ◄── Disabled by default (profile-gated) │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  IAM Role ─────────────────────────────────────────────────────► │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS S3 Bucket                                  │
│  uploads/   tariffs/   processed/   reports/                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│         EC2 AUTO SCHEDULER (Optional — currently DISABLED)       │
│                    Manual start/stop is active                   │
│                                                                  │
│  EventBridge Scheduler ──► Lambda (ec2-start)                    │
│  "cron(0 9 ? * MON-FRI *)" America/New_York (DST auto-handled)  │
│  = 9:00 AM Mon-Fri New York time  ──► StartInstances             │
│                                                                  │
│  EventBridge Scheduler ──► Lambda (ec2-stop)                     │
│  "cron(0 18 ? * MON-FRI *)" America/New_York (DST auto-handled) │
│  = 6:00 PM Mon-Fri New York time  ──► StopInstances              │
│                                                                  │
│  Cost saving: ~$2-3/month vs ~$8/month running 24/7              │
└─────────────────────────────────────────────────────────────────┘
```

See [documentation/AWS_REUSE_SETUP_RUNBOOK.md](documentation/AWS_REUSE_SETUP_RUNBOOK.md) for the full step-by-step setup guide.

---

## 🔧 Terraform — Infrastructure as Code

All AWS resources are defined as **Terraform code** in the `terraform/` directory. This means the entire cloud environment is version-controlled, peer-reviewable, and fully reproducible — you can recreate it in any AWS account by changing a few variable values.

### **Resources Managed by Terraform**

| Terraform Resource | AWS Service | Purpose |
|-------------------|-------------|---------|
| `aws_instance` | EC2 | Application server (`t3.micro`) |
| `aws_security_group` | Security Group | Firewall — SSH (your IP) + HTTP port 80 |
| `aws_eip` | Elastic IP | Static public IP bound to EC2 |
| `aws_iam_role` | IAM | EC2 service identity |
| `aws_iam_instance_profile` | IAM | Attaches role to EC2 |
| `aws_iam_role_policy` | IAM | S3 access permissions inline policy |
| `aws_lambda_function` (x2) | Lambda | Start + Stop EC2 functions (Python 3.12) |
| `aws_scheduler_schedule` (x2) | EventBridge Scheduler | DST-aware cron — 9 AM start + 6 PM stop (America/New_York) |
| `aws_iam_role` (scheduler invoke) | IAM | EventBridge Scheduler role to invoke Lambda |
| `aws_iam_role` (lambda exec) | IAM | Lambda execution role (EC2 start/stop only) |

### **Terraform File Map**

| File | Purpose |
|------|---------|
| `terraform/main.tf` | Core resources — EC2, SG, EIP, IAM |
| `terraform/scheduler.tf` | EC2 auto start/stop — Lambda + EventBridge crons |
| `terraform/variables.tf` | All input variable declarations with types and defaults |
| `terraform/terraform.tfvars` | Your actual values (gitignored — never commit) |
| `terraform/terraform.tfvars.example` | Safe template to copy for new environments |
| `terraform/outputs.tf` | Prints EC2 IP, instance ID, SSH command, scheduler status |
| `terraform/versions.tf` | Required provider + Terraform version pins |
| `terraform/scripts/bootstrap_docker.sh.tftpl` | EC2 first-boot: 2GB swap + Docker CE install |

### **Key Variables to Fill In**

```hcl
# terraform/terraform.tfvars  (copy from terraform.tfvars.example)
aws_region              = "us-east-1"
ssh_key_name            = "utility-billing-key"
ssh_allowed_cidr        = "YOUR_PUBLIC_IP/32"   # curl https://checkip.amazonaws.com
existing_s3_bucket_name = "your-bucket-name"
instance_type           = "t3.micro"
```

### **Terraform Command Workflow**

```bash
# One-time: install tools
brew install awscli terraform

# Authenticate to AWS
aws configure                  # enter Access Key, Secret, region (us-east-1), json
aws sts get-caller-identity    # verify — should return your account ARN

# Infrastructure lifecycle
cd terraform
terraform init                 # download AWS provider plugin (run once per machine)
terraform plan                 # preview changes — safe, no resources created yet
terraform apply                # create/update infrastructure in AWS
terraform destroy              # tear down everything (use with caution!)
```

> **Idempotent**: Running `terraform apply` multiple times is safe — Terraform only changes what differs from current real state.

> **State file**: `terraform.tfstate` is gitignored. It maps Terraform config to real AWS resource IDs. For team use, migrate state to an S3 backend.

See [documentation/TERRAFORM_INFRA_GUIDE.md](documentation/TERRAFORM_INFRA_GUIDE.md) for the full infrastructure reference.

---

## 🧠 LLM API Integration

This project makes **direct OpenAI GPT-4o-mini API calls** at two specific pipeline steps — tariff rule extraction and anomaly explanation. The remaining 4 modules are rule-based Python with no LLM involvement.

### **Where LLM API Calls Are Made**

| Module | File | LLM Task |
|--------|------|---------|
| **Tariff Analysis Module** | `extract_logic_llm_call.py` | Single API call: reads grouped tariff text → returns structured billing rules (tier thresholds, multipliers, conditions) as JSON |
| **Anomaly Detector Module** | `anomaly_detector_llm_call.py` | Single API call: analyses charge discrepancy → returns plain-English explanation of the overcharge cause |

### **LLM Client (`src/utils/llm_client.py`)**

All LLM API calls go through a single shared client that handles:
- OpenAI Python SDK initialisation (`OPENAI_API_KEY` from `.env`)
- Model selection — `gpt-4o-mini` by default (cost-efficient)
- `max_tokens` and `temperature` configured per call type
- Error handling and retry logic for transient API failures

```python
# Usage pattern in pipeline modules
from src.utils.llm_client import LLMClient

client = LLMClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
response = client.call(
    system_prompt="You are a utility billing expert...",
    user_prompt=raw_tariff_text,
    response_format="json"
)
```

> **Important**: Each LLM-integrated module makes a single, one-shot API call per input. There is no autonomous reasoning loop, no tool use by the LLM, and no inter-module communication driven by the LLM. The LLM is used purely as a **smart text parser** at two fixed pipeline steps.

### **Prompt Engineering Strategy**

| Principle | How Applied |
|-----------|------------|
| **Domain system role** | Each agent sets a specific system prompt (e.g. "You are a utility tariff analyst specialising in rate structures") |
| **Structured JSON output** | Prompts explicitly request JSON matching a defined schema — makes LLM output directly parseable |
| **Context injection** | Raw PDF-extracted text or tariff JSON is passed as the user message for each call |
| **Temperature = 0** | Used for calculation-critical extraction tasks to get deterministic output |
| **Slight temperature** | Used for anomaly explanation summaries to allow natural phrasing |
| **Few-shot examples** | Tariff extraction prompts include annotated input → output examples to guide the model |

### **Model Choice: GPT-4o-mini**

| Factor | Reasoning |
|--------|-----------|
| **Cost** | ~15× cheaper than `gpt-4o` per token — critical for per-bill processing economics |
| **Accuracy** | Sufficient for structured extraction from well-formed tariff text |
| **Speed** | Faster latency — important for interactive audit workflows |
| **Upgrade path** | Change one variable in `llm_client.py` to switch to `gpt-4o` or any future model |

### **API Key Security**

- `OPENAI_API_KEY` stored only in `.env` — never hard-coded, never committed to git
- Loaded via `python-dotenv` at runtime
- On the EC2 server, `.env` is placed once via `scp` — CI/CD never touches it
- AWS S3 access uses IAM role on EC2 — no AWS keys stored on the server at all

---

## ⏰ EC2 Manual Start / Stop + Auto Scheduler

The EC2 instance can be started and stopped **manually anytime** from your terminal.
An optional **auto-scheduler** (EventBridge + Lambda) can start/stop it automatically on weekday office hours — currently **DISABLED** (manual mode active).

---

### 🖐️ Manual Start / Stop (Use These Daily)

**Prerequisites — one-time setup:**
```bash
# Install AWS CLI (if not already installed)
brew install awscli

# Configure credentials (one-time only)
aws configure
# Enter: Access Key ID, Secret Access Key, region = us-east-1, output = json

# Verify it works
aws sts get-caller-identity
```

**Start EC2 (app will be live in ~60 seconds):**
```bash
aws ec2 start-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd
```

**Stop EC2 (saves cost — IP and data preserved):**
```bash
aws ec2 stop-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd
```

**Check if EC2 is running:**
```bash
aws ec2 describe-instances \
  --region us-east-1 \
  --instance-ids i-06ebc19f707862bdd \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text
```

> ✅ After starting, open **`http://3.12.193.9`** — app is live once containers boot (~60 sec).

---

### 🔄 What Happens When You Stop / Start

| Item | When Stopped | When Started Again |
|------|-------------|-------------------|
| EC2 Instance | Stopped (NOT terminated) | Starts fresh |
| Elastic IP (`3.12.193.9`) | **Kept** — reserved for you | **Same IP** ✅ |
| Disk / repo / `.env` | **Kept** — disk preserved | **Same files** ✅ |
| Docker containers | Stopped gracefully | **Auto-restart** (`restart: unless-stopped`) ✅ |
| Database data | **Kept** — lives on disk | **Same data** ✅ |
| App URL | Offline (connection refused) | Back at `http://3.12.193.9` ✅ |

---

### 🤖 Auto Scheduler (Currently DISABLED — Optional)

The scheduler uses **AWS EventBridge Scheduler + Lambda** to auto start/stop EC2 on office hours.
Timezone: `America/New_York` — **DST handled automatically** (no UTC math, no manual adjustment ever).

**Schedule when enabled:** Start 9:00 AM Mon–Fri | Stop 6:00 PM Mon–Fri (New York time)

**Enable auto-scheduler (will start/stop automatically):**
```bash
aws scheduler update-schedule \
  --region us-east-1 \
  --name utility-billing-ai-prod-ec2-start \
  --state ENABLED \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule \
  --region us-east-1 \
  --name utility-billing-ai-prod-ec2-stop \
  --state ENABLED \
  --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role
```

**Disable auto-scheduler (go back to manual control):**
```bash
aws scheduler update-schedule \
  --region us-east-1 \
  --name utility-billing-ai-prod-ec2-start \
  --state DISABLED \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule \
  --region us-east-1 \
  --name utility-billing-ai-prod-ec2-stop \
  --state DISABLED \
  --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role
```

**Check scheduler status:**
```bash
aws scheduler get-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --query '{State: State, Schedule: ScheduleExpression, Timezone: ScheduleExpressionTimezone}' \
  --output table
```

**Change schedule time (e.g. 8 AM start):**
```hcl
# In terraform/terraform.tfvars:
ec2_start_cron_local = "cron(0 8 ? * MON-FRI *)"   # 8 AM New York time
ec2_stop_cron_local  = "cron(0 18 ? * MON-FRI *)"  # 6 PM New York time
```
Then: `cd terraform && terraform apply`

**Remove scheduler entirely from AWS:**
```hcl
# In terraform/terraform.tfvars:
enable_ec2_scheduler = false
```
Then: `cd terraform && terraform apply`

### **Cost Comparison**

| Scenario | Hours/month | Approx Cost |
|----------|-------------|-------------|
| 24/7 running | 720 hrs | ~$8/month |
| Office hours (9AM–6PM, Mon–Fri) | ~195 hrs | ~$2–3/month |
| **Saving** | | **~$5–6/month (~65% cheaper)** |

> Elastic IP costs ~$0.005/hr when EC2 is stopped — about $0.70/month. Still much cheaper than running 24/7.

---

## 🗂️ Operations Cheatsheet

### 🖐️ EC2 Start / Stop (Daily Use)

```bash
# ── START EC2 (app live in ~60 sec) ──────────────────────────────────────────
aws ec2 start-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd

# ── STOP EC2 (saves cost — IP + data kept) ───────────────────────────────────
aws ec2 stop-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd

# ── Check EC2 state (running / stopped / pending) ────────────────────────────
aws ec2 describe-instances \
  --region us-east-1 \
  --instance-ids i-06ebc19f707862bdd \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text

# ── Get current public IP ────────────────────────────────────────────────────
aws ec2 describe-instances \
  --region us-east-1 \
  --instance-ids i-06ebc19f707862bdd \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text
```

### 🔄 Scheduler Control (Enable / Disable Auto Start-Stop)

```bash
# ── ENABLE auto-scheduler (9 AM start, 6 PM stop, Mon–Fri, NY time) ──────────
aws scheduler update-schedule \
  --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --state ENABLED \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule \
  --region us-east-1 --name utility-billing-ai-prod-ec2-stop \
  --state ENABLED \
  --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

# ── DISABLE auto-scheduler (go back to manual control) ───────────────────────
aws scheduler update-schedule \
  --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --state DISABLED \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule \
  --region us-east-1 --name utility-billing-ai-prod-ec2-stop \
  --state DISABLED \
  --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

# ── Check scheduler status ────────────────────────────────────────────────────
aws scheduler get-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --query '{State: State, Schedule: ScheduleExpression, Timezone: ScheduleExpressionTimezone}' \
  --output table
```

### 🔒 SSH & Docker

```bash
# ── SSH into EC2 ─────────────────────────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9

# ── Check all containers are running ─────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9 \
  "cd ~/utility-billing-ai && docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"

# ── Start all services manually (if containers stopped) ──────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9 \
  "cd ~/utility-billing-ai && \
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
   up -d api streamlit nginx"

# ── View live logs ────────────────────────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9 \
  "cd ~/utility-billing-ai && docker compose logs -f --tail=50"

# ── API health check ──────────────────────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9 \
  "curl -sS http://127.0.0.1:8000/api/v1/health/live"

# ── Check memory and swap ─────────────────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@3.12.193.9 "free -h"
```

### 🏗️ Terraform

```bash
cd terraform

# ── Preview changes (safe — no resources touched) ────────────────────────────
terraform plan

# ── Apply changes ─────────────────────────────────────────────────────────────
terraform apply

# ── Check current outputs (IP, instance ID, scheduler status) ─────────────────
terraform output

# ── Destroy everything (WARNING: IP will change on next apply) ────────────────
terraform destroy
```

---

## 📞 Support

- 📧 Email: harshal.sanjivpatil2000@gmail.com
- 🐙 GitHub: [harshalsp0011/utility-billing-ai](https://github.com/harshalsp0011/utility-billing-ai)

---

**Last Updated**: March 19, 2026 | **Version**: 1.5.0 | **Status**: ✅ Production Ready — AWS EC2 @ http://3.12.193.9 | Scheduler: DISABLED (manual start/stop active)

<div align="center">

Made with ❤️ by the Utility Billing AI Team

⭐ If you find this helpful, give it a star!

</div>
