# Technology Stack - Utility Billing AI

## Overview
This document outlines all technologies, platforms, and services used in the Utility Billing AI project, organized by category.

---

## 🏗️ **Infrastructure & Orchestration**

### Apache Airflow
- **Version**: 3.1.0
- **Purpose**: Workflow orchestration and DAG management
- **Packages**: 
  - `apache-airflow==3.1.0`
  - `apache-airflow-core==3.1.0`
  - `apache-airflow-providers-standard==1.9.0`
  - `apache-airflow-providers-common-sql==1.28.1`
  - `apache-airflow-task-sdk==1.1.0`
- **DAGs**:
  - `utility_billing_pipeline` - Main billing extraction and validation (3 tasks)
  - `tariff_pipeline_dag` - Tariff document processing
  - `test_dag` - Test/example DAG
- **Features**:
  - REST API v2 with JWT authentication
  - PythonOperator for task execution
  - DAG-based pipeline orchestration
  - Task status monitoring and logging

### Docker & Docker Compose
- **Base Image**: `apache/airflow:2.10.2` (can be upgraded to 3.x)
- **Purpose**: Containerization for consistent deployment
- **Services**:
  - Airflow container
  - PostgreSQL database container
  - Streamlit application container

---

## 🗄️ **Database & ORM**

### PostgreSQL
- **Version**: 14+
- **Purpose**: Primary relational database for production
- **Deployment**: AWS RDS (cluster-based)
- **Connection**: psycopg2 driver
- **Tables**:
  - `raw_documents` - Uploaded bill/tariff document metadata
  - `pipeline_runs` - Airflow DAG execution tracking
  - `user_bills` - Extracted bill data
  - `bill_validation_results` - Error detection and validation findings
  - `tariff_documents` - Tariff source PDFs
  - `tariff_logic_versions` - Tariff calculation rules by service class
  - `logs` - Application audit logs

### SQLAlchemy
- **Version**: Latest (via Flask-SQLAlchemy 3.0.5)
- **Purpose**: ORM for database abstraction
- **Usage**:
  - Model definitions (UserBills, BillValidationResult, TariffLogicVersions)
  - Session-based query execution
  - Relationship management between tables

### Alembic
- **Version**: 1.17.0
- **Purpose**: Database migration management
- **Usage**: Schema version control and evolution

---


## ☁️ **Cloud Services**

### AWS S3 (Simple Storage Service)
- **Packages**: 
  - `boto3==1.42.3`
  - `botocore==1.42.3`
- **Purpose**: File storage for processed documents
- **Storage Structure**:
  - `processed/` - Output files (grouped_tariffs.json, final_logic_output.json, raw_extracted_tarif.json)
  - `raw/` - Input files
  - `samples/` - Sample documents
- **Operations**: Upload/Download JSON, validate S3 objects
- **Credentials**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (from environment)

### AWS RDS (Relational Database Service)
- **Purpose**: Managed PostgreSQL database hosting
- **Region**: us-east-1
- **Host**: c57oa7dm3pc281.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com
- **Benefits**: Automatic backups, scaling, failover

---

## 🎨 **Frontend & UI**

### Streamlit
- **Version**: 1.51.0 (Latest)
- **Purpose**: Interactive web UI for the application
- **Packages**: streamlit==1.51.0
- **Features**:
  - Session state management
  - Multi-page routing
  - Component-based architecture
  - Secrets management for cloud deployment
- **Pages**:
  - Home Dashboard
  - Upload & Ingest
  - Audit Bills
  - Manage Tariffs
  - Pipeline Status (Coming Soon)
  - Generate Reports
  - Upload History

### Streamlit Cloud
- **Purpose**: Deployment platform for Streamlit apps
- **Secrets Management**: TOML-based configuration in `.streamlit/secrets.toml`
- **Authentication**: Login system with session control
- **Automatic Reloading**: Changes to secrets take effect immediately without redeployment

---

## 🤖 **AI/ML & LLM**

### OpenAI API
- **Packages**: `openai==2.7.1`
- **Model**: `gpt-4.1-mini` (or `gpt-4o-mini`)
- **Purpose**: LLM-based tariff logic extraction
- **Usage**:
  - Extract tariff rules from documents
  - Process natural language service classifications
  - Generate structured tariff definitions
- **Authentication**: OPENAI_API_KEY (from environment)

