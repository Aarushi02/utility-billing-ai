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
├── 📄 PROJECT_OVERVIEW.md                 # Detailed project documentation
├── 📦 requirements.txt                    # Python dependencies
├── 🐋 docker-compose.yml                  # Container orchestration
├── 🔧 .env.example                        # Environment variables template
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
│   ├── database/                          # Data Layer
│   │   ├── db_utils.py                    # Database utilities
│   │   ├── init_db.py                     # Database initialization
│   │   └── models.py                      # SQLAlchemy ORM models
│   ├── orchestrator/                      # Airflow Integration
│   │   ├── pipeline_runner.py
│   │   └── workflow_manager.py
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
│   │   ├── utility_billing_dag.py         # Main billing pipeline (3 tasks)
│   │   ├── tariff_pipeline_dag.py         # Tariff processing pipeline
│   │   └── test_dag.py                    # Test/example DAG
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
├── 📔 notebooks/                          # Jupyter Notebooks
│   ├── exploration/                       # Data exploration notebooks
│   └── testing/                           # Testing & debugging notebooks
│
└── ✅ tests/                              # Unit & Integration Tests
    ├── test_db_connection.py
    ├── test_parser_logic.py
    └── test_error_detection.py
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

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for detailed workflow examples.

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
| **Orchestration** | Apache Airflow 3.1 |
| **LLM** | OpenAI API (GPT-4o-mini) |
| **Database** | PostgreSQL (AWS RDS) |
| **File Storage** | AWS S3 |
| **PDF Processing** | pdfplumber, camelot |
| **Containerization** | Docker & Docker Compose |
| **Authentication** | JWT Tokens |

---

## 📋 Quick Start

### **With Docker**
```bash
git clone https://github.com/harshalsp0011/utility-billing-ai.git
cd utility-billing-ai
cp .env.example .env
# Edit .env with your AWS & OpenAI credentials
docker-compose up -d
# Access: http://localhost:8501
```

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

- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - Complete technical documentation
- **[Airflow Documentation](https://airflow.apache.org/)**
- **[Streamlit Docs](https://docs.streamlit.io/)**
- **[OpenAI API](https://platform.openai.com/docs)**

---

## 🎓 Project Status

✅ **Production Ready**
- Core extraction pipeline working
- Tariff rule parsing with LLM
- Airflow orchestration (3-task DAG)
- PostgreSQL database setup
- Streamlit UI (6 pages)
- AWS S3 integration
- Authentication system
- Multi-agent architecture

---

## 📞 Support

- 📧 Email: support@agentic-auditor.com
- 🐙 GitHub: [harshalsp0011/utility-billing-ai](https://github.com/harshalsp0011/utility-billing-ai)

---

**Last Updated**: December 7, 2025 | **Version**: 1.0.0 | **Status**: ✅ Production Ready

<div align="center">

Made with ❤️ by the Utility Billing AI Team

⭐ If you find this helpful, give it a star!

</div>
