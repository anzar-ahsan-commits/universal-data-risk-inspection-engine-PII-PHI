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

### CLI scan

```bash
python scanner.py samples/sample_medium.json
```

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
