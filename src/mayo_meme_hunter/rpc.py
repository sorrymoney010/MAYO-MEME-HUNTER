"""Read-only Solana RPC token checks. Unknown results fail closed."""
from __future__ import annotations
import json, os, urllib.request
from typing import Any

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

class SolanaRPC:
    def __init__(self, endpoint: str | None = None, timeout: float = 10):
        self.endpoint = endpoint or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.timeout, self._id = timeout, 0

    def call(self, method: str, params: list) -> dict[str, Any]:
        self._id += 1
        body = json.dumps({"jsonrpc":"2.0","id":self._id,"method":method,"params":params}).encode()
        req = urllib.request.Request(self.endpoint, data=body,
            headers={"Content-Type":"application/json","Accept":"application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            result = json.load(response)
        if result.get("error"):
            raise RuntimeError(f"Solana RPC error: {result['error']}")
        return result.get("result") or {}

    def inspect_mint(self, mint: str) -> dict[str, Any]:
        account = self.call("getAccountInfo", [mint, {"encoding":"jsonParsed","commitment":"confirmed"}])
        value = account.get("value")
        if not value:
            return {"mint":mint,"status":"UNKNOWN","reason":"mint account missing"}
        owner = value.get("owner")
        parsed = ((value.get("data") or {}).get("parsed") or {})
        info = parsed.get("info") or {}
        if parsed.get("type") != "mint":
            return {"mint":mint,"status":"UNKNOWN","reason":"not parsed as mint","program_owner":owner}
        mint_disabled, freeze_disabled = info.get("mintAuthority") is None, info.get("freezeAuthority") is None
        # Token-2022 extension inspection is not implemented: do not mark safe.
        program_safe = True if owner == TOKEN_PROGRAM else None
        supply = self.call("getTokenSupply", [mint, {"commitment":"confirmed"}]).get("value") or {}
        supply_ui = float(supply.get("uiAmount") or 0)
        largest = self.call("getTokenLargestAccounts", [mint, {"commitment":"confirmed"}]).get("value") or []
        top10 = sum(float(x.get("uiAmount") or 0) for x in largest[:10])
        concentration = 100 * top10 / supply_ui if supply_ui > 0 else None
        return {"mint":mint,"status":"CHECKED" if program_safe is True and concentration is not None else "PARTIAL",
            "slot":account.get("context",{}).get("slot"),"program_owner":owner,
            "mint_authority_disabled":mint_disabled,"freeze_authority_disabled":freeze_disabled,
            "token_program_safe":program_safe,"supply":supply_ui,
            "top10_account_concentration_pct":concentration,
            "holder_concentration_is_owner_aggregated":False,
            "sell_route_available":None,"creator_concentration_pct":None,
            "limitations":["largest accounts are not deduplicated by owner",
              "Token-2022 extensions not decoded" if program_safe is None else "sell route not checked",
              "mint inspection does not prove sellability"],"execution_enabled":False}
