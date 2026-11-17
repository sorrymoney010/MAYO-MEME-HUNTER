"""Jupiter quote preparation only. Live transaction submission is disabled."""
from __future__ import annotations
import json, os, time
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WSOL_MINT = "So11111111111111111111111111111111111111112"
ORDER_URL = "https://api.jup.ag/swap/v2/order"

@dataclass(frozen=True)
class TradeLimits:
    max_buy_lamports: int = 50_000_000
    max_daily_lamports: int = 200_000_000
    max_price_impact_pct: float = 5.0
    max_quote_age_seconds: int = 10
    max_open_positions: int = 2
    def validate(self):
        if not 0 < self.max_buy_lamports <= 50_000_000: raise ValueError("buy cap exceeds hard ceiling")
        if not 0 < self.max_daily_lamports <= 200_000_000: raise ValueError("daily cap exceeds hard ceiling")
        if not 0 < self.max_price_impact_pct <= 5: raise ValueError("price impact cap must be <= 5%")
        if not 1 <= self.max_quote_age_seconds <= 10: raise ValueError("quote age must be 1..10 seconds")

@dataclass(frozen=True)
class TradeIntent:
    mint: str
    amount_lamports: int
    observed_at: float
    candidate_passed: bool
    security_verified: bool
    sell_route_verified: bool

class JupiterClient:
    def __init__(self, api_key=None, timeout=8):
        self.api_key = api_key or os.getenv("JUPITER_API_KEY")
        self.timeout = timeout
    def order(self, mint, amount_lamports, taker):
        query = urlencode({"inputMint": WSOL_MINT, "outputMint": mint,
                           "amount": str(amount_lamports), "taker": taker})
        headers = {"Accept": "application/json"}
        if self.api_key: headers["x-api-key"] = self.api_key
        with urlopen(Request(ORDER_URL + "?" + query, headers=headers), timeout=self.timeout) as response:
            return json.load(response)

class ExecutionGate:
    def __init__(self, limits=None, client=None):
        self.limits = limits or TradeLimits()
        self.limits.validate()
        self.client = client or JupiterClient()
        self.spent_today_lamports = 0
        self.open_positions = 0
    @property
    def live_enabled(self):
        return False
    def validate_intent(self, intent, now=None):
        now = time.time() if now is None else now
        if not intent.mint or intent.mint == WSOL_MINT: raise ValueError("invalid output mint")
        if not intent.candidate_passed: raise ValueError("strategy rejected candidate")
        if not intent.security_verified or not intent.sell_route_verified: raise ValueError("security/sell route unverified")
        if not 0 < intent.amount_lamports <= self.limits.max_buy_lamports: raise ValueError("buy amount outside cap")
        if self.spent_today_lamports + intent.amount_lamports > self.limits.max_daily_lamports: raise ValueError("daily spend cap reached")
        if self.open_positions >= self.limits.max_open_positions: raise ValueError("open-position cap reached")
        age = now - intent.observed_at
        if age < 0 or age > self.limits.max_quote_age_seconds: raise ValueError("stale candidate observation")
        return True
    def prepare_quote(self, intent, taker, now=None):
        self.validate_intent(intent, now)
        quote = self.client.order(intent.mint, intent.amount_lamports, taker)
        if not quote.get("outAmount") or not quote.get("requestId"):
            raise ValueError("Jupiter returned no usable quote")
        return {"mode": "QUOTE_ONLY_NOT_SIGNED_NOT_SUBMITTED", "quote": quote,
                "warning": "MAYO live trading is hard-disabled. No signature or transaction submission occurred."}
    def submit_signed(self, *_args, **_kwargs):
        raise PermissionError("MAYO live trading is disabled in this build; no transaction can be submitted.")
