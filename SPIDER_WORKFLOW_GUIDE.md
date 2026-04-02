# Spider MCP Integration: PHI/PII Scanner Workflow Design Guide

## Overview

Spider workflows using the PHI/PII Scanner MCP can follow several patterns depending on your business needs. The key is understanding how to chain LLM reasoning + tool calls + conditional routing.

---

## Architecture Fundamentals

### Component Layers

```
┌─────────────────────────────────────────────────┐
│  User Input Layer                              │
│  (Chat Input / File Upload / API Trigger)     │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  LLM Agent Layer                               │
│  (Reasoning + Tool Selection)                  │
│  - Parse user request                          │
│  - Decide which MCP tool to call               │
│  - Handle context + memory                     │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  MCP Tool Integration Layer                    │
│  - inspect_file                                │
│  - process_inbound                             │
│  - fetch_audit                                 │
│  - update_rules                                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Decision + Routing Layer                      │
│  (Conditional logic based on risk decision)    │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Output Layer                                  │
│  - Chat output                                 │
│  - Email alert                                 │
│  - Database log                                │
│  - API callback                                │
└─────────────────────────────────────────────────┘
```

---

## Pre-Requisites for Spider Workflow

Before building workflows, ensure:

1. **MCP HTTP Wrapper Running**
   ```bash
   python mcp_http_wrapper.py
   # Accessible at http://127.0.0.1:5051
   ```

2. **Spider Configuration**
   - Access to HTTP Request node (or REST connector)
   - LLM integration (e.g., OpenAI, Claude, LLaMA)
   - Chat UI (optional but recommended)
   - Conditional routing capabilities
   - Logging/storage nodes

3. **Network Access**
   - If Spider is remote: expose MCP HTTP wrapper (use reverse proxy like nginx)
   - If local: ensure ports 5051 accessible

---

## Workflow Pattern 1: Simple File Inspection (Recommended for Beginners)

### Use Case
User uploads a file → System scans → Shows risk decision + details

### Spider Components

```
┌─────────────────┐
│  Chat Input     │ (User asks to scan a file)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  File Upload Widget             │ (User provides file path or uploads)
└────────┬────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  HTTP Request Node                             │
│  POST /tool/inspect_file                       │
│  Headers: Content-Type: application/json       │
│  Body: {                                       │
│    "file_path": "{{ file_path }}",            │
│    "source_system": "Spider-Workflow",        │
│    "submitted_by": "{{ user_id }}"            │
│  }                                             │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  Conditional Node                              │
│  If response.decision == "REJECT"              │
│    → HIGH RISK path                            │
│  Else if response.decision == "QUARANTINE"     │
│    → MEDIUM RISK path                          │
│  Else                                          │
│    → ALLOWED path                              │
└──┬──────────────────┬──────────────────┬───────┘
   │                  │                  │
   ▼                  ▼                  ▼
┌────┐          ┌──────────┐        ┌──────┐
│REJECT│         │QUARANTINE│        │ALLOW │
│PATH  │         │  PATH    │        │PATH  │
└────┘          └──────────┘        └──────┘
   │                  │                  │
   └──────────────────┴──────────────────┘
            │
            ▼
┌────────────────────────────────────────────────┐
│  Chat Output Node                              │
│  Display:                                      │
│  - Risk Score: {{ response.risk_score }}       │
│  - Decision: {{ response.decision }}           │
│  - Severity: {{ response.severity }}           │
│  - Reason: {{ response.reason }}               │
│  - Flagged Data: {{ response.flagged_data }}   │
└────────────────────────────────────────────────┘
```

### Spider Configuration Steps

1. **Add Chat Input**
   - Prompt: "Upload a file to scan for PHI/PII"
   - Store input in variable: `file_path`

2. **Add HTTP Request Node**
   - Method: POST
   - URL: `http://127.0.0.1:5051/tool/inspect_file`
   - Body Type: JSON
   - Map response to `scan_result`

3. **Add Conditional Node**
   - Check `scan_result.decision` value

4. **Add Chat Output (3 branches)**
   - HIGH RISK branch: "⚠️ REJECTED - HIGH RISK DETECTED"
   - MEDIUM RISK branch: "⚠️ QUARANTINE - REQUIRES REVIEW"
   - LOW RISK branch: "✅ ALLOWED - SAFE TO PROCEED"

