# Rollout Threshold Alerts (Doc-First Policy)

This document defines **manual gating rules** for phased MCP rollout. Automation can be added after 2+ weeks of stable telemetry.

## Alert thresholds

| Metric | Warning Threshold | Pause Threshold | Action |
|---|---:|---:|---|
| Cost per session (daily avg) | > baseline high by 10% for 2 days | > baseline high by 20% in one day | Pause rollout stage, run cost root-cause review |
| Tool failure rate (per tool, daily) | > 3% for 2 days | > 5% in one day | Pause rollout stage, open incident + rollback candidate |
| Unknown tool errors | >= 1/day | >= 3/day | Pause rollout stage, validate deployment manifest |

Baseline high cost/session = **$0.024667** derived from `MCP_SERVER_COMPARATIVE_ANALYSIS.md` ($37/1500 sessions).

## Pause workflow

1. Mark current stage as `PAUSED` in rollout tracker.
2. Stop enabling MCP features for new users.
3. Generate `observability/daily_cost_report.py` for the affected date.
4. Identify top offending tool(s) and failure code(s).
5. Require sign-off from Ops + Product before resuming stage.

## Ownership

- **Ops:** Monitoring + pause decision execution.
- **Engineering:** Root-cause analysis and remediation.
- **Product:** Resume approval after risk review.
