from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def load_recent_records(minutes: int = 60) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    records: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            timestamp = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if timestamp >= cutoff:
            records.append(record)
    return records


def dashboard_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    requests = [item for item in records if item.get("event") == "request_received"]
    responses = [item for item in records if item.get("event") == "response_sent"]
    failures = [item for item in records if item.get("event") == "request_failed"]
    latencies = [float(item["latency_ms"]) for item in responses if "latency_ms" in item]
    ttfts = [float(item["ttft_ms"]) for item in responses if "ttft_ms" in item]
    tool_results = [item for item in records if item.get("tool_success") is not None]
    retrieval_success = (
        100 * sum(item.get("tool_success") is True for item in tool_results) / len(tool_results)
        if tool_results
        else 0.0
    )
    error_rate = 100 * len(failures) / len(requests) if requests else 0.0
    error_breakdown: dict[str, int] = {}
    for item in failures:
        error_type = str(item.get("error_type", "unknown"))
        error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
    quality = [float(item["quality_score"]) for item in responses if "quality_score" in item]
    return {
        "request_count": len(requests),
        "rate_per_minute": len(requests) / 60,
        "latency_p50": _percentile(latencies, 50),
        "latency_p95": _percentile(latencies, 95),
        "latency_p99": _percentile(latencies, 99),
        "ttft_p95": _percentile(ttfts, 95),
        "error_rate": error_rate,
        "error_breakdown": error_breakdown,
        "retrieval_success": retrieval_success,
        "cost_total": sum(float(item.get("cost_usd", 0)) for item in responses),
        "tokens_in": sum(int(item.get("tokens_in", 0)) for item in responses),
        "tokens_out": sum(int(item.get("tokens_out", 0)) for item in responses),
        "quality_mean": sum(quality) / len(quality) if quality else 0.0,
    }


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _panel(title: str, unit: str, threshold: str, content: str) -> str:
    return (
        '<section class="panel">'
        f'<div class="panel-head"><h2>{escape(title)}</h2><span>{escape(unit)}</span></div>'
        f'<div class="metrics">{content}</div>'
        f'<div class="threshold">SLO threshold · {escape(threshold)}</div>'
        "</section>"
    )


def render_dashboard() -> str:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
    records = load_recent_records(config["time_range_minutes"])
    values = dashboard_metrics(records)
    panels = {panel["id"]: panel for panel in config["panels"]}

    latency = _panel(
        panels["latency"]["title"],
        panels["latency"]["unit"],
        "P95 ≤ 3,000 ms",
        "".join(
            (
                _metric("P50", f'{values["latency_p50"]:.0f} ms'),
                _metric("P95", f'{values["latency_p95"]:.0f} ms'),
                _metric("P99", f'{values["latency_p99"]:.0f} ms'),
                _metric("TTFT P95", f'{values["ttft_p95"]:.0f} ms'),
            )
        ),
    )
    traffic = _panel(
        panels["traffic"]["title"],
        panels["traffic"]["unit"],
        "rate ≥ 1 request/min",
        _metric("Requests", str(values["request_count"]))
        + _metric("Rate", f'{values["rate_per_minute"]:.2f}/min'),
    )
    breakdown = ", ".join(
        f"{name}: {count}" for name, count in values["error_breakdown"].items()
    ) or "none"
    errors = _panel(
        panels["errors"]["title"],
        panels["errors"]["unit"],
        "error rate ≤ 2% · retrieval ≥ 90%",
        _metric("Error rate", f'{values["error_rate"]:.2f}%')
        + _metric("Retrieval success", f'{values["retrieval_success"]:.1f}%')
        + _metric("Breakdown", breakdown),
    )
    cost = _panel(
        panels["cost"]["title"],
        panels["cost"]["unit"],
        "total ≤ $2.50",
        _metric("60-minute total", f'${values["cost_total"]:.4f}'),
    )
    tokens = _panel(
        panels["tokens"]["title"],
        panels["tokens"]["unit"],
        "combined ≤ 50,000 tokens",
        _metric("Input", f'{values["tokens_in"]:,}')
        + _metric("Output", f'{values["tokens_out"]:,}')
        + _metric("Combined", f'{values["tokens_in"] + values["tokens_out"]:,}'),
    )
    quality = _panel(
        panels["quality"]["title"],
        panels["quality"]["unit"],
        "mean ≥ 0.75",
        _metric("Mean quality", f'{values["quality_mean"]:.2f}'),
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="{config['refresh_seconds']}">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(config['title'])}</title>
<style>
:root{{--bg:#07111f;--card:#101f33;--line:#29415f;--text:#edf5ff;--muted:#8fa7c2;--cyan:#4ed7d1;--amber:#ffbf69}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0,#12304a 0,var(--bg) 42%);color:var(--text);font:15px Inter,Segoe UI,sans-serif}}
main{{max-width:1240px;margin:auto;padding:32px}} header{{display:flex;justify-content:space-between;align-items:end;margin-bottom:22px}} h1{{font-size:28px;margin:0 0 8px}} p{{color:var(--muted);margin:0}} .live{{color:var(--cyan);font-weight:700}} .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}
.panel{{min-height:220px;background:linear-gradient(145deg,rgba(18,39,61,.96),rgba(10,25,42,.96));border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 12px 34px rgba(0,0,0,.2)}}
.panel-head{{display:flex;justify-content:space-between;gap:16px;align-items:start}} h2{{font-size:17px;margin:0}} .panel-head span{{color:var(--muted);font-size:12px;text-transform:uppercase}} .metrics{{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}}
.metric{{flex:1;min-width:125px;background:#0a1728;border:1px solid #203a59;border-radius:11px;padding:13px}} .metric span{{display:block;color:var(--muted);font-size:12px;margin-bottom:8px}} .metric strong{{font-size:22px;color:var(--cyan)}}
.threshold{{border-top:1px solid var(--line);padding-top:13px;color:var(--amber);font-size:12px}} @media(max-width:760px){{.grid{{grid-template-columns:1fr}}header{{display:block}}.live{{margin-top:10px}}}}
</style></head><body><main><header><div><h1>{escape(config['title'])}</h1><p>Source: data/logs.jsonl · Window: last {config['time_range_minutes']} minutes · Refresh: {config['refresh_seconds']} seconds</p></div><div class="live">● LIVE · {len(records)} records</div></header>
<div class="grid">{latency}{traffic}{errors}{cost}{tokens}{quality}</div></main></body></html>"""