### Conversation Flow Example

```
User: "Scan the file at uploads/employee_data.csv"

Spider:
Step 1: Parse file path ✓
Step 2: Calling PHI/PII scanner...
Step 3: Analysis complete

Result: QUARANTINE (Risk Score: 78/150)
- Severity: MEDIUM
- Reason: Multiple PHI indicators detected including email and phone numbers
- Flagged Data:
  * Email: jo***@company.com
  * Phone: ***-***-4567
  * Keywords: patient, diagnosis

Next Steps:
→ Route to quarantine/ folder
→ Notify compliance team
→ Hold for manual review
```

---

## Workflow Pattern 2: Intelligent Agent (Advanced - Recommended for Production)

### Use Case
User describes task → LLM reasons about which scanner tools to use → Executes sequentially

### Design Philosophy

Unlike Pattern 1 (fixed routing), this uses an **agentic loop** where an LLM decides:
- Should I scan a file?
- Should I check audit history?
- Should I update rules?
- How to interpret results?

### Spider Components

```
┌────────────────────────────────┐
│  Chat Input                    │
│  "Scan this file and check if  │
│   we've seen similar issues"   │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│  System Prompt Node                        │
│  (Set agent personality)                   │
│                                            │
│  "You are a PHI/PII compliance agent.     │
│   You have access to these tools:         │
│   - inspect_file (scan a file)            │
│   - fetch_audit (check history)           │
│   - update_rules (adjust thresholds)      │
│                                            │
│   First, scan the file. Then check       │
│   recent audit records to see if         │
│   similar patterns exist."                │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│  LLM Chain / Agent Node                    │
│  (Claude, OpenAI, LLaMA, etc.)            │
│                                            │
│  Input: User message + file path +        │
│         available tools                    │
│  Process: LLM reasons about next step     │
│  Output: Tool call or response text       │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│  Tool Router (Conditional Logic)           │
│  If LLM decision == "call inspect_file":   │
│    → Branch A (Inspect)                    │
│  Else if == "call fetch_audit":            │
│    → Branch B (Audit)                      │
│  Else if == "update_rules":                │
│    → Branch C (Rules)                      │
│  Else:                                     │
│    → Chat Output (Final response)          │
└─┬────────┬──────────┬──────────────────────┘
  │        │          │
  ▼        ▼          ▼
 ┌─A──┐ ┌─B──┐ ┌─C──┐
 │... │ │... │ │... │
 └─┬──┘ └─┬──┘ └─┬──┘
   :      :      :
   └──────┴──────┘
        │
        ▼
  (Loop back to LLM
   with results)
        │
        ▼
┌────────────────────────────────────────────┐
│  Chat Output                               │
│  (Return final analysis to user)           │
└────────────────────────────────────────────┘
```

### Spider Configuration Steps

1. **Add Chat Input** with system context
   - User query variable: `user_message`

2. **Add System Prompt Node** (set agent instructions)
   ```
   You are a PHI/PII compliance specialist assistant.
   
   You have access to tools:
   
   Tool 1: inspect_file
   - Scans a file for PHI/PII
   - Returns: decision, risk_score, findings
   
   Tool 2: fetch_audit
   - Retrieves scan history
   - Helps identify patterns
   
   Tool 3: update_rules
   - Allows dynamic threshold adjustment
   
   When a user asks you to scan:
   1. First call inspect_file
   2. Analyze the result
   3. Call fetch_audit to check for similar cases
   4. Provide recommendations based on findings
   ```

3. **Add LLM Node** (Agent reasoning)
   - Model: OpenAI / Claude / etc.
   - Prompt: Combine system prompt + user message
   - Tools available: Map all 3 MCP tools
   - Store output: `agent_decision`

4. **Add Conditional Router**
   - If `agent_decision.tool == "inspect_file"`:
     - Branch to HTTP POST /tool/inspect_file
   - Else if `agent_decision.tool == "fetch_audit"`:
     - Branch to HTTP GET /resource/audit/summary
   - Else:
     - Output final response

5. **Loop Back to Agent** (if tool was called)
   - Pass tool result back to LLM
   - Let LLM decide next action

6. **Chat Output** (final response)

### Conversation Flow Example

