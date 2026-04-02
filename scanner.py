import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "dob": re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"),
    "member_id": re.compile(r"\b(?:member[\s_-]?id[:\s]*)([A-Za-z0-9-]+)\b", re.IGNORECASE),
    "mrn": re.compile(r"\b(?:mrn[:\s]*)([A-Za-z0-9-]+)\b", re.IGNORECASE),
}

PHI_KEYWORDS = [
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
    "hospital",
]

RISK_WEIGHTS = {
    "ssn": 100,
    "email": 20,
    "phone": 15,
    "dob": 15,
    "member_id": 25,
    "mrn": 25,
    "phi_keywords": 5,
}

DECISION_THRESHOLDS = {
    "reject": 150,
    "quarantine": 50,
}

DEFAULT_RULES_PATH = os.path.join("rules", "rules.json")


def load_rule_definitions(rules_path: Optional[str] = None) -> Dict[str, Any]:
    final_path = rules_path or DEFAULT_RULES_PATH

    rules = {
        "patterns": {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "phone": r"\b(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "dob": r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
            "member_id": r"\b(?:member[\s_-]?id[:\s]*)([A-Za-z0-9-]+)\b",
            "mrn": r"\b(?:mrn[:\s]*)([A-Za-z0-9-]+)\b",
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
            "hospital",
        ],
        "risk_weights": RISK_WEIGHTS,
        "decision_thresholds": DECISION_THRESHOLDS,
    }

    try:
        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as f:
                external = json.load(f)
            # merge and override defaults with user rules
            rules.update({k: v for k, v in external.items() if v is not None})
    except Exception:
        pass

    # compile patterns into regex
    patterns = {}
    for key, expr in rules.get("patterns", {}).items():
        flags = re.IGNORECASE if key in ["member_id", "mrn"] else 0
        patterns[key] = re.compile(expr, flags)

    rules["patterns"] = patterns
    return rules


def apply_rules(rules: Dict[str, Any]) -> None:
    global PATTERNS, PHI_KEYWORDS, RISK_WEIGHTS, DECISION_THRESHOLDS
    PATTERNS = rules.get("patterns", PATTERNS)
    PHI_KEYWORDS = rules.get("phi_keywords", PHI_KEYWORDS)
    RISK_WEIGHTS = rules.get("risk_weights", RISK_WEIGHTS)
    DECISION_THRESHOLDS = rules.get("decision_thresholds", DECISION_THRESHOLDS)


def extract_text_from_file(file_path: str) -> str:
    extension = os.path.splitext(file_path)[1].lower()

    if extension in [".txt", ".csv"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if extension == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)

    raise ValueError(f"Unsupported file type: {extension}")


def load_structured_content(file_path: str) -> Optional[Any]:
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".csv":
        import csv

        items: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
        return items

    if extension == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


def scan_text_and_collect(text: str) -> Dict[str, List[str]]:
    hit_data: Dict[str, List[str]] = {k: [] for k in PATTERNS.keys()}

    for name, pattern in PATTERNS.items():
        raw_matches = pattern.findall(text)

        cleaned_matches = []
        for match in raw_matches:
            if isinstance(match, tuple):
                match = " ".join([str(item) for item in match if item])
            cleaned_matches.append(str(match).strip())

        unique_matches = sorted(set([m for m in cleaned_matches if m]))
        hit_data[name] = [mask_value(name, m) for m in unique_matches[:10]]

    return hit_data


def traverse_structured_data(value: Any) -> Dict[str, List[str]]:
    matches: Dict[str, List[str]] = {k: [] for k in PATTERNS.keys()}

    if isinstance(value, dict):
        for v in value.values():
            child = traverse_structured_data(v)
            for key, vals in child.items():
                matches[key].extend(vals)

    elif isinstance(value, list):
        for item in value:
            child = traverse_structured_data(item)
            for key, vals in child.items():
                matches[key].extend(vals)

    else:
        text = str(value)
        if text:
            child = scan_text_and_collect(text)
            for key, vals in child.items():
                matches[key].extend(vals)

    for key in matches:
        matches[key] = sorted(set(matches[key]))

    return matches


