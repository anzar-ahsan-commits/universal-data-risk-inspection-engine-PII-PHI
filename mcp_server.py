#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for PHI/PII Scanner

Exposes inspection, audit, and rule management capabilities to Spider platform.

Tools:
  - inspect_file: Scan a file for PHI/PII, return decision + findings
  - process_inbound: Batch scan inbound folder, return routing summary
  - update_rules: Modify detection rules (thresholds, patterns, keywords)

Resources:
  - audit://history: Latest audit records for compliance tracking
  - audit://summary: High-level audit statistics
  - rules://current: Current rule configuration for review
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# MCP SDK
from mcp.server import Server, Request
from mcp.types import Tool, TextContent, Resource


# Import scanner functions
sys.path.insert(0, os.path.dirname(__file__))
from scanner import (
    inspect_file,
    process_inbound_folder,
    load_rule_definitions,
    apply_rules,
    fetch_audit,
    DEFAULT_RULES_PATH,
    get_audit_db_path,
)

# Initialize MCP Server
server = Server("phi-pii-scanner")


# ============================================================================
# TOOLS
# ============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="inspect_file",
            description="Scan a single file for PHI/PII indicators. Returns risk decision (ALLOW/QUARANTINE/REJECT), risk score, findings, and severity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to inspect (.txt, .csv, or .json)"
                    },
                    "source_system": {
                        "type": "string",
                        "description": "Optional: originating system name for audit metadata"
                    },
                    "submitted_by": {
                        "type": "string",
                        "description": "Optional: user or service submitting the file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="process_inbound",
            description="Batch process all files in inbound/ folder. Routes files to tibco/, quarantine/, or rejected/ based on risk decision.",
            inputSchema={
                "type": "object",
                "properties": {
                    "inbound_dir": {
                        "type": "string",
                        "description": "Inbound folder path (default: 'inbound')",
                        "default": "inbound"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="fetch_audit",
            description="Retrieve latest audit records (scan history) from the audit database. Useful for compliance, monitoring, and decision tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (default: 100)",
                        "default": 100
                    },
                    "decision_filter": {
                        "type": "string",
                        "enum": ["ALLOW", "QUARANTINE", "REJECT"],
                        "description": "Optional: filter audit records by decision type"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="update_rules",
            description="Modify detection rules including thresholds, pattern weights, and keyword lists. Changes apply to subsequent scans.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reject_threshold": {
                        "type": "integer",
                        "description": "Risk score to trigger REJECT (default: 150)"
                    },
                    "quarantine_threshold": {
                        "type": "integer",
                        "description": "Risk score to trigger QUARANTINE (default: 50)"
                    },
                    "pattern_weights": {
                        "type": "object",
                        "description": "Override individual pattern weights (e.g., {'ssn': 120, 'email': 10})",
                        "additionalProperties": {"type": "integer"}
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocations from Spider agents."""
    
    if name == "inspect_file":
        file_path = arguments.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"File not found: {file_path}",
                    "success": False
                }, indent=2)
            )]
        
        try:
            source_system = arguments.get("source_system", "Spider-Agent")
            submitted_by = arguments.get("submitted_by", "mcp-server")
            
            metadata = {
                "source_system": source_system,
                "submitted_by": submitted_by,
            }
            
            result = inspect_file(file_path, metadata=metadata)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "decision": result.get("decision"),
                    "risk_score": result.get("risk_score"),
                    "severity": result.get("severity"),
                    "reason": result.get("reason"),
                    "findings": result.get("findings"),
                    "flagged_data": result.get("flagged_data"),
                    "report_file": result.get("report_file"),
                    "downstream_action": result.get("downstream_action")
                }, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "success": False
                }, indent=2)
            )]
    
    elif name == "process_inbound":
        inbound_dir = arguments.get("inbound_dir", "inbound")
        try:
            result = process_inbound_folder(inbound_dir=inbound_dir, base_dir=".")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "scanned": result.get("scanned"),
                    "allow": result.get("allow"),
                    "quarantine": result.get("quarantine"),
                    "reject": result.get("reject"),
                    "routed_files": result.get("files"),
                    "errors": result.get("errors", [])
                }, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "success": False
                }, indent=2)
            )]
    
    elif name == "fetch_audit":
        limit = arguments.get("limit", 100)
        decision_filter = arguments.get("decision_filter")
        try:
            all_records = fetch_audit()
            if decision_filter:
                filtered = [r for r in all_records if r.get("decision") == decision_filter]
            else:
                filtered = all_records
            
            result_records = filtered[:limit]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "total_records": len(all_records),
                    "returned": len(result_records),
                    "records": result_records
                }, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "success": False
                }, indent=2)
            )]
    
    elif name == "update_rules":
        try:
            from scanner import DECISION_THRESHOLDS, RISK_WEIGHTS, apply_rules
            
            reject_threshold = arguments.get("reject_threshold")
            quarantine_threshold = arguments.get("quarantine_threshold")
            pattern_weights = arguments.get("pattern_weights")
            
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
            
            # Re-apply rules to propagate changes
            rules = load_rule_definitions()
            apply_rules(rules)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": "Rules updated successfully",
                    "changes": changes
                }, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "success": False
                }, indent=2)
            )]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Unknown tool: {name}",
                "success": False
            }, indent=2)
        )]


# ============================================================================
# RESOURCES
# ============================================================================

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available MCP resources."""
    return [
        Resource(
            uri="audit://history",
            name="Audit History",
            description="Latest audit records from scan operations",
            mimeType="application/json"
        ),
        Resource(
            uri="audit://summary",
            name="Audit Summary",
            description="High-level statistics from audit database",
            mimeType="application/json"
        ),
        Resource(
            uri="rules://current",
            name="Current Rules",
            description="Active detection rules and thresholds",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    
    if uri == "audit://history":
        records = fetch_audit()
        return json.dumps({
            "resource": "audit://history",
            "total_records": len(records),
            "latest_records": records[:50]  # Return latest 50
        }, indent=2)
    
    elif uri == "audit://summary":
        records = fetch_audit()
        allow_count = len([r for r in records if r.get("decision") == "ALLOW"])
        quarantine_count = len([r for r in records if r.get("decision") == "QUARANTINE"])
        reject_count = len([r for r in records if r.get("decision") == "REJECT"])
        
        total_risk_score = sum(r.get("risk_score", 0) for r in records)
        avg_risk_score = total_risk_score / len(records) if records else 0
        
        return json.dumps({
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
        }, indent=2)
    
    elif uri == "rules://current":
        rules = load_rule_definitions()
        from scanner import DECISION_THRESHOLDS, RISK_WEIGHTS, PHI_KEYWORDS
        
        return json.dumps({
            "resource": "rules://current",
            "thresholds": DECISION_THRESHOLDS,
            "pattern_weights": RISK_WEIGHTS,
            "phi_keywords": PHI_KEYWORDS,
            "rules_source": DEFAULT_RULES_PATH
        }, indent=2)
    
    else:
        return json.dumps({
            "error": f"Unknown resource: {uri}"
        }, indent=2)


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with server:
        print("PHI/PII Scanner MCP Server running on stdio", file=sys.stderr)
        await server.wait_for_shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