```
User: "Scan employee_data.csv and tell me if we've 
      had similar issues with this file type recently"

Agent (LLM reasoning):
  "I need to:
   1. Scan the file to see current risk
   2. Check audit history for similar files
   3. Provide insights"

[Calls inspect_file]
Response: REJECT, Risk Score 230, SSN detected

Agent (analyzing):
  "High risk - SSN found. Let me check if we've 
   seen this pattern before."

[Calls fetch_audit with filter REJECT]
Response: 12 rejection records, 8 with SSN present

Agent (final analysis):
  "This file contains an SSN and is REJECTED.
   
   Trend: We've seen 8 similar rejections in the 
   past 30 days, all with direct identifier SSNs.
   
   Recommendation:
   - Move to rejected/ folder immediately
   - Check data source for control failures
   - Request redaction before resubmission"

Output to User: [Detailed analysis + recommendations]
```

---

## Workflow Pattern 3: Batch Processing + Compliance Dashboard

### Use Case
Schedule daily batch processing → Generate compliance report → Update dashboard

### Components

```
┌──────────────────┐
│  Schedule Trigger│ (Daily 2 AM)
│  (Cron Node)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  HTTP Request: process_inbound           │
│  POST /tool/process_inbound              │
│  {"inbound_dir": "inbound"}              │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Extract Results                         │
│  - scanned: {{ response.scanned }}       │
│  - allow: {{ response.allow }}           │
│  - quarantine: {{ response.quarantine }} │
│  - reject: {{ response.reject }}         │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  HTTP Request: fetch audit summary       │
│  GET /resource/audit/summary             │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Format Dashboard Payload                │
│  {                                       │
│    "date": timestamp,                    │
│    "files_processed": scanned,           │
│    "allow_count": allow,                 │
│    "quarantine_count": quarantine,       │
│    "reject_count": reject,               │
│    "avg_risk_score": avg_score           │
│  }                                       │
└────────┬─────────────────────────────────┘
         │
         ├─→ Database (Store results)
         │
         ├─→ Email Alert (Daily report)
         │
         └─→ Dashboard Update (UI refresh)
```

### Spider Configuration

1. **Schedule Trigger Node**
   - Trigger type: Cron
   - Schedule: 0 2 * * * (2 AM daily)

2. **HTTP Request Node 1**
   - POST /tool/process_inbound

3. **Data Transform Node**
   - Extract and format metrics

4. **HTTP Request Node 2**
   - GET /resource/audit/summary

5. **Multiple Output Branches**
   - Database insert (compliance archive)
   - Email send (daily report)
   - Webhook (update dashboard)

### Output Example

```
Subject: Daily PHI/PII Compliance Report - 2026-04-02

Summary:
  Files Processed: 12
  ✅ ALLOW: 5 files
  ⚠️ QUARANTINE: 4 files (held for review)
  ❌ REJECT: 3 files (blocked)

Trends:
  Average Risk Score: 125 / 150
  High-Risk Patterns: SSN (3 cases), Email (6 cases)
  
Actions Required:
  - Review quarantine/ folder
  - Contact data sources about 3 rejections
  
Dashboard: https://compliance.company.com/2026-04-02
```

---

## Workflow Pattern 4: Rule Tuning Loop (Dynamic Governance)

### Use Case
Monitor audit metrics → If too many false positives → Adjust thresholds → Re-scan

### Components

```
Step 1: Monitor Metrics
  │
  ├─→ fetch_audit (get summary)
  │
  └─→ Analyze: quarantine_count > threshold?
       │
       NO: Exit (metrics normal)
       │
       YES: Continue to Step 2
           │
           ▼
Step 2: Human Review
  │
  ├─→ Query recent quarantine records
  │
  ├─→ Present to compliance officer
  │   "We have 10 quarantine in 24h.
  │    Should we lower threshold?"
  │
  └─→ Get approval/decision
       │
       YES: Continue to Step 3
       │
       NO: Exit (keep current rules)
           │
           ▼
Step 3: Update Rules
  │
  ├─→ POST /tool/update_rules
  │
  ├─→ New quarantine_threshold: 40 (was 50)
  │
  └─→ Log change in audit
       │
       ▼
Step 4: Re-Process
  │
  ├─→ Call process_inbound
  │
  ├─→ Measure new outcomes
  │
  └─→ Validate reduction in false positives
```

