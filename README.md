# 🏢 The Agentic Auditor - Utility Billing AI ⚡📄💰

**An intelligent, multi-agent AI system for automating utility bill auditing, tariff analysis, and overcharge detection.**

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

This system leverages a **Multi-Agent Architecture** with **LLM-powered intelligent components** orchestrated by **Apache Airflow**, making it enterprise-ready and scalable.

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
│    AGENTIC CORE (Multi-Agent System)                    │
│                                                         │
│  1️⃣  Document Processor Agent                           │
│      └─ PDF text extraction (pdfplumber)                │
│      └─ Table extraction (camelot)                      │
│      └─ Data validation                                 │
│                                                         │
│  2️⃣  Tariff Analyzer Agent                              │
│      └─ Parse Service Classification (SC) documents     │
│      └─ Extract rate structures                         │
│      └─ Group tariffs by service class                  │
│                                                         │
│  3️⃣  Logic Extractor Agent (LLM)                        │
│      └─ OpenAI GPT-4o-mini analysis                     │
│      └─ Understanding billing rules                     │
│      └─ Structured rule output                          │
│                                                         │
│  4️⃣  Bill Validator Agent                               │
│      └─ Compare calculated vs actual charges            │
│      └─ Detect overcharges                              │
│      └─ Threshold-based anomaly detection               │
│                                                         │
│  5️⃣  Error Detector Agent                               │
│      └─ Validate data completeness                      │
│      └─ Flag missing/invalid fields                     │
│      └─ Consistency checks                              │
│                                                         │
│  6️⃣  Report Generator Agent                             │
│      └─ Create audit reports                            │
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
│   ├── agents/                            # Multi-Agent System (6 Agents)
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
| **📄 Automated PDF Extraction** | AI-powered extraction of bill data from PDFs | Eliminates manual data entry |
| **⚖️ Tariff Rule Engine** | Intelligent parsing of rate structures | Understands complex billing logic |
| **🔍 Overcharge Detection** | Calculates expected vs actual charges | Identifies billing errors automatically |
| **🧠 LLM-Powered Analysis** | Uses OpenAI GPT for intelligent processing | Handles complex, unstructured data |
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
- Public URL: `http://98.89.240.117:8501`
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
- Multi-agent architecture
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
                            SSH into EC2 (98.89.240.117)
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
| `EC2_HOST` | `98.89.240.117` |
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

## 📞 Support

- 📧 Email: support@agentic-auditor.com
- 🐙 GitHub: [harshalsp0011/utility-billing-ai](https://github.com/harshalsp0011/utility-billing-ai)

---

**Last Updated**: March 13, 2026 | **Version**: 1.1.0 | **Status**: ✅ Production Ready — AWS EC2 Live

<div align="center">

Made with ❤️ by the Utility Billing AI Team

⭐ If you find this helpful, give it a star!

</div>