def merge_flagged_data(base: Dict[str, List[str]], extra: Dict[str, List[str]]) -> Dict[str, List[str]]:
    result = {k: sorted(set(v)) for k, v in base.items()}

    for key, values in extra.items():
        result.setdefault(key, [])
        result[key] = sorted(set(result[key] + values))

    return result


def mask_value(indicator: str, value: str) -> str:
    """
    Mask sensitive values for safer display in the UI.
    """
    value = str(value)

    if indicator == "email":
        parts = value.split("@")
        if len(parts) == 2:
            local, domain = parts
            masked_local = local[:2] + "***" if len(local) > 2 else "***"
            return f"{masked_local}@{domain}"

    if indicator == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 4:
            return f"***-***-{digits[-4:]}"

    if indicator == "ssn":
        digits = re.sub(r"\D", "", value)
        if len(digits) == 9:
            return f"***-**-{digits[-4:]}"

    if indicator == "dob":
        return value

    if indicator in ["member_id", "mrn"]:
        if len(value) > 4:
            return value[:2] + "***" + value[-2:]
        return "***"

    return value


def extract_matches(text: str, structured_content: Optional[Any] = None) -> Dict[str, List[str]]:
    """
    Extract unique flagged values for each indicator from text and structured content.
    """
    flagged_data: Dict[str, List[str]] = {}

    for name, pattern in PATTERNS.items():
        raw_matches = pattern.findall(text)

        # findall may return tuples for some regexes; normalize to strings
        cleaned_matches = []
        for match in raw_matches:
            if isinstance(match, tuple):
                match = " ".join([str(item) for item in match if item])
            cleaned_matches.append(str(match).strip())

        unique_matches = sorted(set([m for m in cleaned_matches if m]))
        flagged_data[name] = [mask_value(name, m) for m in unique_matches[:10]]

    lowered_text = text.lower()
    keyword_matches = []
    for keyword in PHI_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_text):
            keyword_matches.append(keyword)

    flagged_data["phi_keywords"] = sorted(set(keyword_matches))

    if structured_content is not None:
        structured_flagged = traverse_structured_data(structured_content)
        flagged_data = merge_flagged_data(flagged_data, structured_flagged)

        # repeat keyword detection in structured content
        structured_text = json.dumps(structured_content, ensure_ascii=False)
        lowered_text_all = (text + " " + structured_text).lower()
        keyword_matches = []
        for keyword in PHI_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered_text_all):
                keyword_matches.append(keyword)
        flagged_data["phi_keywords"] = sorted(set(keyword_matches))

    return flagged_data


def count_pattern_matches(flagged_data: Dict[str, List[str]], text: str) -> Dict[str, int]:
    findings = {}

    for indicator, values in flagged_data.items():
        if indicator == "phi_keywords":
            lowered_text = text.lower()
            keyword_hits = 0
            for keyword in PHI_KEYWORDS:
                keyword_hits += len(re.findall(rf"\b{re.escape(keyword)}\b", lowered_text))
            findings[indicator] = keyword_hits
        else:
            findings[indicator] = len(values)

    return findings


def calculate_risk_score(findings: Dict[str, int]) -> int:
    score = 0
    for indicator, count in findings.items():
        score += count * RISK_WEIGHTS.get(indicator, 0)
    return score


def determine_decision(findings: Dict[str, int]) -> str:
    if findings.get("ssn", 0) > 0:
        return "REJECT"

    score = calculate_risk_score(findings)
    reject_threshold = DECISION_THRESHOLDS.get("reject", 150)
    quarantine_threshold = DECISION_THRESHOLDS.get("quarantine", 50)

    if score >= reject_threshold:
        return "REJECT"
    if score >= quarantine_threshold:
        return "QUARANTINE"

    return "ALLOW"


def determine_severity(decision: str) -> str:
    if decision == "REJECT":
        return "HIGH"
    if decision == "QUARANTINE":
        return "MEDIUM"
    return "LOW"


def determine_reason(findings: Dict[str, int], decision: str) -> str:
    if findings.get("ssn", 0) > 0:
        return "Direct identifier SSN detected in the file."

    if decision == "QUARANTINE":
        score = calculate_risk_score(findings)
        return f"Risk score {score} triggered quarantine rules; review the flagged PHI/PII indicators."

    if decision == "REJECT":
        score = calculate_risk_score(findings)
        return f"Risk score {score} exceeded rejection threshold."

    return "No significant sensitive data detected for the current rule set."


