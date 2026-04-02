#!/usr/bin/env python3
"""
HTTP/REST Wrapper for MCP Server

Provides a REST API interface to the PHI/PII Scanner MCP server.
This allows Spider platform (or any HTTP client) to call scanner tools via REST endpoints.

Endpoints:
  POST /tool/{tool_name}  - Call an MCP tool
  GET  /resource/{resource_uri} - Read an MCP resource
"""

import os
import json
import sys
import asyncio
from typing import Dict, Any

from flask import Flask, request, jsonify

# Import scanner functions directly (simpler than subprocess MCP)
sys.path.insert(0, os.path.dirname(__file__))
from scanner import (
    inspect_file,
    process_inbound_folder,
    load_rule_definitions,
    apply_rules,
    fetch_audit,
    DEFAULT_RULES_PATH,
    DECISION_THRESHOLDS,
    RISK_WEIGHTS,
    PHI_KEYWORDS,
)

app = Flask(__name__)

# ============================================================================
# TOOL ENDPOINTS
# ============================================================================

@app.route("/tool/inspect_file", methods=["POST"])
def tool_inspect_file():
    """MCP Tool: inspect_file via HTTP."""
    data = request.get_json() or {}
    
    file_path = data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({
            "error": f"File not found: {file_path}",
            "success": False
        }), 400
    
    try:
        source_system = data.get("source_system", "Spider-HTTP")
        submitted_by = data.get("submitted_by", "http-api")
        
        metadata = {
            "source_system": source_system,
            "submitted_by": submitted_by,
        }
        
        result = inspect_file(file_path, metadata=metadata)
        return jsonify({
            "success": True,
            "decision": result.get("decision"),
            "risk_score": result.get("risk_score"),
            "severity": result.get("severity"),
            "reason": result.get("reason"),
            "findings": result.get("findings"),
            "flagged_data": result.get("flagged_data"),
            "report_file": result.get("report_file"),
            "downstream_action": result.get("downstream_action")
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route("/tool/process_inbound", methods=["POST"])
def tool_process_inbound():
    """MCP Tool: process_inbound via HTTP."""
    data = request.get_json() or {}
    
    inbound_dir = data.get("inbound_dir", "inbound")
    try:
        result = process_inbound_folder(inbound_dir=inbound_dir, base_dir=".")
        return jsonify({
            "success": True,
            "scanned": result.get("scanned"),
            "allow": result.get("allow"),
            "quarantine": result.get("quarantine"),
            "reject": result.get("reject"),
            "routed_files": result.get("files"),
            "errors": result.get("errors", [])
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route("/tool/fetch_audit", methods=["POST"])
def tool_fetch_audit():
    """MCP Tool: fetch_audit via HTTP."""
    data = request.get_json() or {}
    
    limit = data.get("limit", 100)
    decision_filter = data.get("decision_filter")
    
    try:
        all_records = fetch_audit()
        if decision_filter:
            filtered = [r for r in all_records if r.get("decision") == decision_filter]
        else:
            filtered = all_records
        
        result_records = filtered[:limit]
        return jsonify({
            "success": True,
            "total_records": len(all_records),
            "returned": len(result_records),
            "records": result_records
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route("/tool/update_rules", methods=["POST"])
def tool_update_rules():
    """MCP Tool: update_rules via HTTP."""
    data = request.get_json() or {}
    
    try:
        reject_threshold = data.get("reject_threshold")
        quarantine_threshold = data.get("quarantine_threshold")
        pattern_weights = data.get("pattern_weights")
        
        changes = {}
        
        if reject_threshold is not None:
            DECISION_THRESHOLDS["reject"] = reject_threshold
            changes["reject_threshold"] = reject_threshold
        
        if quarantine_threshold is not None:
            DECISION_THRESHOLDS["quarantine"] = quarantine_threshold
            changes["quarantine_threshold"] = quarantine_threshold
        
        if pattern_weights:
            RISK_WEIGHTS.update(pattern_weights)
            changes["pattern_weights"] = pattern_weights
        
        # Re-apply rules
        rules = load_rule_definitions()
        apply_rules(rules)
        
        return jsonify({
            "success": True,
            "message": "Rules updated successfully",
            "changes": changes
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


# ============================================================================
# RESOURCE ENDPOINTS
# ============================================================================

@app.route("/resource/audit/history", methods=["GET"])
def resource_audit_history():
    """MCP Resource: audit://history via HTTP."""
    try:
        records = fetch_audit()
        return jsonify({
            "resource": "audit://history",
            "total_records": len(records),
            "latest_records": records[:50]
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/resource/audit/summary", methods=["GET"])
def resource_audit_summary():
    """MCP Resource: audit://summary via HTTP."""
    try:
        records = fetch_audit()
        allow_count = len([r for r in records if r.get("decision") == "ALLOW"])
        quarantine_count = len([r for r in records if r.get("decision") == "QUARANTINE"])
        reject_count = len([r for r in records if r.get("decision") == "REJECT"])
        
        total_risk_score = sum(r.get("risk_score", 0) for r in records)
        avg_risk_score = total_risk_score / len(records) if records else 0
        
        return jsonify({
            "resource": "audit://summary",
            "total_scanned": len(records),
            "decisions": {
                "allow": allow_count,
                "quarantine": quarantine_count,
                "reject": reject_count
            },
            "statistics": {
                "average_risk_score": round(avg_risk_score, 2),
                "total_risk_score": total_risk_score
            }
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/resource/rules/current", methods=["GET"])
def resource_rules_current():
    """MCP Resource: rules://current via HTTP."""
    try:
        rules = load_rule_definitions()
        return jsonify({
            "resource": "rules://current",
            "thresholds": DECISION_THRESHOLDS,
            "pattern_weights": RISK_WEIGHTS,
            "phi_keywords": PHI_KEYWORDS,
            "rules_source": DEFAULT_RULES_PATH
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# ============================================================================
# SCHEMA & DISCOVERY
# ============================================================================

@app.route("/tools", methods=["GET"])
def get_tools():
    """Return available tools schema (for Spider discovery)."""
    return jsonify({
        "tools": [
            {
                "name": "inspect_file",
                "endpoint": "POST /tool/inspect_file",
                "description": "Scan a file for PHI/PII, return decision + findings",
                "schema": {
                    "file_path": "string (required)",
                    "source_system": "string (optional)",
                    "submitted_by": "string (optional)"
                }
            },
            {
                "name": "process_inbound",
                "endpoint": "POST /tool/process_inbound",
                "description": "Batch process inbound folder",
                "schema": {
                    "inbound_dir": "string (optional, default: 'inbound')"
                }
            },
            {
                "name": "fetch_audit",
                "endpoint": "POST /tool/fetch_audit",
                "description": "Retrieve audit records",
                "schema": {
                    "limit": "integer (optional, default: 100)",
                    "decision_filter": "string: ALLOW|QUARANTINE|REJECT (optional)"
                }
            },
            {
                "name": "update_rules",
                "endpoint": "POST /tool/update_rules",
                "description": "Modify detection rules",
                "schema": {
                    "reject_threshold": "integer (optional)",
                    "quarantine_threshold": "integer (optional)",
                    "pattern_weights": "object (optional)"
                }
            }
        ]
    })


@app.route("/resources", methods=["GET"])
def get_resources():
    """Return available resources schema (for Spider discovery)."""
    return jsonify({
        "resources": [
            {
                "uri": "audit://history",
                "endpoint": "GET /resource/audit/history",
                "description": "Latest audit records"
            },
            {
                "uri": "audit://summary",
                "endpoint": "GET /resource/audit/summary",
                "description": "Audit statistics"
            },
            {
                "uri": "rules://current",
                "endpoint": "GET /resource/rules/current",
                "description": "Current rules configuration"
            }
        ]
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "phi-pii-scanner-mcp-http",
        "version": "1.0.0"
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    os.makedirs("inbound", exist_ok=True)
    os.makedirs("tibco", exist_ok=True)
    os.makedirs("quarantine", exist_ok=True)
    os.makedirs("rejected", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    print("PHI/PII Scanner MCP HTTP Wrapper running on http://127.0.0.1:5051")
    app.run(host="127.0.0.1", port=5051, debug=False, use_reloader=False)
