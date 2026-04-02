# ARCHITECTURE

## Overview

PHI/PII Inspection Gateway provides three paths:

1. Web upload endpoint (`/inspect`) for manual file inspection.
2. `process_inbound_folder()` for FTP-like batch processing via `inbound/` folder.
3. CLI scan via `scanner.py`.

## Main components

- `app.py`: Flask app + endpoints (`/`, `/inspect`, `/process_inbound`).
- `scanner.py`: detection engine and routing.
- `rules/rules.json`: configurable detection rules.
- `templates/`: UI for upload and results.

## Data flow

1. file uploaded / placed in inbound.
2. scanner extracts text from `.txt`, `.csv`, `.json`.
3. patterns + keywords matched (dynamic config).
4. risk score computed and decision made.
5. result written to `output/` and file moved to destination folder.