### LangChain
- **Packages**:
  - `langchain==1.0.5`
  - `langchain-core==1.0.4`
  - `langchain-openai==1.0.2`
  - `langgraph==1.0.2`
  - `langsmith==0.4.42`
- **Purpose**: LLM framework and prompt management
- **Features**:
  - Chain orchestration
  - Prompt templates
  - Vector operations
  - Agent workflows

### Anthropic
- **Packages**: `anthropic==0.72.1`
- **Purpose**: Alternative LLM provider support

---

## 📄 **Document Processing**

### PDF Processing
- **Packages**:
  - `pdfplumber` - PDF text extraction
  - `camelot` - Table extraction from PDFs
  - `openpyxl==3.1.5` - Excel file handling
- **Purpose**: Extract text and tables from utility bill PDFs

### spaCy
- **Packages**: `spacy` (via various NLP dependencies)
- **Purpose**: Natural language processing for text parsing
- **Sub-packages**:
  - `spacy` - Core NLP
  - `murmurhash==1.0.13` - Hashing
  - `catalogue==2.0.10` - Registry system

---

## 🛠️ **Core Dependencies**

### Web Frameworks
- **FastAPI**: `fastapi==0.119.0` - High-performance web framework
- **Flask**: `Flask==2.2.5` - Lightweight web framework (used by Airflow)
- **Flask-SQLAlchemy**: `Flask-SQLAlchemy==3.0.5` - Flask ORM integration
- **Flask-AppBuilder**: `Flask-AppBuilder==5.0.0` - Admin interface builder

### API & Serialization
- **Pydantic**: Core data validation
  - `pydantic==2.x`
  - `pydantic-settings`
  - `pydantic-extra-types`
- **JSON Processing**:
  - `jsonschema==4.25.1`
  - `jsonpatch==1.33`
  - `jiter==0.12.0`
- **msgspec**: `msgspec==0.19.0` - Fast serialization

### HTTP & Networking
- **Packages**:
  - `requests` - HTTP requests
  - `httpx==0.28.1` - Async HTTP client
  - `aiohttp==3.9.1` - Async HTTP
  - `urllib3` - Low-level HTTP

### Data Processing & Analytics
- **Packages**:
  - `pandas` - DataFrames
  - `numpy==2.2.6` - Numerical computing
  - `pyarrow` - Arrow data format
  - `polars` - DataFrames (via narwhals)
  - `narwhals==2.8.0` - DataFrame abstraction

### Environment & Configuration
- **python-dotenv**: `python-dotenv` - Load .env files
- **ConfigUpdater**: `ConfigUpdater==3.2` - INI file management

---

## 🔐 **Authentication & Security**

### JWT (JSON Web Tokens)
- **Packages**: `Flask-JWT-Extended==4.6.0`
- **Purpose**: Token-based authentication for Airflow API
- **Usage**: Secure Airflow REST API calls

### Cryptography
- **Packages**:
  - `cryptography==42.0.8` - Encryption/decryption
  - `bcrypt` - Password hashing
  - `PyJWT` - JWT handling

### Session Management
- **Packages**: `Flask-Session==0.8.0`
- **Purpose**: Server-side session management
- **Streamlit**: Built-in session_state

---

## 📊 **Data Validation & Serialization**

### Marshmallow
- **Packages**:
  - `marshmallow==3.20.2` - Object serialization
  - `marshmallow-sqlalchemy==0.26.1` - ORM integration
  - `marshmallow-oneofschema==3.0.1` - Schema validation

### Validation Frameworks
- **Packages**:
  - `email-validator==2.3.0` - Email validation
  - `python-multipart` - Form parsing

---

## 🔄 **Async & Concurrency**

### Packages
- `asyncio` - Python async support
- `aiosmtplib==4.0.2` - Async SMTP
- `aiosqlite==0.21.0` - Async SQLite
- `aiohttp==3.9.1` - Async HTTP
- `greenlet==3.2.4` - Lightweight threading
- `gevent` - Coroutine library

---

## 📝 **Logging & Monitoring**

### Logging
- **colorlog**: `colorlog==6.9.0` - Colored terminal output
- **OpenTelemetry**:
  - `opentelemetry-api==1.37.0`
  - `opentelemetry-exporter-otlp==1.37.0`
  - `opentelemetry-exporter-otlp-proto-common==1.37.0`

