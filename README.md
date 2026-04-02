# Universal Data Risk Inspection Engine (PHI/PII Scanner)

**Author:** Anzar Ahsan

A production-ready, configurable gateway for detecting and managing PHI/PII (Protected Health Information / Personally Identifiable Information) risk in file transfers. Supports interactive web UI, automated batch processing, REST API, and MCP integration for agent-driven workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Setup & Installation](#setup--installation)
5. [Quick Start](#quick-start)
6. [Web UI (Flask) - Interactive Mode](#web-ui-flask---interactive-mode)
7. [REST API Endpoints](#rest-api-endpoints)
8. [MCP Integration for Spider Platform](#mcp-integration-for-spider-platform)
9. [CLI Usage](#cli-usage)
10. [Rules & Configuration](#rules--configuration)
11. [Decision Logic](#decision-logic)
12. [Workflow Examples](#workflow-examples)
13. [Testing & CI](#testing--ci)
14. [Troubleshooting](#troubleshooting)
15. [License](#license)

---

## Overview

This system scans files for sensitive data patterns and keywords, calculates risk scores, and makes automated decisions to ALLOW, QUARANTINE, or REJECT file transfers. All scan operations are audited in a local SQLite database for compliance tracking.

### Key Use Cases

- **Compliance & Governance**: Prevent PHI/PII from leaving secure boundaries
- **Data Onboarding**: Inspect incoming files before downstream processing
- **Agentic AI Workflows**: Spider agents can orchestrate scans, audit checks, and dynamic rule tuning
- **Batch Integration**: Process folders automatically via inbound queue
- **Real-time Monitoring**: Track scan history and audit trails

---

## Features

- ✅ **Pattern Detection**: Email, phone, SSN, DOB, MRN, Member ID via regex
- ✅ **Keyword Scanning**: Domain-specific keywords (patient, diagnosis, treatment, etc.)
- ✅ **Configurable Rules**: JSON-based thresholds and weights (no code changes needed)
- ✅ **Risk Scoring**: Weighted cumulative scoring model
- ✅ **Decision Routing**: ALLOW → `tibco/`, QUARANTINE → `quarantine/`, REJECT → `rejected/`
- ✅ **Audit Trail**: SQLite database with full scan history
- ✅ **Multi-File Support**: `.txt`, `.csv`, `.json` formats
- ✅ **Web UI**: Interactive file upload with instant results
- ✅ **REST API**: Machine-readable endpoints for automation
- ✅ **MCP Support**: Native Model Context Protocol for agentic workflows
- ✅ **Test Coverage**: Unit tests with pytest + GitHub Actions CI
- ✅ **Metadata Tracking**: Source system, submitted_by, timestamps for traceability

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Input Sources                             │
│  Web UI Upload  │  Inbound Folder  │  REST API  │ MCP Agent│
└────────┬─────────────────┬──────────────────┬───────────────┘
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │  scanner.py │
                    │   (core)    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐    ┌──────▼─────┐    ┌──────▼──────┐
   │  Patterns │    │  Keywords  │    │   Rules    │
   │   (Regex) │    │   (Domain) │    │  (JSON)    │
   └──────┬────┘    └──────┬─────┘    └──────┬──────┘
          │                │                  │
          └────────────────┼──────────────────┘
                           │
                    ┌──────▼──────────┐
                    │  Risk Scoring   │
                    │  + Decision     │
                    └──────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐    ┌──────▼─────┐    ┌──────▼──────┐
   │  ALLOW   │    │ QUARANTINE │    │   REJECT   │
   │ (tibco)  │    │             │    │ (rejected) │
   └──────────┘    └─────────────┘    └────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐    ┌──────▼─────┐    ┌──────▼──────┐
   │            │    │  Audit DB  │    │   Output   │
   │            │    │ (SQLite)   │    │  Reports   │
   │            │    │            │    │  (JSON)    │
   └────────────┘    └────────────┘    └────────────┘
```

**Components:**
- **scanner.py**: Core detection engine (patterns, keywords, scoring)
- **app.py**: Flask web UI + REST endpoints
- **mcp_http_wrapper.py**: HTTP layer for MCP tools/resources
- **mcp_server.py**: Native MCP stdio server
- **rules/rules.json**: Configurable thresholds and patterns
- **audit.db**: SQLite database for scan history

---

## Setup & Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git (for cloning)

### Step 1: Clone Repository

```bash
git clone https://github.com/anzar-ahsan-commits/universal-data-risk-inspection-engine-PII-PHI.git
cd universal-data-risk-inspection-engine-PII-PHI
```

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

**For Web UI + CLI only:**
```bash
pip install flask pytest
```

**For MCP integration (recommended):**
```bash
pip install -r requirements_mcp.txt
```

### Step 4: Create Required Directories

```bash
mkdir -p uploads inbound tibco quarantine rejected output
```

---

## Quick Start

### 1. Run Web UI

```bash
python app.py
```

Open browser: `http://127.0.0.1:5050`

### 2. Run MCP HTTP Wrapper (for Spider integration)

```bash
python mcp_http_wrapper.py
```

Service available at: `http://127.0.0.1:5051`

### 3. Run CLI Scan

```bash
python scanner.py samples/sample_phi.txt
```

---

## Web UI (Flask) - Interactive Mode

### Home Page (`/`)

- Presents file upload form
- Allows entry of metadata (source system, interface name, submitted by, destination system)
- File type restrictions: `.txt`, `.csv`, `.json`

### Upload File (`/inspect` - POST)

**Form Data:**
- `file` (multipart): The file to scan
- `source_system` (optional): Source system name
- `interface_name` (optional): Interface/workflow identifier
- `submitted_by` (optional): User or service submitting
- `destination_system` (optional): Target downstream system

**Response:**
- HTML result page with:
  - Decision (ALLOW/QUARANTINE/REJECT)
  - Risk score
  - Severity (LOW/MEDIUM/HIGH)
  - Reason for decision
  - Flagged data (masked for safety)
  - Report file location
  - Downstream action

**Example (using curl with file upload):**
```bash
curl -X POST http://127.0.0.1:5050/inspect \
  -F "file=@samples/sample_phi.txt" \
  -F "source_system=FTP-Server" \
  -F "submitted_by=john_doe"
```

### Process Inbound Folder (`/process_inbound` - GET)

**Endpoint:** `http://127.0.0.1:5050/process_inbound`

**Behavior:**
1. Scans all files in `inbound/` directory
2. Moves files to `tibco/`, `quarantine/`, or `rejected/` based on decision
3. Generates JSON reports in `output/`

**Response (JSON):**
```json
{
  "scanned": 5,
  "allow": 2,
  "quarantine": 2,
  "reject": 1,
  "files": [
    {
      "file": "data.txt",
      "decision": "QUARANTINE",
      "report": "output/data_20260402_101234.json",
      "routed_to": "quarantine/data.txt"
    }
  ],
  "errors": []
}
```

**Example:**
```bash
curl http://127.0.0.1:5050/process_inbound
```

### Audit Endpoint (`/audit` - GET)

**Endpoint:** `http://127.0.0.1:5050/audit`

**Response (JSON):**
```json
{
  "audit_records": [
    {
      "id": 1,
      "timestamp": "2026-04-02T10:12:34.567890",
      "file_name": "sample_phi.txt",
      "decision": "REJECT",
      "severity": "HIGH",
      "risk_score": 230,
      "findings": {
        "ssn": 1,
        "email": 1,
        "phone": 1,
        "phi_keywords": 6
      },
      "metadata": {
        "source_system": "FTP-Inbound",
        "submitted_by": "automated-poller"
      },
      "report_file": "output/sample_phi_20260402_101234.json"
    }
  ]
}
```

**Example:**
```bash
curl http://127.0.0.1:5050/audit
```

---

## REST API Endpoints

All endpoints are JSON-based for machine consumption.

### 1. Inspect File (POST)

**Endpoint:** `POST /inspect`

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "file_path": "path/to/file.txt",
  "source_system": "Spider-Agent",
  "submitted_by": "workflow-123",
  "interface_name": "data-onboarding",
  "destination_system": "TIBCO"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "file_name": "file.txt",
  "decision": "QUARANTINE",
  "risk_score": 85,
  "severity": "MEDIUM",
  "reason": "Risk score 85 triggered quarantine rules; review the flagged PHI/PII indicators.",
  "findings": {
    "email": 1,
    "phone": 2,
    "phi_keywords": 3
  },
  "flagged_data": {
    "email": ["jo***@example.com"],
    "phone": ["***-***-4567"],
    "phi_keywords": ["patient", "diagnosis", "treatment"]
  },
  "downstream_action": "HOLD_FOR_REVIEW",
  "report_file": "output/file_20260402_101234.json"
}
```

**Error Response (400/500):**
```json
{
  "error": "File not found: invalid_path.txt",
  "success": false
}
```

### 2. Process Inbound Folder (GET)

**Endpoint:** `GET /process_inbound`

**Query Parameters:**
- `inbound_dir` (optional): Path to inbound folder (default: `inbound/`)

**Response (200 OK):**
```json
{
  "scanned": 3,
  "allow": 1,
  "quarantine": 1,
  "reject": 1,
  "files": [
    {
      "file": "safe_data.csv",
      "decision": "ALLOW",
      "report": "output/safe_data_20260402_101234.json",
      "routed_to": "tibco/safe_data.csv"
    }
  ],
  "errors": []
}
```

### 3. Fetch Audit Records (GET)

**Endpoint:** `GET /audit`

**Query Parameters:**
- `limit` (optional): Max records to return (default: 100)
- `filter` (optional): Filter by decision (ALLOW, QUARANTINE, REJECT)

**Response (200 OK):**
```json
{
  "audit_records": [
    { ...record 1... },
    { ...record 2... }
  ]
}
```

**Example:**
```bash
curl "http://127.0.0.1:5050/audit?limit=10"
```

---

## MCP Integration for Spider Platform

MCP (Model Context Protocol) enables Spider agents to directly call scanner tools and access audit/rule data without direct file operations.

### Two Deployment Modes

#### Option A: HTTP Wrapper (Recommended)

**Start service:**
```bash
python mcp_http_wrapper.py
```

**Access:** `http://127.0.0.1:5051`

#### Option B: Native MCP Stdio (Advanced)

**Start service:**
```bash
python mcp_server.py
```

**Access:** stdin/stdout (for process-level integration)

### MCP Tools

Tools are callable functions that agents can invoke to perform operations.

#### Tool 1: `inspect_file`

**Purpose:** Scan a single file for PHI/PII

**Input Schema:**
```json
{
  "file_path": "string (required)",
  "source_system": "string (optional, default: 'Spider-HTTP')",
  "submitted_by": "string (optional, default: 'mcp-server')"
}
```

**Output:**
```json
{
  "success": true,
  "decision": "REJECT|QUARANTINE|ALLOW",
  "risk_score": 230,
  "severity": "HIGH|MEDIUM|LOW",
  "reason": "string",
  "findings": { ... },
  "flagged_data": { ... },
  "downstream_action": "BLOCK_TRANSMISSION|HOLD_FOR_REVIEW|SEND_TO_TIBCO",
  "report_file": "string"
}
```

**HTTP Example:**
```bash
curl -X POST http://127.0.0.1:5051/tool/inspect_file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "samples/sample_phi.txt",
    "source_system": "Spider",
    "submitted_by": "compliance-agent"
  }'
```

#### Tool 2: `process_inbound`

**Purpose:** Batch scan all files in inbound folder

**Input Schema:**
```json
{
  "inbound_dir": "string (optional, default: 'inbound')"
}
```

**Output:**
```json
{
  "success": true,
  "scanned": 3,
  "allow": 1,
  "quarantine": 1,
  "reject": 1,
  "routed_files": [
    { "file": "...", "decision": "...", "routed_to": "..." }
  ],
  "errors": []
}
```

**HTTP Example:**
```bash
curl -X POST http://127.0.0.1:5051/tool/process_inbound \
  -H "Content-Type: application/json" \
  -d '{"inbound_dir": "inbound"}'
```

#### Tool 3: `fetch_audit`

**Purpose:** Retrieve scan history for compliance/monitoring

**Input Schema:**
```json
{
  "limit": "integer (optional, default: 100)",
  "decision_filter": "string (optional: ALLOW|QUARANTINE|REJECT)"
}
```

**Output:**
```json
{
  "success": true,
  "total_records": 42,
  "returned": 10,
  "records": [
    {
      "id": 1,
      "timestamp": "2026-04-02T10:12:34",
      "file_name": "data.txt",
      "decision": "QUARANTINE",
      "severity": "MEDIUM",
      "risk_score": 85,
      "findings": { ... },
      "metadata": { ... }
    }
  ]
}
```

**HTTP Example:**
```bash
curl -X POST http://127.0.0.1:5051/tool/fetch_audit \
  -H "Content-Type: application/json" \
  -d '{"limit": 50, "decision_filter": "REJECT"}'
```

#### Tool 4: `update_rules`

**Purpose:** Dynamically modify detection thresholds and weights

**Input Schema:**
```json
{
  "reject_threshold": "integer (optional)",
  "quarantine_threshold": "integer (optional)",
  "pattern_weights": "object (optional, e.g., {'ssn': 120, 'email': 10})"
}
```

**Output:**
```json
{
  "success": true,
  "message": "Rules updated successfully",
  "changes": {
    "reject_threshold": 120,
    "quarantine_threshold": 40,
    "pattern_weights": { ... }
  }
}
```

**HTTP Example:**
```bash
curl -X POST http://127.0.0.1:5051/tool/update_rules \
  -H "Content-Type: application/json" \
  -d '{
    "reject_threshold": 120,
    "quarantine_threshold": 40,
    "pattern_weights": {"ssn": 120, "email": 15}
  }'
```

### MCP Resources

Resources are readable data structures that agents can query for information.

#### Resource 1: `audit://history`

**Endpoint:** `GET /resource/audit/history`

**Response:**
```json
{
  "resource": "audit://history",
  "total_records": 42,
  "latest_records": [
    { ...50 most recent records... }
  ]
}
```

#### Resource 2: `audit://summary`

**Endpoint:** `GET /resource/audit/summary`

**Response:**
```json
{
  "resource": "audit://summary",
  "total_scanned": 42,
  "decisions": {
    "allow": 10,
    "quarantine": 20,
    "reject": 12
  },
  "statistics": {
    "average_risk_score": 125.5,
    "total_risk_score": 5271
  }
}
```

#### Resource 3: `rules://current`

**Endpoint:** `GET /resource/rules/current`

**Response:**
```json
{
  "resource": "rules://current",
  "thresholds": {
    "reject": 150,
    "quarantine": 50
  },
  "pattern_weights": {
    "ssn": 100,
    "email": 20,
    "phone": 15,
    "mrn": 25,
    "member_id": 25
  },
  "phi_keywords": [
    "patient",
    "diagnosis",
    "treatment",
    ...
  ],
  "rules_source": "rules/rules.json"
}
```

### MCP Discovery Endpoints

Agents can auto-discover tools and resources:

**Discover Tools:**
```bash
curl http://127.0.0.1:5051/tools
```

**Discover Resources:**
```bash
curl http://127.0.0.1:5051/resources
```

**Health Check:**
```bash
curl http://127.0.0.1:5051/health
```

---

## CLI Usage

### Scan Single File

```bash
python scanner.py path/to/file.txt
```

**Output:** JSON with decision, findings, risk score, etc. (printed to stdout)

### Example

```bash
$ python scanner.py samples/sample_phi.txt
{
  "timestamp": "2026-04-02T10:12:34.567890",
  "file_name": "sample_phi.txt",
  "file_type": ".txt",
  "findings": {
    "ssn": 1,
    "email": 1,
    "phone": 1,
    "phi_keywords": 6
  },
  "flagged_data": {
    "ssn": ["***-**-6789"],
    "email": ["jo***@email.com"],
    ...
  },
  "total_hits": 12,
  "risk_score": 230,
  "decision": "REJECT",
  "severity": "HIGH",
  "reason": "Direct identifier SSN detected in the file.",
  "downstream_action": "BLOCK_TRANSMISSION",
  "report_file": "output/sample_phi_20260402_101234.json"
}
```

---

## Rules & Configuration

### Override Default Rules

Edit `rules/rules.json`:

```json
{
  "patterns": {
    "email": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b",
    "ssn": "\\b\\d{3}-\\d{2}-\\d{4}\\b",
    "phone": "\\b(?:\\+1[-\\.\\s]?)?(?:\\(?\\d{3}\\)?[-\\.\\s]?)\\d{3}[-\\.\\s]?\\d{4}\\b",
    "dob": "\\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\\d|3[01])[/-](?:19|20)\\d{2}\\b",
    "member_id": "\\b(?:member[\\s_-]?id[:\\s]*)([A-Za-z0-9-]+)\\b",
    "mrn": "\\b(?:mrn[:\\s]*)([A-Za-z0-9-]+)\\b"
  },
  "phi_keywords": [
    "patient",
    "diagnosis",
    "treatment",
    "dob",
    "member id",
    "mrn",
    "medical record",
    "insurance",
    "claim",
    "provider",
    "hospital"
  ],
  "risk_weights": {
    "ssn": 100,
    "email": 20,
    "phone": 15,
    "dob": 15,
    "member_id": 25,
    "mrn": 25,
    "phi_keywords": 5
  },
  "decision_thresholds": {
    "reject": 150,
    "quarantine": 50
  }
}
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `reject_threshold` | 150 | Risk score ≥ this triggers REJECT |
| `quarantine_threshold` | 50 | Risk score ≥ this (but < reject) triggers QUARANTINE |
| `ssn` weight | 100 | Any SSN detected → auto REJECT |
| `email` weight | 20 | Each email found adds 20 to score |
| `phone` weight | 15 | Each phone found adds 15 to score |
| `phi_keywords` weight | 5 | Each keyword match adds 5 to score |

### Environment Variables

**Audit DB Path:**
```bash
# Windows PowerShell
$env:AUDIT_DB_PATH = "D:\compliance\phi_audit.db"

# Linux/macOS
export AUDIT_DB_PATH=/var/lib/phi_audit.db
```

---

## Decision Logic

### Scoring Algorithm

1. **Extract** all patterns + keywords from file
2. **Count** occurrences of each pattern/keyword
3. **Calculate** score = Σ(count × weight)
4. **Check** decision thresholds:
   - If any **SSN found** → **REJECT** (highest priority)
   - Else if score ≥ `reject_threshold` → **REJECT**
   - Else if score ≥ `quarantine_threshold` → **QUARANTINE**
   - Else → **ALLOW**

### Example Walkthrough

**File Content:**
```
Patient: John Smith
DOB: 04/12/1988
Email: john@example.com
Phone: 555-123-4567
SSN: 123-45-6789
Member ID: MED-123456
Medical Record Number: MRN-789
```

**Pattern Matches:**
- `ssn`: 1 match (weight: 100) → **auto REJECT**
- `email`: 1 match (weight: 20)
- `phone`: 1 match (weight: 15)
- `dob`: 1 match (weight: 15)
- `member_id`: 1 match (weight: 25)
- `mrn`: 1 match (weight: 25)
- `phi_keywords`: 6 matches (weight: 5 each = 30)

**Score Calculation:**
```
100 (SSN) + 20 (email) + 15 (phone) + 15 (DOB) + 25 (member_id) + 25 (mrn) + 30 (keywords)
= 230 total
```

**Decision:** **REJECT** (SSN detected + score 230 > reject_threshold 150)

**Severity:** **HIGH**

**Reason:** "Direct identifier SSN detected in the file."

**Downstream Action:** "BLOCK_TRANSMISSION"

---

## Workflow Examples

### Workflow 1: Compliance Agent (Audit Monitoring)

**Spider Agent Flow:**
```
1. Every hour, call /resource/audit/summary
2. If reject_count > 5:
   - Alert compliance team
   - Log to compliance dashboard
3. If average_risk_score > 100:
   - Trigger review queue
   - Update governance metrics
```

**HTTP Calls:**
```bash
# Get audit summary
curl http://127.0.0.1:5051/resource/audit/summary

# Check if thresholds exceeded
if [[ reject_count -gt 5 ]]; then
  echo "High rejection count detected!"
fi
```

### Workflow 2: Dynamic Rule Tuning Agent

**Spider Agent Flow:**
```
1. Monitor audit history for false positives (too many QUARANTINE)
2. Analyze patterns in quarantined files
3. If policy decision available:
   - Call /tool/update_rules to adjust thresholds
   - Log rule change in audit trail
```

**HTTP Calls:**
```bash
# Lower quarantine threshold to reduce false positives
curl -X POST http://127.0.0.1:5051/tool/update_rules \
  -H "Content-Type: application/json" \
  -d '{
    "quarantine_threshold": 30
  }'
```

### Workflow 3: Batch Processing with Cleanup

**Spider Agent Flow:**
```
1. Drop files in inbound/ folder
2. Call /tool/process_inbound
3. For each routed file:
   - Log routing decision
   - Update destination system via API
4. Archive report files
```

**HTTP Calls:**
```bash
# Trigger batch processing
curl -X POST http://127.0.0.1:5051/tool/process_inbound \
  -H "Content-Type: application/json" \
  -d '{"inbound_dir": "inbound"}'

# Results are automatically routed to tibco/, quarantine/, rejected/
```

### Workflow 4: File Inspection with Escalation

**Spider Agent Flow:**
```
1. Receive file from upstream system
2. Call /tool/inspect_file
3. If decision == QUARANTINE:
   - Add to review queue
   - Notify approver
   - Log escalation in audit
4. If decision == ALLOW:
   - Send to downstream TIBCO
   - Update tracking system
```

**HTTP Calls:**
```bash
# Inspect file
curl -X POST http://127.0.0.1:5051/tool/inspect_file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "uploads/incoming_data.csv",
    "source_system": "EDI-Import",
    "submitted_by": "data-integration"
  }'

# Handle results based on decision
```

---

## Testing & CI

### Unit Tests

```bash
pytest -q
```

**Output:**
```
5 passed in 1.92s
```

**Test Coverage:**
- File inspection (PHI detection)
- Inbound folder routing
- Custom rule overrides
- Audit endpoint functionality
- Audit database recording

### GitHub Actions CI

**Workflow:** `.github/workflows/python-app.yml`

**Triggers:** On push and pull request

**Steps:**
1. Install dependencies
2. Run pytest
3. Check Python syntax

**View Status:** [GitHub Actions](https://github.com/anzar-ahsan-commits/universal-data-risk-inspection-engine-PII-PHI/actions)

---

## Troubleshooting

### Issue: "Module not found: scanner"

**Cause:** Python path not configured in tests

**Solution:**
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

### Issue: Port Already in Use (5050 or 5051)

**Cause:** Service already running on that port

**Solution:**
```bash
# Windows: Find process using port 5050
netstat -ano | findstr :5050

# Linux/macOS: Find process using port 5050
lsof -i :5050

# Kill process
taskkill /PID <PID> /F  # Windows
kill -9 <PID>           # Linux/macOS
```

### Issue: File Not Found in Audit

**Cause:** File path is relative; service runs from different directory

**Solution:** Use absolute file paths or place files in recognized directories:
- `samples/` - Sample files
- `uploads/` - Web UI uploads
- `inbound/` - Batch processing

### Issue: SQLite Database Locked

**Cause:** Multiple processes accessing audit.db simultaneously

**Solution:** Set unique audit path per process
```bash
set AUDIT_DB_PATH=audit_process1.db  # Windows
export AUDIT_DB_PATH=audit_process1.db  # Linux
```

### Issue: MCP HTTP Wrapper Returns 500 Error

**Solution:** Check Flask logs for details
```bash
# Run with debug output
python mcp_http_wrapper.py  # Check console for errors
```

---

## License

Apache License 2.0

See [LICENSE](LICENSE) file for full text.

---

## Support & Contributing

For issues, feature requests, or contributions:

1. Check [GitHub Issues](https://github.com/anzar-ahsan-commits/universal-data-risk-inspection-engine-PII-PHI/issues)
2. Review existing documentation
3. Create detailed issue with reproducible steps

---

## Compliance & Security Notes

- ⚠️ **Development Use**: Current deployment targets local development
- ⚠️ **Audit Logging**: All scans are logged to `audit.db` for compliance
- ⚠️ **Data Masking**: Sensitive values masked in responses (email, SSN, phone, etc.)
- ⚠️ **HIPAA**: Not HIPAA-certified as-is; requires additional controls for production
- ⚠️ **Data Retention**: Archive `audit.db` regularly per your retention policy

---

## Version History

- **v1.0.0** (2026-04-02): Initial release with audit, tests, MCP support
