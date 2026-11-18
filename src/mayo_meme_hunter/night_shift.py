"""Read-only MAYO Night Shift orchestration; no wallet or transaction code."""
from __future__ import annotations
import json, sqlite3, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo
from .scanner import scan as scan_dex

@dataclass(frozen=True)
class NightShiftConfig:
    database: Path = Path("data/night_shift.sqlite3")
    scan_limit: int = 20
    scan_interval_seconds: int = 600
    morning_hour: int = 7
    timezone_name: str = "UTC"
    def __post_init__(self):
        if not 1 <= self.scan_limit <= 30: raise ValueError("scan_limit must be 1..30")
        if self.scan_interval_seconds < 60: raise ValueError("scan interval must be at least 60 seconds")
        if not 0 <= self.morning_hour <= 23: raise ValueError("morning_hour must be 0..23")
        ZoneInfo(self.timezone_name)

class ResearchStore:
    """Append-only observation/report store; contains no wallet or transaction state."""
    def __init__(self, path: Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, mint TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(observed_at)")
            db.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, report_json TEXT NOT NULL)")
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=15); db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA busy_timeout=15000"); return db
    def record(self,row:dict[str,Any]):
        with self._connect() as db:
            db.execute("INSERT INTO observations(observed_at,mint,status,payload_json) VALUES(?,?,?,?)",
                (row["observed_at"],row["mint"],row["status"],json.dumps(row,sort_keys=True,default=str)))
    def observations_since(self,iso_utc:str):
        with self._connect() as db: rows=db.execute("SELECT payload_json FROM observations WHERE observed_at>=? ORDER BY id",(iso_utc,)).fetchall()
        return [json.loads(x[0]) for x in rows]
    def save_report(self,report):
        with self._connect() as db: db.execute("INSERT INTO reports(created_at,report_json) VALUES(?,?)",(report["created_at"],json.dumps(report,sort_keys=True,default=str)))

def _now(): return datetime.now(timezone.utc).isoformat()
def _role(name,status,evidence,findings=None): return {"agent":name,"status":status,"evidence":evidence,"findings":findings or {}}

def orchestrate_candidate(candidate:dict[str,Any])->dict[str,Any]:
    """Seven deterministic research roles; missing security proof always blocks."""
    mint=str(candidate.get("mint") or "UNKNOWN"); source=candidate.get("pair_url") or candidate.get("source_url")
    missing=candidate.get("missing_security_checks") or []; blockers=candidate.get("all_blockers") or []
    identity=bool(mint!="UNKNOWN" and source)
    lead=_role("Desk Lead","PASS" if identity else "BLOCK",["mint and source URL required"],{"identity_complete":identity})
    launch=_role("Launch Hunter","OBSERVED" if identity else "UNKNOWN",[str(candidate.get("discovery_source") or "DEX Screener profile/pair feed")],{"event_type":candidate.get("event_type","UNKNOWN"),"launch_time":candidate.get("launch_time","UNKNOWN")})
    dev_ev=candidate.get("developer_evidence")
    dev=_role("Developer Investigator","VERIFIED" if dev_ev else "UNKNOWN",[str(dev_ev)] if dev_ev else ["No attributable creator/linked-wallet evidence"],{"creator_share_pct":candidate.get("creator_pct","UNKNOWN")})
    bundle_ev=candidate.get("bundle_evidence")
    bundle=_role("Bundle Detective","VERIFIED" if bundle_ev else "UNKNOWN",[str(bundle_ev)] if bundle_ev else ["No launch-block/early-wallet evidence"],{"bundle_flag":candidate.get("bundle_flag","UNKNOWN")})
    fields=("price_usd","liquidity_usd","volume_5m_usd","buys_5m","sells_5m")
    market_values={k:candidate.get(k,"UNKNOWN") for k in fields}
    market=_role("Market Analyst","OBSERVED" if any(v!="UNKNOWN" for v in market_values.values()) else "UNKNOWN",[str(source or "No pair URL")],market_values)
    ready=bool(identity and dev_ev and bundle_ev and not blockers and not missing)
    strategy=_role("Strategy Agent","HYPOTHESIS_ALLOWED" if ready else "NO_SETUP",["No trade signal generated in V1"],{"paper_review_eligible":ready})
    risk=_role("Risk & Execution Controller","PAPER_REVIEW_ONLY" if ready else "PAPER_ONLY_BLOCK",["Live execution hard-disabled","Unknown evidence fails closed"],{"decision":"PASS_FOR_PAPER_REVIEW" if ready else "SKIP","missing_security_checks":missing,"blockers":blockers,"wallet_signing":False,"transaction_submission":False})
    return {"observed_at":candidate.get("observed_at") or _now(),"mint":mint,"symbol":candidate.get("symbol","UNKNOWN"),"source_url":source,"status":"PASS_FOR_PAPER_REVIEW" if ready else "SKIP","agents":[lead,launch,dev,bundle,market,strategy,risk],"paper_pnl_usd":None,"execution_enabled":False,"candidate":candidate}

def run_once(config:NightShiftConfig,scanner:Callable[[int],list[dict[str,Any]]]=scan_dex)->dict[str,Any]:
    store=ResearchStore(config.database); started=_now()
    try: candidates=scanner(config.scan_limit); source_error=None
    except Exception as exc: candidates=[]; source_error=f"{type(exc).__name__}: {str(exc)[:240]}"
    results=[]
    for candidate in candidates:
        row=dict(candidate); row.setdefault("observed_at",started); row.setdefault("source_url",row.get("pair_url"))
        result=orchestrate_candidate(row); result["scan_observed_at"]=started
        if source_error: result["source_error"]=source_error
        store.record(result); results.append(result)
    report={"created_at":_now(),"scan_started_at":started,"mode":"READ_ONLY_RESEARCH","candidates_seen":len(results),
      "pass_for_paper_review":sum(x["status"]=="PASS_FOR_PAPER_REVIEW" for x in results),"skipped":sum(x["status"]=="SKIP" for x in results),
      "source_error":source_error,"results":results,"execution_enabled":False,"wallet_signing":False,"transaction_submission":False}
    store.save_report(report); return report

def morning_report(config:NightShiftConfig,since_utc:str)->dict[str,Any]:
    rows=ResearchStore(config.database).observations_since(since_utc)
    report={"created_at":_now(),"since_utc":since_utc,"mode":"PAPER_ONLY_MORNING_REVIEW","observations":len(rows),
      "pass_for_paper_review":sum(r["status"]=="PASS_FOR_PAPER_REVIEW" for r in rows),"skipped":sum(r["status"]=="SKIP" for r in rows),
      "paper_pnl_usd":None,"note":"V1 records discovery evidence only; no fills or P&L are inferred.","rows":rows,"execution_enabled":False}
    ResearchStore(config.database).save_report(report); return report

def run_scheduler(config:NightShiftConfig):
    tz=ZoneInfo(config.timezone_name); last_report_date=None; window_start=_now()
    print(f"Night Shift read-only scheduler: {config.timezone_name}; Ctrl-C to stop.")
    while True:
        run_once(config); now=datetime.now(tz)
        if now.hour==config.morning_hour and last_report_date!=now.date():
            print(json.dumps(morning_report(config,window_start),indent=2,default=str))
            last_report_date=now.date(); window_start=_now()
        time.sleep(config.scan_interval_seconds)
