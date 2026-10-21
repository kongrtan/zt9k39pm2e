# Context: AI System Monitoring Agent Specification for Claude Code

## Objective
Implement an automated AI System Monitoring & Control Agent architecture using **Dify API** and an **External Backend Service**. The agent identifies quantitative and qualitative anomalies (trend/rate of change, error log analysis) and triggers automated alerts and human-in-the-loop control actions.

---

## 1. System Architecture Overview

```
[Cron Scheduler]
       │ (1. Periodic Trigger)
       ▼
[Data Collector] ──(Fetch Logs/Metrics)──► [APM / System DB]
       │
       │ (2. Payload: Metrics + Log Text)
       ▼
[Backend Service / Orchestrator]
       │ (3. Pre-configured System Prompt + Input Payload)
       ▼
[Dify Workflow / Agent API]
       │
       │ (4. Qualitative Analysis & Trend Evaluation)
       ├───────────────────────────────────┐
       ▼ (Anomaly Detected)               ▼ (Action Needed)
[Notification Service]               [Human-in-the-Loop Gateway]
 (Email / Slack Alert)                    │ (Admin Approval)
                                          ▼
                                   [System Control API]
                                    (Execute Recovery Script)
```

---

## 2. Dify Workflow & Prompt Design

### A. System Prompt Template (Pre-configured in Dify or Backend)
```text
You are an expert Automated System Reliability & Monitoring AI Agent.

[Task]
Analyze incoming system metrics and log data to perform both quantitative and qualitative anomaly detection.

[Analysis Rules]
1. Quantitative Threshold: Alert if CPU > 90% or Memory > 90% for over 1 minute.
2. Qualitative & Trend Detection: Evaluate rate of change (velocity). Even if current metrics are below thresholds, flag warnings if steep upward trends or abnormal log text patterns indicate impending failure.
3. Root Cause Estimation: Parse provided error logs/stack traces and summarize the probable cause in 2-3 sentences.
4. Recommendation: Suggest specific remediation actions (e.g., restart service, clear cache).

[Output Format]
Output MUST be structured JSON:
{
  "status": "NORMAL | WARNING | CRITICAL",
  "trend_analysis": "<Brief description of trend>",
  "root_cause_summary": "<Summary of log analysis>",
  "recommended_action": "<Proposed system control script/command>",
  "requires_approval": true | false
}
```

---

## 3. Implementation Requirements for Claude Code

### Task 1: Data Collector & Payload Formatter
* Build a module that queries system metrics (CPU, Memory, Traffic) and recent logs from the target DB/APM.
* Format input data into JSON format required by Dify Workflow API.

### Task 2: Dify API Integration
* Call Dify's `/v1/workflows/run` or `/v1/chat-messages` endpoint via REST client.
* Send system parameters along with the strict system prompt rules.

### Task 3: Human-in-the-Loop Control & Notification Pipeline
* **Notification:** Send formatted summary emails/Slack alerts containing `trend_analysis` and `root_cause_summary`.
* **Action Approval:** Include an interactive approval link/button for any system command proposed under `recommended_action`.
* **Execution:** Trigger `System Control API` only upon admin authorization.

---

## 4. Next Steps for Implementation
1. Configure Dify Workflow nodes (HTTP Request Node for external APIs, Python Node for rapid trend calculations, LLM Node for text reasoning).
2. Generate API Keys in Dify web dashboard.
3. Use Claude Code to scaffold the orchestrator server handling API triggers and webhook callbacks.