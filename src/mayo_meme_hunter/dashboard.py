"""Dependency-free static HTML report for offline paper replay results."""
from __future__ import annotations

from html import escape
from typing import Any


def _fmt(value: Any, prefix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{prefix}{value:,.3f}"
    return f"{prefix}{value}"


def render_dashboard(data: dict) -> str:
    summary = data.get("summary") or {}
    trades = data.get("trades") or []
    decisions = data.get("decisions") or []
    metrics = [
        ("Mode", summary.get("mode")),
        ("Marked equity", _fmt(summary.get("marked_equity_usd"), "$")),
        ("Realized P&L", _fmt(summary.get("realized_pnl_usd"), "$")),
        ("Closed trades", summary.get("closed_trades")),
        ("Win rate", _fmt(None if summary.get("win_rate") is None else 100 * summary["win_rate"], "") + "%" if summary.get("win_rate") is not None else "N/A"),
        ("Profit factor", summary.get("profit_factor")),
        ("Max drawdown", _fmt(summary.get("max_observed_drawdown_pct")) + "%"),
        ("Trapped positions", summary.get("trapped_positions")),
    ]
    metric_html = "".join(
        f'<div class="metric"><small>{escape(str(label))}</small><strong>{escape(str(value))}</strong></div>'
        for label, value in metrics
    )
    trade_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(trade.get(key, '')))}</td>" for key in
                             ("symbol", "entry_ts", "exit_ts", "pnl_usd", "reason")) + "</tr>"
        for trade in trades
    )
    decision_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(decision.get(key, '')))}</td>" for key in
                             ("ts", "mint", "action", "reason")) + "</tr>"
        for decision in decisions[-100:]
    )
    # Render a deterministic offline cumulative realized P&L plot.
    points = [(0, 0.0)]
    running = 0.0
    for i, trade in enumerate(trades, 1):
        running += float(trade.get("pnl_usd", 0))
        points.append((i, running))
    ys = [y for _, y in points]
    lo, hi = min(ys), max(ys)
    span = max(hi - lo, 1.0)
    count = max(len(points) - 1, 1)
    polyline = " ".join(f"{40 + 720 * x / count:.1f},{200 - 160 * (y - lo) / span:.1f}" for x, y in points)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAYO MEME HUNTER — Paper Report</title>
<style>
:root {{ color-scheme:dark; font-family:system-ui,-apple-system,sans-serif; }}
body {{ background:#0b111c; color:#edf3fb; max-width:1100px; margin:auto; padding:28px; }}
h1 {{ letter-spacing:.06em; margin-bottom:0; }} p,small {{ color:#aab8ca; }}
.warning {{ border:1px solid #e5aa53; padding:12px; border-radius:10px; color:#ffdba7; }}
.metrics {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:22px 0; }}
.metric {{ background:#172337;padding:16px;border-radius:12px;display:grid;gap:6px; }}
.metric strong {{ font-size:22px; }} section {{ margin-top:28px; }}
table {{ width:100%;border-collapse:collapse;font-size:13px; }} th,td {{ padding:10px;border-bottom:1px solid #344052;text-align:left;word-break:break-word; }}
.wrap {{ overflow-x:auto; }} svg {{ width:100%;height:auto;background:#142032;border-radius:12px; }}
</style></head><body>
<h1>MAYO MEME HUNTER</h1><p>Snag &amp; Go — Offline paper-replay dashboard</p>
<div class="warning">PAPER ONLY. Synthetic example data is not real performance. No live orders or wallet access.</div>
<div class="metrics">{metric_html}</div>
<section><h2>Cumulative realized P&amp;L (USD)</h2>
<svg viewBox="0 0 800 230" role="img" aria-label="Cumulative realized profit and loss">
<path d="M40 30 V200 H760" fill="none" stroke="#52657d" stroke-width="2"/>
<polyline points="{polyline}" fill="none" stroke="#67d3af" stroke-width="3"/>
<text x="45" y="22" fill="#b9c6d5" font-size="12">${hi:.2f} max</text>
<text x="45" y="218" fill="#b9c6d5" font-size="12">${lo:.2f} min</text>
</svg></section>
<section><h2>Closed paper trades</h2><div class="wrap"><table>
<tr><th>Symbol</th><th>Entry timestamp (UTC)</th><th>Exit timestamp (UTC)</th><th>Net P&amp;L ($)</th><th>Reason</th></tr>
{trade_rows}</table></div></section>
<section><h2>Recent decisions</h2><div class="wrap"><table>
<tr><th>Timestamp (UTC)</th><th>Mint</th><th>Action</th><th>Reason</th></tr>
{decision_rows}</table></div></section>
<p>Research prototype. Price marks and simulated fills are not executable quotes.</p>
</body></html>'''
