# 🔍 Utility Billing AI - Project Overview & Flow

## **What is This Project?**

**Utility Billing AI** is an **intelligent automated system** that audits utility bills (electricity, gas, water) to detect billing errors and overcharges. It uses AI/LLM technology to:
- Extract data from complex PDF utility bills
- Parse tariff documents to understand billing rules
- Calculate what customers *should* be charged
- Compare against what they were *actually* charged
- Flag discrepancies and overcharges

---

## 📊 **Project Purpose & Use Case**

### Problem It Solves:
- **Manual auditing is tedious**: Utility bills are complex with multiple rate tiers, surcharges, taxes
- **Human error-prone**: Easy to miss small discrepancies across many bills
- **Time-consuming**: Manually checking one bill can take hours
- **Businesses lose money**: Overcharges often go unnoticed

### Solution:
- **Automated extraction** of bill data from PDFs
- **LLM-powered** understanding of tariff rules and billing logic
- **Automated comparison** of calculated vs. actual charges
- **Reports** showing exactly where overcharges occurred

---

## 🎯 **Key Features**

| Feature | What It Does |
|---------|-------------|
| **📄 PDF Bill Extraction** | Reads utility bills (PDFs), extracts account number, consumption, charges, dates |
| **⚖️ Tariff Rule Engine** | Parses tariff documents to understand rate structures and billing formulas |
| **🔢 Automatic Calculation** | Recalculates what customer should pay based on official tariffs |
| **🔍 Overcharge Detection** | Compares calculated amount vs. actual bill amount |
| **📊 Interactive Dashboard** | Streamlit UI to upload bills, view results, manage tariffs |
| **⚡ Workflow Automation** | Airflow orchestrates the entire pipeline |
| **💾 Data Persistence** | PostgreSQL stores all bills, tariffs, and audit results |
| **☁️ Cloud Integration** | AWS S3 for file storage, RDS for database |

---

## 🔄 **Complete Data Flow**

### **Step 1: Upload & Ingest** 📤
```
User uploads a Utility Bill (PDF)
    ↓
File stored in system
    ↓
Data extracted and logged in database
```

### **Step 2: PDF Extraction** 📄
```
Raw PDF Bill
    ↓
Page-by-page text extraction (pdfplumber)
    ↓
Table extraction (camelot)
    ↓
Structured JSON with all bill data
    ↓
Upload to AWS S3 (raw_extracted_tarif.json)
```

### **Step 3: Tariff Analysis** ⚖️
```
Tariff Rules Document (SC - Service Classification)
    ↓
Group tariffs by Service Class (SC code)
    ↓
Structure rules (rates, tiers, surcharges)
    ↓
Use OpenAI LLM to extract billing logic
    ↓
JSON output: rates for each tier (grouped_tariffs.json)
    ↓
Upload to AWS S3 (grouped_tariffs.json)
```

### **Step 4: Logic Extraction** 🤖
```
Grouped Tariff Rules + Bill Data
    ↓
LLM (GPT-4o-mini) analyzes and extracts tariff logic
    ↓
Output: final_logic_output.json with structured rules
    ↓
Store in PostgreSQL database
    ↓
Upload to AWS S3
```

### **Step 5: Bill Validation** ✅
```
Bill Data + Extracted Tariff Logic
    ↓
Recalculate: Expected Amount = usage × rates from tariff
    ↓
Compare: Expected Amount vs. Actual Amount
    ↓
Flag discrepancies > threshold
    ↓
Store validation results in database
```

### **Step 6: Generate Reports** 📋
```
Validation Results
    ↓
Create audit reports showing:
  - Bill details
  - Calculated amount
  - Actual amount
  - Overcharge amount
  - Error reasons
```

---

## 🎮 **User Interface Pages** (Streamlit App)

### **1. 📤 Upload & Ingest**
- Upload utility bill PDFs
- Extract text/data automatically
- Preview extracted data
- Store in database and S3

### **2. 🔍 Audit Bills**
- View all uploaded bills
- See extracted bill information
- Check validation results
- View calculated vs. actual amounts
- Identify overcharges

### **3. ⚖️ Manage Tariffs**
- Upload tariff documents (SC documents)
- View extracted tariff rules
- Manage rate structures
- Test tariff logic

### **4. ⚡ Execute Pipeline**
- Trigger Airflow DAG manually
- Monitor job execution
- View task progress
- Debug errors

### **5. 📊 Pipeline Status**
- Real-time monitoring of running DAGs
- Task status (running, success, failed)
- Task logs and error messages
- Execution timeline

### **6. 📋 Generate Reports**
- Create audit reports
- Export as PDF/CSV
- Summary statistics
- Overcharge details

### **7. 📑 Upload History**
- View all uploaded files
- Track processing status
- Reprocess files
- Download results

---

## 🏗️ **System Architecture Layers**

