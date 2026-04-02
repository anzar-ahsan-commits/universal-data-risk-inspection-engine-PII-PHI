# Universal Data Risk Inspection Engine

Author: Anzar Ahsan

This repository provides a configurable gateway for detecting and managing PHI/PII risk in file transfers. It supports both interactive web upload and automated inbound folder processing. Outputs are routed and audited based on risk decisions.

## Features

- Flask web UI for file upload and metadata entry
- File type support: `.txt`, `.csv`, `.json`
- Pattern-based detection of PHI/PII (email, phone, SSN, DOB, MRN, Member ID)
- Keyword detection (patient, diagnosis, treatment, provider, etc.)
- Configurable rule set via `rules/rules.json`
- Risk scoring and decision logic: `ALLOW`, `QUARANTINE`, `REJECT`
- Audit report generation in `output/`
- Inbound folder routing to `tibco/`, `quarantine/`, `rejected/`
- Unit tests with pytest and CI workflow via GitHub Actions

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/anzar-ahsan-commits/universal-data-risk-inspection-engine-PII-PHI.git
   cd universal-data-risk-inspection-engine-PII-PHI
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install flask pytest
   ```

4. Create required directories (if missing):
   ```bash
   mkdir uploads inbound tibco quarantine rejected output
   ```

## Running

### Web UI

```bash
python app.py
```

Open `http://127.0.0.1:5050` and submit files.

### Inbound folder processing

1. Place files in `inbound/`.
2. Trigger:
   ```bash
   curl http://127.0.0.1:5050/process_inbound
   ```
3. Check
   - `tibco/` (ALLOW)
   - `quarantine/` (QUARANTINE)
   - `rejected/` (REJECT)
   - `output/` (JSON report)

### Audit log endpoint

- Retrieve latest audit records:
  ```bash
  curl http://127.0.0.1:5050/audit
  ```
- Response shape:
  ```json
  {"audit_records": [ ... ]}
  ```

### Optional runtime settings

- Set a custom audit database path:
  ```bash
  set AUDIT_DB_PATH=custom_audit.db  # Windows PowerShell
  export AUDIT_DB_PATH=custom_audit.db  # Linux/macOS
  ```

### CLI scan

```bash
python scanner.py samples/sample_medium.json
```

## MCP (Model Context Protocol) for Spider Platform

The PHI/PII scanner is available as an MCP-compatible service for integration with HCLTech's Spider platform and other GenAI/agentic workflows.

### Setup

1. Install MCP dependencies:
   ```bash
   pip install -r requirements_mcp.txt
   ```

2. Start the MCP HTTP wrapper:
   ```bash
   python mcp_http_wrapper.py
   ```
   Service runs on `http://127.0.0.1:5051`

### Available Tools (via MCP)

- **inspect_file** - Scan a file for PHI/PII
  - Input: `file_path`, optional `source_system`, `submitted_by`
  - Output: decision, risk_score, findings, flagged_data

- **process_inbound** - Batch scan inbound folder
  - Input: optional `inbound_dir`
  - Output: summary counts, routed files, errors

- **fetch_audit** - Retrieve audit records
  - Input: optional `limit`, optional `decision_filter` (ALLOW/QUARANTINE/REJECT)
  - Output: audit records list with metadata

- **update_rules** - Modify detection thresholds and weights
  - Input: optional `reject_threshold`, `quarantine_threshold`, `pattern_weights`
  - Output: confirmation of changes applied

### Available Resources (via MCP)

- **audit://history** - Latest audit records
- **audit://summary** - Audit statistics summary
- **rules://current** - Current rule configuration

### Spider Integration Examples

#### Via HTTP REST (Recommended)

```bash
# Get tool schema
curl http://127.0.0.1:5051/tools

# Inspect a file
curl -X POST http://127.0.0.1:5051/tool/inspect_file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "samples/sample_phi.txt",
    "source_system": "Spider-Agent",
    "submitted_by": "workflow-123"
  }'

# Fetch audit records
curl -X POST http://127.0.0.1:5051/tool/fetch_audit \
  -H "Content-Type: application/json" \
  -d '{"limit": 50, "decision_filter": "QUARANTINE"}'

# Get audit summary
curl http://127.0.0.1:5051/resource/audit/summary

# Update rules
curl -X POST http://127.0.0.1:5051/tool/update_rules \
  -H "Content-Type: application/json" \
  -d '{
    "reject_threshold": 120,
    "quarantine_threshold": 40
  }'
```

#### Via Native MCP Stdio (Advanced)

For native MCP integration:
```bash
python mcp_server.py
```
This runs the native MCP server on stdio for direct protocol integration.

## Rules

Edit `rules/rules.json` to adjust patterns, keyword list, weights, and thresholds.

## Tests

Run:

```bash
pytest -q
```

## GitHub Actions

Workflow `.github/workflows/python-app.yml` runs on push and pull request and executes tests.

## Cleanup before final commit

```bash
rm -rf output/*
```

## License

Apache License 2.0 (file `LICENSE`).

## Tests

Run:

```bash
pytest -q
```

## GitHub Actions

Workflow `.github/workflows/python-app.yml` runs on push and pull request and executes tests.

## Cleanup before final commit

```bash
rm -rf output/*
```

## License

Apache License 2.0 (file `LICENSE`).
