"""Append-only launch research, forward outcome labels, and rule experiments.

This module is strictly offline/read-only with respect to Solana. It never
creates wallets, signs transactions, requests quotes, or submits orders.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

DEFAULT_HORIZONS_MINUTES = (1, 5, 10, 15, 30, 60)
SCHEMA_VERSION = 1


def _epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    raise ValueError("timestamp must be epoch seconds or ISO-8601")


def _finite_positive(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if result <= 0 or result != result or result == float("inf"):
        raise ValueError(f"{field} must be finite and positive")
    return result


class ResearchStore:
    """SQLite evidence store. Raw source payloads are retained for auditability."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS launch_events (
                    id INTEGER PRIMARY KEY,
                    provider TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    mint TEXT NOT NULL,
                    observed_at REAL NOT NULL,
                    creator TEXT,
                    signature TEXT,
                    payload_json TEXT NOT NULL,
                    UNIQUE(provider, event_type, mint, observed_at, signature)
                );
                CREATE INDEX IF NOT EXISTS idx_launch_mint_time
                    ON launch_events(mint, observed_at);
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY,
                    mint TEXT NOT NULL,
                    ts REAL NOT NULL,
                    price_usd REAL NOT NULL,
                    liquidity_usd REAL,
                    volume_5m_usd REAL,
                    buys_5m INTEGER,
                    sells_5m INTEGER,
                    unique_buyers_5m INTEGER,
                    top10_pct REAL,
                    creator_pct REAL,
                    price_change_5m_pct REAL,
                    source TEXT,
                    payload_json TEXT NOT NULL,
                    UNIQUE(mint, ts, source)
                );
                CREATE INDEX IF NOT EXISTS idx_snap_mint_time
                    ON market_snapshots(mint, ts);
                CREATE TABLE IF NOT EXISTS outcome_labels (
                    event_id INTEGER NOT NULL,
                    horizon_minutes INTEGER NOT NULL,
                    entry_ts REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_ts REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    return_pct REAL NOT NULL,
                    max_runup_pct REAL NOT NULL,
                    max_drawdown_pct REAL NOT NULL,
                    capture_delay_seconds REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(event_id, horizon_minutes),
                    FOREIGN KEY(event_id) REFERENCES launch_events(id)
                );
            """)
            db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)",
                       (str(SCHEMA_VERSION),))

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=20000")
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def ingest_events(self, rows: Iterable[dict[str, Any]]) -> dict[str, int]:
        inserted = rejected = 0
        with self._connect() as db:
            for row in rows:
                try:
                    mint = str(row.get("mint") or "").strip()
                    kind = str(row.get("event_type") or row.get("txType") or "").lower()
                    if kind in {"migrate", "migration"}:
                        kind = "migration"
                    if kind in {"new", "new_token", "create"}:
                        kind = "create"
                    if not mint or kind not in {"create", "migration"}:
                        rejected += 1
                        continue
                    provider = str(row.get("provider") or "unknown")
                    observed = _epoch(row.get("observed_at", row.get("timestamp")))
                    cursor = db.execute("""INSERT OR IGNORE INTO launch_events
                        (provider,event_type,mint,observed_at,creator,signature,payload_json)
                        VALUES(?,?,?,?,?,?,?)""",
                        (provider, kind, mint, observed, row.get("creator"),
                         str(row.get("signature") or ""), json.dumps(row, sort_keys=True, default=str)))
                    inserted += cursor.rowcount
                except (TypeError, ValueError, OverflowError):
                    rejected += 1
        return {"inserted": inserted, "rejected": rejected}

    def ingest_snapshots(self, rows: Iterable[dict[str, Any]]) -> dict[str, int]:
        inserted = rejected = 0
        with self._connect() as db:
            for row in rows:
                try:
                    mint = str(row.get("mint") or "").strip()
                    if not mint:
                        raise ValueError("missing mint")
                    ts = _epoch(row.get("ts", row.get("observed_at")))
                    price = _finite_positive(row.get("price_usd"), "price_usd")
                    optional = {}
                    for field in ("liquidity_usd", "volume_5m_usd", "top10_pct",
                                  "creator_pct", "price_change_5m_pct"):
                        value = row.get(field)
                        optional[field] = None if value is None else float(value)
                    buys = row.get("buys_5m")
                    sells = row.get("sells_5m")
                    buyers = row.get("unique_buyers_5m")
                    source = str(row.get("source") or "unknown")
                    cursor = db.execute("""INSERT OR IGNORE INTO market_snapshots
                        (mint,ts,price_usd,liquidity_usd,volume_5m_usd,buys_5m,sells_5m,
                         unique_buyers_5m,top10_pct,creator_pct,price_change_5m_pct,source,payload_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (mint, ts, price, optional["liquidity_usd"], optional["volume_5m_usd"],
                         None if buys is None else int(buys), None if sells is None else int(sells),
                         None if buyers is None else int(buyers), optional["top10_pct"],
                         optional["creator_pct"], optional["price_change_5m_pct"], source,
                         json.dumps(row, sort_keys=True, default=str)))
                    inserted += cursor.rowcount
                except (TypeError, ValueError, OverflowError):
                    rejected += 1
        return {"inserted": inserted, "rejected": rejected}

    def build_labels(self, horizons: Iterable[int] = DEFAULT_HORIZONS_MINUTES,
                     max_lag_seconds: int = 180, max_entry_delay_seconds: int = 120) -> dict[str, int]:
        """Label only when an observed snapshot exists at/after each horizon.

        Entry is the first observed price snapshot at or after the launch event.
        Exit is the first observed snapshot at/after entry+horizon, no later than
        max_lag_seconds. Run-up/drawdown use only observations through that exit.
        """
        created = skipped = 0
        hs = tuple(sorted(set(int(h) for h in horizons)))
        if not hs or any(h <= 0 for h in hs) or max_lag_seconds < 0 or max_entry_delay_seconds < 0:
            raise ValueError("horizons and delay limits must be positive/nonnegative")
        with self._connect() as db:
            events = db.execute("SELECT * FROM launch_events ORDER BY observed_at,id").fetchall()
            for event in events:
                snaps = db.execute("""SELECT * FROM market_snapshots
                    WHERE mint=? AND ts>=? ORDER BY ts,id""",
                    (event["mint"], event["observed_at"])).fetchall()
                if not snaps:
                    skipped += len(hs)
                    continue
                entry = snaps[0]
                if entry["ts"] - event["observed_at"] > max_entry_delay_seconds:
                    skipped += len(hs)
                    continue
                for horizon in hs:
                    target = entry["ts"] + horizon * 60
                    exit_row = next((s for s in snaps if target <= s["ts"] <= target + max_lag_seconds), None)
                    if exit_row is None:
                        skipped += 1
                        continue
                    path = [s["price_usd"] for s in snaps if entry["ts"] <= s["ts"] <= exit_row["ts"]]
                    entry_price = float(entry["price_usd"])
                    exit_price = float(exit_row["price_usd"])
                    label = (event["id"], horizon, entry["ts"], entry_price,
                             exit_row["ts"], exit_price,
                             (exit_price / entry_price - 1) * 100,
                             (max(path) / entry_price - 1) * 100,
                             (min(path) / entry_price - 1) * 100,
                             entry["ts"] - event["observed_at"],
                             datetime.now(timezone.utc).isoformat())
                    cursor = db.execute("""INSERT OR IGNORE INTO outcome_labels
                        (event_id,horizon_minutes,entry_ts,entry_price,exit_ts,exit_price,
                         return_pct,max_runup_pct,max_drawdown_pct,capture_delay_seconds,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""", label)
                    created += cursor.rowcount
        return {"created": created, "skipped_incomplete": skipped}

    def report(self) -> dict[str, Any]:
        with self._connect() as db:
            counts = {
                "launch_events": db.execute("SELECT COUNT(*) FROM launch_events").fetchone()[0],
                "market_snapshots": db.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0],
                "outcome_labels": db.execute("SELECT COUNT(*) FROM outcome_labels").fetchone()[0],
            }
            horizons = db.execute("""SELECT horizon_minutes,COUNT(*) n,
                AVG(return_pct) avg_return,AVG(max_runup_pct) avg_runup,
                AVG(max_drawdown_pct) avg_drawdown,
                AVG(CASE WHEN return_pct>0 THEN 1.0 ELSE 0.0 END) hit_rate
                FROM outcome_labels GROUP BY horizon_minutes ORDER BY horizon_minutes""").fetchall()
            coverage = db.execute("""SELECT e.event_type,COUNT(DISTINCT e.id) events,
                COUNT(DISTINCT l.event_id) labeled_events
                FROM launch_events e LEFT JOIN outcome_labels l ON l.event_id=e.id
                GROUP BY e.event_type ORDER BY e.event_type""").fetchall()
        return {
            "mode": "OFFLINE_RESEARCH_ONLY",
            "counts": counts,
            "coverage_by_event_type": [dict(r) for r in coverage],
            "outcomes_by_horizon": [dict(r) for r in horizons],
            "limitations": [
                "Labels are descriptive outcomes, not proof of tradable fills.",
                "Missing future snapshots are reported as incomplete, never as zero return.",
                "No live orders, wallet signing, transaction building, or submission are available.",
                "Results are vulnerable to selection bias until the collector captures all launches."
            ],
            "execution_enabled": False
        }

    def run_rule_study(self, horizon_minutes: int = 5) -> dict[str, Any]:
        """Compare predeclared simple rules on labeled events; no fitted model."""
        with self._connect() as db:
            rows = db.execute("""SELECT e.id,e.event_type,s.liquidity_usd,s.volume_5m_usd,
                s.buys_5m,s.sells_5m,s.price_change_5m_pct,l.return_pct,l.max_drawdown_pct
                FROM launch_events e
                JOIN outcome_labels l ON l.event_id=e.id AND l.horizon_minutes=?
                JOIN market_snapshots s ON s.mint=e.mint AND s.ts=l.entry_ts
                ORDER BY e.observed_at,e.id""", (horizon_minutes,)).fetchall()
        rules = {
            "all_labeled_events": lambda r: True,
            "liquidity_10k_volume_5k": lambda r: r["liquidity_usd"] is not None and r["liquidity_usd"] >= 10000 and r["volume_5m_usd"] is not None and r["volume_5m_usd"] >= 5000,
            "buy_pressure_and_momentum": lambda r: r["buys_5m"] is not None and r["sells_5m"] is not None and r["buys_5m"] >= 10 and r["buys_5m"] > r["sells_5m"] and r["price_change_5m_pct"] is not None and 0 <= r["price_change_5m_pct"] <= 35,
        }
        results = []
        for name, predicate in rules.items():
            selected = [r for r in rows if predicate(r)]
            returns = [float(r["return_pct"]) for r in selected]
            drawdowns = [float(r["max_drawdown_pct"]) for r in selected]
            results.append({
                "rule": name, "sample_size": len(selected),
                "mean_return_pct": mean(returns) if returns else None,
                "median_return_pct": median(returns) if returns else None,
                "positive_rate": sum(x > 0 for x in returns) / len(returns) if returns else None,
                "mean_max_drawdown_pct": mean(drawdowns) if drawdowns else None,
                "status": "INSUFFICIENT_SAMPLE" if len(selected) < 30 else "DESCRIPTIVE_ONLY",
            })
        return {
            "mode": "PREDECLARED_RULE_COMPARISON",
            "horizon_minutes": horizon_minutes,
            "rules": results,
            "methodology": "Same labeled event cohort; entry features use first post-event snapshot; labels use later snapshots only.",
            "warning": "Not a strategy recommendation. No fees, slippage, executable sell quotes, or selection-bias correction are included.",
            "execution_enabled": False
        }