```
┌─────────────────────────────────────────┐
│     FRONTEND (Streamlit UI)             │
│  - Login/Authentication                 │
│  - File upload interface                │
│  - Bill viewer                          │
│  - Report generator                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────v──────────────────────────┐
│    ORCHESTRATOR (Apache Airflow 3.1)    │
│  - tariff_pipeline DAG                  │
│  - Task dependencies (3 sequential)     │
│  - REST API for triggering              │
└──────────────┬──────────────────────────┘
               │
┌──────────────v──────────────────────────┐
│   AGENTIC CORE (src/agents/)            │
│                                         │
│  1. Document Processor                  │
│     - pagewise_text_extractor.py        │
│     - Extract text from PDFs            │
│                                         │
│  2. Tariff Analyzer                     │
│     - group_extracted_raw_text.py       │
│     - Extract tariff rules              │
│                                         │
│  3. Logic Extractor (LLM)               │
│     - extract_logic_llm_call.py         │
│     - Use OpenAI to understand rules    │
│                                         │
│  4. Bill Validator                      │
│     - Compare calculated vs. actual     │
│     - Detect overcharges                │
│                                         │
│  5. Error Detector                      │
│     - Flag anomalies                    │
│     - Validate thresholds               │
└──────────────┬──────────────────────────┘
               │
┌──────────────v──────────────────────────┐
│        DATA LAYER                       │
│                                         │
│  Database (PostgreSQL RDS)              │
│  - user_bills                           │
│  - bill_validation_result               │
│  - tariff_logic_versions                │
│                                         │
│  File Storage (AWS S3)                  │
│  - raw_extracted_tarif.json             │
│  - grouped_tariffs.json                 │
│  - final_logic_output.json              │
└─────────────────────────────────────────┘
```

---

## 🔌 **Technology Stack Summary**

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit |
| **Orchestration** | Apache Airflow 3.1.0 |
| **Database** | PostgreSQL (AWS RDS) |
| **File Storage** | AWS S3 |
| **LLM** | OpenAI API (gpt-4o-mini) |
| **PDF Extraction** | pdfplumber, camelot |
| **ORM** | SQLAlchemy |
| **Backend Logic** | Python (FastAPI, Flask) |
| **Containerization** | Docker & Docker Compose |
| **Authentication** | JWT tokens |

---

## 🚀 **Complete Workflow Example**

### **Scenario: Audit a customer's electricity bill**

```
1. USER UPLOADS BILL
   File: customer_oct_2024.pdf
   ↓
2. STREAMLIT UI (Upload & Ingest page)
   - User clicks "Upload Bill"
   - PDF stored in AWS S3
   ↓
3. AIRFLOW DAG TRIGGERED (tariff_pipeline)
   ├─ Task 1: Extract Text from PDF
   │  - Read PDF page by page
   │  - Extract account #, usage, charges
   │  - Save to S3: raw_extracted_tarif.json
   │  ↓
   ├─ Task 2: Group Tariffs by Service Class
   │  - Read uploaded tariff document
   │  - Organize rates by service class
   │  - Save to S3: grouped_tariffs.json
   │  ↓
   └─ Task 3: Extract Logic Using LLM
      - OpenAI analyzes tariff rules
      - Extracts: tier 1 rate, tier 2 rate, surcharges
      - Save to S3: final_logic_output.json
   ↓
4. VALIDATION AGENT
   - Loads extracted bill data
   - Loads extracted tariff rules
   - Calculates: (100 kWh × $0.12) + (50 kWh × $0.15) = $19.50
   - Compares with actual: $22.00
   - Overcharge detected: $2.50
   ↓
5. DATABASE STORAGE
   - Store bill record
   - Store validation result
   - Mark as "Overcharge Detected"
   ↓
6. USER VIEWS RESULTS (Audit Bills page)
   - Bill: Oct 2024
   - Usage: 150 kWh
   - Billed: $22.00
   - Should be: $19.50
   - Overcharge: $2.50 ❌
   ↓
7. GENERATE REPORT (Generate Reports page)
   - PDF export with details
   - Timeline graph
   - Summary statistics
```

---

## 📈 **Key Benefits**

✅ **Saves Time**: Automation instead of manual auditing
✅ **Reduces Errors**: AI-based analysis is consistent and thorough
✅ **Detects Overcharges**: Finds billing mistakes that humans might miss
✅ **Scalable**: Can process thousands of bills automatically
✅ **Transparent**: Clear reports showing exactly where discrepancies are
✅ **Cloud-Native**: AWS integration for enterprise deployment
✅ **API-Ready**: Airflow REST API for programmatic access

---

## 🎓 **Project Status**

- ✅ Core extraction pipeline working
- ✅ Tariff rule parsing with LLM
- ✅ Airflow orchestration (3-task DAG)
- ✅ PostgreSQL database setup
- ✅ Authentication system (login/logout)
- ✅ Streamlit UI with 7 pages
- ✅ AWS S3 integration
- ✅ OpenAI LLM integration
- 🔄 Real-time monitoring dashboard
- 🔄 Advanced error detection

---

## 📝 **Summary**

**Utility Billing AI** is a complete **automated auditing system** that:
1. **Ingests** utility bills and tariff documents
2. **Extracts** structured data using AI/LLM
3. **Analyzes** billing rules and rates
4. **Validates** charges against official tariffs
5. **Reports** discrepancies and overcharges
6. **Scales** to handle thousands of bills

It's production-ready with modern tech stack (Airflow, PostgreSQL, AWS, OpenAI) and provides a user-friendly interface for auditors to upload, analyze, and report on utility bills.

---

**Last Updated**: December 2025
**Current Version**: Multi-Agent Architecture with Airflow 3.1
