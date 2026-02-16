# MCP Observability Dashboard Spec

Concise spec for Ops to validate performance and ROI after introducing **GitHub MCP** and **Qdrant MCP**.

## 1) Data sources

- Structured invocation logs: `observability/logs/tool_invocations.ndjson`.
- Metrics contract: `observability/metrics_schema.json`.
- Daily rollup: `observability/daily_cost_report.py` output in `observability/reports/`.
- Baselines: `MCP_SERVER_COMPARATIVE_ANALYSIS.md`.

## 2) Dashboard panels (minimum viable)

1. **Cost per Session (Daily)**
   - Metric: `per_session_average_token_cost_usd`
   - Overlay baselines: low ($0.010000), high ($0.024667)
   - Goal: stay at or below high baseline.

2. **Token Volume by Session**
   - Metric: input/output tokens by `session_id`
   - View: daily heatmap + p95 session.

3. **Tool Reliability**
   - Metrics: tool call count, latency p50/p95, error rate by `error_code`
   - Goal: tool failure <= 3% warning / <= 5% hard stop.

4. **Cache Efficiency**
   - Metric: hit/miss ratio by tool
   - Goal: trending upward after cache tuning.

5. **ROI: GitHub + Qdrant Additions**
   - GitHub ROI proxy: reduction in unknown tool/config errors + KB sync incidents.
   - Qdrant ROI proxy: lower repeat-session token costs and shorter average latency.
   - Compare last 7 days vs pre-rollout baseline.

## 3) KPI definitions

- **Cost/session:** total token cost for all successful tool calls in session / number of sessions.
- **Tool failure rate:** failed calls / total calls per tool per day.
- **Cache hit ratio:** hits / (hits + misses).
- **Qdrant ROI indicator:** `% drop in returning-session avg token cost`.
- **GitHub ROI indicator:** `% drop in KB drift / config-related incidents`.

## 4) Alert policy linkage

Use `observability/threshold_alerts.md` gating rules:
- If cost/session crosses pause threshold or any tool exceeds failure threshold, **pause rollout stage**.

## 5) Cadence

- Daily 09:00 UTC: run rollup report and review dashboard.
- Weekly: compare 7-day trend vs MCP baseline scenario in comparative analysis.
