from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app import dashboard


def test_dashboard_renders_six_panels_from_recent_jsonl(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = [
        {
            "ts": timestamp,
            "event": "request_received",
        },
        {
            "ts": timestamp,
            "event": "response_sent",
            "latency_ms": 180,
            "ttft_ms": 55,
            "cost_usd": 0.002,
            "tokens_in": 30,
            "tokens_out": 100,
            "quality_score": 0.9,
            "tool_success": True,
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard, "LOG_PATH", log_path)

    html = dashboard.render_dashboard()

    for title in (
        "Latency percentiles and TTFT",
        "Request traffic",
        "Error rate and retrieval success",
        "Cost over time",
        "Input and output tokens",
        "Quality proxy",
    ):
        assert title in html
    assert "P95 ≤ 3,000 ms" in html
    assert "180 ms" in html
    assert "100.0%" in html
