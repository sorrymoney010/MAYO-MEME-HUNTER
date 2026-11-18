"""Rate-limited, read-only DEX Screener market snapshot collector."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "https://api.dexscreener.com"


def _get_pairs(mint: str) -> list[dict[str, Any]]:
    url = BASE + "/token-pairs/v1/solana/" + quote(mint, safe="")
    request = Request(url, headers={"Accept": "application/json",
                                   "User-Agent": "MayoMemeHunter/1.0 research"})
    with urlopen(request, timeout=12) as response:  # nosec: fixed trusted host
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("unexpected DEX Screener token-pairs response")
    return [p for p in payload if isinstance(p, dict)
            and p.get("chainId") == "solana"
            and (p.get("baseToken") or {}).get("address") == mint]


def snapshot_for_mint(mint: str, fetcher: Callable[[str], list[dict[str, Any]]] = _get_pairs,
                      observed_at: float | None = None) -> dict[str, Any] | None:
    pairs = fetcher(mint)
    if not pairs:
        return None
    def liquidity(pair):
        try:
            return float((pair.get("liquidity") or {}).get("usd") or 0)
        except (TypeError, ValueError):
            return 0.0
    pair = max(pairs, key=liquidity)
    tx = (pair.get("txns") or {}).get("m5") or {}
    vol = pair.get("volume") or {}
    change = pair.get("priceChange") or {}
    price = pair.get("priceUsd")
    if price is None or float(price) <= 0:
        return None
    return {
        "mint": mint,
        "ts": observed_at if observed_at is not None else datetime.now(timezone.utc).timestamp(),
        "price_usd": float(price),
        "liquidity_usd": liquidity(pair),
        "volume_5m_usd": float(vol.get("m5") or 0),
        "buys_5m": int(tx.get("buys") or 0),
        "sells_5m": int(tx.get("sells") or 0),
        "unique_buyers_5m": None,
        "top10_pct": None,
        "creator_pct": None,
        "price_change_5m_pct": float(change["m5"]) if change.get("m5") is not None else None,
        "pair_address": pair.get("pairAddress"),
        "pair_url": pair.get("url"),
        "dex_id": pair.get("dexId"),
        "source": "dexscreener_public",
        "observed_at_utc": datetime.fromtimestamp(
            observed_at if observed_at is not None else datetime.now(timezone.utc).timestamp(),
            tz=timezone.utc).isoformat(),
        "execution_enabled": False,
    }


def load_recent_mints(events_path: Path, limit: int = 20) -> list[str]:
    if not 1 <= limit <= 30:
        raise ValueError("limit must be 1..30")
    seen: dict[str, None] = {}
    if not events_path.exists():
        return []
    with events_path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            mint = row.get("mint") if isinstance(row, dict) else None
            if isinstance(mint, str) and mint:
                seen.pop(mint, None)
                seen[mint] = None
    return list(seen)[-limit:]


def collect_snapshots(events_path: Path, output_path: Path, interval_seconds: int = 300,
                      max_tokens: int = 20, duration_seconds: float | None = None,
                      fetcher: Callable[[str], list[dict[str, Any]]] = _get_pairs,
                      sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    if interval_seconds < 60:
        raise ValueError("snapshot interval must be at least 60 seconds")
    if not 1 <= max_tokens <= 30:
        raise ValueError("max_tokens must be 1..30")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cycles = written = errors = 0
    while duration_seconds is None or time.monotonic() - started < duration_seconds:
        cycle_started = time.monotonic()
        mints = load_recent_mints(events_path, max_tokens)
        cycles += 1
        for mint in mints:
            try:
                row = snapshot_for_mint(mint, fetcher=fetcher)
                if row:
                    with output_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                        handle.flush()
                    written += 1
            except Exception as exc:
                errors += 1
                print(f"Snapshot unavailable for {mint[:8]}… ({type(exc).__name__})")
        if duration_seconds is not None and time.monotonic() - started >= duration_seconds:
            break
        sleep(max(0.0, interval_seconds - (time.monotonic() - cycle_started)))
    return {"cycles": cycles, "snapshots_written": written, "source_errors": errors,
            "mode": "READ_ONLY_RESEARCH", "execution_enabled": False}
