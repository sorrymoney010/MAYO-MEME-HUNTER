"""Conservative, fee-aware meme-coin signals and *paper* fills.

All market observations are external data. Unknown safety fields are fail-closed.
This module contains no wallet, signer, RPC write, or transaction submission code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Snapshot:
    ts: int
    mint: str
    symbol: str
    price_usd: float
    age_minutes: float | None = None
    liquidity_usd: float | None = None
    volume_5m_usd: float | None = None
    buys_5m: int | None = None
    sells_5m: int | None = None
    unique_buyers_5m: int | None = None
    top10_pct: float | None = None
    creator_pct: float | None = None
    mint_authority_disabled: bool | None = None
    freeze_authority_disabled: bool | None = None
    token_program_safe: bool | None = None
    sell_route_available: bool | None = None
    suspicious_clusters: bool | None = None
    price_change_5m_pct: float | None = None
    source: str = "replay"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        allowed = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass(frozen=True)
class Config:
    starting_cash: float = 100.0
    min_score: int = 70
    min_liquidity_usd: float = 25_000
    min_volume_5m_usd: float = 10_000
    min_unique_buyers_5m: int = 20
    min_buy_sell_ratio: float = 1.25
    max_top10_pct: float = 35.0
    max_creator_pct: float = 5.0
    min_age_minutes: float = 2.0
    max_age_minutes: float = 120.0
    risk_per_trade: float = 0.01
    max_allocation: float = 0.10
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.10
    max_positions: int = 2
    max_entries_per_day: int = 10
    stop_pct: float = 0.12
    take_profit_pct: float = 0.25
    trail_activate_pct: float = 0.15
    trailing_stop_pct: float = 0.10
    max_hold_seconds: int = 900
    max_signal_age_seconds: int = 60
    cooldown_seconds: int = 60
    fee_bps_per_side: float = 50.0
    slippage_bps_per_side: float = 150.0
    network_cost_usd_per_side: float = 0.02
    min_notional_usd: float = 5.0

    def __post_init__(self) -> None:
        if self.starting_cash <= 0 or not 0 < self.risk_per_trade <= 0.02:
            raise ValueError("Invalid cash/risk settings")
        if not 0 < self.max_allocation <= 0.25 or not 0 < self.max_daily_loss <= 0.05:
            raise ValueError("Allocation or daily-loss cap too high")
        if not 0 < self.stop_pct < 1 or not 0 < self.take_profit_pct:
            raise ValueError("Invalid stop or target")
        if min(self.fee_bps_per_side, self.slippage_bps_per_side, self.network_cost_usd_per_side) < 0:
            raise ValueError("Costs cannot be negative")


def evaluate(s: Snapshot, cfg: Config) -> dict[str, Any]:
    """Fail-closed gates; score is a research heuristic, not win probability."""
    reasons: list[str] = []
    if not s.mint or s.price_usd <= 0:
        reasons.append("invalid mint/price")
    numeric = (
        ("age_minutes", cfg.min_age_minutes, cfg.max_age_minutes),
        ("liquidity_usd", cfg.min_liquidity_usd, None),
        ("volume_5m_usd", cfg.min_volume_5m_usd, None),
        ("unique_buyers_5m", cfg.min_unique_buyers_5m, None),
        ("top10_pct", None, cfg.max_top10_pct),
        ("creator_pct", None, cfg.max_creator_pct),
    )
    for name, low, high in numeric:
        value = getattr(s, name)
        if value is None:
            reasons.append(f"{name} unknown")
        elif low is not None and value < low:
            reasons.append(f"{name} below floor")
        elif high is not None and value > high:
            reasons.append(f"{name} above ceiling")
    if s.buys_5m is None or s.sells_5m is None:
        reasons.append("buy/sell counts unknown")
    elif s.buys_5m < 25 or s.buys_5m / max(s.sells_5m, 1) < cfg.min_buy_sell_ratio:
        reasons.append("insufficient buy pressure")
    for name, expected in (
        ("mint_authority_disabled", True),
        ("freeze_authority_disabled", True),
        ("token_program_safe", True),
        ("sell_route_available", True),
        ("suspicious_clusters", False),
    ):
        actual = getattr(s, name)
        if actual is None:
            reasons.append(f"{name} unverified")
        elif actual is not expected:
            reasons.append(f"{name} failed")

    # Scoring weights: liquidity 20, volume 20, buy pressure 15,
    # unique buyers 15, holder distribution 15, momentum 15.
    liq = min(20, 20 * number(s.liquidity_usd) / 100_000)
    volume = min(20, 20 * number(s.volume_5m_usd) / 50_000)
    ratio = number(s.buys_5m) / max(number(s.sells_5m, 1), 1)
    pressure = max(0, min(15, 15 * (ratio - 1) / 1.5))
    buyers = min(15, 15 * number(s.unique_buyers_5m) / 100)
    distribution = max(0, min(15, 15 * (45 - number(s.top10_pct, 45)) / 30))
    change = s.price_change_5m_pct
    momentum = 0 if change is None or change < 2 or change > 40 else min(15, 15 * change / 20)
    score = int(round(liq + volume + pressure + buyers + distribution + momentum))
    if score < cfg.min_score:
        reasons.append("score below threshold")
    return {"mint": s.mint, "symbol": s.symbol, "score": score,
            "decision": "CANDIDATE" if not reasons else "REJECT",
            "reasons": reasons}


@dataclass
class Position:
    mint: str
    symbol: str
    qty: float
    entry_ts: int
    entry_fill_price: float
    entry_cost: float  # Includes fees, slippage (in fill price), network cost
    peak_price: float
    last_price: float
    trapped: bool = False


@dataclass
class PaperEngine:
    cfg: Config = field(default_factory=Config)
    cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    pending: dict[str, int] = field(default_factory=dict)
    last_prices: dict[str, float] = field(default_factory=dict)
    last_timestamps: dict[str, int] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    equity_peak: float = field(init=False)
    day_open_equity: float = field(init=False)
    day_key: str = ""
    entries_today: int = 0
    last_entry_ts: int = -10**18
    max_seen_drawdown: float = 0.0
    permanently_halted: bool = False
    daily_halted: bool = False

    def __post_init__(self) -> None:
        self.cash = self.cfg.starting_cash
        self.equity_peak = self.cash
        self.day_open_equity = self.cash

    def equity(self) -> float:
        return self.cash + sum(p.qty * self.last_prices.get(mint, p.last_price)
                               for mint, p in self.positions.items())

    def _risk_refresh(self) -> None:
        eq = self.equity()
        self.equity_peak = max(self.equity_peak, eq)
        dd = max(0, (self.equity_peak - eq) / self.equity_peak)
        self.max_seen_drawdown = max(self.max_seen_drawdown, dd)
        if dd >= self.cfg.max_drawdown:
            self.permanently_halted = True
        if eq <= self.day_open_equity * (1 - self.cfg.max_daily_loss):
            self.daily_halted = True

    def _exit(self, s: Snapshot, reason: str) -> None:
        p = self.positions[s.mint]
        # No synthetic 'successful exit' if the route cannot actually be quoted.
        if s.sell_route_available is not True:
            p.trapped = True
            self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "EXIT_BLOCKED", "reason": "no verified sell route"})
            return
        fill = s.price_usd * (1 - self.cfg.slippage_bps_per_side / 10_000)
        gross = p.qty * fill
        fees = gross * self.cfg.fee_bps_per_side / 10_000
        proceeds = max(0, gross - fees - self.cfg.network_cost_usd_per_side)
        pnl = proceeds - p.entry_cost
        self.cash += proceeds
        self.trades.append({"mint": p.mint, "symbol": p.symbol, "entry_ts": p.entry_ts,
                            "exit_ts": s.ts, "qty": p.qty, "entry_price": p.entry_fill_price,
                            "exit_price": fill, "cost_usd": p.entry_cost,
                            "proceeds_usd": proceeds, "pnl_usd": pnl, "reason": reason})
        del self.positions[s.mint]
        self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "PAPER_SELL", "reason": reason,
                               "pnl_usd": round(pnl, 6)})

    def _enter(self, s: Snapshot) -> None:
        equity = self.equity()
        notional = min(equity * self.cfg.risk_per_trade / self.cfg.stop_pct,
                       equity * self.cfg.max_allocation,
                       max(0, self.cash - self.cfg.network_cost_usd_per_side) /
                       (1 + self.cfg.fee_bps_per_side / 10_000))
        if notional < self.cfg.min_notional_usd:
            self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "SKIP", "reason": "position below minimum"})
            return
        fill = s.price_usd * (1 + self.cfg.slippage_bps_per_side / 10_000)
        fee = notional * self.cfg.fee_bps_per_side / 10_000
        cost = notional + fee + self.cfg.network_cost_usd_per_side
        if cost > self.cash + 1e-9:
            raise AssertionError("paper sizing exceeded cash")
        self.cash -= cost
        self.positions[s.mint] = Position(s.mint, s.symbol, notional / fill, s.ts,
                                          fill, cost, s.price_usd, s.price_usd)
        self.entries_today += 1
        self.last_entry_ts = s.ts
        self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "PAPER_BUY", "notional_usd": round(notional, 6),
                               "fill_price": fill})

    def process(self, s: Snapshot) -> None:
        if s.ts < 0 or s.price_usd <= 0:
            raise ValueError("bad timestamp or price")
        if s.ts <= self.last_timestamps.get(s.mint, -1):
            raise ValueError("out-of-order or duplicate token snapshot")
        self.last_timestamps[s.mint] = s.ts
        day = datetime.fromtimestamp(s.ts, tz=timezone.utc).date().isoformat()
        if day != self.day_key:
            self.day_key = day
            self.day_open_equity = self.equity()
            self.entries_today = 0
            self.daily_halted = False
        self.last_prices[s.mint] = s.price_usd

        if s.mint in self.positions:
            p = self.positions[s.mint]
            p.peak_price = max(p.peak_price, s.price_usd)
            p.last_price = s.price_usd
            reason = None
            if s.sell_route_available is not True:
                reason = "sell route unsafe"
            elif s.price_usd <= p.entry_fill_price * (1 - self.cfg.stop_pct):
                reason = "stop"
            elif s.price_usd >= p.entry_fill_price * (1 + self.cfg.take_profit_pct):
                reason = "take profit"
            elif (p.peak_price >= p.entry_fill_price * (1 + self.cfg.trail_activate_pct)
                  and s.price_usd <= p.peak_price * (1 - self.cfg.trailing_stop_pct)):
                reason = "trailing stop"
            elif s.ts - p.entry_ts >= self.cfg.max_hold_seconds:
                reason = "time exit"
            if reason:
                self._exit(s, reason)
        self._risk_refresh()

        signal_ts = self.pending.pop(s.mint, None)
        verdict = evaluate(s, self.cfg)
        can_enter = (not self.permanently_halted and not self.daily_halted
                     and self.entries_today < self.cfg.max_entries_per_day
                     and len(self.positions) < self.cfg.max_positions
                     and s.ts - self.last_entry_ts >= self.cfg.cooldown_seconds
                     and s.mint not in self.positions)
        if signal_ts is not None:
            if (can_enter and verdict["decision"] == "CANDIDATE"
                    and 0 < s.ts - signal_ts <= self.cfg.max_signal_age_seconds):
                self._enter(s)
            else:
                self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "SIGNAL_EXPIRED_OR_BLOCKED",
                                       "reasons": verdict["reasons"]})
        elif can_enter and verdict["decision"] == "CANDIDATE":
            self.pending[s.mint] = s.ts
            self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "PENDING_NEXT_TICK", "score": verdict["score"]})
        else:
            self.decisions.append({"ts": s.ts, "mint": s.mint, "action": "WATCH_OR_REJECT",
                                   "score": verdict["score"], "reasons": verdict["reasons"]})
        self._risk_refresh()

    def report(self) -> dict[str, Any]:
        pnls = [t["pnl_usd"] for t in self.trades]
        wins = sum(x > 0 for x in pnls)
        profits = sum(x for x in pnls if x > 0)
        losses = -sum(x for x in pnls if x < 0)
        pf = profits / losses if losses > 0 else None
        return {
            "mode": "PAPER_ONLY", "starting_cash_usd": self.cfg.starting_cash,
            "ending_cash_usd": round(self.cash, 4), "marked_equity_usd": round(self.equity(), 4),
            "open_positions": len(self.positions), "trapped_positions": sum(p.trapped for p in self.positions.values()),
            "closed_trades": len(pnls), "wins": wins,
            "win_rate": round(wins / len(pnls), 4) if pnls else None,
            "profit_factor": round(pf, 4) if pf is not None else None,
            "realized_pnl_usd": round(sum(pnls), 4),
            "max_observed_drawdown_pct": round(100 * self.max_seen_drawdown, 3),
            "halted": self.permanently_halted, "daily_halted": self.daily_halted,
            "research_gate_passed": len(pnls) >= 30 and pf is not None and pf >= 1.10,
            "live_orders_enabled": False,
            "warning": "Research gate alone never authorizes live trading; price marks are not executable quotes."
        }

    def export(self) -> dict[str, Any]:
        return {"summary": self.report(), "positions": [asdict(p) for p in self.positions.values()],
                "trades": self.trades, "decisions": self.decisions}
