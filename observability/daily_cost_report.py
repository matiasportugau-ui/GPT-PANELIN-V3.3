#!/usr/bin/env python3
"""Generate daily MCP cost and reliability rollup from structured invocation logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# Baselines sourced from MCP_SERVER_COMPARATIVE_ANALYSIS.md (Cost-Efficient Configuration)
BASELINE_MONTHLY_COST_LOW = 15.0
BASELINE_MONTHLY_COST_HIGH = 37.0
BASELINE_SESSIONS_PER_MONTH = 1500
BASELINE_COST_PER_SESSION_LOW = BASELINE_MONTHLY_COST_LOW / BASELINE_SESSIONS_PER_MONTH
BASELINE_COST_PER_SESSION_HIGH = BASELINE_MONTHLY_COST_HIGH / BASELINE_SESSIONS_PER_MONTH

# Token pricing noted in MCP_SERVER_COMPARATIVE_ANALYSIS.md (OpenAI GPT-4o estimate)
INPUT_COST_PER_MILLION = 5.0
OUTPUT_COST_PER_MILLION = 15.0


@dataclass
class SessionTotals:
    input_tokens: int = 0
    output_tokens: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build daily MCP observability cost report")
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path("observability/logs/tool_invocations.ndjson"),
        help="Structured log path produced by mcp.observability logger.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=date.today().isoformat(),
        help="UTC date to aggregate (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("observability/reports/daily_cost_report.json"),
        help="Output report path.",
    )
    return parser.parse_args()


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens / 1_000_000 * INPUT_COST_PER_MILLION)
        + (output_tokens / 1_000_000 * OUTPUT_COST_PER_MILLION),
        6,
    )


def _read_events(log_path: Path, target_day: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not log_path.exists():
        return events

    with log_path.open(encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            ts = payload.get("ts")
            if not ts:
                continue
            parsed_day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
            if parsed_day == target_day:
                events.append(payload)
    return events


def build_report(events: list[dict[str, Any]], report_day: str) -> dict[str, Any]:
    sessions: dict[str, SessionTotals] = defaultdict(SessionTotals)
    tool_call_count: dict[str, int] = defaultdict(int)
    tool_error_count: dict[str, int] = defaultdict(int)

    for event in events:
        event_type = event.get("event")
        session_id = event.get("session_id") or "unknown"
        tool_name = event.get("tool_name") or "unknown_tool"

        if event_type == "tool_invocation_success":
            sessions[session_id].input_tokens += int(event.get("token_input") or 0)
            sessions[session_id].output_tokens += int(event.get("token_output") or 0)
            tool_call_count[tool_name] += 1
        elif event_type == "tool_invocation_error":
            tool_call_count[tool_name] += 1
            tool_error_count[tool_name] += 1

    session_costs: dict[str, float] = {}
    for session_id, totals in sessions.items():
        session_costs[session_id] = _estimate_cost_usd(totals.input_tokens, totals.output_tokens)

    avg_session_cost = round(sum(session_costs.values()) / len(session_costs), 6) if session_costs else 0.0
    low_delta = round(avg_session_cost - BASELINE_COST_PER_SESSION_LOW, 6)
    high_delta = round(avg_session_cost - BASELINE_COST_PER_SESSION_HIGH, 6)

    tool_failure_rates: dict[str, float] = {}
    for tool_name, count in tool_call_count.items():
        failures = tool_error_count.get(tool_name, 0)
        tool_failure_rates[tool_name] = round(failures / count, 6) if count else 0.0

    return {
        "report_date": report_day,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sessions_observed": len(session_costs),
        "per_session_average_token_cost_usd": avg_session_cost,
        "baseline_cost_per_session_low_usd": round(BASELINE_COST_PER_SESSION_LOW, 6),
        "baseline_cost_per_session_high_usd": round(BASELINE_COST_PER_SESSION_HIGH, 6),
        "cost_delta_vs_baseline_low_usd": low_delta,
        "cost_delta_vs_baseline_high_usd": high_delta,
        "session_costs_usd": session_costs,
        "tool_failure_rates": tool_failure_rates,
        "source": "MCP_SERVER_COMPARATIVE_ANALYSIS.md",
    }


def main() -> None:
    args = parse_args()
    events = _read_events(args.log_path, args.date)
    report = build_report(events, args.date)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