---

## Component Checklist for Spider Workflows

### Always Include

- ✅ **Chat Input Node** - Accept user requests
- ✅ **System Prompt Node** - Guide agent behavior
- ✅ **HTTP Request Node(s)** - Call MCP endpoints
- ✅ **Conditional Router** - Route based on decision
- ✅ **Chat Output Node** - Respond to user
- ✅ **Error Handler** - Graceful failure handling

### Optionally Include (Based on Pattern)

- ⚪ **LLM/Agent Node** - For intelligent workflows
- ⚪ **Loop/Iteration** - For multi-step processes
- ⚪ **Database Node** - Store results
- ⚪ **Email Node** - Send alerts
- ⚪ **Webhook Node** - Trigger external systems
- ⚪ **Schedule Trigger** - For batch processes
- ⚪ **Memory/Conversation Store** - Maintain context

---

## MCP Tool Mapping for Spider

### Tool 1: inspect_file

**When to Use:**
- User uploads a single file for analysis
- Interactive feedback needed immediately
- One-off compliance check

**HTTP Configuration:**
```
Method: POST
URL: http://127.0.0.1:5051/tool/inspect_file

Headers:
  Content-Type: application/json

Body Template:
{
  "file_path": "{{ user_file_path }}",
  "source_system": "Spider-Workflow",
  "submitted_by": "{{ current_user_id }}"
}

Response Variables:
  decision: response.decision
  risk_score: response.risk_score
  severity: response.severity
  findings: response.findings
```

**Best With:**
```
Chat Input 
  ↓
HTTP POST /tool/inspect_file
  ↓
Conditional (decision)
  ↓
Chat Output
```

### Tool 2: process_inbound

**When to Use:**
- Batch processing of folder contents
- Scheduled daily/weekly scans
- Bulk file routing

**HTTP Configuration:**
```
Method: POST
URL: http://127.0.0.1:5051/tool/process_inbound

Body:
{
  "inbound_dir": "inbound"
}

Response Variables:
  scanned: response.scanned
  allow: response.allow
  quarantine: response.quarantine
  reject: response.reject
  files: response.routed_files
```

**Best With:**
```
Schedule Trigger
  ↓
HTTP POST /tool/process_inbound
  ↓
Database Store
  ↓
Email Alert + Dashboard Update
```

### Tool 3: fetch_audit

**When to Use:**
- Compliance reporting
- Historical analysis
- Pattern detection
- Agent decision-making

**HTTP Configuration:**
```
Method: POST
URL: http://127.0.0.1:5051/tool/fetch_audit

Body:
{
  "limit": 50,
  "decision_filter": "QUARANTINE"  // optional
}

Response Variables:
  total_records: response.total_records
  records: response.records
  returns: response.returned
```

**Best With:**
```
LLM Agent (needs historical context)
  ↓
HTTP POST /tool/fetch_audit
  ↓
Agent Analyzes Pattern
  ↓
Generate Insights/Recommendations
```

### Tool 4: update_rules

**When to Use:**
- Dynamic threshold adjustment
- Policy changes
- A/B testing thresholds
- Requires approval workflow

**HTTP Configuration:**
```
Method: POST
URL: http://127.0.0.1:5051/tool/update_rules

Body:
{
  "quarantine_threshold": 40,
  "reject_threshold": 120,
  "pattern_weights": {
    "ssn": 120,
    "email": 15
  }
}

Response Variables:
  success: response.success
  changes: response.changes
```

**Best With:**
```
Approval Gate (human decision)
  ↓
HTTP POST /tool/update_rules
  ↓
Log Change to Audit
  ↓
Re-process with new rules
```

---

## Recommended Spider Workflow Design (My Suggestion)

### Start With Pattern 1 (Simple) + Evolve

**Phase 1 - Foundation (Week 1)**
- Build Pattern 1 (Simple File Inspection)
- Test with sample files
- Get stakeholder feedback

**Phase 2 - Enhancement (Week 2-3)**
- Add Pattern 3 (Daily batch)
- Set up email alerts
- Build compliance dashboard

**Phase 3 - Intelligence (Week 4+)**
- Implement Pattern 2 (Agent)
- Add Pattern 4 (Rule tuning)
- Multi-tool orchestration

