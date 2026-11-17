"""Wallet-following *research* with FIFO realized P&L and copy-friction penalty.

The input must contain complete wallet buy/sell histories. Incomplete history
makes any wallet score unreliable. No chain data is fetched in this module.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class Lot:
    qty: float
    unit_cost: float


def analyze_wallet_events(events: list[dict[str, Any]], copy_friction_per_side: float = 0.02) -> list[dict[str, Any]]:
    if not 0 <= copy_friction_per_side < 0.25:
        raise ValueError("invalid friction")
    lots: dict[tuple[str, str], deque[Lot]] = defaultdict(deque)
    realized: dict[str, list[float]] = defaultdict(list)
    ignored: dict[str, int] = defaultdict(int)
    for event in sorted(events, key=lambda e: int(e["ts"])):
        wallet = str(event["wallet"])
        mint = str(event["mint"])
        side = str(event["side"]).lower()
        qty = float(event["qty"])
        price = float(event["price_usd"])
        if qty <= 0 or price <= 0:
            ignored[wallet] += 1
            continue
        key = (wallet, mint)
        if side == "buy":
            lots[key].append(Lot(qty, price * (1 + copy_friction_per_side)))
        elif side == "sell":
            remaining = qty
            while remaining > 1e-12 and lots[key]:
                lot = lots[key][0]
                matched = min(remaining, lot.qty)
                realized[wallet].append(matched * (price * (1 - copy_friction_per_side) - lot.unit_cost))
                lot.qty -= matched
                remaining -= matched
                if lot.qty <= 1e-12:
                    lots[key].popleft()
            if remaining > 1e-12:
                ignored[wallet] += 1  # no entry cost basis, cannot score that quantity
        else:
            ignored[wallet] += 1
    wallets = sorted(set(realized) | set(ignored) | {key[0] for key in lots})
    result = []
    for wallet in wallets:
        pnls = realized[wallet]
        gains = sum(p for p in pnls if p > 0)
        losses = -sum(p for p in pnls if p < 0)
        pf = gains / losses if losses else None
        open_lots = sum(len(q) for (w, _), q in lots.items() if w == wallet)
        result.append({"wallet": wallet, "matched_lots": len(pnls),
                       "win_rate": sum(p > 0 for p in pnls) / len(pnls) if pnls else None,
                       "copy_adjusted_pnl_usd": round(sum(pnls), 4),
                       "profit_factor": round(pf, 4) if pf is not None else None,
                       "open_lots": open_lots, "unmatched_or_invalid_events": ignored[wallet],
                       "watch_eligible": len(pnls) >= 30 and pf is not None and pf >= 1.10
                       and ignored[wallet] == 0 and open_lots == 0})
    return sorted(result, key=lambda x: x["copy_adjusted_pnl_usd"], reverse=True)
