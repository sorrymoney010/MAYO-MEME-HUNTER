"""CLI for read-only MAYO Night Shift."""
import argparse, json
from pathlib import Path
from .night_shift import NightShiftConfig, morning_report, run_once, run_scheduler

def main():
    p=argparse.ArgumentParser(prog="mayo-night-shift",description="MAYO Night Shift — read-only Solana research")
    p.add_argument("--db",type=Path,default=Path("data/night_shift.sqlite3"))
    p.add_argument("--limit",type=int,default=20); p.add_argument("--interval",type=int,default=600)
    p.add_argument("--timezone",default="UTC"); p.add_argument("--morning-hour",type=int,default=7)
    p.add_argument("--once",action="store_true"); p.add_argument("--report-since")
    a=p.parse_args(); cfg=NightShiftConfig(a.db,a.limit,a.interval,a.morning_hour,a.timezone)
    if a.report_since: result=morning_report(cfg,a.report_since)
    elif a.once: result=run_once(cfg)
    else: run_scheduler(cfg); return
    print(json.dumps(result,indent=2,default=str))
if __name__=="__main__": main()
