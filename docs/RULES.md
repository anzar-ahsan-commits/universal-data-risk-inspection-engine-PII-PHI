# RULES

## Location

- `rules/rules.json`

## Format

- `patterns`: dictionary of named regular expressions.
- `phi_keywords`: list of PHI/PII keyword strings.
- `risk_weights`: numerical weights by indicator name.
- `decision_thresholds`:
  - `reject`: score threshold to reject
  - `quarantine`: score threshold to quarantine

## Example

```json
{
  "patterns": {
    "email": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b",
    "ssn": "\\b\\d{3}-\\d{2}-\\d{4}\\b"
  },
  "phi_keywords": ["patient", "diagnosis"],
  "risk_weights": {"ssn": 100, "email": 20, "phi_keywords": 5},
  "decision_thresholds": {"reject": 150, "quarantine": 50}
}
```

## Notes

- If `rules/rules.json` is missing, defaults in `scanner.py` are used.
- Regex patterns are compiled with `re.IGNORECASE` for `member_id` and `mrn`, otherwise case-sensitive.
