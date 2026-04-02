import os
import json
import shutil
import sys
import tempfile

# Ensure module path is available when running in CI with nested checkout paths.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scanner import inspect_file, process_inbound_folder, load_rule_definitions, apply_rules
from app import app


def test_inspect_file_with_sample_medium():
    # Arrange
    sample = "samples/sample_medium.json"

    # Act
    result = inspect_file(sample)

    # Assert
    assert result["file_name"] == "sample_medium.json"
    assert "decision" in result
    assert result["risk_score"] >= 0
    assert os.path.exists(result["report_file"])


def test_process_inbound_folder_moves_file_correctly():
    tmpdir = tempfile.mkdtemp()
    inbound_dir = os.path.join(tmpdir, "inbound")
    os.makedirs(inbound_dir, exist_ok=True)

    sample_path = os.path.join(inbound_dir, "sample_phi.txt")
    shutil.copy("samples/sample_phi.txt", sample_path)

    # Act
    details = process_inbound_folder(inbound_dir=inbound_dir, base_dir=tmpdir)

    # Assert
    assert details["scanned"] == 1
    assert details["files"][0]["file"] == "sample_phi.txt"
    assert details["files"][0]["routed_to"].startswith(os.path.join(tmpdir, ""))

    # Cleanup
    shutil.rmtree(tmpdir)


def test_custom_rule_override():
    tmp_rules = {
        "patterns": {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        },
        "phi_keywords": ["patient", "member"],
        "risk_weights": {"ssn": 999, "email": 1, "phi_keywords": 1},
        "decision_thresholds": {"reject": 100, "quarantine": 20},
    }

    # Write temp file
    tmpdir = tempfile.mkdtemp()
    rules_file = os.path.join(tmpdir, "rules.json")
    with open(rules_file, "w", encoding="utf-8") as f:
        json.dump(tmp_rules, f)

    rules = load_rule_definitions(rules_file)
    apply_rules(rules)

    result = inspect_file("samples/sample_phi.txt", rules_path=rules_file)
    assert result["decision"] in ["ALLOW", "QUARANTINE", "REJECT"]

    shutil.rmtree(tmpdir)


def test_audit_endpoint_returns_entries_after_inspection(tmp_path):
    # Ensure clean audit path and in-memory DB for test scope
    audit_path = tmp_path / 'test_audit.db'
    os.environ['AUDIT_DB_PATH'] = str(audit_path)

    # perform scan and record audit via scanner API (no multipart file upload needed)
    result = inspect_file('samples/sample_phi.txt')
    assert result['decision'] in ['ALLOW', 'QUARANTINE', 'REJECT']

    # fetch audit remark from Flask endpoint
    client = app.test_client()
    audit_resp = client.get('/audit')
    assert audit_resp.status_code == 200
    data = audit_resp.get_json()
    assert isinstance(data, dict)
    assert "audit_records" in data
    assert isinstance(data["audit_records"], list)
    assert len(data["audit_records"]) >= 1


def test_inspect_file_records_audit_row(tmp_path):
    audit_path = tmp_path / 'test_audit.db'
    os.environ['AUDIT_DB_PATH'] = str(audit_path)

    # run direct scanner call
    result = inspect_file('samples/sample_phi.txt')
    assert result['decision'] in ['ALLOW', 'QUARANTINE', 'REJECT']

    # query DB directly to verify record exists
    import sqlite3
    conn = sqlite3.connect(str(audit_path))
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, file_name, decision FROM scans WHERE file_name = ?', ('sample_phi.txt',))
        rows = cur.fetchall()
        assert len(rows) >= 1
        assert rows[0][2] in ['ALLOW', 'QUARANTINE', 'REJECT']
    finally:
        conn.close()
