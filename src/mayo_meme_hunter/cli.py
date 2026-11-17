"""Command-line entry points. Deliberately no live-trading subcommand."""
from __future__ import annotations
import argparse, asyncio, json
from pathlib import Path
from .core import PaperEngine, Snapshot
from .dashboard import render_dashboard
from .scanner import scan
from .wallets import analyze_wallet_events
from .rpc import SolanaRPC
from .stream import collect

def read_jsonl(path: Path) -> list[dict]:
    rows=[]
    with path.open(encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if line.strip():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError as exc: raise ValueError(f"invalid JSONL line {n}: {exc}") from exc
    return rows

def main() -> None:
    parser=argparse.ArgumentParser(prog="mayo-meme",description="MAYO MEME HUNTER: paper-only")
    sub=parser.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("scan",help="Read-only DEX Screener watchlist")
    p.add_argument("--limit",type=int,default=10); p.add_argument("--out",type=Path)
    p=sub.add_parser("stream",help="Collect free PumpPortal create/migration events to JSONL")
    p.add_argument("--out",type=Path,default=Path("data/solana_events.jsonl"))
    p.add_argument("--seconds",type=float,default=0,help="0 means run until interrupted")
    p=sub.add_parser("inspect-mint",help="Read-only Solana RPC mint and top-account inspection")
    p.add_argument("--mint",required=True); p.add_argument("--out",type=Path)
    p=sub.add_parser("replay",help="Replay observations with fee-aware paper fills")
    p.add_argument("--file",type=Path,required=True); p.add_argument("--out",type=Path)
    p=sub.add_parser("wallets",help="Analyze normalized wallet trade history")
    p.add_argument("--file",type=Path,required=True); p.add_argument("--out",type=Path)
    p=sub.add_parser("dashboard",help="Generate static offline HTML")
    p.add_argument("--file",type=Path,required=True); p.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.cmd=="stream":
        asyncio.run(collect(args.out, stop_after=args.seconds or None)); return
    if args.cmd=="inspect-mint":
        data=SolanaRPC().inspect_mint(args.mint)
    elif args.cmd=="dashboard":
        data=json.loads(args.file.read_text(encoding="utf-8"))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(render_dashboard(data),encoding="utf-8")
        print(f"Wrote paper-only dashboard to {args.out}"); return
    elif args.cmd=="scan":
        data={"mode":"READ_ONLY","results":scan(args.limit),
              "notice":"DEX Screener profiles are not a complete launch feed; security is not verified."}
    elif args.cmd=="replay":
        engine=PaperEngine()
        for row in read_jsonl(args.file): engine.process(Snapshot.from_dict(row))
        data=engine.export()
    else:
        data={"mode":"WALLET_RESEARCH_ONLY","wallets":analyze_wallet_events(read_jsonl(args.file))}
    output=json.dumps(data,indent=2); print(output)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(output+"\n",encoding="utf-8")

if __name__=="__main__": main()