### Instrumentation
- **Packages**:
  - `inflection==0.5.1` - String transformations
  - `docstring_parser==0.17.0` - Parse docstrings

---

## 📦 **Development & Testing**

### Testing
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting

### Code Quality
- **docutils==0.20.1** - Documentation utilities
- **typing-extensions** - Advanced type hints

### Jupyter & Interactive Development
- **Packages**:
  - `jupyter_client==8.6.3`
  - `jupyter_core==5.9.1`
  - `ipykernel==7.1.0` - Jupyter kernel
  - `ipython==8.37.0` - Interactive shell
  - `jedi==0.19.2` - Code completion

### Utilities
- **click==8.2.1** - CLI framework
- **rich** - Terminal formatting
- **tqdm** - Progress bars

---

## 🔌 **Special Integrations**

### Scheduling
- **croniter==6.0.0** - Cron expression parsing
- **cron_descriptor==2.0.6** - Human-readable cron

### API Specification
- **apispec==6.4.0** - API spec generation
- **connexion==2.14.2** - OpenAPI framework

### Markdown & Documentation
- **Markdown==3.5.2** - Markdown parsing
- **markdown-it-py==3.0.0` - JS markdown
- **linkify-it-py==2.0.3` - Link detection

---

## 📋 **Deployment & Servers**

### WSGI Servers
- **gunicorn==21.2.0** - Production WSGI server
- **a2wsgi==1.10.10** - ASGI to WSGI adapter

### Flask Extensions
- **Flask-Babel==4.0.0** - Internationalization
- **Flask-Login==0.6.3** - User session management
- **Flask-Limiter==3.5.0** - Rate limiting
- **Flask-WTF==1.2.1** - Form handling
- **Flask-Caching==2.1.0** - Caching support

---

## 🗺️ **System Dependencies**

### OS-Level Packages
- `psycopg2-binary` - PostgreSQL driver (binary)
- `libpq` - PostgreSQL client library

### Utilities
- **distro==1.9.0** - Linux distribution detection
- **platformdirs** - Platform-specific paths
- **tzdata** - Timezone database
- **certifi==2025.10.5** - SSL certificates

---

## 📊 **Data Visualization**

### Packages
- **Dash==3.2.0** - Interactive dashboards
- **Altair==5.5.0** - Declarative visualization
- **matplotlib-inline==0.2.1** - Inline plots
- **plotly** (via Dash)

---

## 🌐 **Miscellaneous**

### Utilities
- **dill==0.4.0** - Extended pickling
- **disabling-streamlit-logger** - Suppress logs
- **cloudpathlib==0.23.0** - Cloud path abstraction
- **fsspec==2025.9.0** - Filesystem abstraction

---

## 📋 **Summary Table**

| Category | Key Technologies |
|----------|------------------|
| **Orchestration** | Apache Airflow 3.1.0 |
| **Database** | PostgreSQL 14 (AWS RDS) |
| **Cloud Storage** | AWS S3 (boto3) |
| **Frontend** | Streamlit |
| **LLM** | OpenAI API (gpt-4o-mini), LangChain |
| **PDF Processing** | pdfplumber, camelot |
| **Backend** | FastAPI, Flask |
| **ORM** | SQLAlchemy |
| **Authentication** | JWT (Flask-JWT-Extended) |
| **Container** | Docker & Docker Compose |
| **Data Processing** | pandas, numpy, polars |
| **NLP** | spaCy, LangChain |
| **Async** | asyncio, aiohttp, greenlet |
| **Deployment** | Streamlit Cloud, AWS |

---

## 🚀 **Deployment Environments**

1. **Local Development**: Docker Compose (PostgreSQL + Airflow + Streamlit)
2. **Streamlit Cloud**: Cloud-hosted Streamlit with Secrets management
3. **Airflow Standalone**: Single-machine Airflow instance
4. **AWS**: RDS for database, S3 for storage

---

## 🔧 **Industry Standard Stack**

This tech stack follows industry best practices:
- **Microservices**: Airflow DAGs + API layers
- **Cloud-Native**: AWS S3, RDS, containerized deployment
- **Modern Python**: FastAPI, Pydantic, async support
- **Enterprise Authentication**: JWT tokens
- **Scalable Data Processing**: pandas, polars, SQLAlchemy
- **AI-Ready**: OpenAI integration, LangChain for LLM workflows

---

**Last Updated**: December 2025
**Project**: Utility Billing AI Audit System
