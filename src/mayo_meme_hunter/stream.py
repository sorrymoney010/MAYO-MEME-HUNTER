"""Single-connection PumpPortal launch/migration collector. Free streams only."""
from __future__ import annotations
import asyncio, json, os, random, time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
import websockets

BASE = "wss://pumpportal.fun/api/data"

def normalize_event(payload: dict[str, Any], observed_at: float | None = None):
    raw_kind = payload.get("txType")
    kind = "migration" if raw_kind in {"migrate", "migration"} else raw_kind
    mint = payload.get("mint")
    if kind not in {"create", "migration"} or not isinstance(mint, str) or not mint:
        return None
    return {"schema_version":1,"provider":"pumpportal","event_type":kind,
        "observed_at":observed_at if observed_at is not None else time.time(),
        "mint":mint,"name":payload.get("name"),"symbol":payload.get("symbol"),
        "creator":payload.get("traderPublicKey") or payload.get("user"),
        "pool":payload.get("pool") or payload.get("bondingCurveKey"),
        "signature":payload.get("signature"),"slot":payload.get("slot"),
        "raw":payload,"execution_enabled":False}

async def collect(output: Path, stop_after: float | None = None):
    output.parent.mkdir(parents=True,exist_ok=True)
    key=os.getenv("PUMPPORTAL_API_KEY")
    url=BASE+(("?" + urlencode({"api-key":key})) if key else "")
    started,backoff=time.monotonic(),1.0
    while stop_after is None or time.monotonic()-started<stop_after:
        try:
            async with websockets.connect(url,ping_interval=20,ping_timeout=20,
                close_timeout=5,max_size=2**20) as ws:
                await ws.send(json.dumps({"method":"subscribeNewToken"}))
                await ws.send(json.dumps({"method":"subscribeMigration"}))
                backoff=1.0
                async for message in ws:
                    try: payload=json.loads(message)
                    except json.JSONDecodeError: continue
                    if isinstance(payload,dict):
                        event=normalize_event(payload)
                        if event:
                            with output.open("a",encoding="utf-8") as f:
                                f.write(json.dumps(event,separators=(",",":"))+"\n")
                                f.flush()
        except asyncio.CancelledError: raise
        except Exception as exc:
            print(f"PumpPortal disconnected ({type(exc).__name__}); retry in {backoff:.1f}s")
            await asyncio.sleep(backoff+random.uniform(0,backoff*.2))
            backoff=min(backoff*2,60.0)