def determine_downstream_action(decision: str) -> str:
    if decision == "ALLOW":
        return "SEND_TO_TIBCO"
    if decision == "QUARANTINE":
        return "HOLD_FOR_REVIEW"
    return "BLOCK_TRANSMISSION"


def build_result(
    file_path: str,
    findings: Dict[str, int],
    decision: str,
    flagged_data: Dict[str, List[str]],
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    severity = determine_severity(decision)
    reason = determine_reason(findings, decision)
    downstream_action = determine_downstream_action(decision)
    risk_score = calculate_risk_score(findings)

    return {
        "timestamp": datetime.now().isoformat(),
        "file_name": os.path.basename(file_path),
        "file_type": os.path.splitext(file_path)[1].lower(),
        "findings": findings,
        "flagged_data": flagged_data,
        "total_hits": sum(findings.values()),
        "risk_score": risk_score,
        "decision": decision,
        "severity": severity,
        "reason": reason,
        "downstream_action": downstream_action,
        "metadata": metadata or {},
    }


def save_result(result: Dict[str, Any]) -> str:
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(result["file_name"])[0]
    timestamp_safe = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{base_name}_{timestamp_safe}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return output_file


def route_file_by_decision(file_path: str, decision: str, base_dir: str = ".") -> str:
    output_dirs = {
        "ALLOW": "tibco",
        "QUARANTINE": "quarantine",
        "REJECT": "rejected",
    }
    dest_dir = os.path.join(base_dir, output_dirs.get(decision, "quarantine"))
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
    os.replace(file_path, dest_path)
    return dest_path


def process_inbound_folder(
    inbound_dir: str = "inbound",
    rules_path: Optional[str] = None,
    base_dir: str = ".",
    skip_processed: bool = True,
) -> Dict[str, Any]:
    os.makedirs(inbound_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "tibco"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "quarantine"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "rejected"), exist_ok=True)

    results: Dict[str, Any] = {
        "scanned": 0,
        "allow": 0,
        "quarantine": 0,
        "reject": 0,
        "errors": [],
        "files": [],
    }

    valid_ext = {"txt", "csv", "json"}

    for filename in sorted(os.listdir(inbound_dir)):
        file_path = os.path.join(inbound_dir, filename)
        if not os.path.isfile(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in valid_ext:
            continue

        try:
            metadata = {
                "source_system": "FTP Inbound",
                "destination_system": "TIBCO",
                "interface_name": os.path.splitext(filename)[0],
                "submitted_by": "automated-poller",
            }
            scan_result = inspect_file(file_path, metadata=metadata, rules_path=rules_path)
            decision = scan_result.get("decision", "QUARANTINE")
            routed_path = route_file_by_decision(file_path, decision, base_dir=base_dir)

            results["scanned"] += 1
            if decision == "ALLOW":
                results["allow"] += 1
            elif decision == "QUARANTINE":
                results["quarantine"] += 1
            elif decision == "REJECT":
                results["reject"] += 1

            results["files"].append({
                "file": filename,
                "decision": decision,
                "report": scan_result.get("report_file"),
                "routed_to": routed_path,
            })

        except Exception as e:
            results["errors"].append({"file": filename, "error": str(e)})

    return results


def inspect_file(file_path: str, metadata: Optional[Dict[str, str]] = None, rules_path: Optional[str] = None) -> Dict[str, Any]:
    rules = load_rule_definitions(rules_path)
    apply_rules(rules)

    text = extract_text_from_file(file_path)
    structured_content = load_structured_content(file_path)
    flagged_data = extract_matches(text, structured_content)
    findings = count_pattern_matches(flagged_data, text)
    decision = determine_decision(findings)
    result = build_result(file_path, findings, decision, flagged_data, metadata=metadata)
    output_path = save_result(result)
    result["report_file"] = output_path
    result["rules_source"] = rules_path or DEFAULT_RULES_PATH
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python scanner.py <file_path>")
        raise SystemExit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: File not found -> {file_path}")
        raise SystemExit(1)

    try:
        result = inspect_file(file_path)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error while processing file: {e}")
        raise SystemExit(1)