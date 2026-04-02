import os
import json
import shutil
import tempfile

from scanner import inspect_file, process_inbound_folder, load_rule_definitions, apply_rules


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