### Why This Order?

1. **Pattern 1** teaches Spider ↔ MCP integration basics
2. **Pattern 3** adds value immediately (daily compliance reports)
3. **Pattern 2** leverages your LLM for intelligent workflows
4. **Pattern 4** enables continuous improvement

---

## Key Spider Settings to Configure

### 1. HTTP Request Node Settings

```
Timeout: 30 seconds
Retry on Failure: 3 attempts with 5s backoff
Error Handling: Catch and respond gracefully
Request Body: JSON
Response Parser: JSON
```

### 2. Conditional Node Settings

```
Condition Type: Expression
Operators: ==, !=, >, <, contains, in
Multiple Branches: Yes
Default Branch: Set to safe fallback
```

### 3. Chat Output Settings

```
Format: Markdown (for rich formatting)
Variables: All response fields accessible
Message History: Store in context
Role: Assistant (from Spider perspective)
```

### 4. LLM Node Settings (if Pattern 2)

```
Model: Claude-3.5 / GPT-4 (recommended)
Temperature: 0.7 (precise but flexible)
Max Tokens: 2000
Tool Calling: Enabled
Function Schema: Map MCP tools
```

---

## Error Handling Considerations

### Common Failure Points

1. **File Not Found**
   ```
   if response.error contains "File not found":
     → User friendly message
     → Suggest correct path
   ```

2. **Network Timeout**
   ```
   if http_request.status_code == timeout:
     → Retry up to 3 times
     → Fallback to cached result if available
   ```

3. **Database Locked**
   ```
   if response.error contains "database is locked":
     → Wait and retry
     → Inform user of processing queue
   ```

### Add to Every Workflow

```
Try-Catch Block:
  Try:
    [Your normal flow]
  Catch Error:
    - Log error details
    - Notify admin if critical
    - Return user-friendly message
    - Don't expose internal details
```

---

## Testing Your Spider Workflow

### Step 1: Validate MCP Connection

```
HTTP GET http://127.0.0.1:5051/health

Expected Response:
{
  "status": "ok",
  "service": "phi-pii-scanner-mcp-http"
}
```

### Step 2: Test Single Tool

```
Workflow:
  Chat Input 
    ↓
  HTTP POST /tool/inspect_file (with test data)
    ↓
  Chat Output (show raw response)

Verify: All fields present + correct types
```

### Step 3: Test Conditional Logic

```
Scenario 1: decision == "ALLOW" → Check branch
Scenario 2: decision == "QUARANTINE" → Check branch
Scenario 3: decision == "REJECT" → Check branch
Scenario 4: Error response → Check error handler
```

### Step 4: Test Full Workflow

```
End-to-end with real sample files:
  - samples/sample_phi.txt (should REJECT)
  - samples/sample_medium.json (should QUARANTINE)
  - samples/sample_safe.txt (should ALLOW)
```

---

## Production Deployment Checklist

Before going live in Spider:

- ✅ MCP HTTP wrapper running 24/7 (e.g., systemd service)
- ✅ Database backups (audit.db) configured
- ✅ Error notifications set up (Slack/email)
- ✅ Load testing done (expected throughput)
- ✅ Compliance approved workflow design
- ✅ User training completed
- ✅ Fallback procedures documented
- ✅ Audit logging enabled in Spider too
- ✅ Rate limiting configured if needed
- ✅ Access control configured (who can trigger workflows)

---

## Summary: Recommended Start

**For your manager demo tomorrow + Spider rollout:**

### Recommended Approach

1. **Build Pattern 1 first** in Spider
   - Simplest to understand
   - Proves MCP integration works
   - Immediate ROI (users can scan files)

2. **Wire up 1 sample workflow**
   - Chat Input → HTTP POST inspect_file → Conditional → Chat Output
   - Test with samples/sample_phi.txt
   - Show risk decision in beautiful UI

3. **Show decision logic**
   - Highlight which patterns triggered
   - Show risk score calculation
   - Explain downstream action

4. **Plan Pattern 3 next**
   - Daily compliance reports add huge value
   - Minimal additional complexity

5. **Evolve to Pattern 2 over time**
   - Once team comfortable with MCP
   - Can build sophisticated agent workflows

---

This gives you a **clear roadmap** for Spider integration!
