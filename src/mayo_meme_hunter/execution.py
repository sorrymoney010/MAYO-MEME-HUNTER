"""Guarded Jupiter Swap API boundary; no private-key signing."""
from __future__ import annotations
import json, os, time
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WSOL_MINT = "So11111111111111111111111111111111111111112"
ORDER_URL = "https://api.jup.ag/swap/v2/order"
EXECUTE_URL = "https://api.jup.ag/swap/v2/execute"

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
    def _request(self, url, method="GET", payload=None):
        headers = {"Accept":"application/json","Content-Type":"application/json"}
        if self.api_key: headers["x-api-key"] = self.api_key
        body = json.dumps(payload).encode() if payload is not None else None
        with urlopen(Request(url,data=body,headers=headers,method=method),timeout=self.timeout) as r:
            return json.load(r)
    def order(self,mint,amount_lamports,taker):
        q=urlencode({"inputMint":WSOL_MINT,"outputMint":mint,"amount":str(amount_lamports),"taker":taker})
        return self._request(ORDER_URL+"?"+q)
    def execute(self,signed_transaction,request_id):
        return self._request(EXECUTE_URL,"POST",{"signedTransaction":signed_transaction,"requestId":request_id})

class ExecutionGate:
    def __init__(self,limits=None,client=None):
        self.limits=limits or TradeLimits(); self.limits.validate()
        self.client=client or JupiterClient()
        self.spent_today_lamports=0; self.open_positions=0
    @property
    def live_enabled(self):
        return os.getenv("MAYO_LIVE_TRADING_ENABLED","").lower()=="true"
    def validate_intent(self,intent,now=None):
        now=time.time() if now is None else now
        if not intent.mint or intent.mint==WSOL_MINT: raise ValueError("invalid output mint")
        if not intent.candidate_passed: raise ValueError("strategy rejected candidate")
        if not intent.security_verified or not intent.sell_route_verified: raise ValueError("security/sell route unverified")
        if not 0<intent.amount_lamports<=self.limits.max_buy_lamports: raise ValueError("buy amount outside cap")
        if self.spent_today_lamports+intent.amount_lamports>self.limits.max_daily_lamports: raise ValueError("daily spend cap reached")
        if self.open_positions>=self.limits.max_open_positions: raise ValueError("open-position cap reached")
        age=now-intent.observed_at
        if age<0 or age>self.limits.max_quote_age_seconds: raise ValueError("stale candidate observation")
        return True
    def prepare_order(self,intent,taker,now=None):
        self.validate_intent(intent,now)
        order=self.client.order(intent.mint,intent.amount_lamports,taker)
        if not order.get("transaction") or not order.get("requestId"): raise ValueError("Jupiter returned no executable order")
        if float(order.get("priceImpactPct",999))>self.limits.max_price_impact_pct: raise ValueError("price impact exceeds cap")
        return {"mode":"PREPARED_NOT_SIGNED","order":order,"warning":"No signing or submission occurred."}
    def execute_signed(self,signed_transaction,request_id,amount_lamports):
        if not self.live_enabled: raise PermissionError("live trading is disabled")
        if not 0<amount_lamports<=self.limits.max_buy_lamports: raise ValueError("amount outside hard cap")
        if self.spent_today_lamports+amount_lamports>self.limits.max_daily_lamports: raise ValueError("daily cap reached")
        if not signed_transaction or not request_id: raise ValueError("signed transaction and request ID required")
        result=self.client.execute(signed_transaction,request_id)
        if result.get("status")!="Success": raise RuntimeError("Jupiter execution failed")
        self.spent_today_lamports+=amount_lamports
        return result
