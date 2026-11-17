"""Read-only DEX Screener discovery adapter. NOT a full launch feed.

This endpoint lacks mint/freeze authority, holder concentration, sell-route
verification and unique-buyer data. We deliberately leave these UNKNOWN.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

from .core import Config, Snapshot, evaluate, number

BASE = "https://api.dexscreener.com"


def _get_json(path: str) -> object:
    request = Request(BASE + path, headers={"Accept": "application/json", "User-Agent": "MayoMemeHunter/0.1 research"})
    with urlopen(request, timeout=12) as response:  # nosec: fixed trusted host
        return json.load(response)


def _as_snapshot(pair: dict, mint: str, now_ms: int) -> Snapshot:
    txns = pair.get("txns") or {}
    m5 = txns.get("m5") or {}
    volume = pair.get("volume") or {}
    changes = pair.get("priceChange") or {}
    created = pair.get("pairCreatedAt")
    age = max(0, (now_ms - created) / 60_000) if isinstance(created, (int, float)) else None
    return Snapshot(
        ts=now_ms // 1000, mint=mint,
        symbol=(pair.get("baseToken") or {}).get("symbol", "?"),
        price_usd=number(pair.get("priceUsd")),
        age_minutes=age,
        liquidity_usd=number((pair.get("liquidity") or {}).get("usd")),
        volume_5m_usd=number(volume.get("m5")),
        buys_5m=int(number(m5.get("buys"))),
        sells_5m=int(number(m5.get("sells"))),
        price_change_5m_pct=number(changes.get("m5")),
        # All the fields below MUST remain unknown until independently verified.
        unique_buyers_5m=None, top10_pct=None, creator_pct=None,
        mint_authority_disabled=None, freeze_authority_disabled=None,
        token_program_safe=None, sell_route_available=None,
        suspicious_clusters=None, source="dexscreener_public",
    )


def scan(limit: int = 10, delay: float = 0.25) -> list[dict]:
    """Return watchlist observations only; never generate an executable order."""
    if not 1 <= limit <= 30:
        raise ValueError("limit must be 1..30")
    profiles = _get_json("/token-profiles/latest/v1")
    if not isinstance(profiles, list):
        raise ValueError("unexpected profile response")
    seen: set[str] = set()
    rows: list[dict] = []
    cfg = Config()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    for profile in profiles:
        if len(rows) >= limit:
            break
        if not isinstance(profile, dict) or profile.get("chainId") != "solana":
            continue
        mint = profile.get("tokenAddress")
        if not isinstance(mint, str) or not mint or mint in seen:
            continue
        seen.add(mint)
        try:
            pools = _get_json("/token-pairs/v1/solana/" + quote(mint, safe=""))
            if not isinstance(pools, list) or not pools:
                continue
            pools = [p for p in pools if isinstance(p, dict) and p.get("chainId") == "solana"
                     and (p.get("baseToken") or {}).get("address") == mint]
            if not pools:
                continue
            best = max(pools, key=lambda p: number((p.get("liquidity") or {}).get("usd")))
            snap = _as_snapshot(best, mint, now_ms)
            verdict = evaluate(snap, cfg)
            rows.append({"mint": mint, "symbol": snap.symbol,
                         "dex": best.get("dexId"), "pair_url": best.get("url"),
                         "liquidity_usd": snap.liquidity_usd, "volume_5m_usd": snap.volume_5m_usd,
                         "score": verdict["score"], "status": "WATCH_ONLY_UNVERIFIED",
                         "missing_security_checks": [r for r in verdict["reasons"] if "unknown" in r or "unverified" in r],
                         "all_blockers": verdict["reasons"]})
        except (OSError, ValueError, TimeoutError) as exc:
            rows.append({"mint": mint, "status": "DATA_ERROR", "error": str(exc)[:160]})
        time.sleep(delay)
    return rows
